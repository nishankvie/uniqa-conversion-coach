# Session-gen validation — step-quant (teacher=openrouter:openai/gpt-4o-mini, N=20/persona)
_generated 20260530_192003_

**VERDICT: ❌ FAIL**  (ε=0.4432 ≤0.12: False · conv: False · each-converts: True)

Overall conversion: observed **0.845** vs target **0.083** (weighted {'judith': 0.3, 'franz': 0.5, 'peter': 0.2}).

| persona | n | conv | (target) | S3 bnc/(t) | S4 bnc/(t) | S6 bnc/(t) | reasons |
|---|---|---|---|---|---|---|---|
| judith | 20 | 0.85 (17) | 0.09 | 0.00/0.05 | 0.10/0.70 | 0.06/0.68 | I'm feeling uncertain about the final price.×1, Ich möchte das Thema weiterdenken, bevor ich mich entscheide.×1, I'll think about it.×1 |
| franz | 20 | 0.90 (18) | 0.10 | 0.00/0.04 | 0.05/0.55 | 0.05/0.78 | I can't continue with these options. I want to finish online without an advisor.×1, The final price isn't what I hoped for, and I didn't like the increase.×1 |
| peter | 20 | 0.70 (14) | 0.04 | 0.00/0.25 | 0.10/0.80 | 0.22/0.72 | I'm not confident about making a choice. I think I'll just call to discuss which tariff is really best for me.×1, Ich bin überfordert mit all den Informationen und brauche eine Erklärung.×1, Ich bin mir unsicher über die Tarife und würde lieber mit jemandem sprechen.×1 |

_bnc/(t) = observed conditional bounce / ABANDON_PROBS target. Targets are eval-only; never in the prompt._