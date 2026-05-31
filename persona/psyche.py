"""
UNIQA Psyche Model — grounded latent mental-state bounce model.

Replaces crude per-step abandon probabilities with an evolving mental state
plus named bounce reasons. A real user bounces because price arrived before they
were ready, or a kid walked in, or the form felt endless — not because of an
abstract p=0.66.

See PSYCHE_WALKTHROUGH.md for the first-person grounding.

Calibration targets (UNIQA funnel data Dec 2025–Feb 2026):
  Step 4 (tariff) conditional bounce ≈ 66%
  Step 5 (add-on) conditional bounce ≈ 24%
  Step 6 (data)   conditional bounce ≈ 78%
  Overall conversion ≈ 5.6%
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from enum import Enum

from calculator.funnel import Step


# ─── Intent (fixed per session) ───────────────────────────────────────────────

class Intent(Enum):
    PURCHASE     = "purchase"      # here to buy today
    ORIENTATION  = "orientation"   # exploring, maybe later
    COMPARISON   = "comparison"    # checking against competitors
    PRICE_CHECK  = "price_check"   # just wants the number


# Per-persona intent mix (sums to 1.0). Grounds "most bouncers were never buyers."
INTENT_MIX: dict[str, dict[Intent, float]] = {
    # Judith: hybrid researcher — often orientation, converts via advisor IRL
    "judith": {Intent.PURCHASE: 0.35, Intent.ORIENTATION: 0.35,
               Intent.COMPARISON: 0.20, Intent.PRICE_CHECK: 0.10},
    # Franz: digital-first, high purchase intent but price-sensitive
    "franz":  {Intent.PURCHASE: 0.55, Intent.ORIENTATION: 0.15,
               Intent.COMPARISON: 0.25, Intent.PRICE_CHECK: 0.05},
    # Peter: service-seeker, low online purchase intent, easily overwhelmed
    "peter":  {Intent.PURCHASE: 0.25, Intent.ORIENTATION: 0.40,
               Intent.COMPARISON: 0.10, Intent.PRICE_CHECK: 0.25},
}


# ─── Bounce Reasons ───────────────────────────────────────────────────────────

class BounceReason(Enum):
    NONE                = "none"
    DISTRACTION         = "distraction"          # attention leaked (external)
    PRICE_SHOCK         = "price_shock"          # price before readiness
    OVERWHELM           = "overwhelm"            # comprehension too low + options
    EFFORT_EXHAUSTION   = "effort_exhaustion"    # patience depleted
    TRUST_GAP           = "trust_gap"            # won't commit / share data
    NOT_READY           = "not_ready"            # orientation intent, not buying today
    COMPARISON_LEAVE    = "comparison_leave"     # left to compare competitors


# ─── Latent Mental State ──────────────────────────────────────────────────────

@dataclass
class Mind:
    """The evolving internal state of a user-consciousness."""
    persona:          str
    intent:           Intent
    attention:        float = 0.85
    price_readiness:  float = 0.30
    comprehension:    float = 0.50
    trust:            float = 0.50
    effort_budget:    float = 1.00
    valence:          float = 0.10   # -1..1

    # diagnostic trail
    last_bounce_reason: BounceReason = BounceReason.NONE

    def clamp(self) -> None:
        self.attention       = _c(self.attention)
        self.price_readiness = _c(self.price_readiness)
        self.comprehension   = _c(self.comprehension)
        self.trust           = _c(self.trust)
        self.effort_budget   = _c(self.effort_budget)
        self.valence         = max(-1.0, min(1.0, self.valence))


def _c(x: float) -> float:
    return max(0.0, min(1.0, x))


# ─── Persona starting minds ───────────────────────────────────────────────────

def init_mind(persona: str, rng: random.Random) -> Mind:
    """Sample a starting Mind for a persona (with per-session variation)."""
    intents = list(INTENT_MIX[persona].keys())
    weights = list(INTENT_MIX[persona].values())
    intent  = rng.choices(intents, weights=weights, k=1)[0]

    if persona == "judith":   # higher trust, advisor-lean, moderate comprehension
        base = dict(attention=0.85, price_readiness=0.35, comprehension=0.55,
                    trust=0.70, effort_budget=1.0, valence=0.10)
    elif persona == "franz":  # high comprehension, lower trust in being upsold, low effort tolerance
        base = dict(attention=0.88, price_readiness=0.40, comprehension=0.70,
                    trust=0.55, effort_budget=0.95, valence=0.12)
    else:  # peter — low comprehension, low trust, easily overwhelmed
        base = dict(attention=0.78, price_readiness=0.25, comprehension=0.35,
                    trust=0.45, effort_budget=0.85, valence=0.05)

    # per-session jitter
    jitter = lambda v, s=0.06: _c(v + rng.gauss(0, s))
    return Mind(
        persona=persona, intent=intent,
        attention=jitter(base["attention"]),
        price_readiness=jitter(base["price_readiness"]),
        comprehension=jitter(base["comprehension"]),
        trust=jitter(base["trust"]),
        effort_budget=jitter(base["effort_budget"]),
        valence=base["valence"] + rng.gauss(0, 0.05),
    )


# ─── Step dynamics: how the mind moves through each step ──────────────────────
# Applied BEFORE the bounce check for that step.

def step_dynamics(mind: Mind, step: Step, rng: random.Random) -> None:
    """Mutate mind in place to reflect what this step does to the psyche."""
    # Irreducible distraction: every step leaks some attention (external world)
    mind.attention -= abs(rng.gauss(0, 0.10))

    if step == Step.COVERAGE_TYPE:
        mind.comprehension += 0.10
        mind.effort_budget -= 0.03
    elif step == Step.INSURED:
        mind.effort_budget -= 0.03
        mind.valence       += 0.05   # momentum
    elif step == Step.PERSONAL_INFO:
        mind.effort_budget   -= 0.10
        mind.comprehension   -= 0.05   # SV dropdown flicker of doubt
        mind.price_readiness += 0.08   # senses price coming
    elif step == Step.TARIFF_SELECT:
        # the price arrives. valence dips on the "could go up" line.
        mind.valence         -= 0.25
        mind.price_readiness -= 0.15   # the shock itself ("Voraussichtliche" = could go up)
    elif step == Step.ADDON_SELECT:
        mind.effort_budget   -= 0.18   # upsell fatigue
        mind.valence         -= 0.15   # premature upsell irritation
        mind.price_readiness -= 0.10   # re-anchoring doubt
    elif step == Step.PERSONAL_DATA:
        mind.effort_budget   -= 0.33   # the wall: SV-number + 10-field form
        mind.trust           -= 0.12   # health data ask (weight, doctor)
        mind.price_readiness -= 0.15   # final price ≠ estimate
    mind.clamp()


# ─── Bounce evaluation: which reason (if any) fires at this step ──────────────

# step → option count (drives OVERWHELM)
STEP_OPTIONS = {
    Step.COVERAGE_TYPE: 2, Step.INSURED: 2, Step.PERSONAL_INFO: 1,
    Step.TARIFF_SELECT: 4, Step.ADDON_SELECT: 6, Step.PERSONAL_DATA: 1,
}

# Steps where a price is salient (drives PRICE_SHOCK)
PRICE_SALIENT = {Step.TARIFF_SELECT, Step.PERSONAL_DATA}


@dataclass
class BounceEval:
    bounced:   bool
    reason:    BounceReason
    # per-reason hazard contributions (for diagnostics / coach targeting)
    hazards:   dict[BounceReason, float] = field(default_factory=dict)


def evaluate_bounce(mind: Mind, step: Step, rng: random.Random) -> BounceEval:
    """
    Compute per-reason hazard, combine, roll. Returns BounceEval.
    Hazards are tuned so aggregate matches the real funnel (see tests).
    """
    h: dict[BounceReason, float] = {}

    # DISTRACTION — attention leak (external, irreducible)
    if mind.attention < 0.30:
        h[BounceReason.DISTRACTION] = 0.50 * (0.30 - mind.attention) / 0.30 + 0.08

    # PRICE_SHOCK — price salient & not ready
    if step in PRICE_SALIENT and mind.price_readiness < 0.60:
        sev = (0.60 - mind.price_readiness) / 0.60
        base = 0.70 if step == Step.TARIFF_SELECT else 0.74   # S6 final price
        h[BounceReason.PRICE_SHOCK] = base * sev

    # OVERWHELM — low comprehension & many options
    opts = STEP_OPTIONS.get(step, 1)
    if mind.comprehension < 0.40 and opts >= 3:
        h[BounceReason.OVERWHELM] = 0.55 * (0.40 - mind.comprehension) / 0.40

    # EFFORT_EXHAUSTION — patience depleted (mostly S6 form, S5 upsell fatigue)
    if mind.effort_budget < 0.40:
        sev = (0.40 - mind.effort_budget) / 0.40
        base = 0.70 if step == Step.PERSONAL_DATA else (0.40 if step == Step.ADDON_SELECT else 0.30)
        h[BounceReason.EFFORT_EXHAUSTION] = base * sev

    # Upsell fatigue floor at S5 (premature upsell, wrong moment)
    if step == Step.ADDON_SELECT:
        h[BounceReason.EFFORT_EXHAUSTION] = max(
            h.get(BounceReason.EFFORT_EXHAUSTION, 0.0), 0.20
        )

    # TRUST_GAP — low trust at commit (S6 health data)
    if step == Step.PERSONAL_DATA and mind.trust < 0.45:
        h[BounceReason.TRUST_GAP] = 0.50 * (0.45 - mind.trust) / 0.45

    # NOT_READY — orientation/price_check intent, price seen
    if mind.intent in (Intent.ORIENTATION, Intent.PRICE_CHECK) and step in PRICE_SALIENT:
        h[BounceReason.NOT_READY] = 0.90 if mind.intent == Intent.PRICE_CHECK else 0.74

    # COMPARISON_LEAVE — comparison intent, lingering at price
    if mind.intent == Intent.COMPARISON and step == Step.TARIFF_SELECT:
        h[BounceReason.COMPARISON_LEAVE] = 0.72

    # Combine: survival across independent hazards → 1 − Π(1 − hᵢ)
    survive = 1.0
    for hz in h.values():
        survive *= (1.0 - max(0.0, min(0.98, hz)))
    p_bounce = 1.0 - survive

    bounced = rng.random() < p_bounce
    reason = BounceReason.NONE
    if bounced and h:
        # attribute to the dominant hazard
        reason = max(h, key=h.get)
    mind.last_bounce_reason = reason
    return BounceEval(bounced=bounced, reason=reason, hazards=h)


# ─── Coach effect on the MIND (not on raw probability) ───────────────────────
# A coach action shifts latent state; bounce is then re-evaluated. This is the
# honest model: the coach changes the person, not a magic probability multiplier.

# Per-action effect gain. Default 1.0 (calibrated baseline). The autoresearch
# loop (deferred.autoresearch) treats this dict as the tunable Coach *policy vector*:
# it proposes perturbations, evaluates uplift on synthetic data, and gate-accepts
# improvements. Resetting all entries to 1.0 restores the hand-calibrated coach.
COACH_GAIN: dict[str, float] = {}


def set_coach_gain(gains: dict[str, float] | None) -> None:
    """Install a policy vector (action_value -> gain multiplier). None resets."""
    COACH_GAIN.clear()
    if gains:
        COACH_GAIN.update(gains)


def apply_coach_effect(mind: Mind, action_value: str, step: Step) -> None:
    """
    Mutate mind in place to reflect a coach intervention's psychological effect.
    action_value is CoachAction.value (str) to avoid import cycle.
    Each additive effect is scaled by the tunable COACH_GAIN policy vector.
    """
    a = action_value
    g = COACH_GAIN.get(a, 1.0)
    if a == "price_reframe":
        mind.price_readiness += 0.30 * g      # €/day framing braces them
        mind.valence         += 0.08 * g
    elif a == "upgrade_explain":
        mind.comprehension   += 0.30 * g      # removes Premium-needs-advisory confusion
        mind.valence         += 0.10 * g
    elif a == "coverage_explain":
        mind.comprehension   += 0.25 * g      # EUR limits → real visits
    elif a == "health_explain":
        mind.price_readiness += 0.25 * g      # explains final-price delta
        mind.trust           += 0.10 * g
    elif a == "trust_signal":
        mind.trust           += 0.20 * g
    elif a == "upgrade_path":
        mind.price_readiness += 0.15 * g      # "switch later, no health check"
        mind.comprehension   += 0.10 * g
    elif a == "form_helper":
        mind.effort_budget   += 0.20 * g      # SV-number located, "3 fields left"
    elif a == "progress_saver":
        mind.effort_budget   += 0.35 * g      # decouples completion → can resume
        mind.valence         += 0.05 * g
    elif a == "callback_offer":
        # routes to human BEFORE the wall — recovers Peter, soft conversion
        mind.effort_budget   += 0.25 * g
        mind.trust           += 0.15 * g
    elif a == "advisor_handoff":
        mind.trust           += 0.20 * g
        mind.effort_budget   += 0.15 * g
    elif a == "feature_highlight":
        mind.valence         += 0.08 * g
        mind.comprehension   += 0.10 * g
    mind.clamp()
