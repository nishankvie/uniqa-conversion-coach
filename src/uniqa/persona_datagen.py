"""
Persona data-gen harness — the A1 probe (PERSONA_MODEL_PLAN §7 step 1).

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

_TRACK = Path("/tmp/zero_one_hack_01/tracks/insurance-uniqa")
_SEGMENT = {"judith": "segment_1", "franz": "segment_2", "peter": "segment_3"}

# in-scope steps that can bounce (skip START / PURCHASE terminal)
_BOUNCE_STEPS = [Step.PERSONAL_INFO, Step.TARIFF_SELECT, Step.ADDON_SELECT, Step.PERSONAL_DATA]


# ─── prompt assembly (used by the real teacher; tested for completeness) ──────

def _persona_json_fields(persona: str) -> dict:
    try:
        d = json.loads((_TRACK / "personas.json").read_text())
        s = d["personas"][_SEGMENT[persona]]
        return {
            "archetype": s.get("persona_archetype", {}),
            "online_funnel_behavior_hypotheses": s.get("online_funnel_behavior_hypotheses", {}),
            "pain_points": s.get("pain_points", {}),
        }
    except Exception:
        return {}


def build_step_prompt(persona: str, step: Step, atoms: list[dict] | None = None,
                      coach_reasoning: str = "") -> list[dict]:
    """Assemble the (system, user) messages a real LLM teacher receives."""
    brief = PERSONA_BRIEFINGS.get(persona)
    persona_md = brief.read_text(encoding="utf-8") if brief and brief.exists() else f"You are {persona}."
    sys = persona_md + "\n\nPERSONA FACTS (json):\n" + json.dumps(_persona_json_fields(persona), ensure_ascii=False)

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


# ─── schema gate ──────────────────────────────────────────────────────────────

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
    def next_events(self, persona: str, step: Step, mind, rng: random.Random) -> list[dict]: ...


class OfflineTeacher:
    """
    Deterministic stand-in. Uses psyche bounce + a per-persona BIAS to simulate a
    teacher that does NOT perfectly match psyche → non-trivial ε. NOT a real A1 number.
    """
    name = "offline-stub"

    def __init__(self, bias: float = 0.08):
        self.bias = bias   # additive shift on bounce propensity vs psyche

    def next_events(self, persona: str, step: Step, mind, rng: random.Random) -> list[dict]:
        ev = evaluate_bounce(mind, step, rng)
        # teacher disagrees with psyche by a controllable bias (the thing ε measures)
        p_bounce = min(1.0, max(0.0, (1.0 if ev.bounced else 0.0) * (1 - self.bias) + self.bias * rng.random()))
        evs = [{"type": "step_enter", "target": None, "value": None}]
        if step in (Step.TARIFF_SELECT, Step.PERSONAL_DATA):
            evs.append({"type": "price_hover", "target": "price", "value": 1})
        evs.append({"type": "idle", "target": None, "value": round(rng.uniform(2, 14), 1)})
        if rng.random() < p_bounce:
            evs.append({"type": "abandon", "target": None, "value": ev.reason.value})
        return evs


class OpenAITeacher:
    """Real LLM teacher (OpenAI-compatible). Used when OPENAI_API_KEY is set."""
    name = "openai-llm"

    def __init__(self, model: str = "gpt-4o-mini"):
        from openai import OpenAI  # lazy import
        self.client = OpenAI(base_url=os.getenv("OPENAI_BASE_URL") or None)
        self.model = model

    def next_events(self, persona: str, step: Step, mind, rng: random.Random) -> list[dict]:
        msgs = build_step_prompt(persona, step)
        resp = self.client.chat.completions.create(
            model=self.model, messages=msgs, temperature=0.9, max_tokens=300,
            response_format={"type": "json_object"},
        )
        try:
            data = json.loads(resp.choices[0].message.content)
            return data if isinstance(data, list) else data.get("events", [])
        except Exception:
            return []


def default_teacher() -> Teacher:
    if os.getenv("OPENAI_API_KEY"):
        try:
            return OpenAITeacher()
        except Exception:
            pass
    return OfflineTeacher()


# ─── feed generation (schema-gated) ───────────────────────────────────────────

def generate_feed(persona: str, teacher: Teacher, rng: random.Random) -> ActivityLog:
    """Drive one full session through the teacher, schema-gating each step."""
    log = ActivityLog(new_session_id())
    mind = init_mind(persona, rng)
    t = 0.0
    for step in STEP_ORDER[1:]:
        if step == Step.PURCHASE:
            log.append(Event(EventType.STEP_ENTER, step.value, t))
            log.append(Event(EventType.CONVERT, step.value, t + 0.2, value="online_purchase"))
            break
        step_dynamics(mind, step, rng)
        raw = teacher.next_events(persona, step, mind, rng)
        evs = parse_events(raw, step, t)            # ← schema gate
        if not evs:                                  # dropped feed → conservative continue
            evs = [Event(EventType.STEP_ENTER, step.value, t)]
        log.events.extend(evs)
        t = evs[-1].t + 0.5
        if any(e.type == EventType.ABANDON for e in evs):
            return log
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
    args = ap.parse_args()

    teacher = default_teacher()
    if isinstance(teacher, OfflineTeacher):
        teacher.bias = args.bias
    logs, stats = generate_batch(args.n, teacher, args.seed)
    eps = epsilon_teacher_vs_psyche(stats)

    print(f"\n=== A1 PROBE — teacher={stats.teacher} N={stats.n} ===")
    if stats.teacher == "offline-stub":
        print("⚠️  offline stub: ε validates the PIPELINE, not a real A1 estimate.")
        print("    Set OPENAI_API_KEY (+ OPENAI_BASE_URL) and re-run for the real number.")
    print(f"dropped feeds (no terminal): {stats.dropped_feeds}/{stats.n}")
    print(f"ε_teacher_vs_psyche (mean abs bounce diff): {eps['epsilon_mean_abs']}  over {eps['n_cells']} cells")
    for persona, cells in eps["per_cell"].items():
        print(f"  {persona}:")
        for sv, c in cells.items():
            print(f"    {sv:22s} teacher={c['teacher']:.2f}  psyche={c['psyche']:.2f}  Δ={c['abs_diff']:.2f}")
    print(f"\nGate (plan §7 step1): real-teacher ε ≤ ~0.05 → A1 live; large → fix prompt or use psyche-as-teacher.")
