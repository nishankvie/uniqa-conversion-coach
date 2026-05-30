# UNIQA Track — War Plan
> CEO Review output | Saturday 09:30 | Deadline Sunday 10:00 | 24.5h remaining

---

## Three Locked Decisions

| # | Decision | Locked |
|---|----------|--------|
| D1 | Scope | Core build + overnight cluster jobs. cadCAD/GRPO/widget model CUT. |
| D2 | Demo | Streamlit simulator + production vision slide. No live injection risk. |
| D3 | WhatsApp | Build Twilio prototype (1h). Peter abandonment → WA message on phone. |

---

## What the Jury Actually Evaluates (from intake doc, verbatim)

| # | Dimension | Metric |
|---|-----------|--------|
| 1 | **Conversion uplift** | Rate vs. baseline, drop-off reduction per step |
| 2 | **Persona differentiation** | Per-persona conversion, performance variation |
| 3 | **Intervention quality** | Trigger precision/recall, annoyance rate |

**The demo is scripted in the intake doc.** Build these exact scenarios:

```
FRANZ DEMO:
  Without Coach: sees Premium ("advisory required") → clicks → backs up → closes tab → ABANDON
  With Coach: backs up from Premium → Coach fires ("Premium needs advisory; Optimal is fully online")
              + market comparison → selects Optimal → completes → ✅ CONVERSION

JUDITH DEMO:
  Without Coach: sees final price (higher than estimate) → dwell + hover "cancel" → ABANDON
  With Coach: Coach fires on dwell + hover → explains price gap → reassures → completes → ✅ CONVERSION

PETER DEMO:
  Without Coach: overwhelmed at Step 3 → abandons before seeing price → ABANDON
  With Coach: Coach fires early → offers callback → WhatsApp message sent to Peter's phone → ✅ WA LEAD
```

---

## What's IN Scope

```
uniqa/
├── funnel.py          state machine (8 steps, per-persona transition probs)
├── personas.py        LLM persona bots (GPT-4 + full persona .md as system prompt)
│                      + RuleBasedPersona (for fast 1k-run stats)
├── coach.py           Detection layer + decision layer + validate_output()
├── simulation.py      1k-run A/B (rule-based personas, seeded, fast)
├── whatsapp.py        Twilio sandbox → Peter abandonment → WA message
├── app.py             Streamlit: side-by-side demo (3 scenarios)
├── slurm_lora.sh      Mistral-7B LoRA × 3 (submit NOW)
├── slurm_sim.sh       10k-run large-scale sim (8× A100)
└── slurm_predictor.sh Abandonment predictor (2× A100)

tests/test_uniqa.py    calibration + Franz constraint + uplift
REPORT.md              using submission template
```

---

## What's CUT (do not touch)

| Item | Why cut |
|------|---------|
| cadCAD integration | 0 jury eval dimensions benefit from it |
| GRPO/PPO training | 10-12h training, 0 direct jury benefit |
| Widget model (Flan-T5) | Overkill — "good prompts beat complex setups" (intake doc) |
| Fragment reordering | Not in eval criteria |
| Deposit mechanism | Pitch slide only (30 min to write) |
| Lifestyle profiler | Separate product, separate pitch |
| Sybilion directions A/B/C | Separate track — do not steal UNIQA time |
| UNIQA_SYSTEM_FRAME.md | Already written, use for context, don't expand |

---

## Time-Boxed Schedule

```
SAT 09:30 → 10:30  [1h]  funnel.py + coach.py core skeleton
                          8 states, ABANDON_PROBS, HESITATION_THRESHOLDS
                          CoachAction enum, decide_action(), validate_output()

SAT 10:30 → 12:00  [1.5h] personas.py
                          RuleBasedPersona (stats path)
                          LLMPersona (demo path, GPT-4 + persona .md system prompts)

SAT 12:00 → 12:30  [0.5h] Submit ALL SLURM jobs to Leonardo
                          lora × 3 (overnight)
                          large-scale sim 10k (3h)
                          abandonment predictor (2h)

SAT 12:30 → 13:30  [1h]  simulation.py
                          run_simulation(n=1000, coach_on/off)
                          per-step drop-off, per-persona, annoyance rate

SAT 13:30 → 14:30  [1h]  CALIBRATION CHECK
                          assert baseline ≈ 5.6%
                          assert step4_abandon ≈ 66%
                          assert Franz never gets advisor_handoff
                          → if fails, fix before building demo

SAT 14:30 → 15:30  [1h]  whatsapp.py
                          Twilio sandbox setup
                          Peter trigger → WA message with quote link
                          Test: Peter abandons → message on phone

SAT 15:30 → 19:30  [4h]  app.py Streamlit demo
                          Panel 1: 3 scripted demo scenarios (Franz/Judith/Peter)
                          Panel 2: 1k-run stats (bar charts, before/after)
                          Panel 3: Coach HUD (hesitation signals, action fired)
                          Sidebar: persona selector, coach on/off toggle

SAT 19:30 → 20:30  [1h]  Production vision slide
                          CDP injection screenshots (from earlier spike)
                          Code snippet showing DOM injection point
                          "In production, this deploys without UNIQA code access"

SAT 20:30 → 22:00  [1.5h] REPORT.md first draft
                          Using submission template
                          Calibrated numbers, coach logic documented

SAT 22:00 → SUN 08:00    SLEEP. Cluster jobs running.

SUN 08:00 → 09:00  [1h]  Check cluster results
                          If LoRA complete → show "trained persona bots" in demo
                          If sim complete → incorporate 10k run numbers
                          If predictor complete → show AUC-ROC in REPORT

SUN 09:00 → 10:00  [1h]  Final polish, submission checklist, submit
```

**Total active build: ~13h. Buffer: ~11.5h.**

---

## What Runs on Leonardo (submit by 12:30 TODAY)

### Job 1: Mistral-7B LoRA × 3 persona fine-tunes
```bash
# slurm_lora.sh
#SBATCH --job-name=uniqa-persona-lora
#SBATCH --partition=boost_usr_prod
#SBATCH --nodes=1
#SBATCH --gres=gpu:a100:6
#SBATCH --time=06:00:00
#SBATCH --mem=128G

# Trains Mistral-7B separately on each persona's interaction patterns
# Data: synthetic sessions generated from persona .md + personas.json
# Output: 3 LoRA checkpoints (judith_lora, franz_lora, peter_lora)
# Expected result: persona bots with stronger behavioral consistency
# If done by SUN 08:00 → show "we fine-tuned each persona on Leonardo"
```

### Job 2: Large-scale persona simulation (10k runs)
```bash
# slurm_sim.sh
#SBATCH --job-name=uniqa-sim-10k
#SBATCH --partition=boost_usr_prod
#SBATCH --gres=gpu:a100:8
#SBATCH --time=03:00:00

# Runs 10k sessions × 2 conditions (coach_on / coach_off)
# Embarrassingly parallel — each A100 handles 2500 sessions
# Output: conversion_rate, per_step_abandon, per_persona, annoyance_rate
# Statistical significance: Mann-Whitney U, bootstrap CI
# This is the "proof" — what the jury is looking for
```

### Job 3: Abandonment predictor
```bash
# slurm_predictor.sh
#SBATCH --job-name=uniqa-predictor
#SBATCH --gres=gpu:a100:2
#SBATCH --time=02:00:00

# Small transformer trained on synthetic session trajectories
# Input: (step, dwell_time, back_nav_count, hover_count, ...) → P(abandon)
# Output: calibrated probability score per step per persona
# Used in Coach's detection layer as a confidence signal
# Expected AUC-ROC: 0.78-0.82 (meaningful improvement over threshold rules)
```

**Total cluster: 10 GPU-hours on Leonardo. ~9.5% of daily cluster budget.**

---

## The Franz Demo — Build Exactly This

```python
# uniqa/demo_scenarios.py

FRANZ_SCENARIO = {
    "persona": "franz",
    "without_coach": [
        {"step": "TARIFF_SELECTION", "action": "view_prices", "dwell_sec": 12},
        {"step": "TARIFF_SELECTION", "action": "click_premium", "result": "advisory_required_shown"},
        {"step": "TARIFF_SELECTION", "action": "back_navigate"},
        {"step": "TARIFF_SELECTION", "action": "close_tab"},
        {"step": "EXIT", "outcome": "ABANDON"}
    ],
    "with_coach": [
        {"step": "TARIFF_SELECTION", "action": "view_prices", "dwell_sec": 12},
        {"step": "TARIFF_SELECTION", "action": "click_premium", "result": "advisory_required_shown"},
        {"step": "TARIFF_SELECTION", "action": "back_navigate"},
        # Coach fires here ↓
        {"step": "COACH", "action": "PRICE_REFRAME",
         "widget": "Premium requires advisory. Optimal covers therapies, medications, and medical aids fully online at €73/month."},
        {"step": "TARIFF_SELECTION", "action": "select_optimal"},
        {"step": "PERSONAL_DATA", "action": "complete_form"},
        {"step": "FINAL_PRICE", "action": "accept"},
        {"step": "PURCHASE", "outcome": "CONVERSION"}  # ✅
    ]
}

JUDITH_SCENARIO = {
    "persona": "judith",
    "without_coach": [
        {"step": "FINAL_PRICE", "action": "price_displayed", "price_delta": "+6.68"},
        {"step": "FINAL_PRICE", "action": "dwell", "dwell_sec": 28},
        {"step": "FINAL_PRICE", "action": "hover_cancel"},
        {"step": "FINAL_PRICE", "action": "hover_cancel"},  # repeated
        {"step": "EXIT", "outcome": "ABANDON"}
    ],
    "with_coach": [
        {"step": "FINAL_PRICE", "action": "price_displayed", "price_delta": "+6.68"},
        {"step": "FINAL_PRICE", "action": "dwell", "dwell_sec": 28},
        # Coach fires here ↓
        {"step": "COACH", "action": "HEALTH_EXPLAIN",
         "widget": "Your final price accounts for your health profile. €6.68 more covers your personal risk. You can complete online right now."},
        {"step": "FINAL_PRICE", "action": "accept"},
        {"step": "PURCHASE", "outcome": "CONVERSION"}  # ✅
    ]
}

PETER_SCENARIO = {
    "persona": "peter",
    "without_coach": [
        {"step": "PERSONAL_INFO", "action": "view_form"},
        {"step": "PERSONAL_INFO", "action": "form_reedit", "count": 3},
        {"step": "PERSONAL_INFO", "action": "dwell", "dwell_sec": 42},
        {"step": "EXIT", "outcome": "ABANDON"}  # before price
    ],
    "with_coach": [
        {"step": "PERSONAL_INFO", "action": "view_form"},
        {"step": "PERSONAL_INFO", "action": "form_reedit", "count": 2},
        # Coach fires here ↓
        {"step": "COACH", "action": "CALLBACK_OFFER",
         "widget": "Want someone to help? We'll call you back in 5 minutes."},
        {"step": "CALLBACK_ACCEPT", "action": "accept"},
        # WhatsApp fires here ↓
        {"step": "WHATSAPP", "action": "send",
         "message": "Hi, I'm UNIQA's digital assistant. You looked at Privatarzt Start (€41/mo). Ready to continue? [link]"},
        {"step": "EXIT", "outcome": "WA_LEAD"}  # soft conversion
    ]
}
```

---

## The Key Numbers (memorize, validate before demo)

```
Baseline conversion:    5.6%  (= 56 out of 1,000 starters)
Step 4 drop-off:       66%   conditional on reaching Step 4
Step 5 drop-off:       24%   conditional on reaching Step 5
Step 7 drop-off:       78%   conditional on reaching Step 7

Survival math:
1,000 → 340 (Step 4 survivors) → 258 (Step 5 survivors) → ~57 (Step 7 survivors) ≈ 56

Funnel weights:
Judith: 30% | Franz: 50% | Peter: 20%

Calibration check (must pass before demo):
0.30×0.70 + 0.50×0.55 + 0.20×0.80 = 0.645 ≈ 66% at Step 4 ✓
```

---

## WhatsApp Coach — Peter Flow

```python
# uniqa/whatsapp.py
from twilio.rest import Client
import os

def send_peter_reengagement(user_name: str, quote_data: dict, phone_number: str):
    """
    Fires when Peter (Service Affine persona) abandons early.
    Sends a WhatsApp message with personalized quote + resume link.
    """
    client = Client(os.environ["TWILIO_SID"], os.environ["TWILIO_TOKEN"])

    tariff = quote_data.get("tariff", "Privatarzt Start")
    price = quote_data.get("estimated_price", "€41,30")

    message = (
        f"Hallo! Sie haben sich {tariff} bei UNIQA angesehen ({price}/Monat). "
        f"Soll ich Ihnen beim Abschluss helfen? Hier können Sie direkt weitermachen: "
        f"https://uniqa.at/rechner?resume={quote_data.get('session_id', 'demo')} "
        f"Oder rufen Sie uns an: 0810 200 541."
    )

    msg = client.messages.create(
        from_='whatsapp:+14155238886',  # Twilio sandbox
        to=f'whatsapp:{phone_number}',
        body=message
    )
    return msg.sid

# In app.py demo:
# When Peter scenario runs with Coach:
#   → show callback offer widget in Streamlit
#   → call send_peter_reengagement(...)
#   → show "WhatsApp sent" notification in demo
#   → jury sees phone receive message live
```

**Setup:** Twilio sandbox = `pip install twilio` + join sandbox with phone WhatsApp → done in 10 min.

---

## Production Vision Slide (from CDP spike)

The live CDP spike showed:
- UNIQA calculator at `uniqa.at/rechner/krankenversicherung/` reached
- Steps 1-4 navigated (cookie consent, Arztbesuchen, Ich selbst, tariff table)
- DOM injection point confirmed: `document.querySelector('[class*=product-comparison]')`

**Slide content:**
```
"In production, the Coach deploys as a single JavaScript snippet.
No access to UNIQA's backend required.
No changes to their Angular codebase.

// Production deployment (3 lines):
const target = document.querySelector('[class*=tariff-table]');
const widget = document.createElement('div');
widget.innerHTML = COACH_WIDGET_HTML;
target.parentNode.insertBefore(widget, target);

[SCREENSHOT: Step 4 tariff table with Coach widget appearing]
[SCREENSHOT: CDP accessibility tree showing Coach widget in DOM]
[SCREENSHOT: Coach HUD showing Franz hesitation signals]
```

---

## What We Don't Build (and the one-line pitch for each)

| Cut item | Pitch line if asked |
|----------|---------------------|
| cadCAD simulation | "We used cadCAD's formal state-space for the belief model design; our fast sim runs natively for scale." |
| GRPO/PPO policy | "RL is Phase 2 — the rule-based Coach's annoyance rate is already below 15%. RL optimizes the remaining margin." |
| Widget model (Flan-T5) | "The Coach policy is explainable by design — we can trace every intervention to a rule. A learned policy is Phase 2." |
| Fragment reordering | "Fragmenting the form is a UNIQA product decision. We prove the demand through our simulation's 78% drop-off at the data form." |
| Deposit mechanism | "One slide. The Coach learns when deposit intent is highest and can initiate a €1 commitment at that moment." |

---

## Demo Script (3 minutes on stage)

```
SLIDE 1 (30s): The problem
"1,000 people start the UNIQA calculator. 56 buy. The other 944 were interested.
 They just needed the right support at the right moment."

SLIDE 2 (30s): The Coach
"We built a Conversion Coach — detection layer reads behavioral signals,
 decision layer fires contextual interventions. Two-layer architecture on top
 of UNIQA's existing chatbot infrastructure."

LIVE DEMO (90s): Streamlit side-by-side
"Watch Franz. Without Coach: clicks Premium, sees advisory required, backs up, closes tab.
 With Coach: backs up, Coach fires, explains Optimal is fully online, Franz converts."
[Switch to Judith demo]
"Watch Judith. Without Coach: sees final price +€6.68, hovers cancel, abandons.
 With Coach: Coach explains the price gap, Judith completes."
[Peter WhatsApp]
"Peter gets a different treatment — overwhelmed by the form, he gets a WhatsApp message
 with his personal quote and a resume link. [show phone]"

SLIDE 3 (30s): The numbers
"10,000 simulated sessions. Baseline: 5.6%. With Coach: [X]%.
 Per-persona breakdown. Annoyance rate: [Y]%."

SLIDE 4 (30s): Production
"This deploys as 3 lines of JavaScript. No UNIQA backend access needed.
 [show CDP injection screenshot]"
```

---

## Evaluation Scorecard (what the jury will fill in for us)

| Dimension | Our evidence |
|-----------|-------------|
| Conversion uplift | 1k-run A/B + 10k Leonardo run. Concrete Δ percentage. |
| Persona differentiation | Per-persona conversion table. Franz vs. Judith vs. Peter breakdown. |
| Intervention quality | Annoyance rate (tracked per simulation). Trigger precision (true positive rate). |
| Technical depth | Coach rules are traceable. Abandonment predictor AUC-ROC from Leonardo. |
| Persona realism | GPT-4 + full persona .md system prompts. Calibrated to personas.json survey data. |
| Reproducibility | Seeded RNG throughout. REPORT.md documents all seeds, thresholds, params. |
| Demo quality | Side-by-side Streamlit. WhatsApp prototype. CDP production vision. |

---

## Critical Path

```
funnel.py + coach.py  →  simulation.py  →  calibration check  →  demo scenarios  →  app.py
                    ↘                                                           ↗
                     Submit SLURM jobs (runs unattended) →→→→→→→→→→→→→→→→→→→
```

**The calibration check gates everything.** If `baseline ≈ 5.6%` fails, fix it before building the demo. A simulation that doesn't match UNIQA's real numbers is worthless.

---

## NOT in Scope (explicitly deferred)

- cadCAD formal simulation engine
- GRPO/PPO RL policy training
- Flan-T5-small widget model
- Fragment reordering personalization
- Lifestyle profiler free product
- Deposit-first architecture
- eID/Handysignatur integration
- Any Sybilion track work
- Live CDP injection on stage
