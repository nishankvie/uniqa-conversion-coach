# Session-gen validation — step-state (teacher=openrouter:openai/gpt-4o-mini, N=20/persona)
_generated 20260530_193408_

**VERDICT: ❌ FAIL**  (ε=0.1594 ≤0.12: False · conv: False · each-converts: False)

Overall conversion: observed **0.100** vs target **0.083** (weighted {'judith': 0.3, 'franz': 0.5, 'peter': 0.2}).

| persona | n | conv | (target) | S3 bnc/(t) | S4 bnc/(t) | S6 bnc/(t) | reasons |
|---|---|---|---|---|---|---|---|
| judith | 20 | 0.00 (0) | 0.09 | 0.05/0.05 | 0.94/0.70 | 1.00/0.68 | too_much_effort:I'll think about it. I need more time to compare these options and possibly talk to someone before deciding.×1, dissatisfied:I'll think about it. The price is higher than I anticipated, and I prefer to discuss this with an advisor before making a decision.×1, dissatisfied:I’ll think about it; the price is higher than I hoped for and I don’t want to talk to someone yet.×1 |
| franz | 20 | 0.20 (4) | 0.10 | 0.05/0.04 | 0.53/0.55 | 0.56/0.78 | dissatisfied:The Optimal tariff is higher than expected, and I can't finish online because of the advisory requirement on Opt.Plus and Premium.×1, dissatisfied:The Optimal price jumped from what I expected, and I don't want to deal with an advisor. I'll check competitors.×1, ?×1 |
| peter | 20 | 0.00 (0) | 0.04 | 0.50/0.25 | 1.00/0.80 | –/0.72 | too_much_effort:I feel overwhelmed by having to choose the right Sozialversicherung. It's too much effort without clear guidance.×1, too_much_effort:Das fühlt sich zu kompliziert an. Ich rufe lieber an, um das mit jemandem zu besprechen.×1, cant_grasp:Die Tarife sind überwältigend und ich habe keine klare Empfehlung. Ich werde anrufen, um Unterstützung zu bekommen.×1 |

_bnc/(t) = observed conditional bounce / ABANDON_PROBS target. Targets are eval-only; never in the prompt._