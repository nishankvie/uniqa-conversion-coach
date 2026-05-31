"""Contract backbone + Coach I/O round-trip tests (JSON-render compatibility)."""

import json
import random

import pytest

from calculator.funnel import Step, generate_signals
from coach.coach import CoachAction
from calculator.contracts import (
    Event, EventType, ActivityLog, Effector, EffectorCommand,
    Hypothesis, HypoStatus, CoachObservation, CoachDecision, RenderEnvelope,
    NEVER_AUTOFILL, SAMPLE_FILLABLE, new_session_id,
)
from coach.coach_io import (
    RuleCoachModel, activity_from_signals, observation_from_log, score_hypotheses,
)


def _json_roundtrips(obj_dict):
    s = json.dumps(obj_dict)            # must serialise
    assert json.loads(s) == obj_dict    # and round-trip


# ─── JSON-render compatibility ────────────────────────────────────────────────

def test_all_contract_objects_are_json_serialisable():
    log = ActivityLog(new_session_id())
    log.append(Event(EventType.STEP_ENTER, Step.TARIFF_SELECT.value, 0.0))
    _json_roundtrips(log.to_dict())

    cmd = EffectorCommand(Effector.SHOW_WIDGET, Step.TARIFF_SELECT.value,
                          payload={"intent": "price_reframe"})
    _json_roundtrips(cmd.to_dict())

    hyp = Hypothesis("h1", "price-shocked", "price_readiness", 0.7,
                     EventType.ABANDON, CoachAction.PRICE_REFRAME.value)
    _json_roundtrips(hyp.to_dict())

    dec = CoachDecision(command=cmd, reasoning="because", hypotheses=[hyp], confidence=0.7)
    _json_roundtrips(dec.to_dict())

    env = RenderEnvelope("coach_widget", Step.TARIFF_SELECT.value, spec={"a": 1})
    _json_roundtrips(env.to_dict())


# ─── Effector guardrails (immutable-app safety) ──────────────────────────────

def test_autofill_blocked_on_protected_fields():
    for fld in NEVER_AUTOFILL:
        with pytest.raises(ValueError):
            EffectorCommand(Effector.AUTOFILL, Step.PERSONAL_DATA.value, target=fld).validate()


def test_fill_sample_only_on_explorable_fields():
    EffectorCommand(Effector.FILL_SAMPLE, Step.TARIFF_SELECT.value, target="tariff").validate()
    with pytest.raises(ValueError):
        EffectorCommand(Effector.FILL_SAMPLE, Step.PERSONAL_DATA.value, target="sv_number").validate()
    assert SAMPLE_FILLABLE.isdisjoint(NEVER_AUTOFILL)


# ─── Coach I/O contract ──────────────────────────────────────────────────────

def test_coach_decides_from_activity_log_only():
    """Coach sees an observation (no persona/latent) and returns a valid decision."""
    rng = random.Random(3)
    log = ActivityLog(new_session_id())
    sig = generate_signals(Step.TARIFF_SELECT, "franz", rng)
    activity_from_signals(log, Step.TARIFF_SELECT, sig)
    obs = observation_from_log(log, Step.TARIFF_SELECT, budget_remaining=3)

    # observation must not leak persona/latent ground truth
    assert "persona" not in obs.to_dict()
    assert "intent" not in obs.to_dict()

    dec = RuleCoachModel().decide(obs)
    assert dec.reasoning                      # reasoning is mandatory + non-empty
    assert isinstance(dec.is_action(), bool)
    dec.command.validate()                    # never proposes an illegal effector
    _json_roundtrips(dec.to_dict())


def test_no_action_when_budget_exhausted():
    log = ActivityLog(new_session_id())
    activity_from_signals(log, Step.TARIFF_SELECT, generate_signals(Step.TARIFF_SELECT, "judith", random.Random(1)))
    obs = observation_from_log(log, Step.TARIFF_SELECT, budget_remaining=0)
    dec = RuleCoachModel().decide(obs)
    assert not dec.is_action()
    assert dec.command.effector is Effector.NO_ACTION


def test_premium_click_yields_upgrade_explain_hypothesis():
    log = ActivityLog(new_session_id())
    log.append(Event(EventType.STEP_ENTER, Step.TARIFF_SELECT.value, 0))
    log.append(Event(EventType.PREMIUM_CLICK, Step.TARIFF_SELECT.value, 1, target="premium_tariff"))
    obs = observation_from_log(log, Step.TARIFF_SELECT, budget_remaining=3)
    dec = RuleCoachModel().decide(obs)
    assert any(h.id == "h_premium" for h in dec.hypotheses)
    assert dec.command.payload.get("intent") == CoachAction.UPGRADE_EXPLAIN.value


def test_hypothesis_scoring_confirm_and_refute():
    h = Hypothesis("h", "price-shocked", "price_readiness", 0.7,
                   EventType.ABANDON, CoachAction.PRICE_REFRAME.value)
    dec = CoachDecision(command=EffectorCommand(Effector.SHOW_WIDGET, "s4"),
                        reasoning="r", hypotheses=[h])
    # abandon → confirmed
    res = score_hypotheses(dec, [Event(EventType.ABANDON, "s4", 5)])
    assert res["confirmed"] == 1

    h2 = Hypothesis("h2", "price-shocked", "price_readiness", 0.7,
                    EventType.ABANDON, CoachAction.PRICE_REFRAME.value)
    dec2 = CoachDecision(command=EffectorCommand(Effector.SHOW_WIDGET, "s4"),
                         reasoning="r", hypotheses=[h2])
    res2 = score_hypotheses(dec2, [Event(EventType.CONVERT, "s7", 9)])
    assert res2["refuted"] == 1
