# Session-gen validation — base (teacher=openrouter:openai/gpt-4o-mini, N=30/persona)
_generated 20260530_185805_

**VERDICT: ❌ FAIL**  (ε=0.309 ≤0.12: False · conv: False · each-converts: False)

Overall conversion: observed **0.053** vs target **0.083** (weighted {'judith': 0.3, 'franz': 0.5, 'peter': 0.2}).

| persona | n | conv | (target) | S3 bnc/(t) | S4 bnc/(t) | S6 bnc/(t) | reasons |
|---|---|---|---|---|---|---|---|
| judith | 30 | 0.00 (0) | 0.09 | 0.00/0.05 | 0.00/0.70 | 0.90/0.68 | I'll think about it.×4, I'll think about it×2, Final price is too high for what I expected.×1 |
| franz | 30 | 0.00 (0) | 0.10 | 0.00/0.04 | 0.00/0.55 | 0.97/0.78 | Final price was higher than expected.×3, final price was higher than expected×2, price discrepancy×2 |
| peter | 30 | 0.27 (8) | 0.04 | 0.00/0.25 | 0.03/0.80 | 0.70/0.72 | price is higher than expected×1, It's frustrating to have so many steps without a clear recommendation. I need to think more about whether I can afford this.×1, Thinking I might come back later after considering the price.×1 |

_bnc/(t) = observed conditional bounce / ABANDON_PROBS target. Targets are eval-only; never in the prompt._