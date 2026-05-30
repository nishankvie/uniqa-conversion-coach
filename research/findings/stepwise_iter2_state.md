# Session-gen validation — step-state (teacher=openrouter:openai/gpt-4o-mini, N=20/persona)
_generated 20260530_192147_

**VERDICT: ❌ FAIL**  (ε=0.2688 ≤0.12: False · conv: False · each-converts: True)

Overall conversion: observed **0.445** vs target **0.083** (weighted {'judith': 0.3, 'franz': 0.5, 'peter': 0.2}).

| persona | n | conv | (target) | S3 bnc/(t) | S4 bnc/(t) | S6 bnc/(t) | reasons |
|---|---|---|---|---|---|---|---|
| judith | 20 | 0.15 (3) | 0.09 | 0.00/0.05 | 0.79/0.70 | 0.25/0.68 | distracted:Ich werde darüber nachdenken und später zurückkommen, um das mit einem Berater zu besprechen.×1, distracted:I need to think it over. The optimal plan looks good, but I’m not ready to commit online without more info about the coverage.×1, distracted:I'll think about it — I need more time to consider my options and maybe look into details later.×1 |
| franz | 20 | 0.70 (14) | 0.10 | 0.00/0.04 | 0.10/0.55 | 0.22/0.78 | dissatisfied:Final price changed from the provisional price. Didn't expect the increase; feels misleading.×1, dissatisfied:The price change wasn't clear and I don’t want to deal with advisory requirements for better options.×1, dissatisfied:Price increased unexpectedly. Not worth my time.×1 |
| peter | 20 | 0.25 (5) | 0.04 | 0.05/0.25 | 0.63/0.80 | 0.29/0.72 | dissatisfied:Ich fühle mich überfordert mit den vielen Tarifen und weiß nicht, was ich wählen soll.×1, dissatisfied:Ich bin mir unsicher wegen der Gesundheitsfragen, und es sind einfach zu viele Felder. Ich rufe lieber an, um das zu klären.×1, dissatisfied:I feel overwhelmed and would rather talk to someone who can help me choose.×1 |

_bnc/(t) = observed conditional bounce / ABANDON_PROBS target. Targets are eval-only; never in the prompt._