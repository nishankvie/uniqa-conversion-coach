"""
Journey + Psyche model tests.

Calibration (psyche-grounded model must match real UNIQA funnel):
  baseline ≈ 5.6%, S4 ≈ 66%, S5 ≈ 24%, S6 ≈ 78%

Harness contract:
  - deterministic given seed (stable token stream)
  - JSON-renderable tokens (composable twin)
  - next-token suggester respects Franz constraint + budget
"""

import random
import json

import pytest

from calculator.funnel import Step, HesitationSignals
from coach.coach import CoachAction
from persona.psyche import init_mind, Intent, BounceReason
from calculator.journey import (
    run_journey, run_batch, suggest_next_token, render_step, render_widget,
    TokenType, JourneyToken,
)


# ─── Calibration (psyche model → real funnel) ─────────────────────────────────

def test_baseline_conversion_calibrated():
    """Psyche baseline must land near 5.6% (range 4.0–7.5% at N=5000)."""
    b = run_batch(n=5_000, seed=42, coach_on=False)
    assert 0.040 <= b.conversion_rate <= 0.075, (
        f"Baseline {b.conversion_rate:.3f} off 5.6% target"
    )


def test_step4_bounce_calibrated():
    b = run_batch(n=5_000, seed=42, coach_on=False)
    s4 = b.per_step_bounce.get(Step.TARIFF_SELECT.value, 0)
    assert 0.60 <= s4 <= 0.72, f"S4 bounce {s4:.3f} off 66% target"


def test_step5_bounce_calibrated():
    b = run_batch(n=5_000, seed=42, coach_on=False)
    s5 = b.per_step_bounce.get(Step.ADDON_SELECT.value, 0)
    assert 0.16 <= s5 <= 0.30, f"S5 bounce {s5:.3f} off 24% target"


def test_step6_bounce_calibrated():
    b = run_batch(n=5_000, seed=42, coach_on=False)
    s6 = b.per_step_bounce.get(Step.PERSONAL_DATA.value, 0)
    assert 0.72 <= s6 <= 0.84, f"S6 bounce {s6:.3f} off 78% target"


# ─── Bounce reason realism ────────────────────────────────────────────────────

def test_bounce_reasons_multi_causal():
    """Bounces must come from multiple named reasons, not one."""
    b = run_batch(n=3_000, seed=42, coach_on=False)
    assert len(b.bounce_reasons) >= 3, f"Too few reasons: {b.bounce_reasons}"
    # not_ready and price_shock should both be material
    assert b.bounce_reasons.get("price_shock", 0) > 50
    assert b.bounce_reasons.get("not_ready", 0) > 50


def test_distraction_is_irreducible():
    """Distraction bounces should persist even WITH coach (can't coach a ringing phone)."""
    coached = run_batch(n=3_000, seed=42, coach_on=True)
    assert coached.bounce_reasons.get("distraction", 0) > 0, (
        "Distraction should remain — it's external/irreducible"
    )


def test_price_check_intent_rarely_converts():
    """price_check intent users should almost never convert (honest opportunity sizing)."""
    b = run_batch(n=5_000, seed=42, coach_on=True)
    pc = b.conv_by_intent.get("price_check", 0)
    assert pc < 0.05, f"price_check converting too much: {pc:.3f} (should be ~0)"


# ─── Coach effect ─────────────────────────────────────────────────────────────

def test_coach_improves_conversion():
    base = run_batch(n=3_000, seed=42, coach_on=False)
    coach = run_batch(n=3_000, seed=42, coach_on=True)
    assert coach.conversion_rate > base.conversion_rate


def test_coach_improves_purchase_intent_most():
    """Coach should lift purchase-intent conversion more than orientation."""
    coach = run_batch(n=5_000, seed=42, coach_on=True)
    assert coach.conv_by_intent.get("purchase", 0) > coach.conv_by_intent.get("orientation", 0)


def test_peter_whatsapp_recovery():
    """Peter who gets callback then bounces → WhatsApp lead."""
    coach = run_batch(n=3_000, seed=42, coach_on=True)
    assert coach.whatsapp_leads > 0, "No Peter WhatsApp recoveries"


# ─── Harness contract ─────────────────────────────────────────────────────────

def test_journey_deterministic():
    r1 = run_journey("franz", random.Random(5), coach_on=True)
    r2 = run_journey("franz", random.Random(5), coach_on=True)
    assert r1.to_dict() == r2.to_dict(), "Journey not deterministic for same seed"


def test_tokens_json_serializable():
    """Every token must render to JSON (composable twin requirement)."""
    r = run_journey("judith", random.Random(1), coach_on=True)
    blob = json.dumps(r.to_dict())   # must not raise
    assert len(blob) > 0
    # every token has a render spec
    for tok in r.tokens:
        assert "render" in tok.to_dict()


def test_render_step_has_screen_and_hud():
    mind = init_mind("franz", random.Random(2))
    spec = render_step(Step.TARIFF_SELECT, mind)
    assert spec["kind"] == "step_screen"
    assert "tariffs" in spec               # price table component
    assert "hud" in spec                   # live mind readout
    assert "price_readiness" in spec["hud"]


def test_render_widget_composable():
    spec = render_widget(CoachAction.PRICE_REFRAME, "franz", Step.TARIFF_SELECT)
    assert spec["kind"] == "coach_widget"
    assert spec["widget_type"] == "price_reframe"
    assert spec["headline"]                # has copy
    assert spec["user_visible"] is True


# ─── Next-token suggester ─────────────────────────────────────────────────────

def test_suggester_respects_franz_constraint():
    """Suggester must NEVER suggest advisor_handoff for Franz."""
    rng = random.Random(3)
    for _ in range(200):
        mind = init_mind("franz", rng)
        sig = HesitationSignals(cancel_hover_count=5, dwell_time_sec=30.0,
                                premium_click=False, backward_nav_count=2)
        sug = suggest_next_token(mind, Step.PERSONAL_DATA, sig, message_count=0)
        assert sug.action != CoachAction.ADVISOR_HANDOFF, (
            "Suggester proposed advisor_handoff for Franz!"
        )


def test_suggester_respects_budget():
    mind = init_mind("judith", random.Random(4))
    sig = HesitationSignals(dwell_time_sec=30.0, cancel_hover_count=3)
    sug = suggest_next_token(mind, Step.PERSONAL_DATA, sig, message_count=3)
    assert sug.action == CoachAction.NONE, "Suggester ignored budget ceiling"


def test_suggester_names_targeted_reason():
    """Suggestion should name which bounce reason it counters."""
    mind = init_mind("franz", random.Random(6))
    mind.price_readiness = 0.1   # force price_shock hazard
    sig = HesitationSignals(dwell_time_sec=15.0, price_hover_count=4)
    sug = suggest_next_token(mind, Step.TARIFF_SELECT, sig, message_count=0)
    if sug.action != CoachAction.NONE:
        assert sug.targeted_reason in {r.value for r in BounceReason} or sug.targeted_reason == "preventive"
