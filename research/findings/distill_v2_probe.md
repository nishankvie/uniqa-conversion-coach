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
