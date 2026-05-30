# UNIQA Decision-State Engine — System Frame + cadCAD Architecture
> 2026-05-30 | Post-CDP funnel spike + System Frame integration

---

## Funnel Spike Findings (live CDP walkthrough)

```
Step 1: "Wo möchten Sie abgesichert sein?"
  → Bei Arztbesuchen ✓ (in-scope) | Im Krankenhaus (out-of-scope)
  UI: Checkbox cards. Both clickable. Validation fires if neither selected.
  Signal: which card gets hovered first (intent signal before click)

Step 2: "Wer soll versichert werden?"
  → Ich selbst ✓ (in-scope) | Andere Personen (out-of-scope → advisor route)
  UI: Radio cards. Single selection.
  Signal: dwell time before choice (uncertainty proxy)

Step 3: "Um eine voraussichtliche individuelle Prämie für Sie zu berechnen"
  → Geburtsdatum (TT.MM.JJJJ) + Sozialversicherung (ÖGK, BVAEB-OEB, SVS, BVAEB-EB, KFA...)
  UI: Angular date input + ng-select custom dropdown (NOT native select)
  Signal: form-reedits on birthdate, dropdown open/close without selection, time-on-field
  Note: date validation is client-side, format TT.MM.JJJJ enforced

Step 4: "Welche Leistungen soll Ihre Privatarzt-Versicherung abdecken?" ← 66% ABANDON
  UI: Tariff comparison table (Start/Optimal/Opt.Plus/Premium)
  UNIQA's OWN trust signal already present: "Nach 3 Jahren können Sie wechseln, ohne erneute Gesundheitsprüfung"
  "Online abschließbar" badge only on Start + Optimal
  Coverage amounts:
    Start:   €1,400/yr | Arztleistungen €1,120 | ...
    Optimal: €2,800/yr | Arztleistungen €1,400 | ...
    Opt.Plus: €4,200/yr | Nur nach Beratung
    Premium:  €8,400/yr | Nur nach Beratung
  Signal: scroll depth on table, hover over Opt.Plus/Premium (upgrade intent),
          time before clicking Weiter, hover on info (ℹ) icons

Breadcrumb macro-phases: Angaben → Produkt → Empfehlung → Abschluss
```

**Key insight from spike:** The live calculator is Angular SPA. All form state is in Angular component tree, not in native DOM inputs. CDP interaction requires:
1. Click Angular `label` elements (not `input` directly) for checkboxes
2. Use `ng-select` custom dropdowns (click trigger button → find DFN text node → click)
3. Date format enforced: TT.MM.JJJJ (not ISO 8601)
4. Weiter/Zurück navigate Angular router steps — same URL, different component state

**What UNIQA already has baked in as Coach-equivalents:**
- "Nach 3 Jahren können Sie wechseln" — pre-empts the upgrade-path objection
- "Online abschließbar" badge — guides toward in-scope tariffs
- ℹ icons on coverage categories — comprehension support

Our Coach's job: fill the gaps at the behavioral signals level, not add more static copy.

---

## System Frame (Decision-State Engine)

### Core premise
Insurance purchase = accumulation of micro-decisions. Engine never assumes readiness — it *estimates* it and acts to advance it by the *smallest sufficient increment*.

### User State (three layers)

```
Layer 1: FACTUAL (quote_state) — objective, monotonically accumulating
  coverage_type: "arzt" | "krankenhaus" | "both"
  insured_persons: "myself" | "family"
  birthdate: date
  sozialversicherung: "ÖGK" | "BVAEB-OEB" | "SVS" | ...
  tariff_selected: "Start" | "Optimal" | null
  addons: list[str]
  health_answers: dict[str, any]  # filled late in funnel
  final_price_shown: float | null
  current_step: Step

Layer 2: READINESS (latent belief, inferred not observed)
  intent_type:       "purchase" | "orientation" | "comparison" | "price_check"
  proximity:         float  # 0.0 cold → 1.0 hot (distance to purchase)
  trust:             float  # in UNIQA brand + online channel
  price_acceptance:  float  # tolerance vs. sticker-shock risk
  comprehension:     float  # does user understand what they're buying
  confidence:        float  # decision certainty
  friction_tolerance:float  # patience for remaining effort
  channel_lean:      float  # 0.0 = online, 1.0 = advisor
  urgency:           float  # life-event pressure
  frustration:       float  # cumulative negative affect
  satisfaction:      float  # cumulative positive affect

Layer 3: CONTEXT (brand/policy frame, static per session)
  product_scope: ["Start", "Optimal"]   # online purchasable only
  brand_voice: {"formal": True, "Austrian": True, "no_exclamation": True}
  message_budget: int     # max interventions before annoyance risk
  message_count: int      # interventions fired this session
  ltv_horizon: True       # prefer preserved trust over short-term conversion
  channel_economics: {"online": 1.0, "advisor": 0.3}  # conversion value weights
```

### Mechanism (state machine + feedback loop)

```
┌─────────────────────────────────────────────────────────────────────┐
│  USER ACTION                                                         │
│  (click, hover, scroll, dwell, back-nav, field-edit, tab-open)      │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ behavioral_signal
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  SIGNAL PROCESSOR                                                    │
│  Raw signal → typed SignalEvent                                      │
│  {signal_type, step, value, timestamp}                              │
│  Also: frustration_score(signals) + satisfaction_score(signals)      │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ SignalEvent
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  BELIEF UPDATER                                                      │
│  readiness_state_t+1 = update(readiness_t, signal, quote_state)     │
│  Pluggable: Bayesian | trained classifier | rule-based               │
│  Key: gap between inferred belief and true hidden state is a        │
│       quality metric tracked across simulation runs                 │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ updated readiness_state
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  POLICY                                                              │
│  given (factual, readiness, context) → NextBestAction               │
│  OR deliberate no-op (respect message_budget / annoyance ceiling)   │
│                                                                      │
│  Action types:                                                       │
│  - UX widget (price reframe, trust signal, upgrade path)            │
│  - Channel switch (advisor handoff, callback offer)                 │
│  - Nurture (email follow-up if session times out)                   │
│  - No-op (annoyance budget exceeded or user in flow)                │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ NextBestAction
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ACTION EXECUTOR                                                     │
│  Demo: emit widget JSON → Streamlit renderer                        │
│  Sim:  return action enum → RuleBasedPersona reacts                 │
│  Prod: inject component into live Angular calculator                │
└─────────────────────────────────────────────────────────────────────┘
                            │ user_reaction (demo/sim) or AB_result (prod)
                            └────────────────────────────────────────────┐
                                                                         │
                                   NEXT TICK ◄────────────────────────────┘
```

---

## cadCAD-ri Architecture

cadCAD maps perfectly to this: **Spaces are state schemas, Blocks are transition functions, Experiments are simulation runs.**

```python
from cadcad.spaces import space, Space
from cadcad.points import Point
from cadcad.dynamics import block
from cadcad.systems import Experiment

# ─── SPACES (typed state containers) ──────────────────────────────────────────

@space
class FactualState:
    coverage_type: str        # "arzt" | "krankenhaus" | "both"
    insured: str              # "myself" | "family"
    step: int                 # 1-15 (funnel step index)
    tariff: str               # "" | "Start" | "Optimal"
    price_shown: float        # 0.0 if not yet shown
    sozialversicherung: str   # "ÖGK" | ...

@space
class ReadinessState:
    proximity: float          # 0.0 → 1.0
    trust: float
    price_acceptance: float
    comprehension: float
    confidence: float
    channel_lean: float       # 0.0=online, 1.0=advisor
    frustration: float
    satisfaction: float
    intent_type: str          # "purchase"|"orientation"|"comparison"|"price_check"
    message_count: int        # interventions fired this session

@space
class SignalEvent:
    signal_type: str          # "dwell"|"back_nav"|"hover"|"price_hover"|"tab_open"|...
    value: float              # normalized intensity [0,1]
    step: int
    persona_type: str         # "judith"|"franz"|"peter"

@space
class ActionEvent:
    action_type: str          # "price_reframe"|"upgrade_path"|"callback"|"no_op"|...
    widget_type: str          # widget class name for renderer
    message_budget_consumed: int
    confidence: float         # policy confidence in this action

@space
class OutcomeEvent:
    converted: bool
    abandoned: bool
    abandoned_at_step: int
    channel: str              # "online"|"advisor"|"timeout"
    readiness_at_exit: float  # proximity score at session end

# Combined user session state = FactualState * ReadinessState
UserSessionState = FactualState + ReadinessState


# ─── BLOCKS (transition functions) ────────────────────────────────────────────

@block
def signal_processor(session: Point[UserSessionState]) -> Point[SignalEvent]:
    """
    Generate a behavioral signal from current session state.
    In simulation: persona generates synthetic signal from hidden true state.
    In production: real browser event → typed signal.
    """
    from uniqa.personas import RuleBasedPersona
    import random
    rng = random.Random()

    # Extract state
    step = session.data["step"]
    persona = session.data.get("persona_type", "franz")
    rb = RuleBasedPersona(persona, rng)
    signals = rb.generate_signals_at_step(step)

    return Point(SignalEvent, {
        "signal_type": signals.dominant_signal_type(),
        "value": signals.intensity(),
        "step": step,
        "persona_type": persona,
    })


@block
def belief_updater(signal: Point[SignalEvent]) -> Point[ReadinessState]:
    """
    Bayesian-style belief update on readiness parameters given new signal.
    Pluggable: replace rule-based update with trained classifier.
    """
    s = signal.data
    step = s["step"]
    persona = s["persona_type"]

    # Load current readiness (in real cadCAD this would be stateful)
    # Here: default priors per persona (from personas.json survey data)
    PRIORS = {
        "judith": {"proximity": 0.45, "trust": 0.75, "price_acceptance": 0.55,
                   "channel_lean": 0.70, "frustration": 0.10},
        "franz":  {"proximity": 0.60, "trust": 0.55, "price_acceptance": 0.60,
                   "channel_lean": 0.10, "frustration": 0.10},
        "peter":  {"proximity": 0.25, "trust": 0.40, "price_acceptance": 0.45,
                   "channel_lean": 0.60, "frustration": 0.20},
    }
    r = dict(PRIORS[persona])

    # Update rules — Bayesian-flavored
    if s["signal_type"] == "back_nav":
        r["frustration"] = min(1.0, r["frustration"] + 0.15)
        r["confidence"] = max(0.0, r.get("confidence", 0.5) - 0.10)
    elif s["signal_type"] == "dwell_long":
        r["comprehension"] = min(1.0, r.get("comprehension", 0.5) + 0.10)
        # long dwell ambiguous: either reading carefully or overwhelmed
        r["frustration"] = min(1.0, r["frustration"] + 0.05 * s["value"])
    elif s["signal_type"] == "price_hover":
        r["price_acceptance"] = max(0.0, r["price_acceptance"] - 0.08)
    elif s["signal_type"] == "tab_open":
        r["proximity"] = max(0.0, r["proximity"] - 0.12)  # comparison intent = not ready
    elif s["signal_type"] == "field_complete":
        r["proximity"] = min(1.0, r["proximity"] + 0.08)
        r["frustration"] = max(0.0, r["frustration"] - 0.05)

    # Step-specific prior adjustments
    if step == 4:  # price display — critical
        r["price_acceptance"] = max(0.0, r["price_acceptance"] - 0.05)

    return Point(ReadinessState, {
        **r,
        "comprehension": r.get("comprehension", 0.5),
        "confidence": r.get("confidence", 0.5),
        "satisfaction": max(0.0, 1.0 - r["frustration"] - 0.2),
        "intent_type": "purchase" if r["proximity"] > 0.7 else "orientation",
        "message_count": r.get("message_count", 0),
    })


@block
def policy(readiness: Point[ReadinessState]) -> Point[ActionEvent]:
    """
    Given current readiness belief → select next best action.
    Respects message_budget (annoyance ceiling = 3 per session).
    """
    r = readiness.data
    MESSAGE_BUDGET = 3

    if r["message_count"] >= MESSAGE_BUDGET:
        return Point(ActionEvent, {
            "action_type": "no_op",
            "widget_type": "NoOp",
            "message_budget_consumed": r["message_count"],
            "confidence": 1.0,
        })

    # Peter: route to advisor immediately (before price shock)
    if r["channel_lean"] > 0.55 and r["proximity"] < 0.40:
        action = "callback_offer"
        widget = "CallbackOffer"

    # High frustration: reduce friction immediately
    elif r["frustration"] > 0.60:
        action = "friction_reducer"
        widget = "TrustSignal"

    # Low price acceptance: reframe price
    elif r["price_acceptance"] < 0.45:
        action = "price_reframe"
        widget = "PriceReframe"

    # Low comprehension: explain coverage
    elif r.get("comprehension", 0.5) < 0.40:
        action = "comprehension_boost"
        widget = "CoverageExplainer"

    # Judith: high trust, offer advisor path smoothly
    elif r["channel_lean"] > 0.40 and r["trust"] > 0.65:
        action = "advisor_handoff"
        widget = "AdvisorHandoff"

    # Franz: price transparency at final step
    elif r["proximity"] > 0.70 and r["price_acceptance"] < 0.55:
        action = "health_explain"
        widget = "HealthExplain"

    # Default: no intervention
    else:
        action = "no_op"
        widget = "NoOp"

    return Point(ActionEvent, {
        "action_type": action,
        "widget_type": widget,
        "message_budget_consumed": r["message_count"] + (0 if action == "no_op" else 1),
        "confidence": 0.75,
    })


@block
def persona_reactor(action: Point[ActionEvent]) -> Point[OutcomeEvent]:
    """
    Persona reacts to Coach action from its hidden true state.
    The gap between policy's inferred belief and persona's true state
    is the quality metric tracked across simulation runs.
    """
    import random
    from uniqa.coach import COACH_MODIFIERS, CoachAction
    from uniqa.funnel import ABANDON_PROBS, Step

    a = action.data
    # Minimal outcome simulation — proper version reads full session state
    return Point(OutcomeEvent, {
        "converted": False,  # placeholder — real version uses step + persona probs
        "abandoned": a["action_type"] == "no_op",
        "abandoned_at_step": 4,
        "channel": "online",
        "readiness_at_exit": 0.5,
    })


# ─── EXPERIMENT (simulation entry point) ─────────────────────────────────────

def run_cadcad_experiment(
    persona_type: str = "franz",
    n_iterations: int = 1000,
    n_steps: int = 8,
) -> list:
    """
    Run cadCAD simulation for one persona type.
    Each iteration = one user session.
    Each step = one funnel step (up to 8).
    """
    from cadcad.points import Point

    init_state = Point(UserSessionState, {
        # FactualState dimensions
        "coverage_type": "arzt",
        "insured": "myself",
        "step": 1,
        "tariff": "",
        "price_shown": 0.0,
        "sozialversicherung": "",
        # ReadinessState dimensions
        "proximity": {"judith": 0.45, "franz": 0.60, "peter": 0.25}[persona_type],
        "trust": {"judith": 0.75, "franz": 0.55, "peter": 0.40}[persona_type],
        "price_acceptance": {"judith": 0.55, "franz": 0.60, "peter": 0.45}[persona_type],
        "comprehension": 0.50,
        "confidence": 0.50,
        "channel_lean": {"judith": 0.70, "franz": 0.10, "peter": 0.60}[persona_type],
        "frustration": 0.10,
        "satisfaction": 0.80,
        "intent_type": "orientation",
        "message_count": 0,
        # extra context
        "persona_type": persona_type,
    })

    experiment = Experiment(
        init_state=init_state,
        experiment_params={"iteration_n": n_iterations, "steps": n_steps},
        pipeline=(signal_processor, belief_updater, policy, persona_reactor),
    )

    return experiment.run()
```

**Note on cadCAD-ri wiring:** The current cadCAD-ri requires Space/Block type matching through the pipeline. The above sketch uses a simplified chaining. Full wiring requires each Block's codomain to match the next Block's domain exactly. In practice: wrap the multi-space session state as a single augmented Space, or use cadCAD's `*` cartesian product operator.

---

## Mini Models (what to train on Leonardo)

Three small models trained on synthetic simulation data + personas.json priors:

### Model 1: Frustration/Satisfaction Scorer
```
Input:  sequence of SignalEvents for this session so far
Output: (frustration: float, satisfaction: float, confidence: float)
Architecture: lightweight sequence model (LSTM or tiny Transformer)
Training data: synthetic sessions from cadCAD simulation + labeled outcomes
Size: ~500K params — trains in 20 min on 1× A100
```

### Model 2: Psychological Stage Classifier
```
Input:  ReadinessState vector (8 floats) + FactualState (step, tariff, price_shown)
Output: stage ∈ {"orienting", "evaluating", "hesitating", "deciding", "exiting"}
Architecture: shallow MLP (3 layers, 128 units)
Training data: cadCAD trajectory data with labeled conversion/abandon outcomes
Size: ~100K params — trains in 5 min on CPU
Purpose: maps continuous belief to discrete stage for coaching rules
```

### Model 3: Next-Best-Action Policy (RL)
```
Input:  (ReadinessState, FactualState, stage) → stage-conditioned state
Output: CoachAction (discrete action space, 8 actions)
Architecture: PPO or GRPO on top of Model 2's stage representation
Reward: conversion_uplift × (1 - annoyance_penalty)
Training: 100k simulation episodes from cadCAD experiment runs
HPC job: 8× A100, 10h (matches existing slurm_ppo.sh plan)
```

### Model 4: Cohort Segmenter (optional stretch)
```
Input:  session features up to current step (partial trajectory)
Output: predicted segment + confidence (judith/franz/peter + latent blend)
Architecture: gradient boosted classifier (LightGBM or tiny MLP)
Training: personas.json quantitative data + synthetic sessions
Purpose: enables cohort-level campaign simulation
```

---

## Cohort + Campaign Simulation (cadCAD Experiment design)

```python
# Define cohorts as parameter sweeps over initial belief distributions
COHORTS = {
    "high_value_hesitant": {  # Judith-like, high income, advisor-lean
        "proximity": (0.35, 0.55),      # range
        "trust": (0.70, 0.90),
        "channel_lean": (0.60, 0.85),
        "price_acceptance": (0.50, 0.70),
        "n": 500,
    },
    "digital_native_price_sensitive": {  # Franz-like
        "proximity": (0.55, 0.75),
        "trust": (0.40, 0.60),
        "channel_lean": (0.05, 0.20),
        "price_acceptance": (0.45, 0.65),
        "n": 1000,
    },
    "overwhelmed_service_seeker": {  # Peter-like
        "proximity": (0.15, 0.35),
        "trust": (0.30, 0.50),
        "channel_lean": (0.50, 0.75),
        "price_acceptance": (0.35, 0.55),
        "n": 400,
    },
}

# Marketing campaign = a Policy variant
CAMPAIGNS = {
    "baseline": "no_coach",
    "rule_based_coach": "rule_based",
    "rl_coach": "ppo_policy",
    "price_first_campaign": "price_reframe_always_at_step4",
    "advisor_routing_campaign": "aggressive_callback_for_high_channel_lean",
}

# cadCAD experiment: sweep cohorts × campaigns
# Result: (cohort, campaign) → conversion_rate, abandon_by_step, avg_messages_fired
# This is the "simulate marketing campaigns for cohorts" requirement
```

---

## User Labeling System

```python
@dataclass
class UserLabel:
    """Assigned at end of session or mid-session for live coaching."""
    session_id: str
    
    # Predicted segment
    primary_segment: str              # "judith"|"franz"|"peter"|"unknown"
    segment_confidence: float
    segment_blend: dict[str, float]   # {"judith": 0.6, "franz": 0.3, "peter": 0.1}
    
    # Psychological stage at exit
    stage_at_exit: str                # "orienting"|"evaluating"|"hesitating"|"deciding"|"exiting"
    
    # Readiness profile
    readiness_at_exit: ReadinessState
    frustration_peak: float           # max frustration observed in session
    
    # Outcome
    outcome: str                      # "converted"|"abandoned"|"advisor_routed"|"timeout"
    abandoned_at_step: int | None
    coach_actions_fired: list[str]
    
    # Cohort membership (for campaign targeting)
    cohorts: list[str]                # ["high_value_hesitant", "price_sensitive_digital"]

def label_session(trajectory: list[Point]) -> UserLabel:
    """Extract label from a completed cadCAD trajectory."""
    ...

def define_cohort(sessions: list[UserLabel], rules: dict) -> list[str]:
    """
    Return session_ids matching cohort criteria.
    Example: all sessions with frustration_peak > 0.6 AND price_acceptance < 0.5
    → cohort "sticker_shocked_high_frustration" → target with price reframe + soft offer
    """
    ...
```

---

## Eval Metrics (the jury-facing scorecard)

| Metric | What it measures | How computed |
|--------|-----------------|--------------|
| **Conversion uplift** | Does Coach improve online purchase rate? | (coach_conv - baseline_conv) / baseline_conv |
| **Per-persona conversion** | Does Coach generalize across segments? | Separate runs per persona type |
| **Intervention precision** | Did Coach fire at right moment? | % of fires that preceded positive step transition |
| **Annoyance rate** | Did Coach over-touch? | % of sessions where message_count > budget before conversion |
| **Belief calibration** | Is inferred readiness accurate? | Correlation: predicted_proximity vs. actual_outcome |
| **Stage accuracy** | Does classifier identify stage correctly? | Model 2 accuracy on held-out cadCAD trajectories |
| **Frustration peak reduction** | Does Coach lower frustration? | Mean frustration_peak: coach vs. no_coach |
| **Channel efficiency** | Are we routing the right people to advisors? | % of advisor routes that match high channel_lean users |

**Two calibration anchors (must pass before claiming results):**
1. `baseline_conversion ≈ 5.6%` → validates simulation matches real data
2. `step4_abandon_rate ≈ 66%` → validates persona priors are correctly calibrated

---

## File Structure (revised, incorporating cadCAD)

```
uniqa/
├── funnel.py              — Step enum, abandon probs, hesitation thresholds
├── coach.py               — CoachAction enum, decide_action, emit_widget, validate_output
├── personas.py            — RuleBasedPersona, LLMPersona, signal generation
├── belief.py              — BeliefUpdater, belief state update rules (pluggable)
├── policy.py              — Policy (rule-based → PPO → GRPO), message budget enforcement
├── widgets.py             — WidgetEnvelope, emit_widget, all 13 widget types
├── labels.py              — UserLabel, label_session, define_cohort
├── simulation.py          — run_simulation (fast, rule-based, seeded)
├── cadcad_sim.py          — cadCAD-ri experiment definition (Spaces, Blocks, Experiment)
├── models/
│   ├── frustration_scorer.py   — LSTM frustration/satisfaction model
│   ├── stage_classifier.py     — MLP stage classifier
│   └── rl_policy.py            — PPO/GRPO action policy
├── app.py                 — Streamlit demo (persona selector + funnel + HUD + sim button)
├── slurm_frustration.sh   — A100 job: frustration scorer training
├── slurm_stage.sh         — A100 job: stage classifier training
├── slurm_ppo.sh           — A100 job: PPO RL policy
└── tests/
    ├── test_uniqa.py      — 5 core tests (calibration, Franz constraint, uplift)
    └── test_cadcad.py     — cadCAD space/block/experiment smoke tests
```

---

## CDP Spike Conclusions

1. **Angular SPA** — all state in Angular component tree. Native DOM events work but need dispatching to Angular's change detection.
2. **ng-select dropdowns** — click the DFN text node inside the option, not the list item
3. **Date input** — `input[placeholder="TT.MM.JJJJ"]`, click + focus + type via CDP
4. **Step navigation** — Angular router, same URL. CDP `snap` is reliable for state reading.
5. **Key drop-off UX**: Step 4 (tariff comparison) shows all 4 tariffs including out-of-scope. UNIQA already has a trust signal here. Our Coach activates at the signal level.

**For a future CDP-based A/B test injection:** The Coach can inject a div before the tariff table by:
```javascript
// Inject Coach widget into live UNIQA calculator
const target = document.querySelector('[class*=product-comparison], [class*=tariff-table]');
const widget = document.createElement('div');
widget.innerHTML = COACH_WIDGET_HTML;
target.parentNode.insertBefore(widget, target);
```
This is NOT the hackathon demo path but shows the production injection point.
