"""
UNIQA Conversion Funnel — State Machine
Privatarzt / Ich selbst / Start+Optimal path only.

Steps (in-scope online path):
  S0 START            → user lands on calculator
  S1 COVERAGE_TYPE    → "Bei Arztbesuchen" selected
  S2 INSURED_PERSONS  → "Ich selbst" selected
  S3 PERSONAL_INFO    → DOB + Sozialversicherung
  S4 TARIFF_SELECT    → price table, 66% abandon here
  S5 ADDON_SELECT     → add-on upsell, 24% abandon
  S6 PERSONAL_DATA    → form: name, SV-nr, health data, 78% abandon
  S7 PURCHASE         → terminal success

Survival math (from UNIQA data, Dec 2025–Feb 2026):
  1,000 → 340 (Step 4) → 258 (Step 5) → ~57 (Step 6) → ~56 purchase
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum


# ─── Steps ───────────────────────────────────────────────────────────────────

class Step(Enum):
    START          = "S0_START"
    COVERAGE_TYPE  = "S1_COVERAGE_TYPE"
    INSURED        = "S2_INSURED_PERSONS"
    PERSONAL_INFO  = "S3_PERSONAL_INFO"     # DOB + SV type
    TARIFF_SELECT  = "S4_TARIFF_SELECT"     # ← 66% abandon (conditional)
    ADDON_SELECT   = "S5_ADDON_SELECT"      # ← 24% abandon (conditional)
    PERSONAL_DATA  = "S6_PERSONAL_DATA"     # ← 78% abandon (conditional)
    PURCHASE       = "S7_PURCHASE"          # terminal success


STEP_ORDER = [
    Step.START,
    Step.COVERAGE_TYPE,
    Step.INSURED,
    Step.PERSONAL_INFO,
    Step.TARIFF_SELECT,
    Step.ADDON_SELECT,
    Step.PERSONAL_DATA,
    Step.PURCHASE,
]


def next_step(current: Step) -> Step | None:
    idx = STEP_ORDER.index(current)
    return STEP_ORDER[idx + 1] if idx + 1 < len(STEP_ORDER) else None


# ─── Persona Types ────────────────────────────────────────────────────────────

PERSONAS = ("judith", "franz", "peter")

# Funnel traffic share (source: UNIQA internal estimate)
PERSONA_WEIGHTS: dict[str, float] = {
    "judith": 0.30,   # S1 Rising Hybrids
    "franz":  0.50,   # S2 Online Affine
    "peter":  0.20,   # S3 Service Affine
}

# ─── Baseline abandon probabilities (conditional on reaching that step) ───────
# Calibration target:
#   0.30×0.70 + 0.50×0.55 + 0.20×0.80 = 0.645 ≈ 66% at Step 4 ✓
#
# Overall survival chain:
#   S4: 1 − weighted_avg ≈ 34% survive
#   S5: 76% survive (24% abandon)
#   S6: 22% survive (78% abandon)
#   Overall: 34% × 76% × 22% ≈ 5.7% ≈ 5.6% ✓

ABANDON_PROBS: dict[str, dict[Step, float]] = {
    "judith": {
        Step.PERSONAL_INFO: 0.05,   # usually fine, researched online first
        Step.TARIFF_SELECT: 0.70,   # primary drop-off — sticker shock + advisor lean
        Step.ADDON_SELECT:  0.18,   # moderate — compares options
        Step.PERSONAL_DATA: 0.68,   # final price higher than estimate → abandons
    },
    "franz": {
        Step.PERSONAL_INFO: 0.04,   # low friction, digital native
        Step.TARIFF_SELECT: 0.55,   # moderate — may click Premium then back
        Step.ADDON_SELECT:  0.22,   # price-conscious, considers carefully
        Step.PERSONAL_DATA: 0.78,   # final price > estimate = primary drop-off
    },
    "peter": {
        Step.PERSONAL_INFO: 0.25,   # overwhelmed by form — major early exit
        Step.TARIFF_SELECT: 0.80,   # price shock + complexity overload
        Step.ADDON_SELECT:  0.35,   # confused by add-on choices
        Step.PERSONAL_DATA: 0.72,   # if he's made it this far, high drop-off
    },
}

# Steps where personas can generate hesitation signals (Coach fires here)
COACHABLE_STEPS = {
    Step.PERSONAL_INFO,
    Step.TARIFF_SELECT,
    Step.ADDON_SELECT,
    Step.PERSONAL_DATA,
}


# ─── Hesitation Signals ───────────────────────────────────────────────────────

@dataclass
class HesitationSignals:
    """Behavioral signals emitted at each step. Proxy for user state."""
    dwell_time_sec:       float = 0.0
    backward_nav_count:   int   = 0
    price_hover_count:    int   = 0
    form_reedits:         int   = 0
    session_gap_spike:    bool  = False
    premium_click:        bool  = False   # clicked Opt.Plus or Premium
    cancel_hover_count:   int   = 0

    def any_hesitation(self) -> bool:
        return (
            self.dwell_time_sec > 0 or
            self.backward_nav_count > 0 or
            self.price_hover_count > 0 or
            self.form_reedits > 0 or
            self.session_gap_spike or
            self.premium_click or
            self.cancel_hover_count > 0
        )


# Per-persona hesitation thresholds (rule-based trigger for Coach)
HESITATION_THRESHOLDS: dict[str, dict] = {
    "judith": {
        "dwell_time_sec":   8.0,
        "price_hover_count": 3,
        "backward_nav_count": 1,
        "cancel_hover_count": 2,
    },
    "franz": {
        "dwell_time_sec":   12.0,
        "session_gap_spike": True,
        "backward_nav_count": 1,
        "premium_click":     True,   # Franz clicks Premium, sees "advisory required"
        "cancel_hover_count": 3,
    },
    "peter": {
        "dwell_time_sec":   6.0,
        "form_reedits":     2,
        "backward_nav_count": 1,
    },
}


def is_hesitating(signals: HesitationSignals, persona: str) -> bool:
    """Rule-based hesitation detection. Returns True if Coach should consider firing."""
    t = HESITATION_THRESHOLDS[persona]
    return (
        signals.dwell_time_sec        >= t.get("dwell_time_sec",       999.0) or
        signals.price_hover_count     >= t.get("price_hover_count",    999)   or
        signals.backward_nav_count    >= t.get("backward_nav_count",   999)   or
        signals.form_reedits          >= t.get("form_reedits",         999)   or
        signals.cancel_hover_count    >= t.get("cancel_hover_count",   999)   or
        (t.get("session_gap_spike")  and signals.session_gap_spike)           or
        (t.get("premium_click")      and signals.premium_click)
    )


# ─── Funnel State ─────────────────────────────────────────────────────────────

@dataclass
class FunnelState:
    step:         Step
    persona:      str
    signals:      HesitationSignals = field(default_factory=HesitationSignals)
    tariff_shown: str | None = None   # "Start" | "Optimal" | "OptPlus" | "Premium"
    price_delta:  float = 0.0         # final price − initial estimate (€)
    history:      list[Step] = field(default_factory=list)


# ─── Signal Generation (rule-based, for simulation) ──────────────────────────

def generate_signals(step: Step, persona: str, rng: random.Random) -> HesitationSignals:
    """Synthetic hesitation signals consistent with persona profile."""
    s = HesitationSignals()

    if persona == "judith":
        if step == Step.TARIFF_SELECT:
            s.dwell_time_sec   = rng.gauss(10.0, 3.0)
            s.price_hover_count = rng.randint(2, 5)
            s.backward_nav_count = 1 if rng.random() < 0.4 else 0
        elif step == Step.PERSONAL_DATA:
            s.dwell_time_sec    = rng.gauss(22.0, 6.0)
            s.cancel_hover_count = rng.randint(1, 4) if rng.random() < 0.6 else 0
            s.price_delta        = rng.gauss(7.0, 3.0)   # stored externally but signal proxy

    elif persona == "franz":
        if step == Step.TARIFF_SELECT:
            # Franz is the Premium-click scenario
            s.premium_click      = rng.random() < 0.45   # 45% click Premium
            s.dwell_time_sec     = rng.gauss(8.0, 3.0)
            s.backward_nav_count = 1 if s.premium_click else (1 if rng.random() < 0.25 else 0)
        elif step == Step.PERSONAL_DATA:
            s.dwell_time_sec    = rng.gauss(18.0, 5.0)
            s.session_gap_spike = rng.random() < 0.55
            s.cancel_hover_count = rng.randint(1, 5) if rng.random() < 0.65 else 0

    elif persona == "peter":
        if step == Step.PERSONAL_INFO:
            s.dwell_time_sec   = rng.gauss(9.0, 3.0)
            s.form_reedits     = rng.randint(1, 4)
            s.backward_nav_count = 1 if rng.random() < 0.45 else 0
        elif step == Step.TARIFF_SELECT:
            s.dwell_time_sec   = rng.gauss(14.0, 4.0)
            s.price_hover_count = rng.randint(1, 3)

    # Clamp negatives
    s.dwell_time_sec = max(0.0, s.dwell_time_sec)
    return s
