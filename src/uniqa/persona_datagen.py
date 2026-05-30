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
                          widget_response_model)

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
_PARAM_LEVELS = [(0.2, "very low"), (0.4, "low"), (0.6, "moderate"), (0.8, "high"), (1.01, "very high")]
_PARAM_VERB = {"very low": "almost never", "low": "rarely", "moderate": "sometimes",
               "high": "often", "very high": "very often"}
_PARAM_TEXT = {
    "price_shock_s4": "First-price shock (S4): {lvl} — when the tariff price FIRST appears and it is above what you hoped, you {verb} leave right there (to think / compare / call) instead of continuing.",
    "complexity_overwhelm": "Complexity overwhelm: {lvl} — too many tariffs, jargon and no clear recommendation {verb} make you give up early (S3 or S4).",
    "final_price_sensitivity_s6": "Final-price sensitivity (S6): {lvl} — if the final price is higher than the estimate, you {verb} abandon at the very end.",
    "advisor_lean": "Advisor lean: {lvl} — you {verb} prefer to stop the online flow and deal with a real person instead.",
    "patience": "Patience: {lvl} — with LOW patience long forms {verb} exhaust you into leaving; with high patience they rarely do.",
    "online_completion": "Online-completion drive: {lvl} — you {verb} push all the way through and finish the purchase online.",
}


def _bucket(x: float) -> str:
    return next(lbl for thr, lbl in _PARAM_LEVELS if x < thr)


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
                 include_params: bool = False):
        self.include_quant = include_quant
        self.include_params = include_params
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


OpenAITeacher = LLMTeacher   # back-compat alias


def _strip_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[-1] if "\n" in s else s
        s = s.rsplit("```", 1)[0]
    return s.strip()


def default_teacher(model: str | None = None, include_quant: bool = False) -> Teacher:
    if os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY"):
        try:
            return LLMTeacher(model, include_quant=include_quant)
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
