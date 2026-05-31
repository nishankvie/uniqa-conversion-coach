# Persona classification from generated state-steps — probe

**Question:** Can we classify persona (judith/franz/peter) from its generated
state-step records, and at which funnel stage is confidence good enough?

**Data:** `datasets/persona_v2/sft_steps.jsonl` — 2,398 per-step records, balanced
800/persona, 5 steps (S1,S2,S3,S4,S6). State-covering K-sampled → per-step samples
are independent (NOT live trajectories).

**Features (no prompt leakage — only generated output):** output state vars
(attention, satisfaction, effort_left, grasp, effort_vs_reward), their delta from
incoming running_state, decision(leave), n_events, leave_rate, feeling(one-hot).
21 features. Model: RandomForest, 5-fold CV.

## Answer 1 — Yes, persona is recoverable from one generated step
- **Overall accuracy 0.72** (chance 0.33), mean top-class confidence 0.60.
- Top discriminators: **grasp** (Δ + level), **satisfaction**, **effort_vs_reward**,
  **effort_left**, **attention**. → comprehension/effort dynamics carry the signal,
  exactly the dials that separate the segments (Peter low comprehension/overwhelm).
- Confusion: each persona mostly recovered; franz↔judith the main mixup early.

## Answer 2 — Per-step: signal rises at the price/health screens
| step | n | acc | per-persona recall |
|------|---|-----|--------------------|
| S1 coverage | 480 | 0.69 | J .64 F .84 P .60 |
| S2 persons  | 480 | 0.69 | J .57 F .84 P .65 |
| S3 personal | 480 | 0.74 | J .74 F .77 P .70 |
| S4 tariff/price | 480 | 0.71 | J .75 F .47 **P .90** |
| S6 final/health | 478 | 0.76 | J .67 F .74 **P .86** |

**Peter becomes the most separable at S4/S6** (price + complexity overwhelm fire).
Franz dips at S4 (confused w/ peter under price reaction).

## Answer 3 — Sequential: confidence "good enough" by S4
Accumulating independent per-step evidence over a live trajectory (naive-Bayes
combine of per-step posteriors, Monte-Carlo n=4000):

| after step | cum accuracy | conf in true persona |
|------------|--------------|----------------------|
| S1 | 0.69 | 0.53 |
| S2 | 0.80 | 0.67 |
| S3 | 0.88 | 0.77 |
| **S4 tariff/price** | **0.95** | **0.87**  ← good enough |
| S6 final/health | 0.97 | 0.92 |

## Takeaway for the Coach
- A behaviour-only classifier (no persona label, no health data — fits the Coach's
  observation contract) reaches **~95% persona ID by the tariff screen (S4)** and
  **~97% by the end**.
- **One screen is weak (~70%); 3–4 screens make it confident.** So the Coach should
  treat early-funnel segment inference as a soft prior and only commit to
  persona-specific intervention from **S3–S4 onward**, when grasp/satisfaction
  trajectories have separated.
- Peter (low comprehension, high overwhelm) is detectable earliest at the price
  step → highest-value early intervention target.

Repro: `python3 research/persona_classify_probe.py`
