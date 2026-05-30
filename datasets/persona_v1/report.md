# Session-gen validation — population {'judith': 150, 'franz': 250, 'peter': 100} (teacher=openrouter:openai/gpt-4o-mini, N=500/persona)
_generated 20260530_231840_

**VERDICT: ❌ FAIL**  (ε=0.0998 ≤0.12: True · conv: False · each-converts: True)

Overall conversion: observed **0.142** vs target **0.083** (weighted {'judith': 0.3, 'franz': 0.5, 'peter': 0.2}).

| persona | n | conv | (target) | S3 bnc/(t) | S4 bnc/(t) | S6 bnc/(t) | reasons |
|---|---|---|---|---|---|---|---|
| judith | 150 | 0.04 (6) | 0.09 | 0.01/0.05 | 0.91/0.70 | 0.57/0.68 | too_much_effort:I have filled out all these fields and still need reassurance before committing.×1, unanswered_question:I can't tell what really differs between Start and Optimal, and I need more clarity before committing.×1, unanswered_question:I need to confirm whether my doctor is in-network and I don’t want to commit without advice.×1 |
| franz | 250 | 0.25 (62) | 0.10 | 0.00/0.04 | 0.39/0.55 | 0.59/0.78 | dissatisfied:The final price is higher than expected, and it's not clear why.×2, dissatisfied:Final price is higher than expected and not explained. Too much effort for unclear value.×2, unanswered_question:I can't tell what really differs between Start and Optimal, and I’m looking for dental coverage that’s not clear here.×1 |
| peter | 100 | 0.03 (3) | 0.04 | 0.30/0.25 | 0.77/0.80 | 0.80/0.72 | ?×2, too_much_effort:Ich verstehe nicht genau, welche Tarifoption ich wählen soll und ob die gewünschte Behandlung abgedeckt ist.×1, cant_grasp:Ich fühle mich überfordert von den vielen Optionen und brauche jemanden, der mir klar sagt, was am besten für mich ist.×1 |

_bnc/(t) = observed conditional bounce / ABANDON_PROBS target. Targets are eval-only; never in the prompt._