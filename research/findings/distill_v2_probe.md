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
