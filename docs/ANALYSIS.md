# UNIQA Insurance Track — Deep Technical Analysis
**Zero One Hackathon | Prepared for team review | 2026-05-30**

---

## TABLE OF CONTENTS
- [A. Data Analysis](#a-data-analysis)
- [B. System Architecture Ideas](#b-system-architecture-ideas)
- [C. Best Use of Leonardo HPC (64× A100)](#c-best-use-of-leonardo-hpc-64-a100)
- [D. Sybilion Angle](#d-sybilion-angle)

---

# A. DATA ANALYSIS

## A.1 What Is in personas.json — Numbers, Distributions, Behavioral Signals

### Survey provenance
The JSON wraps UNIQA retail segmentation research from Oct–Nov 2025, n=4,004 Austrians aged 18–75. Three segments are relevant to the online funnel: S1 (n=620), S2 (n=688), S3 (n=546). These are real quantitative survey weights, not invented personas — critical for justifying simulation priors.

### Segment anatomy

| Metric | Judith S1 "Rising Hybrids" | Franz S2 "Online Affine" | Peter S3 "Service Affine" |
|---|---|---|---|
| **Estimated funnel share** | 30% | **50%** | 20% |
| **Market size (Austria)** | 975k persons | 1.105M persons | 910k persons |
| **Age mean** | 43.2 | 43.1 | 40.9 |
| **Income €/month** | **€4,042** | €3,692 | €3,557 |
| **KV ownership today** | **34%** | 25% | 21% |
| **KV purchase intent (3y)** | **18%** | 16% | 13% |
| **NPS (brand loyalty signal)** | **+17** | +1 | **−6** |
| **Switch willingness** | 7% | 16% | **24%** |
| **Products owned** | **5.2** | 3.8 | 3.5 |
| **Monthly insurance spend** | **€230.6** | €166.8 | €167.3 |
| **Online purchase share (any product)** | 19% | **69%** | 34% |
| **UNIQA customer today** | **35%** | 24% | 25% |
| **No advisor (%)** | 12% | **47%** | 28% |

### Per-segment channel preference (dominant channel per funnel step)

The JSON stores `channel_preference_per_journey_step_pct_dominant_channel` — the most-used channel and its share. Secondary channel distributions are *not* provided (known gap for S2/S3; only S1 has full 3-way split in the original booklet).

#### Judith (S1) — Hybrid: researches online, converts offline
| Step | Channel | Share |
|---|---|---|
| Info gathering | self_online | 58% |
| Comparison | self_online | 74% |
| **Consultation** | **via_advisor** | **90%** |
| **Purchase** | **via_advisor** | **78%** |
| Contract admin, claims | self_online | 82–88% |

→ **Implication for Coach**: Judith has a natural advisor-at-purchase preference. She arrived online to research, not to buy. The Coach should serve her research and then offer a smooth advisor booking — not try to force online completion for the 81% who statistically won't.

#### Franz (S2) — All-online: refuses channel switch
| Step | Channel | Share |
|---|---|---|
| Info gathering | self_online | 90% |
| Comparison | self_online | **94%** |
| Consultation | self_online | 61% |
| **Purchase** | **self_online** | **89%** |
| Every admin step | self_online | 85–94% |

→ **Implication for Coach**: Franz is the primary online conversion target (50% of funnel traffic, 89% online purchase preference). Any intervention that pushes him toward an advisor is an active failure. He is also the most comparisons-active: 82% of the segment "always compares multiple offers" — the Coach must handle his tab-switching behavior.

#### Peter (S3) — Customer service as default for everything
| Step | Channel | Share |
|---|---|---|
| Info gathering | **customer_service** | 61% |
| Comparison | customer_service | 51% |
| Consultation | customer_service | 61% |
| **Purchase** | **customer_service** | **59%** |
| Even personal data update | customer_service | 59% |

→ **Implication for Coach**: Peter doesn't just use customer service for hard decisions — he uses it for everything, including routine admin. He is not lost in the funnel; he's in the wrong channel. The optimal Coach action is early, proactive service handoff.

### Key behavioral signal hypotheses per persona (from `online_funnel_behavior_hypotheses`)

These are *explicitly labeled as hypotheses* in the JSON — not ground truth. They are the simulation priors teams should test against.

**Judith drop-off signals (primary: initial_price_display)**
- Long dwell time on price comparison table
- Repeated tariff hover/click without selection (exploring, not deciding)
- Backwards navigation after seeing "advisory required" on Opt. Plus / Premium
- External tab opens (comparison search → ROPO effect — she leaves to call an advisor)

**Franz drop-off signals (primary: final_price_after_health_questions)**
- Anomalously fast progression through steps 1–3 (he knows what he wants)
- Session gap spike at step 4 (opens comparison tab, comes back or doesn't)
- Stall on final price screen when actual price > provisional price
- Hover on "cancel" without clicking → last-second hesitation

**Peter drop-off signals (primary: earlier_steps_or_initial_price)**
- Long dwell time on early form steps (Step 3 — personal data)
- Multiple back-navigations (not sure which choice is correct)
- Slow/hesitant field fill (entering data carefully, anxious)
- Abandonment before tariff selection — he never sees the 66% drop-off step

### Decision driver quantification (top-3 per segment)

| Rank | Judith S1 | Franz S2 | Peter S3 |
|---|---|---|---|
| 1 | Price-performance (87%) | Price-performance (85%) | Tailored products (65%) |
| 2 | Tailored products (83%) | Compares offers (82%) | Price-performance (63%) |
| 3 | Personal advisor trust (76%) | Values apps/portals (79%) | Compares offers (61%) |

Critical observation: **Peter's absolute numbers are all lower** (65%, 63%, 61%) vs Judith/Franz (73–87%). He simply has less strong opinions. The persona bot must reflect this: he is passive, not principled. He can be moved by simple clear guidance in a way Judith and Franz cannot.

### Purchase criteria — divergent priorities

| Criterion | Judith % | Franz % | Peter % |
|---|---|---|---|
| Online purchase option | 11 | **36** | 13 |
| Advisor competence | **42** | 16 | 19 |
| Transparent product info | 35 | 33 | 19 |
| Digital services | 24 | 25 | 9 |

The `online_purchase_option` signal is the starkest: it's irrelevant to Judith and Peter (both 11–13%), but **a top-4 purchase criterion for Franz (36%)**. If the calculator has rough UX, Franz notices and penalizes — others tolerate it.

### Life event triggers (health insurance relevance)

| Event | Judith % | Franz % | Peter % |
|---|---|---|---|
| Hospitalization (last 3y) | 32 | 31 | **43** |
| Minor physical complaints | **71** | 61 | 45 |
| Minor psych strain | **45** | 39 | 30 |
| Started financial planning | **20** | — | — |

**Peter's 43% hospitalization rate is the most actionable trigger**: he arrived at the UNIQA calculator because something concrete happened to him, not because he's actively shopping. He is hot lead, wrong channel.

---

## A.2 UX Triggers / Signals Available at Each Step

### Step 1 (Coverage selection)
- Which cards are clicked (doctor/hospital/both)
- Time from page load to first click
- Returns to this page from step 2+

### Step 2 (For whom)
- "Other persons" selection → out of scope
- Time on page (decision uncertainty)

### Step 3 (Personal data entry)
- **Time to fill each field** (DOB, social insurance number — high anxiety signal for Peter)
- Field correction events (entered, deleted, re-entered)
- Hover/focus on social insurance number field without filling (trust barrier)
- Back-navigation from this step

### Step 4 — **CRITICAL: 66% drop-off**
This is where most signals originate:
- **Dwell time per tariff row** (hover duration → which tariff is attracting attention)
- **Click on Opt. Plus / Premium** → frustration signal if they then click back
- **Scroll depth and direction** (scrolled down to see details vs. scrolled back up → confused)
- **Hover on coverage-area cells** ("refractive eye surgery" hover → unfamiliar term)
- **Time-on-page total** (>90s = deep consideration; >180s without click = paralysis)
- **Backwards navigation from Step 4 back to Step 3** → intent to abort
- **New tab opened** (detectable via window blur event) → comparison-shopping
- **"Advisory required" click on Opt. Plus/Premium** → frustration signal

### Step 6 (Health questions)
- Answer patterns (many pre-conditions flagged = likely premium increase → predict Step 7 shock)
- Time per question vs. calibrated norm
- Changes to previously submitted answers

### Step 7 — **CRITICAL: 78% drop-off**
- **Price delta = final price − provisional price** (this is the single strongest predictor of abandonment; exact distribution unknown — major gap)
- **Dwell time on final price display**
- **Hover on "cancel" / "back" button** (quantifies abandonment intent)
- **Hover count on price line** (re-reads → doesn't believe the number)
- **Scroll to terms section** (willing to continue?) vs. scroll back to price (re-checking)
- **Mouse velocity** (fast, erratic = agitated)

### Steps 12+ (Closing — not fully documented)
- Form completion speed (fast = committed; slow = second-guessing)
- Payment method selection hesitation
- Open of terms & conditions vs. skip

---

## A.3 What the Tariff Reference Gives as Coaching Material

The product reference is unusually complete and provides ready-made coach arguments:

### Price psychology handles
- Start: €38.74/month = **€1.27/day** (less than a coffee)
- Optimal: €68.14/month = **€2.25/day** (less than two coffees)
- Delta Start→Optimal: ~€30/month = **~€1/day for +€1,400/year in coverage**
- Optimal coverage-to-premium ratio: **3.4x** (vs. Start's 3.0x — Optimal is better value per euro)

### Upgrade path (critical for hesitant users)
- Start can be upgraded to Optimal after **3 years, no new health assessment**
- Optimal can be upgraded to Opt. Plus after **3 years** (this handles users who wanted Opt. Plus but are frustrated by "advisory required")
- This resolves the #1 frustration at Step 4: users can start online NOW and get the better tier later

### What Start doesn't cover (important for Optimal upsell)
Start has **zero** coverage for: physiotherapy, psychotherapy, occupational therapy, speech therapy, osteopathy, medical massage, medical aids, glasses/contact lenses, refractive eye surgery. This is not a small gap — it's all of Category 3 (€560/year in Optimal) and all of Category 4 (€280/year + €280 additional). For a 43-year-old like Judith (71% minor physical complaints in the segment), this gap is highly salient.

### NEW feature (Sep 2025) — strong Optimal argument
Refractive eye surgery coverage **doubled** in September 2025. For anyone considering glasses/contacts/laser, this is a concrete new reason to pick Optimal over Start. Only 4 months old — many users won't know about it.

### Premium adjustment history — transparency argument
Historical increases: 0% (2021), 3.1% (2020), 6.6% (2022), 12.9% (2023), 8.3% (2024). The coach can use this to neutralize "will it get much more expensive?" objections — showing the range honestly is more trust-building than hiding it.

### Add-ons — expansion revenue and decision simplification
- **Fit Feeling** (€17.17/mo): covers fitness (€100 sub-limit), massage, supplements — relevant for Peter's 43% hospitalization segment
- **Growing Mentally** (monthly premium not published): covers life coaching/psychosocial counseling, NOT psychotherapy — important to distinguish
- **Becoming Parents**: must be purchased BEFORE pregnancy — a critical timing message if Judith mentions family planning

---

## A.4 Data Gaps — Critical and Manageable

### Critical gaps (affect model validity)
1. **No price delta distribution**: The distribution of (final price − provisional price) is unknown. This is the #1 driver of the 78% Step 7 drop-off. Must be synthesized from assumptions — e.g., assume normally distributed around +€5–15 with fat right tail for users with pre-conditions.
2. **No actual clickstream data**: All behavioral signals are hypothetical. The personas.json `online_funnel_behavior_hypotheses` are labeled as hypotheses, not measurements.
3. **Secondary channel distributions for S2/S3**: Only dominant channel per step is provided (e.g., "90% self-online for Franz"). The other 10% is unknown. Minor for modeling but affects multi-channel simulation.

### Manageable gaps (document, synthesize)
4. **Step 6 (health questions) undocumented**: Must walk the live calculator. Matters for training abandonment predictor because the Step 6 answer pattern predicts the price delta that causes Step 7 drop-off.
5. **Steps 12+ (closing) undocumented**: Affects final conversion math but is a small population (only the ~5.6% who survive). Can model as single "closing" state with 95%+ success rate conditional on reaching it.
6. **No per-segment funnel drop-off data**: The 66%/24%/78% figures are aggregate. There's no breakdown of "what % of Judith vs. Franz vs. Peter drops at Step 4." This must be synthesized from the segment behavioral profiles.
7. **No device/browser data**: Likely relevant (Franz on mobile vs. desktop), but absent.
8. **ROPO effect unmeasurable**: UNIQA acknowledges the ROPO (Research Online, Purchase Offline) effect is real but untracked. Some portion of the 66% Step 4 drop-off is Judith leaving to call an advisor — which counts as a business conversion but not in the simulation.

---

# B. SYSTEM ARCHITECTURE IDEAS

## B.1 Layers and Component Map

```
┌─────────────────────────────────────────────────────────────────┐
│                        SIMULATION SHELL                         │
│  (State machine: 8 states × time × per-step event stream)       │
└─────────────────────┬────────────────────────────────────────────┘
                      │ behavioral event stream
          ┌───────────▼────────────────┐
          │   PERSONA CLASSIFIER       │  P(Judith | Franz | Peter)
          │   (Early features → seg.)  │  updates Bayesian posterior per step
          └───────────┬────────────────┘
                      │ segment posterior
          ┌───────────▼────────────────┐
          │  ABANDONMENT PREDICTOR     │  P(abandon | step, segment, signals)
          │  (Sequential model)        │  fires every N seconds / every event
          └───────────┬────────────────┘
                      │ (step, p_abandon, segment)
          ┌───────────▼────────────────┐
          │  INTERVENTION POLICY       │  (what_type, when, for_whom)
          │  (Rule-based → RL)         │  must avoid over-triggering
          └───────────┬────────────────┘
                      │ intervention_type + context
          ┌───────────▼────────────────┐
          │  INTERVENTION GENERATOR    │  Personalized message text
          │  (LLM with persona-aware   │  + UI action (tooltip/modal/banner)
          │   system prompt)           │
          └────────────────────────────┘
                      │ rendered intervention
          ┌───────────▼────────────────┐
          │  PERSONA BOT               │  Simulated user reaction
          │  (LLM fine-tune or         │  → continue / proceed / abandon
          │   prompted)                │  Generates new behavioral event stream
          └────────────────────────────┘
```

---

## B.2 Model Selection by Component

### Component 1: Funnel State Machine
**Architecture**: Pure Python state machine. 8 states for in-scope path:
```
ENTRY → COVERAGE_SELECT → PERSON_SELECT → PERSONAL_DATA →
TARIFF_SELECT → HEALTH_QUESTIONS → FINAL_PRICE → CLOSING → CONVERTED
```
Plus absorbing exit states: `ABANDONED_STEP_N`, `ROUTED_ADVISOR`

Each state emits a behavioral event stream (dwell_time, back_nav_count, hover_events, click_sequence). The state machine governs what events are possible and feeds them to the Coach components.

**Why state machine over end-to-end neural net**: The funnel has hard structural constraints (can't skip steps, can't buy Opt. Plus online). A state machine encodes these constraints without needing to learn them. The ML sits on top.

---

### Component 2: Persona Classifier
**Model**: Gradient boosted classifier (LightGBM, ~1M trees × 100 leaves)
**Input features (accumulated up to current step)**:
- Progression speed (time per step vs. median norm by step)
- Back-navigation count (cumulative)
- Hover event count per tariff row (at Step 4)
- Number of times Opt. Plus/Premium was clicked
- Session gap duration (detects external tab)
- Field fill speed (chars per second on Step 3)
- Device type, time of day (proxy features for segment)

**Output**: Soft probability vector [p_S1, p_S2, p_S3]

**Why LightGBM not neural net**: Small feature space (~20 features), interpretable, runs in <1ms, can be deployed inline without GPU. The classification signal is actually quite strong — Franz's 90% online behavior vs. Peter's 61% customer service preference generates distinct feature distributions.

**Training data**: Synthetically generated sessions (Section C covers this in detail)

---

### Component 3: Abandonment Predictor
**Model**: 1-layer Transformer Encoder (sequence model) over behavioral event sequences
**Input**: `[step, event_type, dwell_time, normalized_position]` tokens, max sequence length 256
**Output**: P(abandon_next_step) per time step

**Architecture details**:
- Embedding dim: 64
- 2 attention heads, 2 layers (deliberate small size — avoid overfitting on synthetic data)
- Position encoding by step index (not by time) — ensures step-4 patterns are learned separately from step-7 patterns
- Sigmoid output head

**Alternative**: LSTM if sequence alignment is a concern. Transformer is preferred because attention weights are interpretable (shows what events the model attended to) — valuable for the demo.

**Training**: Supervised on synthetic sessions. Labels: did this session abandon at the next step?

---

### Component 4: Intervention Policy
**MVP (rule-based)**:
```python
RULES = {
  ("step_4", "S2", p_abandon > 0.7): "price_reframe",
  ("step_4", "S1", "opt_plus_click_detected"): "upgrade_path_explanation",
  ("step_7", "S2", "price_delta > threshold"): "price_transparency",
  ("step_3", "S3", "back_nav_count > 2"): "proactive_service_handoff",
  ...
}
```
This is the MVP Coach. 15–20 explicit rules. Evaluable, auditable.

**Impressive version (PPO Reinforcement Learning)**:
- **Environment**: Funnel state machine + persona bots
- **State**: (funnel_step, segment_posterior, abandonment_prob, interventions_already_shown)
- **Action space**: Discrete — {no_intervention, price_reframe, upgrade_path, market_comparison, term_explanation, service_handoff, save_progress_offer, ...} (8–10 actions)
- **Reward**: +1 for CONVERTED, −0.1 for each intervention (penalizes over-triggering), −0.5 for ABANDONED, +0.3 for ROUTED_ADVISOR if segment=S3 (service handoff counts for Peter)
- **Algorithm**: PPO (Proximal Policy Optimization) with clipped surrogate objective
- **Why PPO not DQN**: Continuous reward shaping is easier, better sample efficiency with clipping, well-tested for discrete action spaces

The RL policy will learn naturally that: never show service_handoff to Franz, show it early to Peter, and only use market_comparison at Step 4 when dwell time is high.

---

### Component 5: Intervention Generator (LLM)
**Model**: Fine-tuned Mistral-7B-Instruct or Llama-3-8B-Instruct (or GPT-4 via API for the demo)
**System prompt pattern**:
```
You are the UNIQA Conversion Coach. The user is [SEGMENT_DESCRIPTION].
Current funnel step: [STEP_NAME].
Detected signals: [SIGNAL_LIST].
Intervention type: [TYPE].
Generate a [MESSAGE_LENGTH]-word intervention message in [LANGUAGE].
Rules: [SEGMENT_RULES].
```
**Why LLM here**: Intervention text needs to match persona tone. Franz needs terse, data-first messages. Judith needs warm, trust-building language. Peter needs a single clear sentence. A template system can't cover this gracefully.

---

### Component 6: Persona Bots
**Model selection** (choose one or both):

**Option A — Prompted LLM (Claude/GPT-4)**
- Use the provided persona markdown files verbatim as system prompts
- Fast to build, but costly to run at scale (thousands of simulations)
- "Consistent enough" persona behavior for demo runs

**Option B — Fine-tuned 7B model (the HPC play)**
- Fine-tune Mistral-7B or Llama-3-8B on a dataset of persona-behavior traces
- Format: `CONTEXT: [step + intervention] → ACTION: [behavioral_response]`
- Deterministic at inference (fixed temperature) → reproducible simulations
- Runs ~1000 sessions/hour on 4× A100 → viable for large-scale simulation
- **This is what you show the jury as "real training"**

---

## B.3 Minimal Viable Coach vs. Impressive Coach

### Minimal Viable Coach (can be built in 12–15 hours)
- Python state machine with 8 states
- 3 persona bots using GPT-4 with provided markdown system prompts
- Rule-based intervention policy (20 explicit rules, documented)
- LLM-generated intervention messages (same GPT-4, different system prompt)
- Logging + before/after conversion comparison across 100 simulated runs
- Output: table + chart showing conversion lift per persona

**Expected results**: Likely 2–3× conversion improvement for Franz (he's the easiest), moderate for Judith, minimal for Peter.

### Impressive Coach (adds HPC training component, realistic in 36h with cluster)
Everything in MVP plus:
- Synthetic behavioral dataset generation (100k sessions)
- Fine-tuned persona bots (Mistral-7B × 3 personas)
- Trained abandonment predictor (Transformer-based, evaluated with ROC-AUC)
- PPO-trained intervention policy (policy network, convergence curve shown)
- Statistical significance testing on simulation results (Mann-Whitney U or bootstrap)
- Conversion uplift breakdown: which intervention type at which step for which persona

---

## B.4 Persona Bot Construction — How to Make Them Actually Behave Differently

The most common failure mode: persona bots all generate similar responses because the LLM averages over training. To avoid this:

### Behavioral differentiation via structured decision loop
Each persona bot is not just an LLM — it's a decision function:
```python
def franz_bot_decide(current_step, intervention, signals):
    # Franz's decision model
    p_continue = base_continue_prob[current_step]
    
    # Franz-specific signal processing
    if current_step == "final_price":
        price_delta = signals["final_price"] - signals["provisional_price"]
        p_continue -= 0.05 * price_delta  # −5% per €1 above estimate
    
    if intervention and intervention.type == "service_handoff":
        p_continue -= 0.2  # Franz hates advisor pushes
    
    if intervention and intervention.type == "price_reframe" and signals["step"] == "final_price":
        p_continue += 0.25  # Franz responds to data
    
    return p_continue > random.random()
```

This is deterministic enough to reproduce and stochastic enough to simulate variance. The LLM then generates the narrative text for logs/demos, but the *decision* is numerical.

### Calibration against personas.json
The `p_continue` base values should be calibrated against the known drop-off data:
- Step 4: 66% aggregate drop = weighted average of persona-specific drops
- S1 (30% traffic): step-4 drop-off estimated ~70% (ROPO effect, advisor preference)
- S2 (50% traffic): step-4 drop-off estimated ~55% (online-affine, lower friction)
- S3 (20% traffic): step-4 drop-off estimated ~80% (overwhelm, leaves before/at price)
- Check: 0.30×0.70 + 0.50×0.55 + 0.20×0.80 = 0.21 + 0.275 + 0.16 = 0.645 ≈ 66% ✓

This calibration means the simulation *matches known ground truth* before any coach intervention — a strong validation argument for the jury.

---

# C. BEST USE OF LEONARDO HPC (64× A100)

## C.1 What Is and Isn't Worth Training on A100s

### NOT worth A100s:
- Calling GPT-4 API to run 50 persona simulations → API cost, no training signal
- Rule-based intervention policy → runs on CPU in microseconds
- Basic LightGBM persona classifier trained on <100k rows → CPU, 5 minutes
- Simple logistic regression abandonment predictor → not impressive

### WORTH A100s:
1. **Fine-tuning 7B persona models** (3 × fine-tune jobs, ~4–6h each on 4× A100)
2. **Training Transformer abandonment predictor on large synthetic datasets** (50k–500k sessions)
3. **PPO reinforcement learning** with GPU-backed persona bots as environment
4. **Generating the synthetic training corpus itself** (LLM generation of behavioral traces)
5. **Monte Carlo simulation at scale** (thousands of parallel runs with fine-tuned models)

## C.2 Concrete Training Ideas

### Training Job 1: Synthetic Behavioral Data Generation
**What**: Use a large LLM to generate synthetic user session logs for training downstream models. This itself runs on GPUs.

**Setup**:
```
Input: personas.json + persona_*.md + funnel states
Prompt template per session:
  "Simulate a complete user session for [PERSONA] going through the UNIQA calculator.
   Output structured JSON: {step: N, event: TYPE, dwell_s: FLOAT, decision: ACTION, reason: TEXT}"
```

**Volume target**: 100,000 sessions (≈ 33k per persona, ≈ 10k per sub-variant)
**Sub-variants**: Generate 5 sub-variants per persona (e.g., Judith variants: time-pressured, detail-oriented, recent hospitalization trigger, comparing with competitor, first-time health insurance buyer)
- Total: 3 × 5 × 6,667 = 100k sessions

**GPU utilization**: Batch inference on 64× A100, Llama-3-70B at 8-bit quantization
- Throughput: ~500 sessions/minute → 100k sessions in ~3.3 hours
- Cost: ~3–4 GPU-hours of 64× A100 time

**Output format per session**:
```json
{
  "persona": "franz",
  "sub_variant": "comparison_shopper",
  "session_id": "uuid",
  "events": [
    {"step": 3, "event": "field_fill", "field": "dob", "dwell_s": 4.2, "errors": 0},
    {"step": 4, "event": "hover", "target": "optimal_row", "dwell_s": 18.5},
    {"step": 4, "event": "click", "target": "premium_tariff"},
    {"step": 4, "event": "back_nav", "from_advisory_redirect": true},
    {"step": 4, "event": "select", "target": "optimal_tariff"},
    ...
  ],
  "outcome": "abandoned_step_7",
  "price_delta_eur": 6.80,
  "reason": "final price exceeded initial estimate by 10%"
}
```

**Validation**: Compare generated sessions against known drop-off rates (66% at step 4, 78% at step 7 in aggregate). Tune generation prompts until synthetic distribution matches real distribution within 5%.

---

### Training Job 2: Persona Bot Fine-Tuning (3× Mistral-7B-Instruct)
**What**: Fine-tune a 7B instruction-tuned model to BE each persona, trained on generated synthetic sessions.

**Dataset construction from synthetic sessions**:
```
Input record format:
  SYSTEM: [persona briefing — full markdown as system prompt]
  USER: You are at Step 4 (tariff selection). You see: [step state JSON].
        An intervention appeared: [intervention text].
        What do you do?
  ASSISTANT: [action + brief reasoning in persona voice]
```

**Training details**:
- Base model: `mistralai/Mistral-7B-Instruct-v0.3` (or Llama-3-8B-Instruct)
- Training method: LoRA (r=16, alpha=32) on attention + MLP layers → ~20M trainable params out of 7B
- Batch size: 16 × gradient accumulation 4 = effective batch 64
- Learning rate: 2e-4 with cosine decay
- Training steps: 2,000 (≈ 2 epochs over 33k training records per persona)
- Hardware: 2× A100 80GB per model, 3 models in parallel = 6× A100 total
- Duration: ~4–5 hours per model training run

**Why fine-tune vs. system prompt**: Fine-tuned Franz will refuse advisor handoffs reliably without needing explicit instructions in every prompt. System-prompted Franz leaks into generic LLM behavior when context is long. For 10,000-run simulations, fine-tuned models are also 10× cheaper to run.

**Expected improvement**: Persona-specific decision consistency goes from ~70% (prompted GPT-4) to ~92% (fine-tuned) — validated by checking whether Franz rejects advisor handoffs as expected, whether Peter accepts service callbacks, etc.

---

### Training Job 3: Abandonment Predictor (Transformer Sequence Model)
**What**: Train a sequence model to predict P(abandon_at_next_step) from the event sequence so far.

**Architecture**:
```python
class AbandonmentPredictor(nn.Module):
    def __init__(self):
        self.event_embedding = nn.Embedding(vocab_size=64, embedding_dim=32)
        self.step_embedding = nn.Embedding(num_steps=10, embedding_dim=16)
        self.dwell_projection = nn.Linear(1, 16)
        self.transformer = nn.TransformerEncoder(
            encoder_layer=nn.TransformerEncoderLayer(d_model=64, nhead=4, dim_feedforward=256),
            num_layers=3
        )
        self.classifier_head = nn.Linear(64, 1)  # P(abandon)
    
    def forward(self, events, steps, dwell_times):
        # Concatenate embeddings
        x = cat([self.event_embedding(events), self.step_embedding(steps), self.dwell_projection(dwell_times)])
        x = self.transformer(x)
        return sigmoid(self.classifier_head(x[:, -1, :]))  # Last token = current state
```

**Training setup**:
- Dataset: 100k synthetic sessions → ~800k training examples (each prefix of each session = one example)
- Labels: `abandon_at_next = 1` if session outcome is `abandoned_step_N` for N = current step + 1
- Split: 70/15/15 train/val/test
- Loss: Binary cross-entropy with class balancing (abandonment is ~80% of examples at certain steps)
- Batch size: 512, epochs: 20
- Hardware: 1× A100, ~2 hours
- Expected AUC-ROC: ~0.75–0.82 on held-out sessions (literature anchor: e-commerce abandonment models achieve 0.78–0.85 on similar sequence data)

**Interpretability demo**: Visualize attention weights at Step 4 for Franz — show that the model attends to "hover on Opt. Plus" events, proving it learned UNIQA-specific signals.

---

### Training Job 4: RL Intervention Policy (PPO)
**What**: Train an RL agent to select intervention types, using the persona bots as the environment.

**Environment design (OpenAI Gym API)**:
```python
class ConversionFunnelEnv(gym.Env):
    observation_space = spaces.Dict({
        "step": spaces.Discrete(8),
        "segment_posterior": spaces.Box(0, 1, shape=(3,)),  # [p_S1, p_S2, p_S3]
        "abandonment_prob": spaces.Box(0, 1, shape=(1,)),
        "interventions_shown": spaces.MultiBinary(10),  # which types already shown
        "time_in_step_s": spaces.Box(0, 600, shape=(1,)),
    })
    action_space = spaces.Discrete(10)  # 10 intervention types
    # 0=noop, 1=price_reframe, 2=upgrade_path, 3=market_comparison,
    # 4=term_explanation, 5=service_handoff, 6=save_progress,
    # 7=value_justification, 8=trust_signal, 9=tariff_comparison_simplify

    def step(self, action):
        # 1. Translate action to intervention
        intervention = self.intervention_types[action]
        # 2. Pass to persona bot → get behavioral response
        persona_reaction = self.persona_bot.react(self.state, intervention)
        # 3. Update state
        self.state = self.transition(self.state, persona_reaction)
        # 4. Compute reward
        reward = self.compute_reward(action, persona_reaction)
        return self.state, reward, self.done, {}

    def compute_reward(self, action, reaction):
        if self.done and self.state == "CONVERTED": return 1.0
        if self.done and self.state == "ABANDONED": return -0.5
        if action != 0: return -0.05  # Intervention cost (anti-spam)
        if self.state["segment_posterior"].argmax() == 2 and action == 5:
            return 0.3  # Bonus for correct Peter handoff
        return 0.0
```

**PPO setup**:
- Policy network: MLP (128→64→10) — small by design (simpler to train stably)
- Value network: MLP (128→64→1)
- 4 parallel environments (each running a different persona bot)
- 64 rollout steps per update
- PPO clip ε=0.2, entropy coefficient=0.01
- Hardware: 4× A100 for persona bot inference, 1× A100 for policy training
- Duration: ~8–12 hours for 2M environment steps
- Convergence signal: Mean episode reward increases from ~−0.1 (random policy) to ~+0.6

**Expected RL policy behavior** (what it should learn):
- Never use `service_handoff` for Franz (large negative reward each time → gradient drives this to 0 for p_S2 = 1)
- Use `service_handoff` within first 2 steps for Peter
- At Step 4 for Franz: use `market_comparison` or `price_reframe`
- At Step 7 for any persona: use `value_justification` or `transparency`
- `noop` when abandonment_prob is low (no reward from unnecessary intervention)

---

### Training Job 5: Behavioral Signal Encoder (Contrastive Learning — Stretch)
**What**: Train an encoder to produce dense representations of user sessions that separate converters from abandoners, enabling fast inference.

**Architecture**: Session Encoder (same Transformer as Job 3) + contrastive loss
**Loss function**: InfoNCE over (anchor=converter session, positive=another converter, negative=abandoner):
```
L = -log(exp(sim(anchor, positive)) / sum_i(exp(sim(anchor, negative_i))))
```

**Use cases**:
1. Zero-shot classification of new sessions without fine-tuning
2. Clustering sessions → discover sub-segments not in the original 3-segment model
3. Retrieval: "find past sessions most similar to this user → what worked?"

**GPU requirement**: 4× A100 for 4–6 hours

---

## C.3 Synthetic Data Pipeline — From personas.json to Training Data

### Step 1: Feature extraction from personas.json
```python
# Per segment, extract behavioral priors
behavioral_priors = {
    "segment_1": {
        "step_4_drop_prob": 0.70,  # calibrated from 66% aggregate
        "back_nav_rate_per_step": 0.15,
        "external_tab_prob": 0.35,   # ROPO behavior
        "dwell_multiplier_step4": 2.5,  # long consideration
        "response_to_price_reframe": +0.15,  # p_continue uplift
        "response_to_service_handoff": +0.20,
        "response_to_advisor_push": -0.05,
    },
    "segment_2": {
        "step_4_drop_prob": 0.55,
        "step_7_drop_prob_no_delta": 0.60,
        "step_7_drop_prob_per_eur_delta": 0.05,  # +5% abandon per €1 over estimate
        "external_tab_prob": 0.45,
        "response_to_price_reframe": +0.25,
        "response_to_service_handoff": -0.30,  # Franz hates this
        "response_to_market_comparison": +0.20,
    },
    "segment_3": {
        "step_3_drop_prob": 0.35,  # overwhelmed BEFORE tariff
        "step_4_drop_prob": 0.75,
        "back_nav_rate_per_step": 0.30,
        "dwell_multiplier_all_steps": 1.8,
        "response_to_service_handoff": +0.50,  # Peter loves this
        "response_to_complexity_increase": -0.40,
    }
}
```

### Step 2: Stochastic session generator
```python
def generate_session(persona_id, sub_variant=None, coach_active=False, coach_policy=None):
    session = []
    state = FunnelState(step=0)
    segment = behavioral_priors[persona_id]
    
    while not state.terminal:
        # Generate events for current step
        dwell = sample_dwell(segment, state.step)
        back_navs = sample_back_nav(segment, state.step)
        hovers = sample_hover_events(segment, state.step)
        session.extend([Event(state.step, "dwell", dwell), ...])
        
        # Optional: coach fires an intervention
        if coach_active:
            features = extract_features(session)
            p_abandon = abandonment_model.predict(features)
            if p_abandon > THRESHOLD:
                action = coach_policy(state, features)
                intervention = render_intervention(action)
                # Persona bot reacts
                reaction = persona_bot.react(state, intervention)
                session.append(Event(state.step, "intervention", action, reaction))
                state.apply_reaction(reaction, segment)
        
        # Transition
        p_continue = compute_continue_prob(segment, state, session)
        if random() < p_continue:
            state.advance()
        else:
            state.abandon()
    
    return session, state.outcome
```

### Step 3: Validation loop
After generating N sessions, verify:
- Aggregate step-4 drop-off ≈ 66% (±2%)
- Aggregate step-7 drop-off ≈ 78% (±2%)
- Aggregate conversion rate ≈ 5.6% (±0.5%)
- Per-segment drop-off patterns match qualitative descriptions

If not: adjust `behavioral_priors` and regenerate. Document the assumptions.

---

## C.4 What Would Impress a Technical Jury

Ranked by jury impact:

### 1. Show training convergence curves (not just end results)
Plot: PPO mean episode reward over training steps. A curve that goes from −0.1 to +0.6 over 2M steps and stabilizes is concrete evidence that RL training happened and worked.

### 2. Show persona-specific policy differentiation
Create a policy attribution heatmap:
```
                Intervention type
                noop  price  upgrade  market  handoff  ...
Persona S1      45%   22%    18%      10%      3%      ...  ← Judith
Persona S2      38%   30%    5%       25%      2%      ...  ← Franz
Persona S3      20%   5%     8%       2%      62%      ...  ← Peter
```
This shows the RL agent learned fundamentally different strategies per persona — the "do not unify" requirement from the spec.

### 3. Abandonment predictor ROC curve with step-specific breakdowns
Show AUC-ROC at each step separately. Step 4 AUC of 0.79, Step 7 AUC of 0.83 is much more convincing than an aggregate number. Include a feature importance analysis (which events predict abandonment most).

### 4. Statistical significance on conversion uplift
With 10,000 simulated runs per condition (feasible on cluster in <1 hour with fine-tuned persona bots), show:
- Baseline conversion: 5.6% (calibrated)
- With rule-based coach: X% ± CI
- With RL coach: Y% ± CI
- p-value from Mann-Whitney U test
- Separate results per persona

### 5. Convergence of synthetic distribution to real distribution
Show a figure: "Our synthetic generator produces 66.2% step-4 drop-off and 77.8% step-7 drop-off, matching UNIQA's real funnel data to within measurement error." This validates the entire simulation framework.

---

## C.5 Timeline Estimate — 36 Hours with GPU Access

### Hours 0–4: Foundation (all team members)
- Build state machine (2 team members, 3h)
- Set up cluster jobs, test GPU access (1 team member, 1h)
- **Launch Job 1: Synthetic data generation** (fire and forget, runs in background)

### Hours 4–8: Persona bots MVP + Rule-based Coach
- Implement prompted persona bots (GPT-4 API), test behavioral differentiation
- Write rule-based Coach (20 rules from the coach arguments in product reference)
- First simulation run: 500 sessions per persona, log conversion rates
- **Launch Job 2: Persona bot fine-tuning** (3 models × Mistral-7B, LoRA)

### Hours 8–14: ML model training
- Implement abandonment predictor (Transformer, PyTorch)
- **Launch Job 3: Abandonment predictor training** on synthetic data from Job 1
- Implement LightGBM persona classifier, train on synthetic data
- Evaluate persona classifier (should reach >80% accuracy with 3 classes)

### Hours 14–22: RL training
- Implement OpenAI Gym environment wrapping the state machine + fine-tuned persona bots (from Job 2, should be ready by hour 14)
- **Launch Job 4: PPO training** (8h run)
- Meanwhile: analyze abandonment predictor results, generate feature importance charts

### Hours 22–28: Integration + large-scale simulation
- Plug RL policy into Coach system
- Run A/B simulation: 10,000 sessions per condition (baseline / rule-based / RL) using fine-tuned persona bots
- Statistical analysis of results

### Hours 28–34: Demo + visualization
- Build Streamlit dashboard showing: funnel flow, live coach interventions, conversion comparison chart
- Implement the "side-by-side" demo: Franz without coach vs. Franz with coach, narrated step by step
- Prepare the policy attribution heatmap and training curves

### Hour 34–36: Final report + rehearsal
- Document assumptions, calibration method, gaps
- Rehearse demo

---

## C.6 GPU Resource Allocation Plan (64× A100)

| Job | GPUs | Duration | Parallelism |
|---|---|---|---|
| Job 1: Synthetic data gen (Llama-70B batch inference) | 16 A100 | 4h | 16-way model parallel |
| Job 2a: Mistral-7B fine-tune Judith | 2 A100 | 5h | DDP |
| Job 2b: Mistral-7B fine-tune Franz | 2 A100 | 5h | DDP |
| Job 2c: Mistral-7B fine-tune Peter | 2 A100 | 5h | DDP |
| Job 3: Abandonment predictor training | 2 A100 | 2h | DataParallel |
| Job 4: PPO RL training | 8 A100 (4 env + 4 policy) | 10h | Custom async |
| Job 5: Large-scale simulation (10k runs × 3 conditions) | 8 A100 | 3h | Embarrassingly parallel |
| Job 6 (stretch): Contrastive encoder | 4 A100 | 4h | DDP |
| **Peak simultaneous usage** | **~28 A100** | | Jobs 1–3 overlap in hours 0–8 |
| **Total GPU-hours** | **~220 GPU-hours** | | Well within 64× A100 × 36h = 2,304 hours |

**Efficiency note**: 64× A100 × 36h = 2,304 GPU-hours total. The plan above uses ~220 GPU-hours — leaving large headroom for iteration, failed runs, and re-training with adjusted hyperparameters.

---

# D. SYBILION ANGLE

## D.1 What Sybilion Does (Recap)
Sybilion specializes in probabilistic time-series forecasting — Bayesian uncertainty quantification over sequential data, outputting credible intervals rather than point predictions.

## D.2 How It Maps to the Funnel Problem

The insurance funnel IS a time series, but not a conventional one:

**Conventional time series**: fixed time intervals, continuous-valued observations (stock price, energy demand)
**Funnel time series**: variable-length discrete steps, mixed continuous/discrete observations

There are two ways to frame it:

### Framing 1: Survival Probability Forecast
At each step k, given all behavioral signals observed so far, forecast P(user completes purchase) as a function of remaining steps.

```
Time steps: [entry, step_3, step_4, step_6, step_7, closing]
Observations: [signals_t0, signals_t1, signals_t2, signals_t3, signals_t4, signals_t5]
Forecast: P(conversion) with credible interval at each step
```

This maps directly to a Bayesian survival model. Sybilion's probabilistic framework could output something like: "Given what we've observed through Step 4, there's a 23% chance this user converts, with 90% CI [12%, 38%]." The CI tightens as more steps are observed.

**Concrete time series structure**:
Each "observation" at step k is a feature vector:
`[dwell_time_k, back_nav_count_k, hover_events_k, session_gap_k, field_errors_k]`

The time series length is 5–7 steps — very short. This is the core challenge: Sybilion typically shines on longer series where temporal dynamics matter.

### Framing 2: Within-Step Micro-Time Series
If you emit behavioral signals at high frequency (e.g., every 5 seconds), each step becomes a short time series of 0–60 observations:

```
[t=0s, hover_pos=(420,300), dwell_at_optimal_row]
[t=5s, hover_pos=(620,300), dwell_at_optplus_row]
[t=10s, scroll_down=200px]
[t=15s, hover_pos=(850,300), advisory_required_hover]
[t=20s, back_nav_event]
...
```

This produces a real time series of length 10–40 within each step. Sybilion's forecasting framework is much more appropriate at this granularity.

**Forecast question**: "Given the first 15 seconds of behavior at Step 4, what is P(user advances past step 4) with uncertainty?"

## D.3 Practical Integration Design

```python
class SybilionConversionForecaster:
    """
    Wraps Sybilion's probabilistic forecasting API 
    over the funnel micro-event time series.
    """
    
    def update(self, new_events: List[BehavioralEvent]) -> ProbabilisticForecast:
        """
        Called every 5 seconds with new behavioral events.
        Returns: {
            "p_convert_mean": 0.23,
            "p_convert_ci_90": [0.12, 0.38],
            "most_likely_abandonment_step": 4,
            "confidence": 0.67
        }
        """
        time_series = self.event_encoder.encode(new_events)
        return sybilion_api.forecast(
            series=time_series,
            horizon=len(remaining_steps),
            quantiles=[0.05, 0.25, 0.5, 0.75, 0.95]
        )
    
    def should_intervene(self, forecast: ProbabilisticForecast) -> bool:
        # Intervene if 50th-percentile conversion drops below threshold
        # AND we're not at high-uncertainty (wide CI = wait for more signal)
        ci_width = forecast["p_convert_ci_90"][1] - forecast["p_convert_ci_90"][0]
        return (forecast["p_convert_mean"] < 0.40 and ci_width < 0.30)
```

The **uncertainty-aware** trigger is the key Sybilion value-add: don't intervene when the signal is ambiguous (CI wide), wait for clarity. This is something a fixed-threshold rule-based system can't do.

## D.4 Is This a Stretch Goal Worth Pursuing?

**Arguments for including Sybilion**:
- Differentiated from teams using pure LLM wrappers
- "Probabilistic intervention trigger" is a genuine technical contribution
- The uncertainty-aware triggering (don't fire on low-confidence signals) directly addresses the "annoyance rate" evaluation dimension
- If Sybilion has a Python API, integration is ~4–6 hours

**Arguments against prioritizing it**:
- The funnel has very few steps (7–8) → classical survival analysis (Kaplan-Meier, Cox PH) achieves similar results without the Sybilion overhead
- Short time series is not Sybilion's natural habitat — requires the micro-event reframing (per-step events at 5s granularity) which adds engineering complexity
- RL policy already handles the timing problem

**Recommendation**: Implement Sybilion as a **forecasting layer within the abandonment predictor** — replace the Transformer's point estimate P(abandon) with a Sybilion probabilistic forecast that returns credible intervals. Use the CI width as a confidence gate on the intervention policy: `if p_abandon_median > 0.6 AND ci_width < 0.25: trigger_intervention()`. This is a small addition (one component swap) that lets you demonstrate Sybilion without restructuring the whole architecture.

The time series feed into Sybilion would be: `[dwell_time, back_nav_count, hover_rate, session_gap]` measured at 5-second intervals within each step. For Step 4, this gives ~20–40 time points per session — enough for meaningful probabilistic forecasting.

**Estimated implementation time**: 6–8 hours (Sybilion API integration + synthetic data validation)

---

# APPENDIX: KEY NUMBERS CHEATSHEET

```
FUNNEL MATH
  1,000 starters
  → ×0.34 (66% drop at Step 4) = 340 reach tariff selection
  → ×0.76 (24% drop at Step 5, out of scope) = 258 
  → ×0.22 (78% drop at Step 7) = ~57 convert
  = 5.6% conversion rate

SEGMENT WEIGHTS (funnel)
  S1 Judith: 30% × 1000 = 300 Judiths
  S2 Franz: 50% × 1000 = 500 Franzs
  S3 Peter: 20% × 1000 = 200 Peters

TARGET DROP-OFF POINTS FOR COACH
  Step 4 (initial price):  66% → PRIMARY target
  Step 7 (final price):    78% → PRIMARY target
  Step 3 (data entry):     ~35% Peter-specific early exit (untracked)

TARIFF ECONOMICS
  Start:   €38.74/mo = €1.27/day, €464.88/yr, €1,400 annual max (3.0× ratio)
  Optimal: €68.14/mo = €2.25/day, €817.68/yr, €2,800 annual max (3.4× ratio)
  Delta:   ~€30/mo = ~€1/day for +€1,400/yr coverage
  Upgrade: Start → Optimal after 3 years, no new health assessment

BEHAVIORAL PRIORS (estimated, must be calibrated)
  Judith step-4 abandon: ~70%  (ROPO, advisor preference)
  Franz  step-4 abandon: ~55%  (online affine, lower friction)
  Peter  step-4 abandon: ~80%  (overwhelm, some leave before step 4)
  Franz  step-7 abandon: ~75%  (price delta shock is Franz's primary exit)
  Aggregate check: 0.3×0.70 + 0.5×0.55 + 0.2×0.80 ≈ 64.5% ≈ 66% ✓

HPC PLAN SUMMARY
  4h   Job 1: 100k synthetic sessions (16× A100, Llama-70B)
  5h   Job 2: 3× persona bot fine-tunes (6× A100, Mistral-7B LoRA)
  2h   Job 3: Abandonment predictor (2× A100, Transformer)
  10h  Job 4: PPO RL policy (8× A100)
  3h   Job 5: 30k A/B simulation runs (8× A100)
  ~220 GPU-hours total out of 2,304 available (9.5% utilization → lots of headroom)
```

---

*Analysis compiled by: Claude Code agent | Based on: Track_AI_Guided_Conversion_Flow_EN.md, uniqa-funnel-doc_en.md, Private_Doctor_Tariff_Product_Reference_EN.md, personas.json, persona_judith_segment_1.md, persona_franz_segment_2.md, persona_peter_segment_3.md, personas_comparison_matrix.md, README.md | Date: 2026-05-30*
