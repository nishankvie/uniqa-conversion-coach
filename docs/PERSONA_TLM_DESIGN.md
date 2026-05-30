# PERSONA-TLM — model design, proof, calibration

> **Role: baseline, not the headline model.** The primary persona path is now
> [`PERSONA_TRAIN_PLAN.md`](PERSONA_TRAIN_PLAN.md) (H1 = fine-tune MiniCPM5-1B).
> This tiny from-scratch TLM stays because it is the *calibratable* model that
> pins the Z3 safety budget `b = ε_anchor` (§3.4) — a job the generative FT model
> does poorly. Keep both; they are complements.

Folds into `docs/PERSONA_MODEL_PLAN.md`. Grounded in `src/uniqa/contracts.py`,
`src/uniqa/tlm.py`, `src/uniqa/psyche.py`, `src/uniqa/eventproc.py`,
`docs/TLM_RESEARCH.md`, `docs/ARCHITECTURE.md`. Does not duplicate them —
extends and critiques.

---

## 1. PERSONA-TLM MODEL DESIGN

### 1.1 Architecture (v0: decoder-only, text-token-only)

Pick a **tiny decoder-only GPT** over the `tlm.VOCAB` token stream. Same shape
as `tlm.TLMConfig` (4L / 4H / d=128 / block=512, ~0.8M params). nanoGPT adapter
from `karpathy-experiment/` is the trainer. **No UI patches in v0.** UI state
enters as text tokens (see §1.3) — keeps vocab small, lets us reuse the same
trained backbone for the coach-TLM head, and is buildable in one Leonardo job.

v1 multimodal (later): bolt a frozen low-res UI encoder (e.g. CLIP-ViT-B/32,
64×64 thumbnails → 16 patch tokens) and prepend patch embeddings per step.
Only justified if v0 fails the persona-separability gate (§2.4).

```
v0 stream  (decoder-only, single modality):

  <bos> <persona:franz> <ui:S4:tariff_grid>
        <step:S4> <ev:step_enter> <tgt:none> <dt:0>
        <atom:price_reframe:offered>            ← intervention atom embedded inline
        <ev:price_hover> <tgt:price> <dt:2> <count:1>
        <ev:idle>       <tgt:none>  <dt:1> <dwell:4>
        <ev:abandon>    <tgt:none>  <dt:0>
  <eos>
```

### 1.2 I/O

- **Input (training):** id sequence from extended `tlm.encode(log, persona, ui_state, atoms)`.
- **Loss mask:** loss only on `<ev:…> <tgt:…> <dt:b> <dwell:b> <count:b>` tokens
  (the **USER tokens**). All `<persona:…>` / `<ui:…>` / `<atom:…>` / `<step:…>`
  are CONDITIONING — never predicted. Mirrors Decision Transformer: condition on
  context, predict action stream.
- **Output (inference):** sample next user tokens until `<ev:abandon>`,
  `<ev:convert>`, or block boundary. `eventproc.collapse` reverses noise expansion
  if we sample mouse-level granularity (we do not — see §1.5).

### 1.3 Persona conditioning — three options, pick one

| Option | Mechanism | Pro | Con |
|---|---|---|---|
| **A. Tag token** (current `tlm.py`) | `<persona:franz>` at position 1 | trivial, conditionable at inference | one embedding row per persona → underfits within-persona variance |
| **B. Learned profile embedding** | concat `(persona_tag, intent_tag, attrs)` → small MLP → 1 prefix vector summed to every token embedding (prefix-tuning style) | captures intent + jitter from `psyche.init_mind`; one model handles N personas | slightly more plumbing; need to expose `intent` at training time |
| **C. Prompt distillation** | feed full `persona.md` text through a frozen encoder, cache the vector | richest signal, future-proof for new personas | needs a text encoder, breaks token-only purity |

**Pick B for v0.** It's cheap, subsumes A, and lets us inject the same
`Intent` axis the psyche model already uses (`psyche.INTENT_MIX`). Prefix vector
shape = `(1, d=128)`. Trained jointly. **Critical:** `Intent` is sampled per
session and stays fixed — same contract as `psyche.Mind.intent`.

### 1.4 UI state + intervention atoms entering the stream

Add two **new token families** to `tlm.VOCAB` (see §1.6 deltas):

- `<ui:STEP:layout_id>` — one token per step, names the static layout the user
  is looking at (e.g. `<ui:S4:tariff_grid_2col>`, `<ui:S6:health_form_long>`).
  This is what the data-gen workflow prompt also encodes as the "json-render
  representation". Closed set, ~15 ids total.
- `<atom:intent:phase>` where `intent ∈ CoachAction.value` and
  `phase ∈ {offered, shown, dismissed, cta}`. An intervention atom embedded by
  the data-gen prompt becomes a literal token at the position it was offered.
  Mirrors the existing `EventType.WIDGET_*` events but pre-decision: lets the
  persona-TLM learn how each atom shifts behaviour (the supervised analog of
  `psyche.apply_coach_effect`).

Both families are **CONDITIONING tokens** (loss-masked). The persona-TLM never
predicts the UI or the atom; it predicts how the user reacts.

### 1.5 Granularity choice

Train on **collapsed Moments** (`eventproc.collapse`), not raw mouse spam. Reasons:
(a) keeps sequences ≤ ~150 tokens, well under `block_size=512`;
(b) the LLM teacher in the data-gen workflow naturally emits collapsed events
(it won't fake 200 mouse-move events); (c) raw mouse timing is the place
assumption A1 (synthetic ≈ real) breaks hardest — don't model what we can't fit.

### 1.6 Concrete deltas vs current `tlm.py`

Current vocab is ~83 tokens; proposed v0 is ~110. Diff:

```
ADD:
  <ui:S0:welcome> … <ui:S7:summary>           ~15 ids   (closed UI layout set)
  <atom:{coach}:{offered|shown|dismissed|cta}> ~44 ids  (11 CoachActions × 4)
  <intent:purchase|orientation|comparison|price_check>  4 ids   (conditioning, see §1.3 opt B)
  <outcome:convert|abandon|handoff>            3 ids   (terminal marker, cleaner than ev:abandon)

KEEP but raise resolution where it matters:
  DT_EDGES → add 0.1 lower bound and 60s upper (price-shock dwells go > 30s in real logs)
  DWELL_EDGES → fine; covers the regimes psyche.py uses

RECONSIDER:
  TARGETS list = 12; promote to a per-step closed set indexed via <tgt:…>.
    Today "field" is a wildcard catch-all → loses Step-6 form-field signal
    (which field churned matters for form_helper targeting). Expand to ≈25 ids.

LOSS MASK:
  Persona-TLM:  loss on <ev:…> <tgt:…> <dt:…> <dwell:…> <count:…> <outcome:…>
  Coach-TLM:    loss on <atom:…:offered> only (the policy decision)
  Both heads share embeddings + transformer; differ only in the loss mask.
                This is the cheapest way to get the "shared vocab, two heads"
                story TLM_RESEARCH.md already commits to.
```

Total vocab ≈ 110 → `approx_params ≈ 12·4·128² + 110·128 ≈ 0.8M`. Unchanged
compute envelope.

---

## 2. PROVE-THE-CONCEPT EXPERIMENT (one Leonardo afternoon)

### 2.1 Smallest experiment that answers two questions

Q1: **Does a persona-TLM learn persona-differentiated behaviour?**
Q2: **Does it reproduce the known funnel metrics within tolerance?**

### 2.2 Dataset

- **Source A (volume floor):** `psyche.py` synthetic — 30k sessions
  (9k Judith / 15k Franz / 6k Peter, matching the 30/50/20 mix). Already
  calibrated to 5.6 % / 66 / 24 / 78. Free, fast, reproducible.
- **Source B (LLM-teacher, the actual experiment):** 6k sessions via the
  data-gen workflow described in the task brief (system prompt = persona.md +
  persona.json; workflow prompt = low-res UI image + json-render + atoms +
  Coach TLM reasoning). 2k per persona. Validated through
  `contracts.Event` schema gate — any feed that doesn't parse is dropped.
- **Splits:** 90 / 5 / 5 (train / val / test) **stratified by persona × outcome**
  (convert/abandon-step). Hold out one whole-cohort test bucket so funnel-stat
  evaluation isn't leakage.

### 2.3 Baselines (cheap, mandatory)

1. **Uniform** — sample next event uniformly from in-step legal set. Floor.
2. **Per-persona n-gram (n=4)** over the same token stream. The real baseline
   the TLM must beat on next-token perplexity. ~5 min to fit.
3. **Psyche model** (`psyche.py` end-to-end) — the *behavioural* baseline. The
   TLM only earns its keep if it matches psyche on funnel stats **and** beats
   n-gram on next-token PPL.

### 2.4 Metrics + pass thresholds (3 gates, all must pass)

| Gate | Metric | Threshold |
|---|---|---|
| **G1 next-token** | val perplexity on USER tokens | < 0.85 × n-gram-4 PPL |
| **G2 funnel match** | sample 5k sessions per persona; compute per-step survival; TV vs anchors (5.6 / 66 / 24 / 78) | TV ≤ 0.08 marginal; KL ≤ 0.15 |
| **G3 persona separability** | for each persona pair (J/F, F/P, J/P): JS-divergence of next-event distribution at S4 entry | JS ≥ 0.10 (direction matches `psyche.INTENT_MIX` priors); also classifier-2-sample test AUC ≥ 0.65 |

Bonus diagnostic (not a gate): **bounce-reason recoverability** — train a
linear probe on TLM hidden state at the abandon position to predict
`psyche.BounceReason`. Acc > 0.5 means the model internalised the latent
structure, not just the marginal.

### 2.5 Leonardo job shape

```
partition: boost_usr_prod   reservation: s_tra_ncc
1 × A100 64GB, 1 node, 8 CPU, 96GB RAM
walltime: 2h (training) + 30min (eval)
trainer:  nanoGPT adapter from karpathy-experiment/
config:   TLMConfig(n_layer=4, n_head=4, n_embd=128, block_size=512)
batch:    256 sessions × ~150 tok = 38k tok/step
optim:    AdamW lr=3e-4 cosine, 4k steps, fp16
data:     36k sessions total (~5.4M tokens) → ~140 epochs in 2h on 1 A100
artifacts: tlm_v0.pt, eval_report.json, samples_per_persona.jsonl
```

Single SLURM job. Falls back to laptop M-series in ~6h if Leonardo queue is
deep — keeps it hackathon-safe.

---

## 3. TRAIN AGAINST KNOWN METRICS

### 3.1 Division of labour — teacher vs calibration

The LLM teacher (data-gen workflow) provides:

- **shape**: realistic event sequences, persona voice, plausible reactions to atoms;
- **persona × intent → behaviour mapping** (it reads the same persona.md the
  psyche model was hand-coded from);
- **reasoning labels** ("Coach TLM reasoning" field) we can later distil into
  the coach-TLM head.

The teacher **does not** reliably provide:

- correct marginal conversion rate;
- correct per-step drop-off ratios;
- correct persona mix (we control mix at sampling time anyway).

So we **don't** ask the LLM to be metric-accurate. We let it generate
*conditional* shape, then **calibrate marginals** with a tiny set of free
parameters.

### 3.2 Free parameters (small, auditable)

| Param | Shape | Role |
|---|---|---|
| `T_persona` | scalar per persona (3 values) | sampling temperature; lower → more deterministic = higher survival |
| `π_intent[persona]` | 3 × 4 simplex | intent-mix prior at sampling (overrides teacher's implicit prior); init from `psyche.INTENT_MIX` |
| `b_outcome[persona, step]` | learned logit bias head | per-persona, per-step additive bias on `<outcome:abandon>` vs `<ev:next_step_enter>` |
| `α_mix` | scalar in [0,1] | mixture weight teacher data vs psyche data in the training set |

Total free params: 3 + 12 + 3·8 + 1 = **40 scalars**. Trivially fittable.

### 3.3 Calibration objective

Two-stage. Stage 1 trains the TLM, stage 2 calibrates the 40 scalars **without
retraining the transformer** (CMA-ES or just grid-search on a laptop).

```
Stage 1 (gradient):   minimise CE on USER tokens, no metric loss.
Stage 2 (black-box):  given the trained TLM, sample N=5000 cohorts at
                      candidate (T, π, b, α). Compute:

  L_calib(θ) =   λ1 · TV(funnel_marginal_sim, funnel_anchors)
               + λ2 · Σ_p KL(p_step_survival_sim[p]  ‖  psyche_anchors[p])
               + λ3 · TV(persona_mix_sim, [0.30, 0.50, 0.20])
               + λ4 · TV(bounce_reason_sim, bounce_reason_psyche)

  anchors = { overall: 0.056,
              S4_cond: 0.66, S5_cond: 0.24, S6_cond: 0.78,
              per-persona conditional survival from psyche calibration tests }
```

`λ1..λ4` = 1.0 / 0.5 / 0.3 / 0.2 (overall conversion dominates). CMA-ES with
σ=0.1 converges in ~50 generations × 5k samples = ~30 CPU-min. Outputs
`tlm_v0.calib.json` next to the weights.

### 3.4 Tie to assumption A1 (ε estimate)

Assumption A1 in `docs/AUTORESEARCH.md` / `TLM_RESEARCH.md`: synthetic feeds
statistically match real. Operationally **ε := TV(synthetic_funnel, real_funnel)**.

We can't measure ε directly (no real per-session logs). Two proxies:

1. **ε_anchor** = TV vs the published anchors (5.6 / 66 / 24 / 78). Stage-2
   calibration explicitly minimises this; report final value. Target ε_anchor ≤ 0.05.
2. **ε_teacher_vs_psyche** = TV between LLM-teacher distributions and
   psyche-engine distributions on identical (persona, step) cells. If this is
   large *before* calibration, A1 is wobbly and we need Loop B to close it.
   Report this as the **headline "how much do we trust the teacher" number**.

The Z3 gate in `specs/z3/coach_autoimprove.py` requires `τ ≥ 2b`; the budget
`b` here is exactly `ε_anchor`. So §3.3 directly sets the safety threshold for
Loop A acceptance. **This is the load-bearing connection between the persona-
TLM design and the rest of the autoresearch story.**

---

## 4. RISKS / OPEN ASSUMPTIONS

| # | Risk | Where it bites | Cheap mitigation |
|---|---|---|---|
| R1 | **A1 wrong**: LLM teacher feeds don't match real users (most likely on timing + recovery from atoms) | G2 funnel gate fails after calibration; coach over-fits to a fiction | Mix-in psyche data with weight `α_mix`; report ε_teacher_vs_psyche; Loop B re-fits as soon as real data exists |
| R2 | **Mode collapse**: TLM emits one canonical Franz journey | G3 separability looks fine on means but variance dies | Nucleus sampling p=0.9, temperature ≥ 0.8 at gen, label-smoothing 0.05 on USER tokens, EOS regularisation |
| R3 | **Timing realism**: Δt buckets don't match real ms-scale interactions | downstream coach learns wrong "wait then intervene" timing | Keep timing coarse (current `DT_EDGES`); commit to *decision-event* granularity not ms; revisit only in v1 multimodal |
| R4 | **Eval circularity**: G2 anchors come from the same source we calibrated on | "passing" the gate is tautological | Keep one held-out cohort the calibrator never sees; report *uncalibrated* funnel stats alongside calibrated ones (transparency) |
| R5 | **Persona leakage**: TLM uses tag as a shortcut, learns no real behavioural diff | G3 still passes (tag explains it) but the model is brittle to unknown personas | Train with 10% `<persona:unknown>` dropout; require G3 to hold under tag-dropout (re-score with tag masked → JS ≥ 0.05) |
| R6 | **Atom-effect spurious**: model attributes outcome shifts to atoms that came from teacher prior | coach-TLM later picks dud atoms | Counterfactual augmentation in data-gen: for X % of sessions, re-run with atom removed → contrast pairs make atom effect identifiable |
| R7 | **Vocab churn breaks coach-TLM**: adding UI / atom tokens later forces retraining | re-do Leonardo job | Lock vocab v0 spec **before** training run; reserve 32 unused ids for future growth |
| R8 | **Reasoning field is decorative** (the "Coach TLM reasoning" in data-gen) | wasted signal | Even in v0 store reasoning out-of-band keyed by session_id; distil into coach-TLM in v2 |

---

## 5. FURTHER WORK / SEQUENCING

```
v0 — text-only persona-TLM        ← MINIMAL DE-RISK MILESTONE
  • vocab deltas §1.6, prefix-embed persona conditioning (§1.3 opt B)
  • train on psyche(30k) + LLM-teacher(6k)
  • stage-2 calibrate 40 scalars to anchors
  • pass G1/G2/G3 (§2.4) → ε_anchor ≤ 0.05 → Z3 gate has a real `b`
  ETA: 1 Leonardo job + 1 day plumbing

v1 — multimodal persona-TLM
  • only if v0 fails G3 OR demo needs visual-grounding story
  • frozen CLIP-ViT on 64×64 step thumbnails → 16 patch tokens per <ui:…>
  • same loss, same heads
  ETA: +1 day, +1 Leonardo job (still 1×A100, walltime 4h)

v2 — coach-TLM sharing the vocab
  • same backbone, second head, loss mask on <atom:*:offered>
  • teacher = the data-gen "Coach TLM reasoning" field + psyche rule-coach traces
  • plugs into RuleCoachModel.decide signature in coach_io.py — zero contract churn
  ETA: +1 day after v0

v3 — Loop B online
  • PersonaFit (refit prefix embeddings + 40 calib scalars on real batch)
  • IPS off-policy eval of coach-TLM on real logs
  • hypothesis hit-rate (contracts.Hypothesis.evaluate) closes the loop
  ETA: post-hack
```

**De-risk pick:** v0 alone is the milestone that earns the bet. It produces
(a) a concrete ε number for the Z3 safety story, (b) a faster differentiable
persona engine for Loop A, and (c) the trained backbone v2 reuses for free.
Everything after v0 is incremental and gated on its result.
