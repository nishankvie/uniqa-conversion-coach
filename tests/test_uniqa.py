"""
UNIQA Coach — Core Tests

Critical tests (must pass before demo):
  1. Calibration: baseline ≈ 5.6%
  2. Calibration: Step 4 conditional abandon ≈ 66%
  3. Franz constraint: AdvisorHandoff always raises
  4. Coach improves conversion (coached > baseline)
  5. Message budget ceiling enforced
  6. Per-persona differentiation present
"""

import pytest

from calculator.funnel import (
    Step, FunnelState, HesitationSignals, ABANDON_PROBS, PERSONA_WEIGHTS, PERSONAS,
)
from coach.coach import CoachAction, decide_action, validate_output, MESSAGE_BUDGET
from deferred.simulation import run_simulation, run_ab_simulation


# ─── Constraint Tests ─────────────────────────────────────────────────────────

def test_franz_advisor_handoff_blocked():
    """Franz MUST NEVER receive AdvisorHandoff. Hard constraint."""
    with pytest.raises(ValueError, match="CONSTRAINT VIOLATION"):
        validate_output(CoachAction.ADVISOR_HANDOFF, "franz")


def test_judith_advisor_handoff_allowed():
    """Judith CAN receive AdvisorHandoff."""
    validate_output(CoachAction.ADVISOR_HANDOFF, "judith")  # must not raise


def test_peter_advisor_handoff_allowed():
    """Peter CAN receive AdvisorHandoff (soft routing)."""
    validate_output(CoachAction.ADVISOR_HANDOFF, "peter")  # must not raise


def test_message_budget_returns_none():
    """Coach returns NONE when message budget exhausted."""
    sig = HesitationSignals(dwell_time_sec=30.0, backward_nav_count=2)
    state = FunnelState(step=Step.TARIFF_SELECT, persona="franz", signals=sig)
    action = decide_action(state, message_count=MESSAGE_BUDGET)
    assert action == CoachAction.NONE, f"Expected NONE at budget limit, got {action}"


def test_franz_premium_click_gets_upgrade_explain():
    """Franz who clicks Premium should get UPGRADE_EXPLAIN (removes confusion)."""
    sig = HesitationSignals(premium_click=True, backward_nav_count=1, dwell_time_sec=8.0)
    state = FunnelState(step=Step.TARIFF_SELECT, persona="franz", signals=sig)
    action = decide_action(state, message_count=0)
    assert action == CoachAction.UPGRADE_EXPLAIN, f"Got {action} instead of UPGRADE_EXPLAIN"


def test_peter_early_gets_callback():
    """Peter overwhelmed at PERSONAL_INFO should get CALLBACK_OFFER."""
    sig = HesitationSignals(form_reedits=2, dwell_time_sec=9.0)
    state = FunnelState(step=Step.PERSONAL_INFO, persona="peter", signals=sig)
    action = decide_action(state, message_count=0)
    assert action == CoachAction.CALLBACK_OFFER, f"Got {action} instead of CALLBACK_OFFER"


def test_no_hesitation_yields_no_action():
    """No hesitation signal anywhere → the coach stays silent (annoyance restraint)."""
    for persona in PERSONAS:
        for step in (Step.COVERAGE_TYPE, Step.TARIFF_SELECT, Step.PERSONAL_DATA):
            state = FunnelState(step=step, persona=persona, signals=HesitationSignals())
            assert decide_action(state, message_count=0) == CoachAction.NONE


# ─── Calibration Tests ────────────────────────────────────────────────────────

def test_calibration_step4_weighted_abandon():
    """
    Weighted average of Step 4 abandon probs ≈ 0.645 ≈ 66%.
    Source: UNIQA funnel data Dec 2025–Feb 2026.
    0.30×0.70 + 0.50×0.55 + 0.20×0.80 = 0.645
    """
    weighted = sum(
        PERSONA_WEIGHTS[p] * ABANDON_PROBS[p].get(Step.TARIFF_SELECT, 0.0)
        for p in PERSONAS
    )
    assert abs(weighted - 0.645) < 0.05, (
        f"Step 4 calibration FAIL: {weighted:.3f} (target 0.645 ± 0.05)"
    )


def test_baseline_conversion_near_target():
    """
    Baseline simulation (N=2000, no coach) should produce conversion ≈ 5.6%.
    Acceptable range: 3.5% – 8.5% at N=2000 (sampling variance).
    """
    result = run_simulation(n=2_000, seed=42, coach_on=False)
    assert 0.035 <= result.conversion_rate <= 0.085, (
        f"Baseline conversion {result.conversion_rate:.3f} diverges from 5.6% (range 3.5%–8.5%)"
    )


# ─── Uplift Tests ─────────────────────────────────────────────────────────────

def test_coach_improves_overall_conversion():
    """Coach simulation must produce higher conversion than baseline."""
    baseline, coached = run_ab_simulation(n=1_000, seed=42)
    assert coached.conversion_rate > baseline.conversion_rate, (
        f"Coach failed to improve: {coached.conversion_rate:.3f} ≤ {baseline.conversion_rate:.3f}"
    )


def test_coach_reduces_step4_abandon():
    """Coach must reduce Step 4 (tariff selection) conditional abandon rate."""
    baseline, coached = run_ab_simulation(n=1_000, seed=42)
    base_s4 = baseline.per_step_abandon.get(Step.TARIFF_SELECT.value, 1.0)
    coach_s4 = coached.per_step_abandon.get(Step.TARIFF_SELECT.value, 1.0)
    assert coach_s4 < base_s4, (
        f"Step 4 not improved: {coach_s4:.3f} ≥ {base_s4:.3f}"
    )


def test_coach_reduces_step6_abandon():
    """Coach must reduce Step 6 (personal data) conditional abandon rate."""
    baseline, coached = run_ab_simulation(n=1_000, seed=42)
    base_s6 = baseline.per_step_abandon.get(Step.PERSONAL_DATA.value, 1.0)
    coach_s6 = coached.per_step_abandon.get(Step.PERSONAL_DATA.value, 1.0)
    assert coach_s6 < base_s6, (
        f"Step 6 not improved: {coach_s6:.3f} ≥ {base_s6:.3f}"
    )


def test_persona_differentiation():
    """Coach must show different conversion rates per persona (not one-size-fits-all)."""
    _, coached = run_ab_simulation(n=2_000, seed=42)
    per_persona = coached.per_persona_conv
    rates = [per_persona.get(p, 0) for p in PERSONAS]
    # At least one persona should differ meaningfully from the average
    avg = sum(rates) / len(rates)
    max_diff = max(abs(r - avg) for r in rates)
    assert max_diff > 0.02, (
        f"Persona differentiation too low: max_diff={max_diff:.3f} (should be >0.02)"
    )


# ─── Modifier Sanity ──────────────────────────────────────────────────────────

def test_modifiers_reduce_or_neutral():
    """All Coach modifiers must be ≤ 1.0 (never worsen abandon prob)."""
    from coach.coach import COACH_MODIFIERS
    for action, persona_map in COACH_MODIFIERS.items():
        for persona, step_map in persona_map.items():
            for step, mod in step_map.items():
                assert mod <= 1.0, (
                    f"Modifier > 1.0: {action.value} / {persona} / {step.value} = {mod}"
                )
                assert mod > 0.0, (
                    f"Modifier ≤ 0: {action.value} / {persona} / {step.value} = {mod}"
                )
