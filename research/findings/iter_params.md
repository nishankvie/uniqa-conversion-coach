# Session-gen validation — params (teacher=openrouter:openai/gpt-4o-mini, N=30/persona)
_generated 20260530_190649_

**VERDICT: ❌ FAIL**  (ε=0.3332 ≤0.12: False · conv: False · each-converts: False)

Overall conversion: observed **0.034** vs target **0.083** (weighted {'judith': 0.3, 'franz': 0.5, 'peter': 0.2}).

| persona | n | conv | (target) | S3 bnc/(t) | S4 bnc/(t) | S6 bnc/(t) | reasons |
|---|---|---|---|---|---|---|---|
| judith | 30 | 0.07 (2) | 0.09 | 0.00/0.05 | 0.00/0.70 | 1.04/0.68 | I'll think about it.×7, Final price is higher than hoped.×1, The final price was higher than the estimate.×1 |
| franz | 30 | 0.00 (0) | 0.10 | 0.00/0.04 | 0.00/0.55 | 0.86/0.78 | Final price was higher than expected.×4, Final price higher than expected.×4, ?×2 |
| peter | 30 | 0.07 (2) | 0.04 | 0.00/0.25 | 0.07/0.80 | 0.96/0.72 | price too high×3, final price too high×3, Feels overwhelming, I need to think about it.×1 |

_bnc/(t) = observed conditional bounce / ABANDON_PROBS target. Targets are eval-only; never in the prompt._