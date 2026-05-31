# Problem → Solution: distilling a prompted teacher into a tiny local persona model

> Hackathon report — "problems encountered → solutions". Concerns the persona model: we
> want fast, local, offline persona simulation (for the autoresearch / coach loop) by
> distilling our prompted frontier teacher (OpenRouter `gpt-4o-mini`) into a tiny LoRA
> (Qwen2.5-1.5B / MiniCPM5-1B) on Leonardo.

## The problem

Our first distillation used **hard-label sequence-level KD**: the teacher walks the funnel
S1→S6 (one turn per step), we keep each step's `(prompt → sampled output)` pair, and SFT the
student with completion-only loss, then drop the prompt. Standard "context/prompt
distillation".

It **collapsed**. Eval of the distilled models (batched, on A100):

```
judith  conv = 1.00   S4 churn 0.00 / target 0.70   S6 churn 0.00 / 0.68   ε ≈ 0.48
```

The student made **every** persona convert — zero abandonment — vs the frontier teacher's
faithful ε ≈ 0.10. It learned "always continue → convert" and discarded the churn behaviour,
which is the *entire* point of the persona model.

## Why (root cause)

The failure is well-documented in the distillation literature; three named modes compounded:

1. **Hard labels discard the teacher's distribution.** One sample per step → the student
   never sees `P(leave)` vs `P(continue)`; the knowledge that matters lives in the *soft*
   distribution (Hinton 2015), not the argmax.
2. **Per-step class imbalance.** Each session has ~4–5 `continue` decisions and **at most one**
   `leave`. The decision token is ~5:1 toward continue → the student modes to continue →
   everyone reaches S6 and converts (cf. *BalanceSFT*, 2505.20192).
3. **Exposure bias / state drift.** SFT supervises **teacher-visited** states (dominated by
   "continue" because the teacher mostly progresses); at inference the student visits its own
   states and compounds the bias (*"Post-Training is About States, Not Tokens"*, 2605.22731;
   DAgger). Diversity collapse under SFT is also documented (2604.16027).

## The solution: per-step, state-covering distillation with K-sampled soft targets

Reframe the student from a **trajectory imitator** to a **per-step Markov policy**:

```
π(events, state_update, stay/leave | step, running_state, disposition, history_brief, [coach_widget])
```

Four changes, each targeting a failure mode above:

- **Cover the state space, not the teacher's path.** Sample contexts (disposition + plausible
  running state) that include the *leave-prone* region — fed-up, price-shocked, "just
  comparing". The teacher then honestly says `leave` for many of them, so the data is
  **balanced** instead of harvesting rare leaves. (Fixes #2 and #3 — DAgger / Decision-
  Transformer / state-distribution view.)
- **K-sampling → soft leave-probability.** Query the teacher **K times** per context (temp>0);
  the empirical leave-rate *is* `P(leave | context)`. This distils the teacher's
  **distribution** even though the API exposes no logits. (Fixes #1.)
- **Roll out coherently, then calibrate.** Marginal churn = per-step policy × state-visitation.
  We train the policy over the whole state space, roll out coherently (cohort lockstep), and
  add a thin **Stage-2 calibration** (temperature on the leave decision per persona/step) to
  snap the marginals onto the funnel anchors.
- **Targets stay eval-only — never in the prompt.** Conformance to the 66/24/78 anchors comes
  from the **state-sampler distribution + calibration**, *not* from telling the persona "leave
  66% at S4". The persona only ever decides honestly given its state. (Keeps the simulator
  scientifically honest: it must *reproduce* the anchors, not be handed them.)

## Operational lessons (also in the report)

- **`scancel` mid-training loses the final adapter** (saved only at the end) — recover from the
  last `checkpoint-N/`.
- **64 GB A100 OOMs** at batch 100 with ~2.5k-token prompts; batch ≈48 fits. Set
  `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`.
- **Make eval crash-robust** (per-persona try/except + incremental writes) so one failed
  persona doesn't lose the whole run; raise SLURM `--time` for long batched evals.
- **Batched local inference is the speed unlock** (cohort lockstep batches all sessions'
  per-step generations) — but it's *prefill-bound* on large prompts, which also motivates the
  per-step (smaller-context) reformulation above.
