# Session-gen validation — step-base (teacher=openrouter:openai/gpt-4o-mini, N=20/persona)
_generated 20260530_191839_

**VERDICT: ❌ FAIL**  (ε=0.3816 ≤0.12: False · conv: False · each-converts: True)

Overall conversion: observed **0.715** vs target **0.083** (weighted {'judith': 0.3, 'franz': 0.5, 'peter': 0.2}).

| persona | n | conv | (target) | S3 bnc/(t) | S4 bnc/(t) | S6 bnc/(t) | reasons |
|---|---|---|---|---|---|---|---|
| judith | 20 | 0.45 (9) | 0.09 | 0.00/0.05 | 0.35/0.70 | 0.31/0.68 | I'll think about it.×5, Ich werde darüber nachdenken und vielleicht später zurückkommen.×1, I want to see the final price, but I feel a bit unsure if it will be higher than expected.×1 |
| franz | 20 | 0.90 (18) | 0.10 | 0.00/0.04 | 0.00/0.55 | 0.10/0.78 | Final price better not be higher, or I'm out.×1, The final price better not increase beyond €68, or I'm out.×1 |
| peter | 20 | 0.65 (13) | 0.04 | 0.00/0.25 | 0.10/0.80 | 0.28/0.72 | Ich bin überfordert mit dem ganzen Formular und den Gesundheitsfragen.×1, Ich finde es kompliziert und möchte lieber anrufen.×1, Ich fühle mich überfordert und würde lieber mit jemandem sprechen, der mir helfen kann.×1 |

_bnc/(t) = observed conditional bounce / ABANDON_PROBS target. Targets are eval-only; never in the prompt._