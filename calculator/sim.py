"""
Session simulator — the orchestrator that runs persona ↔ widget ↔ (coach).

Two flows, one engine:

  FLOW A  persona ↔ widget            (no coach)
     The whole session is determined up front → if the persona backend supports
     it, generate it in ONE shot (fast path). Otherwise fall back to the turn loop.

  FLOW B  persona ↔ widget ↔ coach
     The coach is a live third participant. A session can only be generated up to
     the FIRST coach intervention; then the persona must REACT, which may change
     everything downstream. So Flow B is a multi-step (turn-based) simulation.

```
  FLOW A (one-shot)                     FLOW B (turn-based, per step)
  ───────────────────                   ──────────────────────────────────────────
  persona.whole_session() ─▶ log        for step in funnel:
                                          persona.step()      → within-step signals
                                          widget.observe()    → CoachObservation
                                          coach.decide()      → CoachDecision
                                          widget.apply(d)     → inject coach events
                                          persona.resolve(d)  → react: advance|abandon
                                          (stop at terminal)
```

The three roles are PROTOCOLS — any backend implements them: static (psyche),
LLM-prompted, a trained TLM, or something not even transformer-based. The
orchestrator never knows which.
"""

from __future__ import annotations

import random
from typing import Optional, Protocol, runtime_checkable

from calculator.funnel import Step, STEP_ORDER, generate_signals
from calculator.contracts import Event, EventType, ActivityLog, CoachObservation, CoachDecision, new_session_id
from coach.coach_io import activity_from_signals, observation_from_log
from persona.psyche import init_mind, step_dynamics, evaluate_bounce, apply_coach_effect
from calculator.widget import legal_events, tariff_by_id
from coach.coach import MESSAGE_BUDGET

_BOUNCE_STEPS = [Step.PERSONAL_INFO, Step.TARIFF_SELECT, Step.ADDON_SELECT, Step.PERSONAL_DATA]


# ════════════════════════════════════════════════════════════════════════════
#  ROLE INTERFACES (any backend: static / LLM / TLM / other)
# ════════════════════════════════════════════════════════════════════════════

@runtime_checkable
class PersonaModel(Protocol):
    can_whole_session: bool
    def reset(self, persona: str, rng: random.Random) -> None: ...
    def whole_session(self, rng: random.Random) -> list[Event]: ...               # Flow A fast path
    def step(self, step: Step, history: list[Event], t: float, rng: random.Random) -> list[Event]: ...
    def resolve(self, step: Step, history: list[Event], coach: Optional[CoachDecision],
                t: float, rng: random.Random) -> tuple[str, list[Event]]: ...      # ("advance"|"abandon"|"convert", events)


@runtime_checkable
class WidgetModel(Protocol):
    def observe(self, step: Step, history: list[Event], budget: int) -> CoachObservation: ...
    def apply(self, decision: CoachDecision, step: Step, history: list[Event], t: float) -> list[Event]: ...


@runtime_checkable
class CoachModel(Protocol):
    def decide(self, obs: CoachObservation) -> CoachDecision: ...


# ════════════════════════════════════════════════════════════════════════════
#  WIDGET (immutable app twin) — default implementation
# ════════════════════════════════════════════════════════════════════════════

class WidgetTwin:
    """Observes history into a CoachObservation; executes effector commands into app events."""

    def observe(self, step: Step, history: list[Event], budget: int) -> CoachObservation:
        log = ActivityLog("obs"); log.events = list(history)
        return observation_from_log(log, step, budget_remaining=budget)

    def apply(self, decision: CoachDecision, step: Step, history: list[Event], t: float) -> list[Event]:
        cmd = decision.command
        cmd.validate()                                   # guardrails regardless of policy
        ev = Event(EventType.WIDGET_SHOWN, step.value, t,
                   target=cmd.payload.get("intent") or cmd.effector.value,
                   value=cmd.effector.value, source="coach",
                   thought=decision.reasoning[:80])
        return [ev]


# ════════════════════════════════════════════════════════════════════════════
#  PERSONA backends
# ════════════════════════════════════════════════════════════════════════════

class PsychePersona:
    """Static backend: latent-Mind psyche. Supports BOTH flows, no API, deterministic."""
    can_whole_session = True

    def __init__(self):
        self.persona = "judith"
        self.mind = None

    def reset(self, persona: str, rng: random.Random) -> None:
        self.persona = persona
        self.mind = init_mind(persona, rng)

    def whole_session(self, rng: random.Random) -> list[Event]:
        log = ActivityLog("ws"); t = 0.0
        for step in STEP_ORDER[1:]:
            if step == Step.PURCHASE:
                log.append(Event(EventType.STEP_ENTER, step.value, t))
                log.append(Event(EventType.CONVERT, step.value, t + 0.2, value="online_purchase"))
                break
            log.append(Event(EventType.STEP_ENTER, step.value, t)); t += 0.3
            evs = self.step(step, log.events, t, rng); log.events += evs
            t = (evs[-1].t if evs else t) + 0.5
            outcome, react = self.resolve(step, log.events, None, t, rng)
            log.events += react
            if outcome == "abandon":
                break
            t = (react[-1].t if react else t) + 0.5
        return log.events

    def step(self, step: Step, history: list[Event], t: float, rng: random.Random) -> list[Event]:
        step_dynamics(self.mind, step, rng)
        sig = generate_signals(step, self.persona, rng)
        tmp = ActivityLog("s")
        activity_from_signals(tmp, step, sig, t0=t)
        # orchestrator / whole_session owns STEP_ENTER; return signals only
        return [e for e in tmp.events if e.type is not EventType.STEP_ENTER]

    def resolve(self, step: Step, history: list[Event], coach: Optional[CoachDecision],
                t: float, rng: random.Random) -> tuple[str, list[Event]]:
        # coach intervention acts on the MIND, then we re-roll bounce (honest)
        if coach is not None and coach.is_action():
            intent = coach.command.payload.get("intent")
            if intent:
                apply_coach_effect(self.mind, intent, step)
        ev = evaluate_bounce(self.mind, step, rng)
        if ev.bounced:
            return "abandon", [Event(EventType.ABANDON, step.value, t, value=ev.reason.value,
                                     thought=f"bounce:{ev.reason.value}")]
        return "advance", []


class LLMPersona:
    """
    LLM backend. Flow A = one whole-session call (persona_datagen teacher). Flow B
    turn methods delegate to the same teacher per-step (functional; costs API calls).
    """
    can_whole_session = True

    def __init__(self, model: str | None = None):
        from persona.persona_datagen import LLMTeacher, parse_session
        self._teacher = LLMTeacher(model)
        self._parse = parse_session
        self.persona = "judith"

    def reset(self, persona: str, rng: random.Random) -> None:
        self.persona = persona

    def whole_session(self, rng: random.Random) -> list[Event]:
        return self._parse(self._teacher.session(self.persona, rng))

    # Turn-mode for Flow B: fall back to psyche dynamics for stepping/resolving but
    # keep the LLM for whole-session realism. (A full per-step LLM react loop is a
    # drop-in here; left as the v1 upgrade to avoid burning API in the hot loop.)
    def step(self, step, history, t, rng):
        return _PSYCHE_FALLBACK.step(step, history, t, rng)

    def resolve(self, step, history, coach, t, rng):
        return _PSYCHE_FALLBACK.resolve(step, history, coach, t, rng)


_PSYCHE_FALLBACK = PsychePersona()


# ════════════════════════════════════════════════════════════════════════════
#  ORCHESTRATOR
# ════════════════════════════════════════════════════════════════════════════

def simulate(persona: PersonaModel, widget: WidgetModel, coach: Optional[CoachModel] = None,
             persona_name: str = "judith", rng: Optional[random.Random] = None,
             budget: int = MESSAGE_BUDGET) -> ActivityLog:
    """
    Run one session. coach=None → Flow A (one-shot if supported); coach set → Flow B
    (turn-based, persona reacts to each intervention). Returns a schema-valid ActivityLog.
    """
    rng = rng or random.Random(0)
    persona.reset(persona_name, rng)
    log = ActivityLog(new_session_id())

    # FLOW A fast path: no coach + whole-session-capable backend
    if coach is None and getattr(persona, "can_whole_session", False):
        log.events = persona.whole_session(rng)
        return log

    # TURN-BASED (Flow B, or Flow A without a whole-session backend)
    t = 0.0
    _PSYCHE_FALLBACK.reset(persona_name, rng)   # keep fallback aligned if used
    for step in STEP_ORDER[1:]:
        if step == Step.PURCHASE:
            log.append(Event(EventType.STEP_ENTER, step.value, t))
            log.append(Event(EventType.CONVERT, step.value, t + 0.2, value="online_purchase"))
            break
        log.append(Event(EventType.STEP_ENTER, step.value, t)); t += 0.3

        # 1) persona behaves within the step (up to the coach decision point)
        within = persona.step(step, log.events, t, rng)
        log.events += within
        t = (within[-1].t if within else t) + 0.3

        # 2) coach is consulted once per step (Flow B only)
        decision: Optional[CoachDecision] = None
        if coach is not None and budget > 0:
            obs = widget.observe(step, log.events, budget)
            d = coach.decide(obs)
            if d.is_action():
                log.events += widget.apply(d, step, log.events, t)   # inject coach event(s)
                t += 0.5
                budget -= 1
                decision = d                                          # persona must REACT to this

        # 3) persona resolves the step (reacting to the coach if it acted)
        outcome, react = persona.resolve(step, log.events, decision, t, rng)
        log.events += react
        t = (react[-1].t if react else t) + 0.5
        if outcome == "abandon":
            break
    return log


# ─── CLI demo ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from coach.coach_io import RuleCoachModel
    rng = random.Random(7)
    w, coach = WidgetTwin(), RuleCoachModel()
    print("FLOW A (persona↔widget, one-shot):")
    a = simulate(PsychePersona(), w, coach=None, persona_name="franz", rng=random.Random(7))
    print(f"  {len(a.events)} events, outcome={a.events[-1].type.value}")
    print("FLOW B (persona↔widget↔coach, turn-based):")
    b = simulate(PsychePersona(), w, coach=coach, persona_name="franz", rng=random.Random(7))
    shown = [e for e in b.events if e.type == EventType.WIDGET_SHOWN]
    print(f"  {len(b.events)} events, coach interventions={len(shown)}, outcome={b.events[-1].type.value}")
    for e in b.events:
        mark = " ←COACH" if e.source == "coach" else ""
        print(f"    t={e.t:5.1f} {e.type.value:14s} {e.target or '':14s}{mark}")
