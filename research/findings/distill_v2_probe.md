# T3a probe — per-step state-covering datagen (OpenRouter gpt-4o-mini)

600 teacher calls (M=20 contexts × K=5 × {S4,S6} × 3 personas), 140s. Mood split 34/33/33.
Targets shown for reference only — **never in the prompt**.

| persona·step | obs leave_rate | target | by_mood fresh/neutral/worn | token balance |
|---|---|---|---|---|
| franz S4  | 0.44 | 0.55 | 0.35 / 0.37 / 0.63 | 0.44 |
| franz S6  | 0.57 | 0.78 | 0.50 / 0.80 / 0.40 | 0.57 |
| judith S4 | 0.93 | 0.70 | 0.97 / 0.97 / 0.88 | 0.93 |
| judith S6 | 0.77 | 0.68 | 0.80 / 0.64 / 0.83 | 0.77 |
| peter S4  | 0.95 | 0.80 | 0.97 / 0.93 / 0.96 | 0.95 |
| peter S6  | 0.83 | 0.72 | 0.83 / 0.80 / 0.87 | 0.83 |

## Verdict: GO
- **No continue-collapse** (v1's failure): abundant honest `leave` examples, both classes present.
- **State-sensitivity confirmed** (franz S4 fresh→worn 0.35→0.63); disposition dominates for
  judith/peter (realistic — they bail at price walls).
- **Marginals run high** for judith/peter — expected (raw per-step rate over a leave-inclusive
  state sample ≠ rollout marginal). Closed by: (a) mood weights → 0.5/0.3/0.2 (more `fresh` →
  more `continue` coverage + lower rates), (b) Stage-2 calibration on the leave decision.

## Decisions
- Keep targets out of the prompt; shape marginals via sampler + calibration.
- Bumped `fresh` mass to 0.5 for `continue` coverage on leave-heavy personas.
- Next: full build (T3) at bounded volume, then train (T4) + coherent-rollout eval (T5) + calibrate (T6).

---

# Prompt trim — what is redundant? (A/B determined, not guessed)

Measured component sizes (char/4), peter S4 (~6.7k tok total): persona.md ~2770 · cognitive_model
952 (state_update ~150 · price_reaction ~200 · commitment ~300 · coverage ~180 · decision ~100)
· rules 712 · action_space 364 · tariff_coverage_brief 308 · params 455.

A/B'd each candidate cut by re-probing (M=20,K=5,seed=7) and comparing per-cell leave-rates to
the FULL prompt. Binomial noise at n=100 ≈ ±0.10.

| trim attempt | result |
|---|---|
| cut ALL cognitive_model + compress rules (−20%) | ❌ S6 broke: franz −0.31, judith −0.23 (lost the price-jump driver) |
| keep only price+commitment+decision (cut coverage) | ❌ peter S4 −0.24 (lost coverage-confusion leaves) |
| **drop only `state_update_rules` + compress rules (−~10%)** | ✅ all cells within ±0.08 of FULL |

**Conclusion — load-bearing vs redundant:**
- **Redundant (safe to cut, ~10%):** `cognitive_model.state_update_rules` (the dials already encode
  state drops) + the verbose feeling-taxonomy prose in `rules` (compressed to terse one-liners).
- **Load-bearing (do NOT cut — A/B-proven):** `persona.md`, `params_block` (dials),
  `price_reaction_rule`, **`commitment_rule`** (S6 price-jump → the franz/judith S6 leave driver),
  **`coverage_reaction_rule`** (peter S4 coverage-confusion driver), `decision_rule`,
  `action_space`, price blocks.

Net: only ~10% (~550 tok) is safely removable; the prompt is mostly signal. Trim shipped as the
opt-in `lean=True` flag (default off → v1/datagen unchanged); `datagen_v2` uses it.

---

# Exact v2 dataset statistics (research/v2_stats.py)

2400 rows, decision balance continue 1658 / leave 742 (**leave share 0.309**). Per-step
leave-rate vs anchors (n=160/cell, Wilson 95% CI):

| step | judith (t) | franz (t) | peter (t) |
|---|---|---|---|
| S3 | 0.025 (0.05) | 0.00 (0.04) | 0.206 (0.25) |
| S4 | 0.944 (0.70) Δ.24 | 0.419 (0.55) Δ.13 | 0.844 (0.80) |
| S6 | 0.700 (0.68) | 0.681 (0.78) | 0.819 (0.72) |

**ε = 0.0828 (< 0.12 gate)**; implied weighted conversion 0.102 (anchor 0.083). Strong; only
judith S4 is a real outlier (calibration target). These are per-step rates over the sampled
state mix, not a coherent rollout.

# Single-prompt vs stepwise generation are NOT equivalent (research/compare_gen.py)

N=40/persona, OpenRouter teacher, both methods, validated vs anchors:

| | single whole-session prompt | stepwise rollout |
|---|---|---|
| overall ε | **0.314 (fails)** | **0.112 (≈gate)** |
| S4 churn (j/f/p) | **0.00 / 0.00 / 0.00** | 0.90 / 0.42 / 0.89 |
| S6 churn | 0.82–0.90 | 0.43–0.75 |

**The single whole-session prompt produces 0% S4 churn for every persona** — it pushes everyone
past the first price wall and concentrates all abandonment at S6. The teacher, when writing the
entire journey in one call, plans a coherent arc and biases toward *complete-then-decide*; it
cannot authentically bail mid-funnel. Deciding **one step at a time, blind to the future**, it
abandons at the price wall like a real user.

**Conclusion:** per-step (stepwise) generation is **necessary**, not just convenient — it's the
only way to reproduce the documented mid-funnel (S4) drop-off. This justifies the v2 per-step
distillation architecture end-to-end.

---

# Provenance check (course-correction): we were calibrating to OUR numbers, not UNIQA's

**UNIQA ground truth** (`uniqa-funnel-doc_en.md`, "source: UNIQA funnel analysis"): AGGREGATE
drop-off **S4=66%, S5=24%, S6=78%**, mix **30/50/20**, conversion ~5.6%; plus qualitative
segment descriptions. **What we invented:** the per-persona `ABANDON_PROBS` splits (funnel.py
comment proves it: `0.30×0.70+0.50×0.55+0.20×0.80≈66%`) and ALL the dials/disposition weights.

Consequence: the "judith S4 0.94 outlier" was vs our INVENTED 0.70, not UNIQA. Tuning judith's
dials to chase 0.70 actually moved the REAL aggregate **away** (66.1%→68.4%). Reverted.

**Survival-weighted population aggregate of the original v2 dataset vs UNIQA:**

| step | v2 aggregate | UNIQA | Δ |
|---|---|---|---|
| S4 | 0.651 | 0.66 | **0.009** ✅ |
| S6 | 0.692 | 0.78 | 0.088 (real gap — S6 under-churns ~9pp) |
| conversion (in-scope) | 0.102 | ~0.075 | follows S6 |

**Corrected eval policy:** PRIMARY gate = population aggregate vs UNIQA (66/78 + conversion);
per-persona ε is SECONDARY/diagnostic (our decomposition — judith>franz at S4 is consistent with
UNIQA's advisor-affine segment, which is the qualitative truth). The legitimate calibration
target is **S6 (+9pp)**, NOT judith S4.
