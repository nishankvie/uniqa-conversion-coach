# Session-gen validation — quant (teacher=openrouter:openai/gpt-4o-mini, N=30/persona)
_generated 20260530_190050_

**VERDICT: ❌ FAIL**  (ε=0.2803 ≤0.12: False · conv: False · each-converts: False)

Overall conversion: observed **0.067** vs target **0.083** (weighted {'judith': 0.3, 'franz': 0.5, 'peter': 0.2}).

| persona | n | conv | (target) | S3 bnc/(t) | S4 bnc/(t) | S6 bnc/(t) | reasons |
|---|---|---|---|---|---|---|---|
| judith | 30 | 0.13 (4) | 0.09 | 0.00/0.05 | 0.00/0.70 | 0.73/0.68 | I'll think about it.×5, Final price was higher than expected.×1, Deciding to think about it, the final price is too high for my expectation.×1 |
| franz | 30 | 0.00 (0) | 0.10 | 0.00/0.04 | 0.00/0.55 | 0.77/0.78 | Final price higher than expected.×3, Final price was higher than expected.×3, Final price is higher than expected.×1 |
| peter | 30 | 0.13 (4) | 0.04 | 0.00/0.25 | 0.03/0.80 | 0.82/0.72 | Der Preis ist mir zu hoch und ich bin unsicher, ob ich die Fragen richtig beantwortet habe.×1, price is higher than I expected, need to think about it×1, Price is higher than I hoped.×1 |

_bnc/(t) = observed conditional bounce / ABANDON_PROBS target. Targets are eval-only; never in the prompt._