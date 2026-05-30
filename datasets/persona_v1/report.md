# Session-gen validation — dataset (teacher=openrouter:openai/gpt-4o-mini, population 30/50/20: judith 150 / franz 250 / peter 100 (N=500))
_generated 20260530_224925_

**VERDICT: ❌ FAIL**  (ε=0.1282 ≤0.12: False · conv: False · each-converts: True)

Overall conversion: observed **0.138** vs target **0.083** (weighted {'judith': 0.3, 'franz': 0.5, 'peter': 0.2}).

| persona | n | conv | (target) | S3 bnc/(t) | S4 bnc/(t) | S6 bnc/(t) | reasons |
|---|---|---|---|---|---|---|---|
| judith | 150 | 0.05 (8) | 0.09 | 0.06/0.05 | 0.91/0.70 | 0.39/0.68 | goal_achieved:I'll think about it.×2, goal_achieved:I feel like I need to talk to someone before making a final decision on the Optimal tariff.×1, unanswered_question:I need to consult someone before making a choice, especially since I can't discern the differences between Start and Optimal.×1 |
| franz | 250 | 0.24 (60) | 0.10 | 0.00/0.04 | 0.41/0.55 | 0.59/0.78 | dissatisfied:Final price is higher than expected and unclear on why it increased.×2, unanswered_question:I'm not sure what the real difference is between the Start and Optimal plans, and dental work isn't covered. I'll check back later.×1, goal_achieved:The optimal price is higher than expected, and I don't have the coverage I need for my doctor.×1 |
| peter | 100 | 0.01 (1) | 0.04 | 0.21/0.25 | 0.86/0.80 | 0.90/0.72 | ?×2, cant_grasp:Ich brauche mehr Klarheit über die Tarife, bevor ich weiter mache. Es gibt keine Empfehlungen und ich fühle mich überfordert.×1, too_much_effort:Ich fühle mich überfordert von den Anforderungen und brauche mehr Klarheit, bevor ich weiter mache.×1 |

_bnc/(t) = observed conditional bounce / ABANDON_PROBS target. Targets are eval-only; never in the prompt._