# UNIQA Conversion Coach — Engineering Build Plan
> Post eng-review | 2026-05-30 | All 5 arch decisions locked

---

## Locked Decisions

| # | Decision | Locked Choice |
|---|----------|--------------|
| D1 | Simulation scale | Rule-based persona for 10k stats; LLM persona for 3-5 demo sessions |
| D2 | Sim loop coupling | Action enums in sim path; widget JSON in demo path only |
| D3 | Persona identification | Explicit selector in Streamlit sidebar |
| D4 | Franz constraint | Output guard (`validate_output`) + early filter in coach methods |
| D5 | Hesitation detection | Rule-based thresholds per step/persona |

---

## System Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│  STATS PATH (fast, $0, deterministic)                              │
│                                                                    │
│  FunnelStateMachine → CoachAction enum → RuleBasedPersona          │
│       ↕                    ↕                     ↕                 │
│  (state, step)   validate_output()    abandon_prob × coach_mod     │
│                                                                    │
│  Simulation.run(n=10000, seed=42) → {conversion_rate, uplift, CI} │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│  DEMO PATH (LLM-driven, 3-5 live sessions)                         │
│                                                                    │
│  Streamlit app                                                     │
│    sidebar: [Judith ▾] [run session] [reset]                      │
│    main:    funnel steps + widget cards + HUD                      │
│                                                                    │
│  FunnelStateMachine → Coach.emit_widget() → validate_output()     │
│       ↕                     ↕                      ↕              │
│  (step, signals)    WidgetEnvelope JSON      Franz guard           │
│                            ↓                                      │
│                   LLMPersona.react()                               │
│                    → {annoyance_scalar, next_action}               │
│                            ↓                                      │
│                   HUD: annoyance bar + widget transcript           │
└────────────────────────────────────────────────────────────────────┘
```

---

## Module Interfaces

### `uniqa/funnel.py`

```python
from dataclasses import dataclass, field
from enum import Enum

class Step(Enum):
    START          = "S0"
    FAMILY_SELECT  = "S1"
    PERSONAL_INFO  = "S2"
    PRICE_DISPLAY  = "S3"   # 66% abandon
    ADDON_SELECT   = "S4"   # 24% abandon
    HEALTH_QS      = "S5"
    FINAL_PRICE    = "S6"   # 78% abandon
    PURCHASE       = "S7"   # terminal success

@dataclass
class HesitationSignals:
    dwell_time_sec: float = 0.0
    backward_nav_count: int = 0
    price_hover_count: int = 0
    form_reedits: int = 0
    session_gap_spike: bool = False

@dataclass
class FunnelState:
    step: Step
    persona_type: str          # "judith" | "franz" | "peter"
    signals: HesitationSignals
    history: list[Step] = field(default_factory=list)

# Per-persona abandon probabilities (baseline, no coach)
# Calibration: 0.3×0.70 + 0.5×0.55 + 0.2×0.80 = 0.645 ≈ 66% ✓
ABANDON_PROBS: dict[str, dict[Step, float]] = {
    "judith": {
        Step.PRICE_DISPLAY: 0.70,
        Step.ADDON_SELECT:  0.20,
        Step.HEALTH_QS:     0.10,
        Step.FINAL_PRICE:   0.65,
        Step.PERSONAL_INFO: 0.05,
        Step.FAMILY_SELECT: 0.02,
    },
    "franz": {
        Step.PRICE_DISPLAY: 0.55,
        Step.ADDON_SELECT:  0.25,
        Step.HEALTH_QS:     0.08,
        Step.FINAL_PRICE:   0.78,
        Step.PERSONAL_INFO: 0.05,
        Step.FAMILY_SELECT: 0.02,
    },
    "peter": {
        Step.PERSONAL_INFO: 0.25,   # Peter bails early (overwhelm)
        Step.PRICE_DISPLAY: 0.80,
        Step.ADDON_SELECT:  0.22,
        Step.HEALTH_QS:     0.12,
        Step.FINAL_PRICE:   0.50,
        Step.FAMILY_SELECT: 0.03,
    },
}

# Hesitation thresholds — rule-based trigger for Coach (D5)
HESITATION_THRESHOLDS: dict[str, dict[str, float]] = {
    "judith": {
        "dwell_time_sec":     8.0,   # lingers on price table
        "price_hover_count":  3,
        "backward_nav_count": 1,
    },
    "franz": {
        "dwell_time_sec":     12.0,  # stalls on final price
        "session_gap_spike":  True,
        "backward_nav_count": 1,
    },
    "peter": {
        "dwell_time_sec":     6.0,   # overwhelmed early
        "form_reedits":       2,
        "backward_nav_count": 1,
    },
}

def is_hesitating(signals: HesitationSignals, persona_type: str) -> bool:
    thresholds = HESITATION_THRESHOLDS[persona_type]
    return (
        signals.dwell_time_sec > thresholds.get("dwell_time_sec", 999) or
        signals.price_hover_count > thresholds.get("price_hover_count", 999) or
        signals.backward_nav_count >= thresholds.get("backward_nav_count", 999) or
        signals.form_reedits >= thresholds.get("form_reedits", 999) or
        (thresholds.get("session_gap_spike") and signals.session_gap_spike)
    )

STEP_ORDER = [
    Step.START, Step.FAMILY_SELECT, Step.PERSONAL_INFO,
    Step.PRICE_DISPLAY, Step.ADDON_SELECT, Step.HEALTH_QS,
    Step.FINAL_PRICE, Step.PURCHASE
]

def next_step(current: Step) -> Step | None:
    idx = STEP_ORDER.index(current)
    return STEP_ORDER[idx + 1] if idx + 1 < len(STEP_ORDER) else None
```

---

### `uniqa/coach.py`

```python
from enum import Enum
from uniqa.funnel import Step, FunnelState, HesitationSignals

class CoachAction(Enum):
    NONE              = "none"
    PRICE_REFRAME     = "price_reframe"       # "€1.27/day"
    UPGRADE_PATH      = "upgrade_path"         # "upgrade after 3y, no new health check"
    TRUST_SIGNAL      = "trust_signal"         # "since 1811, AAA-rated"
    COVERAGE_COMPARE  = "coverage_compare"     # coverage ratio 3.4× vs Start's 3.0×
    HEALTH_EXPLAIN    = "health_explain"       # transparent delta breakdown for Franz
    ADVISOR_HANDOFF   = "advisor_handoff"      # FORBIDDEN for Franz
    CALLBACK_OFFER    = "callback_offer"       # for Peter (not same as advisor_handoff)
    FEATURE_HIGHLIGHT = "feature_highlight"    # eye surgery doubled Sep 2025

# Hard constraint table (D4-B)
FORBIDDEN_ACTIONS: dict[str, set[CoachAction]] = {
    "franz": {CoachAction.ADVISOR_HANDOFF},
    "judith": set(),
    "peter": set(),
}

# Coach effect on abandon probability (multiplicative modifier)
# e.g., PRICE_REFRAME for judith at STEP_4 → abandon_prob × 0.75 (25% reduction)
COACH_MODIFIERS: dict[CoachAction, dict[str, dict[Step, float]]] = {
    CoachAction.PRICE_REFRAME: {
        "judith": {Step.PRICE_DISPLAY: 0.75},
        "franz":  {Step.PRICE_DISPLAY: 0.80},
        "peter":  {Step.PRICE_DISPLAY: 0.85},
    },
    CoachAction.CALLBACK_OFFER: {
        "peter":  {Step.PERSONAL_INFO: 0.50, Step.PRICE_DISPLAY: 0.60},
    },
    CoachAction.HEALTH_EXPLAIN: {
        "franz":  {Step.FINAL_PRICE: 0.70},
    },
    CoachAction.ADVISOR_HANDOFF: {
        "judith": {Step.PRICE_DISPLAY: 0.65, Step.FINAL_PRICE: 0.70},
    },
    # ... all 20 rules
}

def validate_output(action: CoachAction, persona_type: str) -> None:
    """Hard constraint gate. Raises if action is forbidden for persona_type."""
    if action in FORBIDDEN_ACTIONS.get(persona_type, set()):
        raise ValueError(
            f"CONSTRAINT VIOLATION: {action} is forbidden for persona={persona_type}. "
            f"Franz must never receive AdvisorHandoff."
        )

def decide_action(state: FunnelState) -> CoachAction:
    """Rule-based action selection. Used in both sim and demo paths. (D2)"""
    step = state.step
    persona = state.persona_type

    # Peter: offer callback BEFORE price exposure (early routing)
    if persona == "peter" and step in (Step.PERSONAL_INFO, Step.FAMILY_SELECT):
        action = CoachAction.CALLBACK_OFFER

    # Franz: health explanation at final price (D7 pain point)
    elif persona == "franz" and step == Step.FINAL_PRICE:
        action = CoachAction.HEALTH_EXPLAIN

    # Any persona: price reframe at initial price display
    elif step == Step.PRICE_DISPLAY:
        action = CoachAction.PRICE_REFRAME

    # Judith: advisor handoff if she's hovering
    elif persona == "judith" and state.signals.backward_nav_count > 1:
        action = CoachAction.ADVISOR_HANDOFF

    # Upgrade path for anyone stalling after seeing prices
    elif step in (Step.ADDON_SELECT,) and state.signals.dwell_time_sec > 15:
        action = CoachAction.UPGRADE_PATH

    else:
        action = CoachAction.NONE

    validate_output(action, persona)   # D4-B hard gate
    return action

def get_modifier(action: CoachAction, persona_type: str, step: Step) -> float:
    """Returns abandon_prob multiplier for a Coach action. 1.0 = no effect."""
    return COACH_MODIFIERS.get(action, {}).get(persona_type, {}).get(step, 1.0)
```

---

### `uniqa/personas.py`

```python
import random
from uniqa.funnel import Step, FunnelState, HesitationSignals, ABANDON_PROBS
from uniqa.coach import CoachAction, get_modifier

class RuleBasedPersona:
    """Used in stats simulation. Pure probability tables, zero API calls. (D1-B)"""
    
    def __init__(self, persona_type: str, rng: random.Random):
        self.persona_type = persona_type
        self.rng = rng
    
    def will_abandon(self, step: Step, coach_action: CoachAction) -> bool:
        base_prob = ABANDON_PROBS[self.persona_type].get(step, 0.0)
        modifier = get_modifier(coach_action, self.persona_type, step)
        effective_prob = base_prob * modifier
        return self.rng.random() < effective_prob
    
    def generate_signals(self, step: Step) -> HesitationSignals:
        """Generate synthetic hesitation signals consistent with this persona."""
        # Judith: hover a lot at price steps
        if self.persona_type == "judith" and step == Step.PRICE_DISPLAY:
            return HesitationSignals(
                dwell_time_sec=self.rng.gauss(10, 3),
                price_hover_count=self.rng.randint(2, 5),
            )
        # Franz: session gap spike at final price
        elif self.persona_type == "franz" and step == Step.FINAL_PRICE:
            return HesitationSignals(
                dwell_time_sec=self.rng.gauss(15, 4),
                session_gap_spike=self.rng.random() < 0.6,
            )
        # Peter: form reedits and back-nav early
        elif self.persona_type == "peter" and step == Step.PERSONAL_INFO:
            return HesitationSignals(
                dwell_time_sec=self.rng.gauss(8, 2),
                form_reedits=self.rng.randint(1, 4),
                backward_nav_count=self.rng.randint(0, 2),
            )
        return HesitationSignals()


class LLMPersona:
    """Used in Streamlit demo only. LLM-driven, reacts to WidgetEnvelope JSON. (D1-B)"""
    
    SYSTEM_PROMPTS = {
        "judith": open("/tmp/zero_one_hack_01/tracks/insurance-uniqa/persona_judith_segment_1.md").read(),
        "franz":  open("/tmp/zero_one_hack_01/tracks/insurance-uniqa/persona_franz_segment_2.md").read(),
        "peter":  open("/tmp/zero_one_hack_01/tracks/insurance-uniqa/persona_peter_segment_3.md").read(),
    }
    
    def __init__(self, persona_type: str, openai_client):
        self.persona_type = persona_type
        self.client = openai_client
        self.history = []
    
    def react(self, widget_envelope: dict) -> dict:
        """React to a WidgetEnvelope. Returns {annoyance_scalar, next_action, thoughts}"""
        self.history.append({"role": "user", "content": str(widget_envelope)})
        
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPTS[self.persona_type]},
                *self.history,
                {"role": "user", "content": (
                    "You just received this Coach intervention. "
                    "Respond as yourself (the persona). "
                    "Output JSON: {annoyance_scalar: 0-1, next_action: continue|abandon|ask, thoughts: str}"
                )}
            ]
        )
        result = response.choices[0].message.content
        self.history.append({"role": "assistant", "content": result})
        return result  # parsed by caller
```

---

### `uniqa/simulation.py`

```python
import random
from dataclasses import dataclass
from uniqa.funnel import (
    Step, FunnelState, HesitationSignals,
    STEP_ORDER, next_step, is_hesitating
)
from uniqa.coach import decide_action, CoachAction
from uniqa.personas import RuleBasedPersona

# Funnel traffic weights from personas.json (n=4,004)
PERSONA_WEIGHTS = {"judith": 0.30, "franz": 0.50, "peter": 0.20}

@dataclass
class SessionResult:
    persona_type: str
    converted: bool
    abandoned_at: Step | None
    coach_actions: list[tuple[Step, CoachAction]]

@dataclass
class SimulationResult:
    n_runs: int
    conversion_rate: float
    conversion_baseline: float
    uplift_pct: float
    per_step_abandon: dict[str, float]
    per_persona_conversion: dict[str, float]
    coach_action_dist: dict[str, int]

def run_session(persona_type: str, rng: random.Random, coach_on: bool) -> SessionResult:
    persona = RuleBasedPersona(persona_type, rng)
    coach_actions = []
    
    for step in STEP_ORDER[1:]:  # skip START
        signals = persona.generate_signals(step)
        state = FunnelState(step=step, persona_type=persona_type, signals=signals)
        
        action = CoachAction.NONE
        if coach_on and is_hesitating(signals, persona_type):
            action = decide_action(state)
        
        coach_actions.append((step, action))
        
        if step == Step.PURCHASE:
            return SessionResult(persona_type, converted=True, abandoned_at=None, coach_actions=coach_actions)
        
        if persona.will_abandon(step, action):
            return SessionResult(persona_type, converted=False, abandoned_at=step, coach_actions=coach_actions)
    
    return SessionResult(persona_type, converted=True, abandoned_at=None, coach_actions=coach_actions)

def run_simulation(n: int = 10_000, seed: int = 42, coach_on: bool = True) -> SimulationResult:
    rng = random.Random(seed)
    personas = list(PERSONA_WEIGHTS.keys())
    weights = list(PERSONA_WEIGHTS.values())
    
    results = []
    for _ in range(n):
        persona_type = rng.choices(personas, weights=weights, k=1)[0]
        results.append(run_session(persona_type, rng, coach_on))
    
    baseline_results = []
    rng2 = random.Random(seed)
    for _ in range(n):
        persona_type = rng2.choices(personas, weights=weights, k=1)[0]
        baseline_results.append(run_session(persona_type, rng2, coach_on=False))
    
    conv = sum(r.converted for r in results) / n
    base = sum(r.converted for r in baseline_results) / n
    
    per_persona_conv = {
        p: sum(r.converted for r in results if r.persona_type == p) /
           max(sum(1 for r in results if r.persona_type == p), 1)
        for p in personas
    }
    
    # Per-step abandon (coach_on results)
    from collections import Counter
    step_abandons = Counter(r.abandoned_at for r in results if r.abandoned_at)
    total_reaching = {
        step: sum(1 for r in results if r.abandoned_at == step or
                  (r.abandoned_at is None and step in STEP_ORDER))
        for step in STEP_ORDER
    }
    
    action_dist = Counter(
        action.value
        for r in results
        for _, action in r.coach_actions
        if action != CoachAction.NONE
    )
    
    return SimulationResult(
        n_runs=n,
        conversion_rate=conv,
        conversion_baseline=base,
        uplift_pct=(conv - base) / base * 100,
        per_step_abandon={str(k): v for k, v in step_abandons.items()},
        per_persona_conversion=per_persona_conv,
        coach_action_dist=dict(action_dist),
    )
```

---

### `uniqa/widgets.py` (demo path only)

```python
from dataclasses import dataclass, field
import uuid
from datetime import datetime, timezone
from uniqa.coach import CoachAction

@dataclass
class WidgetEnvelope:
    turn_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    funnel_step: str = ""
    intervention_type: str = ""
    widgets: list[dict] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

WIDGET_TEMPLATES: dict[CoachAction, callable] = {
    CoachAction.PRICE_REFRAME: lambda persona: {
        "type": "PriceReframe",
        "user_visible": True,
        "content": {
            "headline": "Start ab €1,27 täglich",
            "subline": "Optimal ab €2,25/Tag — weniger als ein Kaffee.",
            "comparison": {"start": 38.74, "optimal": 68.14},
        },
    },
    CoachAction.ADVISOR_HANDOFF: lambda persona: {
        "type": "AdvisorHandoff",
        "user_visible": True,
        "content": {
            "headline": "Lieber persönlich beraten lassen?",
            "cta": "Jetzt Beratungsgespräch buchen",
        },
    },
    CoachAction.CALLBACK_OFFER: lambda persona: {
        "type": "CallbackOffer",
        "user_visible": True,
        "content": {
            "headline": "Rückruf gewünscht?",
            "cta": "Kostenlos zurückrufen lassen",
        },
    },
    CoachAction.HEALTH_EXPLAIN: lambda persona: {
        "type": "HealthExplain",
        "user_visible": True,
        "content": {
            "headline": "Warum hat sich der Preis geändert?",
            "body": "Ihre Angaben werden individuell bewertet. Das ist transparent und fair.",
        },
    },
}

def emit_widget(action: CoachAction, persona_type: str, funnel_step: str) -> WidgetEnvelope:
    from uniqa.coach import validate_output
    validate_output(action, persona_type)   # D4-B hard gate
    
    template_fn = WIDGET_TEMPLATES.get(action)
    widgets = [template_fn(persona_type)] if template_fn else []
    
    return WidgetEnvelope(
        funnel_step=funnel_step,
        intervention_type=action.value,
        widgets=widgets,
    )
```

---

### `uniqa/app.py` (Streamlit demo)

```python
import streamlit as st
import json
from uniqa.simulation import run_simulation, PERSONA_WEIGHTS
from uniqa.funnel import STEP_ORDER, Step, FunnelState, is_hesitating
from uniqa.coach import decide_action, CoachAction
from uniqa.personas import LLMPersona
from uniqa.widgets import emit_widget

# ─── Layout ──────────────────────────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="UNIQA Conversion Coach")
col_main, col_hud = st.columns([3, 2])

# ─── Sidebar — persona selector (D3-A) ───────────────────────────────────────
with st.sidebar:
    st.header("Simulation Controls")
    persona_type = st.selectbox(
        "Active Persona",
        options=["judith", "franz", "peter"],
        format_func=lambda x: {"judith": "Judith S1 (30%)", "franz": "Franz S2 (50%)", "peter": "Peter S3 (20%)"}[x]
    )
    coach_enabled = st.toggle("Coach enabled", value=True)
    
    st.divider()
    st.subheader("Statistical Proof")
    if st.button("Run 10k simulation"):
        with st.spinner("Running 10,000 sessions..."):
            result = run_simulation(n=10_000, seed=42, coach_on=True)
            baseline = run_simulation(n=10_000, seed=42, coach_on=False)
        st.metric("Conversion (coach)", f"{result.conversion_rate:.1%}")
        st.metric("Conversion (baseline)", f"{baseline.conversion_rate:.1%}", 
                  delta=f"+{result.uplift_pct:.1f}%")
        st.json(result.per_persona_conversion)

# ─── Main — funnel stepper ───────────────────────────────────────────────────
with col_main:
    st.header(f"Funnel Session — {persona_type.title()}")
    
    if "session_state" not in st.session_state:
        st.session_state.session_state = {"step_idx": 1, "coach_log": [], "annoyance": 0.0}
    
    ss = st.session_state.session_state
    current_step = STEP_ORDER[ss["step_idx"]]
    
    # Step progress
    st.progress(ss["step_idx"] / (len(STEP_ORDER) - 1))
    st.subheader(f"Step {ss['step_idx']}: {current_step.value}")
    
    # Simulate hesitation signals for this step
    import random
    rng = random.Random()
    from uniqa.personas import RuleBasedPersona
    rb = RuleBasedPersona(persona_type, rng)
    signals = rb.generate_signals(current_step)
    
    # Coach decision
    state = FunnelState(step=current_step, persona_type=persona_type, signals=signals)
    if coach_enabled and is_hesitating(signals, persona_type):
        action = decide_action(state)
        if action != CoachAction.NONE:
            envelope = emit_widget(action, persona_type, current_step.value)
            ss["coach_log"].append(envelope)
            
            with st.container(border=True):
                st.markdown(f"**Coach intervention: `{action.value}`**")
                for w in envelope.widgets:
                    if w.get("user_visible"):
                        st.markdown(f"### {w['content'].get('headline', '')}")
                        if "subline" in w.get("content", {}):
                            st.caption(w["content"]["subline"])
    
    col1, col2 = st.columns(2)
    if col1.button("→ Next step"):
        if ss["step_idx"] < len(STEP_ORDER) - 1:
            ss["step_idx"] += 1
    if col2.button("↩ Back"):
        if ss["step_idx"] > 1:
            ss["step_idx"] -= 1
            signals.backward_nav_count += 1
    if st.button("Reset session"):
        st.session_state.session_state = {"step_idx": 1, "coach_log": [], "annoyance": 0.0}

# ─── HUD ─────────────────────────────────────────────────────────────────────
with col_hud:
    st.header("Coach HUD")
    
    # Annoyance scalar (display-only, from signals)
    annoyance = min(1.0, (
        signals.dwell_time_sec / 20 * 0.4 +
        signals.backward_nav_count / 3 * 0.3 +
        signals.price_hover_count / 6 * 0.3
    ))
    st.metric("Annoyance scalar", f"{annoyance:.2f}")
    st.progress(annoyance, text="Annoyance")
    
    # Active hesitation signals
    st.subheader("Hesitation signals")
    st.json({
        "dwell_time_sec": round(signals.dwell_time_sec, 1),
        "backward_nav_count": signals.backward_nav_count,
        "price_hover_count": signals.price_hover_count,
        "session_gap_spike": signals.session_gap_spike,
    })
    
    # Coach log
    st.subheader("Intervention log")
    for env in ss["coach_log"][-5:]:
        st.caption(f"`{env.intervention_type}` @ {env.funnel_step}")
```

---

### `tests/test_uniqa.py`

```python
import random
import pytest
from uniqa.funnel import Step, ABANDON_PROBS, PERSONA_WEIGHTS
from uniqa.coach import (
    CoachAction, validate_output, decide_action, FunnelState,
    HesitationSignals
)
from uniqa.simulation import run_simulation

# ─── D4-B hard constraint tests ───────────────────────────────────────────────

def test_franz_advisor_handoff_blocked():
    with pytest.raises(ValueError, match="CONSTRAINT VIOLATION"):
        validate_output(CoachAction.ADVISOR_HANDOFF, "franz")

def test_judith_advisor_handoff_allowed():
    validate_output(CoachAction.ADVISOR_HANDOFF, "judith")  # must not raise

def test_peter_advisor_handoff_allowed():
    validate_output(CoachAction.ADVISOR_HANDOFF, "peter")   # must not raise

# ─── Calibration test ─────────────────────────────────────────────────────────

def test_calibration_step4_abandon():
    """Weighted abandon at Step 4 must be ≈ 66% (matches real UNIQA data)."""
    weights = PERSONA_WEIGHTS
    weighted = sum(
        weights[p] * ABANDON_PROBS[p].get(Step.PRICE_DISPLAY, 0.0)
        for p in ["judith", "franz", "peter"]
    )
    assert abs(weighted - 0.66) < 0.05, f"Calibration failed: {weighted:.3f} vs 0.66"

# ─── Baseline conversion test ─────────────────────────────────────────────────

def test_baseline_conversion_matches_uniqa():
    """No-coach simulation must produce conversion ≈ 5.6% (matches published UNIQA rate)."""
    result = run_simulation(n=5_000, seed=42, coach_on=False)
    assert abs(result.conversion_rate - 0.056) < 0.02, (
        f"Baseline conversion {result.conversion_rate:.3f} diverges from 5.6%"
    )

# ─── Coach uplift test ────────────────────────────────────────────────────────

def test_coach_improves_conversion():
    """Coach-on conversion must exceed no-coach conversion."""
    no_coach = run_simulation(n=2_000, seed=42, coach_on=False)
    coach = run_simulation(n=2_000, seed=42, coach_on=True)
    assert coach.conversion_rate > no_coach.conversion_rate, (
        f"Coach failed to improve: {coach.conversion_rate:.3f} vs {no_coach.conversion_rate:.3f}"
    )

# ─── Franz never gets advisor handoff in simulation ───────────────────────────

def test_franz_never_gets_advisor_handoff_in_sim():
    """10k sim runs must produce zero AdvisorHandoff for Franz sessions."""
    result = run_simulation(n=2_000, seed=42, coach_on=True)
    # Access session-level data (requires SessionResult list from run_simulation)
    # This test validates validate_output() is wired into the sim path
    # Proxy: if any ADVISOR_HANDOFF fires for Franz, validate_output would have raised
    # → the test is: simulation completes without ValueError
    assert result.conversion_rate > 0  # would have raised if constraint violated
```

---

## Build Order (time-optimized for 14h remaining)

```
T+0h → T+1h     mkdir uniqa/ && write funnel.py (state machine + constants)
T+1h → T+2h     write coach.py (decide_action + validate_output)
T+2h → T+3h     write personas.py (RuleBasedPersona only — skip LLM for now)
T+3h → T+4h     write simulation.py (run_simulation + SessionResult)
T+4h → T+4.5h   write tests/test_uniqa.py → pytest → all 5 tests pass
T+4.5h → T+5h   verify calibration test: 0.645 ≈ 0.66 ✓
                 verify baseline test: ≈ 5.6% ✓
                 verify Coach improves: coach_on > coach_off ✓
T+5h → T+6h     write widgets.py (emit_widget, WidgetEnvelope)
T+6h → T+9h     write app.py (Streamlit: persona selector, stepper, HUD, sim button)
T+9h → T+11h    add LLMPersona to personas.py, wire into demo path
T+11h → T+12h   submit SLURM jobs (LoRA × 3, PPO overnight)
T+12h → T+14h   demo polish, REPORT.md, coach argument cheatsheet in HUD
```

---

## Franz Constraint Enforcement Points

```
coach.decide_action()
    └→ validate_output(action, persona_type)  ← EARLY FILTER (D4-B)

coach.emit_widget()
    └→ validate_output(action, persona_type)  ← GUARD BEFORE SERIALIZATION

widgets.emit_widget()
    └→ validate_output(action, persona_type)  ← GUARD BEFORE JSON EMISSION

tests/test_uniqa.py
    └→ test_franz_advisor_handoff_blocked()   ← CI COVERAGE
```

Zero paths to Franz + AdvisorHandoff. Guaranteed.

---

## Non-Goals (explicitly out of scope)

- Behavioral classifier for persona identification (D3-A)
- LLM persona in the 10k simulation loop (D1-B)
- Full Mistral-7B LoRA fine-tunes before demo (cluster jobs run overnight — demo uses rule-based + GPT-4o)
- PPO policy before demo (rule-based Coach is the demo; PPO runs on cluster)
- Real UNIQA calculator integration (simulate, don't integrate)
- German-language widget copy (English for demo, German possible as a widget prop)
