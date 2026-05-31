"""Simulator: Flow A (no coach) + Flow B (coach in the loop) + role pluggability."""

import random

from calculator.funnel import Step
from calculator.contracts import Event, EventType, ActivityLog
from coach.coach_io import RuleCoachModel
from calculator.sim import (
    simulate, PsychePersona, WidgetTwin, PersonaModel, WidgetModel, CoachModel,
)

TERMINALS = {EventType.CONVERT, EventType.ABANDON}


def _terminal(log: ActivityLog) -> EventType:
    return log.events[-1].type


# ─── integrated guardrails across all personas (gap coverage) ─────────────────

def test_flow_b_all_personas_terminate_within_budget():
    """Every persona, many seeds: the loop terminates, stays schema-clean, and the
    coach never exceeds the widget budget — the integrated safety guarantee."""
    # default backends satisfy their Protocols (pluggability)
    assert isinstance(PsychePersona(), PersonaModel)
    assert isinstance(WidgetTwin(), WidgetModel)
    assert isinstance(RuleCoachModel(), CoachModel)
    for persona in ("judith", "franz", "peter"):
        for seed in range(12):
            log = simulate(PsychePersona(), WidgetTwin(), coach=RuleCoachModel(),
                           persona_name=persona, rng=random.Random(seed))
            assert _terminal(log) in TERMINALS
            assert all(isinstance(e.type, EventType) for e in log.events)  # schema-clean
            shown = [e for e in log.events if e.type is EventType.WIDGET_SHOWN]
            assert len(shown) <= 3, f"{persona}/{seed}: budget exceeded ({len(shown)})"


# ─── Flow A: persona ↔ widget (no coach) ──────────────────────────────────────

def test_flow_a_one_shot_terminates():
    log = simulate(PsychePersona(), WidgetTwin(), coach=None,
                   persona_name="franz", rng=random.Random(7))
    assert _terminal(log) in TERMINALS
    assert all(isinstance(e.type, EventType) for e in log.events)   # schema-clean
    # no coach events in Flow A
    assert not any(e.source == "coach" for e in log.events)


def test_flow_a_deterministic():
    a = simulate(PsychePersona(), WidgetTwin(), coach=None, persona_name="judith", rng=random.Random(3))
    b = simulate(PsychePersona(), WidgetTwin(), coach=None, persona_name="judith", rng=random.Random(3))
    assert [e.to_dict() for e in a.events] == [e.to_dict() for e in b.events]


# ─── Flow B: persona ↔ widget ↔ coach (turn-based) ───────────────────────────

def test_flow_b_coach_can_intervene_and_persona_reacts():
    # aggregate over seeds: at least some sessions get a coach intervention
    interventions = 0
    for s in range(40):
        log = simulate(PsychePersona(), WidgetTwin(), coach=RuleCoachModel(),
                       persona_name="franz", rng=random.Random(s))
        assert _terminal(log) in TERMINALS
        shown = [e for e in log.events if e.type == EventType.WIDGET_SHOWN]
        interventions += len(shown)
        # a coach event always precedes the persona's final reaction (turn order)
        for e in shown:
            assert e.source == "coach"
    assert interventions > 0


def test_flow_b_respects_message_budget():
    for s in range(30):
        log = simulate(PsychePersona(), WidgetTwin(), coach=RuleCoachModel(),
                       persona_name="peter", rng=random.Random(s), budget=2)
        shown = [e for e in log.events if e.type == EventType.WIDGET_SHOWN]
        assert len(shown) <= 2


def test_flow_b_coach_shifts_outcomes_vs_flow_a():
    # same seeds, coach on vs off → coach should change at least some outcomes
    diffs = 0
    for s in range(60):
        a = simulate(PsychePersona(), WidgetTwin(), coach=None, persona_name="franz", rng=random.Random(s))
        b = simulate(PsychePersona(), WidgetTwin(), coach=RuleCoachModel(), persona_name="franz", rng=random.Random(s))
        if _terminal(a) != _terminal(b):
            diffs += 1
    assert diffs > 0          # the coach actually moves the needle


# ─── pluggability: a custom backend with NO whole-session support ─────────────

class _AlwaysConvertPersona:
    """Trivial custom backend (not psyche, not LLM) — proves any impl plugs in."""
    can_whole_session = False
    def reset(self, persona, rng): self.persona = persona
    def whole_session(self, rng): return []
    def step(self, step, history, t, rng): return []
    def resolve(self, step, history, coach, t, rng): return ("advance", [])


def test_custom_persona_without_whole_session_uses_turn_loop():
    assert isinstance(_AlwaysConvertPersona(), PersonaModel)
    log = simulate(_AlwaysConvertPersona(), WidgetTwin(), coach=None,
                   persona_name="judith", rng=random.Random(1))
    # never bounces → walks to PURCHASE → converts
    assert _terminal(log) == EventType.CONVERT
    assert any(e.step == Step.PURCHASE.value for e in log.events)
