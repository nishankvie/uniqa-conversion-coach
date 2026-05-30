# Session-gen validation — dataset (teacher=openrouter:openai/gpt-4o-mini, N=100/persona)
_generated 20260530_221625_

**VERDICT: ❌ FAIL**  (ε=0.1042 ≤0.12: True · conv: False · each-converts: True)

Overall conversion: observed **0.179** vs target **0.083** (weighted {'judith': 0.3, 'franz': 0.5, 'peter': 0.2}).

| persona | n | conv | (target) | S3 bnc/(t) | S4 bnc/(t) | S6 bnc/(t) | reasons |
|---|---|---|---|---|---|---|---|
| judith | 100 | 0.02 (2) | 0.09 | 0.09/0.05 | 0.88/0.70 | 0.82/0.68 | dissatisfied:I'll think about it×2, goal_achieved:I checked everything, but I need to consult someone before finalizing, especially since this is such an important commitment.×1, dissatisfied:I need to think more about this and get reassurance from an advisor before committing.×1 |
| franz | 100 | 0.33 (33) | 0.10 | 0.01/0.04 | 0.34/0.55 | 0.49/0.78 | ?×2, dissatisfied:The final price is higher than expected, and it wasn't what I came for. Too many personal questions for a higher number.×1, dissatisfied:I can't get past the 'advisory required' on some plans. I thought I could finish online but this feels restrictive.×1 |
| peter | 100 | 0.04 (4) | 0.04 | 0.21/0.25 | 0.81/0.80 | 0.71/0.72 | ?×2, cant_grasp:Ich möchte nicht einfach wählen müssen, ich brauche erstmal jemanden, der mir hilft.×1, too_much_effort:I need to think this through and get some advice before making a decision. The price is higher than I hoped, and I want to make sure it's right for me.×1 |

_bnc/(t) = observed conditional bounce / ABANDON_PROBS target. Targets are eval-only; never in the prompt._