# Plan — Persona distillation v2 (per-step, state-covering, K-sampled)

Goal: a tiny local persona model whose **emergent S4/S6 churn + conversion match the funnel
anchors** (ε ≤ 0.12, per-persona conv within tol), distilled from the OpenRouter teacher
(`gpt-4o-mini`), runnable fast/offline for the coach loop.

> Background + rationale: `docs/REPORT_distillation_collapse.md`.
> Start over cleanly — new prompt, new dataset, new train/eval. The old `datasets/persona_v1`
> + `sft_steps.jsonl` are superseded (keep for reference).

## Invariants (do not violate)
- **No targets in the prompt.** The 66/24/78 anchors live only in `funnel.py` (eval).
  Conformance comes from the **state sampler + Stage-2 calibration**, never from telling the
  persona its bounce rate.
- **Per-step Markov policy** is the unit: input = (step UI/action-space, running_state,
  disposition, history_brief, [coach_widget]) → output = (events, state_update, decision,
  feeling, thought). Same interface Mode-B coach injection uses.
- **Train on broad states; roll out coherently.** Training examples are independent per-step
  contexts; generation/eval rolls the state forward through the student's own outputs.
- S5/add-on stays out of scope (in-scope flow S1→S2→S3→S4→S6).

---

## Task 1 — Per-step prompt v2  (`build_step_prompt_v2`)
Rebuild the step prompt as a clean, **single-step, Markov** prompt.
- Inputs surfaced: `you_are_on`, `ui_ascii`, `action_space`, `ux_complexity_here`, real
  price block (S4/S6), `your_running_state`, `session_instance` (disposition), `history_brief`,
  optional `coach_widget_shown`.
- Output schema: `events[]`, `state` (attention/satisfaction/effort_left/grasp/effort_vs_reward),
  `feeling`, `decision: continue|leave`, `reason`, `thought`; + `intervention_assessment` when a
  coach widget is shown.
- Rules: decide **honestly** given state vs intent; no mention of any target rate.
- **DoD:** prompt builds for every (persona, step, sampled context); produces valid JSON from
  the teacher on a 20-sample smoke test; contains zero anchor numbers (grep gate).

## Task 2 — State-space sampler  (`sample_state(persona, step, rng)`)
Produce realistic, leave-inclusive contexts.
- Disposition: reuse `_sample_disposition` (persona-weighted; encodes leave-propensity).
- Running state: sample per-step within **plausible** ranges (don't go uniform/off-manifold);
  bias coverage so the leave-prone region (low satisfaction/effort, price-shock dispositions at
  S4/S6) is well represented. Option: seed ranges from a quick "marginal pass" of normal teacher
  sessions, then oversample the tails (DAgger-style).
- **DoD:** sampler yields a balanced spread; a dry-run histogram shows ~1:1 leave/stay in the
  teacher's labels at S4 and S6 (measured on a small probe, Task 3a).

## Task 3 — K-sampled datagen (OpenRouter teacher)
For each (persona, step) draw M contexts; query the teacher **K times** each (temp≈0.9).
- Record per context: the `(messages → output)` SFT pair(s) **and** the empirical
  `leave_rate = #leave/K` (soft target).
- Keep per-K samples as individual SFT rows (natural balancing) OR keep one row + soft-label
  weight — decide in 3a.
- Volume budget (tune): ~M=150 contexts × K=5 × 5 steps × 3 personas ≈ 11k contexts / ~55k
  teacher calls; threaded. Cost check before full run.
- **3a (probe, do first):** M=20, K=5 on S4+S6 for all personas → confirm leave/stay balance
  and that leave-rate tracks disposition. Gate before the full run.
- Writers: `datasets/persona_v2/{sft_steps.jsonl, soft_labels.jsonl, manifest.json}`; commit.
- **DoD:** dataset built at the population mix; per-(persona,step) leave-rate distribution looks
  sane; balanced.

## Task 4 — Prepare + train LoRA (Leonardo)
- `prepare_sft` on v2 (per-persona chat-format), with **decision-token balancing / upweighting**
  of `leave` (BalanceSFT-style) if rows aren't already balanced.
- Train per persona, both bases (Qwen2.5-1.5B, MiniCPM5-1B) — reuse `slurm_finetune.sh`
  (OUTROOT split). Fewer epochs / early-stop on churn-ε, not loss.
- **DoD:** 3 adapters/base saved (verify `adapter_config.json` present — don't `scancel` mid-save).

## Task 5 — Coherent rollout eval (batched)
- `BatchedLocalTeacher.generate_cohort` (Mode A) → `validate` → per-persona **S4/S6 cond churn +
  conversion + ε** vs `ABANDON_PROBS`. (`leonardo/show_eval.py`.)
- Settings that worked: batch=48, N≈60–100, `max_new_tokens≈384`, `expandable_segments`,
  `--time 1:00:00`, robust incremental writes.
- **DoD:** report printed; compare to frontier ε≈0.10 and to v1's ε≈0.48.

## Task 6 — Fix outliers at SOURCE (dials), calibration last-resort
Measure the **coherent-rollout marginal** (T5), NOT the per-step sampled-state rate, then:
1. **Primary — tune dials/disposition** (`research/tune.py`). Structural outliers (e.g. judith
   S4 saturated-high across moods ⇒ disposition-driven, not state) are fixed by shifting that
   persona's dials / `_DISP_W` weights (judith → more "proceed online / prepared for premium")
   so the teacher's behaviour matches anchors → regenerate the affected cells → retrain. This
   fixes the model's *understanding*, and reshapes the training data correctly.
2. **Last-resort — Stage-2 calibration** (per-(persona,step) temperature/threshold on the leave
   decision) ONLY for the small residual after dial-tuning — because dial-tuning costs a full
   regen+retrain loop while calibration is free. Don't lead with it; it rescales a logit, it
   doesn't fix behaviour.
- **DoD:** post-fix rollout ε ≤ 0.12; each persona converts >0; per-persona conv within tol;
  outliers addressed via dials where structural.

> Note: single whole-session prompting is rejected (compare_gen: S4 churn ≡ 0, ε 0.31). It can
> match *overall conversion* (0.11) but not the per-step funnel shape — hence the per-step gate.

## Task 7 — Base comparison + pick
- Qwen2.5-1.5B vs MiniCPM5-1B on {ε, per-persona churn, sessions/sec, calibration effort}.
- **DoD:** one chosen base + a short results table for the report.

## Task 8 — Wire into the sim loop
- Swap chosen `LocalTeacher` into the sim/autoresearch loop (Mode A) and the coach loop
  (Mode B, `coach_widget` injection + `intervention_assessment`).
- **DoD:** Mode-A uplift run + Mode-B `coach_log` assessments produced locally, fast, offline.

---

## Execution order & checkpoints
`T1 → T2 → T3a (PROBE GATE) → T3 → T4 → T5 → T6 (GATE: ε≤0.12) → T7 → T8`

Two hard gates: **T3a** (state sampler actually yields balanced honest leaves before spending on
the full teacher run) and **T6** (ε passes before wiring into the loop).

## Risks
- Off-manifold sampled states → junk labels → constrain ranges / seed from teacher marginal (T2).
- Teacher cost/volume → bound M·K; probe first (T3a).
- Marginal still off after good per-step policy → that's expected; T6 calibration closes it.
- Prefill-bound batched eval → the smaller per-step prompt (T1) should also speed generation.
