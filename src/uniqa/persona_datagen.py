"""
Persona data-gen harness — the A1 probe (docs/deferred/PERSONA_MODEL_PLAN.md §7 step 1).

Goal: cheaply test assumption A1 (LLM-teacher feeds ≈ real user behaviour) BEFORE
any GPU. We:
  1. assemble the step prompt (persona.md + persona.json fields + json-render UI +
     ASCII low-res screen + intervention atoms + a 'Coach TLM reasoning' line),
  2. ask a TEACHER for the next user event(s) as contracts.Event JSON,
  3. SCHEMA-GATE every emitted event (drop non-parsing feeds),
  4. compute ε_teacher_vs_psyche = per-(persona,step) bounce-rate divergence
     between the teacher and the calibrated psyche engine.

Two teacher backends:
  • OpenAITeacher  — real LLM (needs OPENAI_API_KEY / OpenAI-compatible base_url).
  • OfflineTeacher — deterministic stand-in (psyche-derived + a controllable bias)
    so the whole pipeline + ε machinery runs NOW with no key. Its ε is
    PIPELINE-VALIDATION ONLY, not a real A1 estimate — clearly flagged in output.

Swap the backend, re-run, get the real A1 number.
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from uniqa.funnel import Step, STEP_ORDER, PERSONA_WEIGHTS, ABANDON_PROBS
from uniqa.contracts import Event, EventType, ActivityLog, new_session_id
from uniqa.personas import PERSONA_BRIEFINGS
from uniqa.journey import STEP_SCREENS, render_step
from uniqa.play import ascii_screen
from uniqa.psyche import init_mind, step_dynamics, evaluate_bounce
from uniqa.widget import (render_action_space, legal_events, STEP_ACTIONS,
                          widget_response_model, ux_complexity, TARIFFS)
from uniqa.scope import premium as _premium, Tariff as _Tariff

_STEP_BY_VALUE = {s.value: s for s in Step}


def _load_dotenv() -> None:
    """Best-effort .env loader (cwd then repo root) — populates os.environ."""
    here = Path(__file__).resolve()
    for d in [Path.cwd(), *here.parents]:
        f = d / ".env"
        if f.exists():
            for line in f.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
            return

_load_dotenv()

_TRACK = Path("/tmp/zero_one_hack_01/tracks/insurance-uniqa")
_SEGMENT = {"judith": "segment_1", "franz": "segment_2", "peter": "segment_3"}

# Agent-facing persona prompts are HAND-SCRUBBED, version-controlled files under
# prompts/personas/. They are the single editable source of the system prompt: the
# funnel churn/bounce/conversion TARGETS (S4~66%, S6~78%, ~5.6%, 30/50/20 mix) are
# removed by hand there, never by a runtime regex. Anchors stay only in funnel.py (eval).
_PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts" / "personas"


def agent_persona_prompt(persona: str) -> str:
    """The hand-scrubbed system prompt for a persona (prompts/personas/<persona>.md).

    Falls back to the raw briefing only if the scrubbed file is missing (so a missing
    file is loud in tests rather than silently leaking targets).
    """
    f = _PROMPT_DIR / f"{persona}.md"
    if f.exists():
        return f.read_text(encoding="utf-8")
    brief = PERSONA_BRIEFINGS.get(persona)
    return brief.read_text(encoding="utf-8") if brief and brief.exists() else f"You are {persona}."


# Curated, behaviour-only quantitative characteristics (population averages for people
# like this persona). ESCALATION lever: injected only when base prompt under-conforms.
# Deliberately EXCLUDES every funnel-outcome stat (no per-step bounce, no conversion
# rate, no 30/50/20 mix) — only persona-level propensities that should *shape*, not
# dictate, behaviour. Allowlist is explicit (no raw json dump).
_QUANT_ALLOW = {
    "online_behavior": ["ever_purchased_insurance_online_pct",
                        "likely_to_purchase_online_next_3y_pct"],
    "insurance_behavior": ["switch_willingness_pct", "net_promoter_score",
                           "general_attitude_positive_pct", "monthly_insurance_spend_eur"],
    "purchase_split_pct": ["summary_purchase_online", "summary_purchase_in_person"],
}


def quant_metrics_block(persona: str) -> str:
    """Compact text block of allowlisted behavioural metrics from personas.json."""
    try:
        d = json.loads((_TRACK / "personas.json").read_text())
        s = d["personas"][_SEGMENT[persona]]
    except Exception:
        return ""
    picked = {}
    for group, keys in _QUANT_ALLOW.items():
        g = s.get(group, {})
        for k in keys:
            if k in g:
                picked[k] = g[k]
    if not picked:
        return ""
    return ("\n\nBEHAVIOURAL TENDENCIES of people like you (population averages — general "
            "propensities, NOT a target for this one session):\n"
            + json.dumps(picked, ensure_ascii=False))

# in-scope steps that can bounce (skip START / PURCHASE terminal)
_BOUNCE_STEPS = [Step.PERSONAL_INFO, Step.TARIFF_SELECT, Step.ADDON_SELECT, Step.PERSONAL_DATA]


# ─── prompt assembly (used by the real teacher; tested for completeness) ──────

def build_step_prompt(persona: str, step: Step, atoms: list[dict] | None = None,
                      coach_reasoning: str = "") -> list[dict]:
    """Assemble the (system, user) messages a real LLM teacher receives."""
    sys = agent_persona_prompt(persona)

    ui_json = STEP_SCREENS.get(step, {"screen": step.value})
    workflow = {
        "instruction": (
            "You are this persona using the UNIQA online calculator. You are on the step "
            "shown below. Emit the next user event(s) as a JSON list of objects "
            '{"type": <event_type>, "target": <str|null>, "value": <num|bool|str|null>}. '
            "Allowed types: " + ", ".join(e.value for e in EventType) + ". "
            "End the session with exactly one terminal event: convert | abandon."
        ),
        "low_res_ui_ascii": ascii_screen(step),
        "json_render_static_ui": ui_json,
        "intervention_atoms": atoms or [],
        "coach_tlm_reasoning": coach_reasoning,
    }
    return [
        {"role": "system", "content": sys},
        {"role": "user", "content": json.dumps(workflow, ensure_ascii=False)},
    ]


# Parameter-driven persona dials (ITER 2). Behavioural traits in [0,1], stored in
# editable prompts/personas/<persona>.params.json. Rendered to GRADED LANGUAGE (never
# raw numbers, never a churn target) so the agent reasons with a 'pressure', not a quota.
# A tuning loop nudges these dials until the funnel stats EMERGE (research/run.py --params).
# Finer granularity (7 levels) so small dial nudges register in the prompt (codex P1).
_PARAM_LEVELS = [(0.15, "very low"), (0.3, "low"), (0.45, "somewhat low"), (0.6, "moderate"),
                 (0.75, "fairly high"), (0.9, "high"), (1.01, "very high")]
_PARAM_VERB = {"very low": "almost never", "low": "rarely", "somewhat low": "occasionally",
               "moderate": "sometimes", "fairly high": "fairly often", "high": "often",
               "very high": "very often"}
# FUNDAMENTAL human factors (not synthetic step-sensitivities). A real person has no innate
# 'price sensitivity at step 6'; price/commitment reactions EMERGE from these + the real price.
_PARAM_TEXT = {
    "budget_pressure": "Budget pressure: {lvl} — a monthly insurance premium {verb} feels like a real strain on your finances; when HIGH, a price at/above what you pictured hits hard.",
    "value_orientation": "Value scrutiny: {lvl} — you {verb} refuse to pay unless the price clearly matches coverage/value you actually understand; if the value isn't clear, the price feels too high.",
    "complexity_overwhelm": "Complexity overwhelm: {lvl} — too many tariffs, jargon and no clear recommendation {verb} make you give up early (S3 or S4).",
    "advisor_lean": "Advisor lean: {lvl} — you {verb} prefer to stop the online flow and deal with a real person instead.",
    "patience": "Patience: {lvl} — you {verb} stay patient through long forms; when this is LOW, long forms exhaust you into leaving.",
    "ux_willingness": "Willingness to push through heavy UI/UX: {lvl} — you {verb} push through heavy screens (many fields, jargon, many choices); when this is LOW, a heavy screen feels high-effort / low-reward and you subconsciously give up.",
    "comprehension": "Comprehension under load: {lvl} — on dense/jargon screens you {verb} actually absorb what you read; when this is LOW you may stare at the text without grasping it and drift off.",
    "distractibility": "Distractibility: {lvl} — real life (a phone notification, a message, family duties, your surroundings) {verb} pulls you away mid-step; if it does, you may not come back.",
    "commitment_anxiety": "Commitment anxiety: {lvl} — at the binding moment (entering personal + health data, about to actually buy) you {verb} hesitate, want to be sure, or step back to think / ask someone first.",
    "uncertainty_aversion": "Uncertainty aversion: {lvl} — an unknown (the price is only 'preliminary' and the binding premium is confirmed later, or an unclear next step) {verb} makes you uneasy enough to pause or leave.",
}


def _bucket(x: float) -> str:
    return next(lbl for thr, lbl in _PARAM_LEVELS if x < thr)


# The brain framing: the model is the persona's CONSCIOUSNESS. STATIC traits (dials) are
# fixed codified empirical values; DYNAMIC state evolves per step via the cognitive rules;
# the decision is a state-threshold crossing. (taxonomy: docs in research/PERSONA_PARAM_MODEL.md)
_CONSCIOUSNESS_PREAMBLE = (
    "\n\nYOU ARE THE CONSCIOUSNESS OF THIS PERSON. Simulate a real mind, not a form-filler.\n"
    "• Your BEHAVIOURAL DIALS above are FIXED dispositions (codified empirical values) — "
    "do not second-guess them; let them govern how strongly each pressure acts on you.\n"
    "• You also carry a MENTAL STATE (attention, satisfaction, effort_left, grasp, "
    "effort_vs_reward) that CHANGES as you move through the funnel.\n"
    "• At each step: perceive the screen, UPDATE your mental state per `cognitive_model`, "
    "then make a FELT decision — you leave when a state variable crosses your tolerance.")

_COGNITIVE_MODEL = {
    "state_update_rules": {
        "grasp": "starts high; on a high-complexity screen it falls toward your `comprehension` dial. Low comprehension × high complexity → you read without absorbing.",
        "effort_vs_reward": "falls on heavy screens; your `ux_willingness` sets how fast (low willingness → 'too much work for little').",
        "attention": "drifts down over time; your `distractibility` × `session_context` (mobile / commuting / busy surroundings) sets the chance an exogenous interruption knocks it down sharply.",
        "effort_left": "drains with every field and step; your `patience` sets the rate (low patience → drains fast → exhaustion).",
        "satisfaction": "rises when the screen matches `your_initial_intent`; falls on mismatch.",
    },
    "price_reaction_rule": (
        "You have NO innate 'price sensitivity'. When real prices appear (S4 shows "
        "`tariff_economics_for_your_age`: monthly, annual = monthly×12, and the yearly coverage "
        "limit per tariff), your reaction EMERGES: (a) compare the price to what you pictured "
        "(`session_instance.price_expectation`); (b) weigh how much it strains you (`budget_pressure`); "
        "(c) if you are value-minded (`value_orientation` × your `grasp`), do the FEASIBILITY math — "
        "annual cost vs the coverage limit vs how much private care you'd realistically use (a healthy "
        "person may judge the cheap plan poor value: paying a big fraction of a small limit you won't "
        "use up). A price above your picture, a budget strain, OR a worth-it calculation that fails "
        "pushes you toward leaving / wanting advice — otherwise it's fine."),
    "commitment_rule": (
        "S6 gives personal + HEALTH data, then shows the FINAL price/proposal. Real things here: "
        "(1) PRICE may JUMP — the `final_price` block shows provisional (S4) vs final; if your "
        "health answers added a ~6-10% loading the final is HIGHER, which triggers the SAME price "
        "reaction as S4 (above `price_expectation`, straining `budget_pressure`, failing your value "
        "math → you bail, especially if you hate surprises). (2) the form asks height/weight — if "
        "`session_instance.recalls_measurements` says you're unsure, that's friction (you guess, get "
        "annoyed, or stall). (3) the binding commitment itself: `commitment_anxiety` + "
        "`uncertainty_aversion` + drain (`effort_left`) + `advisor_lean`. UNIVERSAL TRUTH: finishing "
        "a health-insurance purchase online in one sitting is the EXCEPTION (insurance abandons ~84% "
        "of carts) — even decisive shoppers often stop to finish later or check with someone. If your "
        "`visit_goal` was to see the final price/proposal, you may read it here and leave CONTENT."),
    "decision_rule": (
        "Leave when a state variable crosses your tolerance, via the feeling that fired. Your "
        "`session_instance.visit_goal` (price-check vs research vs ready-to-buy) is your drive to "
        "push through — a price-checker leaves CONTENT once they see the number (goal_achieved). "
        "Weigh it against the leave pressures. Do NOT continue merely to see what's next."),
}


def params_block(persona: str) -> str:
    """Render the persona's behavioural dials as graded prompt language (no numbers)."""
    f = _PROMPT_DIR / f"{persona}.params.json"
    if not f.exists():
        return ""
    try:
        params = json.loads(f.read_text())
    except Exception:
        return ""
    lines = []
    for key, tmpl in _PARAM_TEXT.items():
        if key in params:
            lvl = _bucket(float(params[key]))
            lines.append("- " + tmpl.format(lvl=lvl.upper(), verb=_PARAM_VERB[lvl]))
    if not lines:
        return ""
    return ("\n\nBEHAVIOURAL DIALS — how strongly each pressure acts on you; let them govern "
            "your stay-or-leave choices at each step:\n" + "\n".join(lines))


# In-scope online flow we orchestrate step by step (S5 add-on is out of scope; PURCHASE
# is the terminal success after S6).
_INSCOPE_FLOW = [Step.COVERAGE_TYPE, Step.INSURED, Step.PERSONAL_INFO,
                 Step.TARIFF_SELECT, Step.PERSONAL_DATA]


def _real_prices_block(step: Step, disposition: dict | None) -> dict:
    """At the tariff step, show the REAL age-based monthly premium per tariff (recon curve),
    so the persona reacts to the actual number vs its expectation — no synthetic shock dial."""
    if step is not Step.TARIFF_SELECT or not disposition or "age" not in disposition:
        return {}
    age = disposition["age"]
    rows = {}
    for t in TARIFFS:
        try:
            m = _premium(_Tariff(t["id"]), age)
        except Exception:
            continue
        rows[t["id"]] = {"monthly_eur": m, "annual_eur": round(m * 12, 2),
                         "coverage_limit_eur_per_year": t["max_year"]}
    return {"tariff_economics_for_your_age": {"age": age, "tariffs": rows,
            "note": "annual_eur = monthly x 12; coverage_limit is the max the plan pays out per year. "
                    "A value-minded person weighs annual cost vs that limit vs how much private "
                    "care they'd realistically use."}}


def _final_price_block(disposition: dict | None, selected_tariff: str | None) -> dict:
    """At S6, after the health questions, the binding FINAL price may be ~6-10% higher than the
    S4 provisional if the health answers flag a risk loading. Show provisional vs final."""
    if not disposition or "age" not in disposition or not selected_tariff:
        return {}
    try:
        prov = _premium(_Tariff(selected_tariff), disposition["age"])
    except Exception:
        return {}
    sur = float(disposition.get("_health_surcharge_pct", 0) or 0)
    final = round(prov * (1 + sur / 100.0), 2)
    blk = {"provisional_eur_seen_at_s4": prov, "final_eur_after_health_questions": final,
           "increase_pct": round(sur, 1),
           "note": (f"Your health answers added a {round(sur,1)}% risk loading — the final price "
                    f"€{final} is HIGHER than the €{prov} you saw at S4.") if sur > 0
                   else f"No risk loading — the final price equals the €{prov} you saw at S4."}
    return {"final_price": blk}


def build_step_decision_prompt(persona: str, step: Step, history_brief: list[str],
                               state: dict, *, include_quant: bool = False,
                               include_params: bool = False,
                               include_state: bool = False,
                               session_context: dict | None = None,
                               intent: str | None = None,
                               disposition: dict | None = None,
                               selected_tariff: str | None = None) -> list[dict]:
    """One STEP-BASED turn: emit this step's events, (optionally) track state vars, and
    make an explicit felt stay/leave decision. Returns (system, user) messages."""
    sys = agent_persona_prompt(persona)
    if include_quant:
        sys += quant_metrics_block(persona)
    if include_params:
        sys += params_block(persona)
    if include_state:
        sys += _CONSCIOUSNESS_PREAMBLE
        if disposition:
            sys += ("\n\nTODAY'S SESSION INSTANCE (who this individual is RIGHT NOW — this "
                    "OVERRIDES the segment profile whenever they conflict):\n"
                    + json.dumps(disposition, ensure_ascii=False))

    wrm = widget_response_model()
    first = not history_brief
    out_schema = {
        "events": [{"step": step.value, "type": "<legal type>", "target": "<str|null>",
                    "value": "<num|bool|str|null>", "t": "<rel seconds on THIS step>",
                    "thought": "<short first-person>"}],
        "decision": "continue | leave",
        "reason": "<first-person why>",
    }
    rules = [
        "Emit ONLY what you do on THIS step (this step's events).",
        "Only use event types in action_space.legal_event_types.",
        "Respect widget_response_model: actions have the stated effects; hospital / other-persons / Opt.Plus / Premium hand off to an advisor (leave = online abandon, not a conversion).",
    ]
    if first:
        rules.append("This is your FIRST step: the first event's thought must set context "
                     "— who you are arriving as, what triggered this visit, what you expect.")
    rules.append("If a price appears (S4 select, or the S6 final price), voice EXPECTATION "
                 "vs REALITY in the thought, then decide.")
    if include_state:
        out_schema["state"] = {"attention": "0..1", "satisfaction": "0..1",
                               "effort_left": "0..1", "grasp": "0..1 (how much you actually understood this screen)",
                               "effort_vs_reward": "0..1 (1 = feels worth it, 0 = lots of work for little)"}
        out_schema["feeling"] = "engaged | distracted | cant_grasp | too_much_effort | dissatisfied | goal_achieved"
        if first:
            out_schema["intent"] = "<what info/outcome you came here to reach>"
        rules += [
            "Weigh this screen's `ux_complexity_here` against your own willingness/comprehension "
            "and your `session_context` (device + surroundings), then set `feeling`:",
            "  • 'distracted' — an EXOGENOUS life interruption pulled you away: a notification, a "
            "message, family/household duty, or your surroundings (traffic, someone talking) if you "
            "are on mobile / commuting. You may emit idle/tab_blur and then LEAVE (didn't come back).",
            "  • 'cant_grasp' — SUBCONSCIOUS: the screen is heavy and you are looking at the text "
            "without actually absorbing it (low grasp × high complexity) — you quietly drift off.",
            "  • 'too_much_effort' — SUBCONSCIOUS: the screen feels high-effort for low reward; you "
            "refuse to continue without consciously articulating why.",
            "  • 'dissatisfied' — CONSCIOUS: the screen contradicts or undershoots what you came for "
            "(`your_initial_intent`) — price higher than hoped, 'advisory required' when you wanted "
            "online, unexpected/contradicting info — and you decide to close it.",
            "  • 'goal_achieved' — INTENT-DRIVEN (not friction): if your `visit_goal` was to CHECK / "
            "COMPARE the price or to SEE THE FINAL PRICE/PROPOSAL (not buy today), then once you have "
            "seen the number you came for (the S4 price, or the S6 final price/proposal) you leave "
            "CONTENT — you got what you came for. A calm, satisfied exit, not frustration.",
            "  • 'engaged' — it delivers what you expected; continue.",
            "If `session_instance.familiarity` says you have been here before, you input data "
            "MECHANICALLY and fast (low dwell, skip reading/tooltips) and beeline to the price.",
            "Update `state` honestly: attention/satisfaction/effort_left/grasp/effort_vs_reward DROP on "
            "heavy screens and as the journey wears on; carry them forward from your_running_state.",
            "Judge the screen against `your_initial_intent`: a mismatch raises your urge to leave.",
            "Let your feeling + state drive the decision — do NOT continue just to see what's next.",
        ]
        if first:
            rules.append("Set `intent` on this first step: the information/outcome you actually came for.")
    user = {
        "you_are_on": step.value,
        "ui_ascii": ascii_screen(step),
        "action_space": render_action_space(step),
        "ux_complexity_here": ux_complexity(step),
        **(_real_prices_block(step, disposition) if include_state else {}),
        **(_final_price_block(disposition, selected_tariff) if include_state and step is Step.PERSONAL_DATA else {}),
        **({"cognitive_model": _COGNITIVE_MODEL} if include_state else {}),
        "widget_responses_here": wrm["transitions"].get(step.value, {}),
        "conversion_definition": wrm["conversion_definition"],
        "your_running_state": state,
        "history_brief": history_brief,
        "output_schema": out_schema,
        "rules": rules,
    }
    if session_context:
        user["session_context"] = session_context
    if disposition:
        user["session_instance"] = {k: v for k, v in disposition.items() if not k.startswith("_")}
    if intent:
        user["your_initial_intent"] = intent
    return [{"role": "system", "content": sys},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)}]


def build_session_prompt(persona: str, include_quant: bool = False,
                         include_params: bool = False) -> list[dict]:
    """
    WHOLE-SESSION prompt: one call → the entire journey as timestamped events with
    per-event motivation. Cheaper + more coherent than per-step prompting, and lets
    the model reason about pacing (reactive vs engaged vs distracted) across steps.

    include_quant: escalation lever — append allowlisted behavioural metrics (no
    funnel-outcome stats) when the base prompt under-conforms to the anchors.
    """
    sys = agent_persona_prompt(persona)
    if include_quant:
        sys += quant_metrics_block(persona)
    if include_params:
        sys += params_block(persona)
    widget = {s.value: {"ui_ascii": ascii_screen(s), "action_space": render_action_space(s)}
              for s in STEP_ACTIONS}
    instruction = {
        "task": (
            "You are this persona going through the UNIQA online health-insurance "
            "calculator end to end. Produce the WHOLE realistic session as a JSON object "
            '{"events":[ ... ]}. Each event: '
            '{"step": <step id>, "type": <event_type>, "target": <str|null>, '
            '"value": <num|bool|str|null>, "t": <seconds since start, absolute & increasing>, '
            '"thought": <short first-person motivation>}. '
            "Behave exactly as THIS persona would — do not aim for any particular outcome; "
            "let convert-or-abandon fall out of how the journey actually feels to you."
        ),
        "rules": [
            "Only use action atoms / event types legal for that step (see action_space.legal_event_types).",
            "Use keystroke events (value = #keystrokes) and tap events (value = #taps) to reflect REAL UX effort of filling fields — long forms cost more and frustrate impatient personas.",
            "On the tariff step, select_tariff reveals a price (emit price_reveal); clicking opt_plus/premium is a premium_click (advisory-only).",
            "Timestamps matter: small gaps = reactive/engaged, large idle/session_gap = distracted. Pace the session like THIS persona really would.",
            "Respect widget_response_model: each action has the stated effect. Bei Arztbesuchen + Ich selbst + Start/Optimal is the only online-completable path; hospital, other-persons, Opt.Plus/Premium hand off to an advisor (= online abandon, not a conversion).",
            "At EACH step make an explicit stay-or-leave decision — ESPECIALLY the moment the FIRST tariff price appears (S4) and at the final price (S6). Do NOT default to continuing just to see what happens next; many real sessions end at the first price screen.",
            "THOUGHTS carry your reasoning. The FIRST event's thought must set context: who is arriving, what triggered this visit, and what you expect/want from the session.",
            "At every price_reveal, the thought must voice EXPECTATION vs REALITY (e.g. 'hoped for ~60, 68 is ok' / 'estimate said 68, now 71 — annoying').",
            "If you abandon, the thought may reveal the gap between your STATED and REAL reason (you might 'just think about it' while the real driver is something specific).",
            "End with exactly one terminal event: convert (online purchase) or abandon (with a value naming why).",
        ],
        "widget_response_model": widget_response_model(),
        "widget": widget,
    }
    return [
        {"role": "system", "content": sys},
        {"role": "user", "content": json.dumps(instruction, ensure_ascii=False)},
    ]


# ─── schema gate ──────────────────────────────────────────────────────────────

def parse_session(raw: str | dict) -> list[Event]:
    """
    Schema-gate a WHOLE-session payload → contracts.Event list with absolute t +
    thought. Drops events whose type is unknown or illegal for their step. Sorts by t.
    """
    try:
        data = raw if isinstance(raw, (dict, list)) else json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    items = data.get("events", []) if isinstance(data, dict) else data
    if not isinstance(items, list):
        return []
    out: list[Event] = []
    last_t = 0.0
    for it in items:
        if not isinstance(it, dict) or "type" not in it:
            continue
        step = _STEP_BY_VALUE.get(it.get("step"))
        if step is None:
            continue
        try:
            et = EventType(it["type"])
        except (ValueError, KeyError):
            continue
        if et.value not in legal_events(step):
            continue
        try:
            t = float(it.get("t", last_t))
        except (TypeError, ValueError):
            t = last_t
        last_t = t
        out.append(Event(et, step.value, t, target=it.get("target"),
                         value=it.get("value"), thought=it.get("thought")))
    out.sort(key=lambda e: e.t)
    return out


def parse_events(raw: str | list, step: Step, t: float) -> list[Event]:
    """
    Schema gate: parse teacher output (JSON string or list) into contracts.Event.
    Drops any malformed entry. Returns [] if nothing valid.
    """
    try:
        items = raw if isinstance(raw, list) else json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    out: list[Event] = []
    for i, it in enumerate(items if isinstance(items, list) else []):
        if not isinstance(it, dict) or "type" not in it:
            continue
        try:
            et = EventType(it["type"])
        except (ValueError, KeyError):
            continue
        out.append(Event(et, step.value, t + i * 0.5,
                         target=it.get("target"), value=it.get("value")))
    return out


# ─── teacher backends ─────────────────────────────────────────────────────────

class Teacher(Protocol):
    name: str
    def session(self, persona: str, rng: random.Random) -> list[dict]: ...   # whole-session events


class OfflineTeacher:
    """
    Deterministic stand-in. Uses psyche bounce + a per-persona BIAS to simulate a
    teacher that does NOT perfectly match psyche → non-trivial ε. NOT a real A1 number.
    """
    name = "offline-stub"

    def __init__(self, bias: float = 0.08):
        self.bias = bias

    def session(self, persona: str, rng: random.Random) -> list[dict]:
        """Build a whole timestamped session with thoughts + UX-cost events."""
        mind = init_mind(persona, rng)
        evs: list[dict] = []
        t = 0.0
        for step in STEP_ORDER[1:]:
            if step == Step.PURCHASE:
                evs.append({"step": step.value, "type": "step_enter", "t": round(t, 1)})
                evs.append({"step": step.value, "type": "convert", "value": "online_purchase",
                            "t": round(t + 0.5, 1), "thought": "done, that was painless"})
                break
            step_dynamics(mind, step, rng)
            evs.append({"step": step.value, "type": "step_enter", "t": round(t, 1)}); t += rng.uniform(0.5, 2)
            if step == Step.PERSONAL_INFO:
                evs.append({"step": step.value, "type": "keystroke", "target": "date_of_birth",
                            "value": 8, "t": round(t, 1), "thought": "typing my birthday"}); t += rng.uniform(2, 6)
                evs.append({"step": step.value, "type": "dropdown_open", "target": "sv_number", "t": round(t, 1)}); t += 1
                evs.append({"step": step.value, "type": "select", "target": "sv_number",
                            "value": "ÖGK", "t": round(t, 1)}); t += rng.uniform(1, 3)
            elif step == Step.TARIFF_SELECT:
                evs.append({"step": step.value, "type": "select", "target": "optimal",
                            "value": "optimal", "t": round(t, 1), "thought": "optimal looks right"}); t += 1
                evs.append({"step": step.value, "type": "price_reveal", "target": "optimal",
                            "value": 68.14, "t": round(t, 1)}); t += rng.uniform(2, 10)
            elif step == Step.PERSONAL_DATA:
                evs.append({"step": step.value, "type": "keystroke", "target": "email",
                            "value": 22, "t": round(t, 1)}); t += rng.uniform(3, 9)
            evs.append({"step": step.value, "type": "idle", "value": round(rng.uniform(2, 14), 1),
                        "t": round(t, 1)}); t += rng.uniform(2, 14)
            ev = evaluate_bounce(mind, step, rng)
            p_bounce = min(1.0, max(0.0, (1.0 if ev.bounced else 0.0) * (1 - self.bias) + self.bias * rng.random()))
            if rng.random() < p_bounce:
                evs.append({"step": step.value, "type": "abandon", "value": ev.reason.value,
                            "t": round(t, 1), "thought": "not now"})
                break
            t += rng.uniform(0.5, 2)
        return evs


class LLMTeacher:
    """
    Real LLM teacher over any OpenAI-compatible endpoint. Auto-selects provider:
      • OPENROUTER_API_KEY → OpenRouter (base https://openrouter.ai/api/v1)
      • else OPENAI_API_KEY → OpenAI (or OPENAI_BASE_URL)
    """
    name = "llm"

    def __init__(self, model: str | None = None, include_quant: bool = False,
                 include_params: bool = False, stepwise: bool = False,
                 include_state: bool = False):
        self.include_quant = include_quant
        self.include_params = include_params
        self.stepwise = stepwise
        self.include_state = include_state
        from openai import OpenAI  # lazy import
        if os.getenv("OPENROUTER_API_KEY"):
            self.client = OpenAI(base_url="https://openrouter.ai/api/v1",
                                 api_key=os.getenv("OPENROUTER_API_KEY"))
            self.model = model or os.getenv("TEACHER_MODEL", "openai/gpt-4o-mini")
            self.name = f"openrouter:{self.model}"
        else:
            self.client = OpenAI(base_url=os.getenv("OPENAI_BASE_URL") or None)
            self.model = model or os.getenv("TEACHER_MODEL", "gpt-4o-mini")
            self.name = f"openai:{self.model}"
        self._no_json_fmt = False

    def _call(self, msgs: list[dict]) -> str:
        kw = dict(model=self.model, messages=msgs, temperature=0.9, max_tokens=2000)
        if not self._no_json_fmt:
            try:
                r = self.client.chat.completions.create(
                    response_format={"type": "json_object"}, **kw)
                return r.choices[0].message.content or ""
            except Exception:
                self._no_json_fmt = True
        r = self.client.chat.completions.create(**kw)
        return r.choices[0].message.content or ""

    def session(self, persona: str, rng: random.Random) -> list[dict]:
        if self.stepwise:
            return self._session_stepwise(persona, rng)
        msgs = build_session_prompt(persona, include_quant=self.include_quant,
                                    include_params=self.include_params)
        try:
            content = _strip_fences(self._call(msgs))
            data = json.loads(content)
        except Exception:
            return []
        if isinstance(data, dict):
            return data.get("events", []) or []
        return data if isinstance(data, list) else []

    def _session_stepwise(self, persona: str, rng: random.Random) -> list[dict]:
        """Walk S1→S6 one LLM turn per step; each turn emits the step's events, tracks
        running state, and decides continue/leave. Returns raw events (parse_session gates)."""
        state = {"attention": 1.0, "satisfaction": 0.7, "effort_left": 1.0,
                 "grasp": 1.0, "effort_vs_reward": 0.7}
        ctx = _sample_session_context(persona, rng) if self.include_state else None
        disp = _sample_disposition(persona, rng) if self.include_state else None
        intent = None
        selected_tariff = None
        events: list[dict] = []
        brief: list[str] = []
        t = 0.0
        for step in _INSCOPE_FLOW:
            events.append({"step": step.value, "type": "step_enter", "t": round(t, 2)})
            msgs = build_step_decision_prompt(
                persona, step, brief[-6:], state,
                include_quant=self.include_quant, include_params=self.include_params,
                include_state=self.include_state, session_context=ctx, intent=intent,
                disposition=disp, selected_tariff=selected_tariff)
            try:
                out = json.loads(_strip_fences(self._call(msgs)))
            except Exception:
                out = {}
            t += rng.uniform(0.5, 2.0)
            step_evs = out.get("events") if isinstance(out, dict) else None
            done_here = []
            for ev in (step_evs or []):
                if not isinstance(ev, dict) or "type" not in ev:
                    continue
                ev["step"] = step.value
                try:
                    ev["t"] = t + float(ev.get("t", 0.0))
                except (TypeError, ValueError):
                    ev["t"] = t
                done_here.append(ev)
            if done_here:
                t = max(e["t"] for e in done_here)
                events.extend(done_here)
                tgt = [str(e.get("target")) for e in done_here if e.get("target")]
                brief.append(f"{step.value}: " + ", ".join(tgt[:4]) if tgt else f"{step.value}: (viewed)")
                if step is Step.TARIFF_SELECT:
                    for e in done_here:
                        if str(e.get("target") or "") in ("start", "optimal", "opt_plus", "premium"):
                            selected_tariff = str(e["target"]); break
            if isinstance(out.get("intent"), str) and not intent:
                intent = out["intent"]
            if self.include_state and isinstance(out.get("state"), dict):
                for k in ("attention", "satisfaction", "effort_left", "grasp", "effort_vs_reward"):
                    if isinstance(out["state"].get(k), (int, float)):
                        state[k] = float(out["state"][k])
            if str(out.get("decision", "")).lower() == "leave":
                reason = out.get("reason") or out.get("feeling") or "left"
                feeling = out.get("feeling")
                val = f"{feeling}:{reason}" if feeling and feeling != "engaged" else reason
                events.append({"step": step.value, "type": "abandon", "target": None,
                               "value": val, "t": t + 0.4, "thought": reason})
                return events
        events.append({"step": Step.PURCHASE.value, "type": "step_enter", "t": t + 0.5})
        events.append({"step": Step.PURCHASE.value, "type": "convert", "value": "online_purchase",
                       "t": t + 1.0, "thought": "done — finished it online"})
        return events


# Per-session context priors (device + surroundings) — contextual heterogeneity that
# modulates distraction & perceived UX heaviness. Persona-weighted, NOT a funnel target.
_DEVICE_W = {"judith": [("desktop", 0.6), ("mobile", 0.4)],
             "franz":  [("desktop", 0.55), ("mobile", 0.45)],
             "peter":  [("mobile", 0.65), ("desktop", 0.35)]}
_ENV_W = {"judith": [("home, evening, kids around", 0.55), ("at work, between tasks", 0.3), ("commuting", 0.15)],
          "franz":  [("home, focused", 0.5), ("at work, between tasks", 0.4), ("commuting", 0.1)],
          "peter":  [("commuting / on the move", 0.4), ("home, tired after shift", 0.4), ("on a work break", 0.2)]}


def _weighted(rng: random.Random, pairs: list[tuple[str, float]]) -> str:
    opts, w = [p[0] for p in pairs], [p[1] for p in pairs]
    return rng.choices(opts, weights=w, k=1)[0]


def _sample_session_context(persona: str, rng: random.Random) -> dict:
    device = _weighted(rng, _DEVICE_W.get(persona, [("desktop", 1.0)]))
    env = _weighted(rng, _ENV_W.get(persona, [("home", 1.0)]))
    return {"device": device, "surroundings": env}


# Per-session LATENT DISPOSITION (codex P1): this individual TODAY. Sampled uniformly per
# axis → population spread that breaks the deterministic 'narrative lock' of the persona
# prose. It is heterogeneity, NOT a funnel target. Instance overrides the segment prior on
# conflict, so e.g. a 'just curious / expects cheap' Judith bounces at S4 while an
# 'urgent / prepared-for-premium / can-proceed-alone' Judith converts.
_INSTANCE_AXES = {
    "time_pressure": ["calm, has time", "mildly busy", "interrupted / rushed"],
    "visit_goal": ["just checking / comparing the S4 price (NOT buying today)",
                   "click all the way through to see the FINAL price + proposal (then decide; likely not buying now)",
                   "researching, might buy if it fits",
                   "seriously considering buying now",
                   "urgent need, ready to buy"],
    "familiarity": ["first time on this calculator",
                    "been here before — knows the steps, inputs mechanically"],
    "price_expectation": ["expects it to be cheap", "flexible on price", "prepared for a premium price"],
    "advisor_need_today": ["wants human reassurance before committing", "happy to proceed alone today"],
    "screening_confidence": ["comfortable with forms/health questions", "a bit uncertain", "anxious about it"],
}


# Persona-weighted disposition priors: spread WITHIN a persona, but keep each persona's
# defining sensitivity (e.g. Franz almost never 'prepared for premium' — he is price-jump
# sensitive; Peter mostly anxious + wants reassurance). Axes not listed default to uniform.
_DISP_W = {
    "judith": {
        "advisor_need_today": [("wants human reassurance before committing", .65), ("happy to proceed alone today", .35)],
        "price_expectation": [("expects it to be cheap", .2), ("flexible on price", .6), ("prepared for a premium price", .2)],
        "time_pressure": [("calm, has time", .3), ("mildly busy", .45), ("interrupted / rushed", .25)],
        "visit_goal": [("just checking / comparing the price (NOT buying today)", .35), ("researching, might buy if it fits", .35), ("seriously considering buying now", .2), ("urgent need, ready to buy", .1)],
        "familiarity": [("first time on this calculator", .6), ("been here before — knows the steps, inputs mechanically", .4)],
    },
    "franz": {
        "advisor_need_today": [("happy to proceed alone today", .9), ("wants human reassurance before committing", .1)],
        "price_expectation": [("expects it to be cheap", .45), ("flexible on price", .5), ("prepared for a premium price", .05)],
        "visit_goal": [("just checking / comparing the price (NOT buying today)", .35), ("researching, might buy if it fits", .25), ("seriously considering buying now", .25), ("urgent need, ready to buy", .15)],
        "familiarity": [("first time on this calculator", .5), ("been here before — knows the steps, inputs mechanically", .5)],
        "screening_confidence": [("comfortable with forms/health questions", .7), ("a bit uncertain", .25), ("anxious about it", .05)],
    },
    "peter": {
        "advisor_need_today": [("wants human reassurance before committing", .8), ("happy to proceed alone today", .2)],
        "screening_confidence": [("comfortable with forms/health questions", .1), ("a bit uncertain", .4), ("anxious about it", .5)],
        "price_expectation": [("expects it to be cheap", .55), ("flexible on price", .4), ("prepared for a premium price", .05)],
        "visit_goal": [("just checking / comparing the price (NOT buying today)", .3), ("researching, might buy if it fits", .35), ("seriously considering buying now", .25), ("urgent need, ready to buy", .1)],
        "familiarity": [("first time on this calculator", .7), ("been here before — knows the steps, inputs mechanically", .3)],
    },
}


# Persona-anchored age (drives the REAL price via scope.premium). Judith~43, Franz~40,
# Peter~35, with realistic spread; clamped to the calculator's 19–72 working range.
_AGE_ANCHOR = {"judith": 43, "franz": 40, "peter": 35}


# Fraction of sessions where the health answers trigger a real risk loading on the FINAL
# (binding) price — a ~6-10% increase shown at S6 after the questionnaire (CDP recon: the
# pre-health displayed price is age+tariff only, but the binding /calculate can load risk).
_HEALTH_LOADING_RATE = {"judith": 0.45, "franz": 0.40, "peter": 0.50}


def _sample_disposition(persona: str, rng: random.Random) -> dict:
    w = _DISP_W.get(persona, {})
    out = {}
    for axis, opts in _INSTANCE_AXES.items():
        out[axis] = _weighted(rng, w[axis]) if axis in w else rng.choice(opts)
    out["age"] = max(19, min(72, round(_AGE_ANCHOR.get(persona, 40) + rng.gauss(0, 9))))
    out["recalls_measurements"] = _weighted(rng, [("knows their height/weight", .7),
                                                  ("not sure of their exact height/weight", .3)])
    rate = _HEALTH_LOADING_RATE.get(persona, 0.45)
    out["_health_surcharge_pct"] = round(rng.uniform(6, 10), 1) if rng.random() < rate else 0
    return out


OpenAITeacher = LLMTeacher   # back-compat alias


def _strip_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[-1] if "\n" in s else s
        s = s.rsplit("```", 1)[0]
    return s.strip()


def default_teacher(model: str | None = None, include_quant: bool = False,
                    include_params: bool = False, stepwise: bool = False,
                    include_state: bool = False) -> Teacher:
    if os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY"):
        try:
            return LLMTeacher(model, include_quant=include_quant, include_params=include_params,
                              stepwise=stepwise, include_state=include_state)
        except Exception:
            pass
    return OfflineTeacher()


# ─── feed generation (schema-gated) ───────────────────────────────────────────

def generate_feed(persona: str, teacher: Teacher, rng: random.Random) -> ActivityLog:
    """One whole-session teacher call → schema-gated ActivityLog (timestamps + thoughts)."""
    log = ActivityLog(new_session_id())
    raw = teacher.session(persona, rng)
    evs = parse_session(raw)                         # ← per-step action-space schema gate
    if not evs:
        evs = [Event(EventType.STEP_ENTER, Step.COVERAGE_TYPE.value, 0.0)]
    cut = len(evs)
    for i, e in enumerate(evs):
        if e.type in (EventType.CONVERT, EventType.ABANDON):
            cut = i + 1; break
    log.events = evs[:cut]
    return log


@dataclass
class BatchStats:
    n: int
    teacher: str
    dropped_feeds: int
    per_step_bounce: dict[str, dict[str, float]]   # persona → {step: cond bounce}


def generate_batch(n: int, teacher: Teacher, seed: int = 0) -> tuple[list[ActivityLog], BatchStats]:
    rng = random.Random(seed)
    plist, pw = list(PERSONA_WEIGHTS), list(PERSONA_WEIGHTS.values())
    logs, by_persona = [], {p: [] for p in plist}
    dropped = 0
    for _ in range(n):
        persona = rng.choices(plist, weights=pw, k=1)[0]
        log = generate_feed(persona, teacher, rng)
        if not any(e.type in (EventType.ABANDON, EventType.CONVERT) for e in log.events):
            dropped += 1
        logs.append(log); by_persona[persona].append(log)
    return logs, BatchStats(n, teacher.name, dropped, _per_step_bounce(by_persona))


def _per_step_bounce(by_persona: dict[str, list[ActivityLog]]) -> dict[str, dict[str, float]]:
    out = {}
    for persona, logs in by_persona.items():
        reach, bounce = {}, {}
        for log in logs:
            seen, bstep = set(), None
            for e in log.events:
                if e.type == EventType.STEP_ENTER and e.step not in seen:
                    reach[e.step] = reach.get(e.step, 0) + 1; seen.add(e.step)
                if e.type == EventType.ABANDON:
                    bstep = e.step
            if bstep:
                bounce[bstep] = bounce.get(bstep, 0) + 1
        out[persona] = {s.value: bounce.get(s.value, 0) / reach[s.value]
                        for s in _BOUNCE_STEPS if reach.get(s.value)}
    return out


# ─── ε_teacher_vs_psyche ──────────────────────────────────────────────────────

def psyche_reference() -> dict[str, dict[str, float]]:
    """Per-(persona,step) conditional bounce from the calibrated psyche tables."""
    return {p: {s.value: ABANDON_PROBS[p].get(s, 0.0) for s in _BOUNCE_STEPS} for p in ABANDON_PROBS}


def epsilon_teacher_vs_psyche(teacher_stats: BatchStats) -> dict:
    """Mean abs difference of per-(persona,step) conditional bounce. TV-like scalar."""
    ref = psyche_reference()
    diffs, table = [], {}
    for persona, steps in teacher_stats.per_step_bounce.items():
        table[persona] = {}
        for sv, rate in steps.items():
            step = next((s for s in _BOUNCE_STEPS if s.value == sv), None)
            r = ref.get(persona, {}).get(sv, 0.0)
            d = abs(rate - r)
            table[persona][sv] = {"teacher": round(rate, 3), "psyche": round(r, 3), "abs_diff": round(d, 3)}
            diffs.append(d)
    eps = round(sum(diffs) / len(diffs), 4) if diffs else 0.0
    return {"epsilon_mean_abs": eps, "n_cells": len(diffs), "per_cell": table}


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="A1 probe: ε_teacher_vs_psyche")
    ap.add_argument("-n", type=int, default=300)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--bias", type=float, default=0.08, help="offline-teacher disagreement")
    ap.add_argument("--model", default=None, help="teacher model (e.g. openai/gpt-4o-mini)")
    ap.add_argument("--offline", action="store_true", help="force offline stub")
    args = ap.parse_args()

    teacher = OfflineTeacher(args.bias) if args.offline else default_teacher(args.model)
    logs, stats = generate_batch(args.n, teacher, args.seed)
    eps = epsilon_teacher_vs_psyche(stats)

    print(f"\n=== A1 PROBE — teacher={stats.teacher} N={stats.n} ===")
    if stats.teacher.startswith("offline"):
        print("⚠️  offline stub: ε validates the PIPELINE, not a real A1 estimate.")
        print("    Set OPENROUTER_API_KEY (or OPENAI_API_KEY) and re-run for the real number.")
    print(f"dropped feeds (no terminal): {stats.dropped_feeds}/{stats.n}")
    print(f"ε_teacher_vs_psyche (mean abs bounce diff): {eps['epsilon_mean_abs']}  over {eps['n_cells']} cells")
    for persona, cells in eps["per_cell"].items():
        print(f"  {persona}:")
        for sv, c in cells.items():
            print(f"    {sv:22s} teacher={c['teacher']:.2f}  psyche={c['psyche']:.2f}  Δ={c['abs_diff']:.2f}")
    print(f"\nGate (plan §7 step1): real-teacher ε ≤ ~0.05 → A1 live; large → fix prompt or use psyche-as-teacher.")
