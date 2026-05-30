# Session-gen validation — step-state (teacher=openrouter:openai/gpt-4o-mini, N=20/persona)
_generated 20260530_193219_

**VERDICT: ❌ FAIL**  (ε=0.1314 ≤0.12: False · conv: False · each-converts: False)

Overall conversion: observed **0.050** vs target **0.083** (weighted {'judith': 0.3, 'franz': 0.5, 'peter': 0.2}).

| persona | n | conv | (target) | S3 bnc/(t) | S4 bnc/(t) | S6 bnc/(t) | reasons |
|---|---|---|---|---|---|---|---|
| judith | 20 | 0.00 (0) | 0.09 | 0.05/0.05 | 1.00/0.70 | –/0.68 | dissatisfied:I'm feeling uncertain about selecting a tariff without expert guidance, especially since Opt. Plus isn't available online. I’ll think about it and maybe call later.×1, Ich denke, ich muss darüber nachdenken, ob ich wirklich für andere Personen eine Versicherung abschließen möchte.×1, dissatisfied:I'll think about it, this isn't what I expected.×1 |
| franz | 20 | 0.10 (2) | 0.10 | 0.00/0.04 | 0.55/0.55 | 0.78/0.78 | dissatisfied:final price is higher than expected and I can't complete online anyway.×1, dissatisfied:The Optimal tariff is more expensive than I expected without clear justification, and I’m not going to deal with an advisory-only option.×1, dissatisfied:The final price jumped to €72, not what I expected. I feel misled.×1 |
| peter | 20 | 0.00 (0) | 0.04 | 0.62/0.25 | 1.00/0.80 | –/0.72 | too_much_effort:I feel overwhelmed with these fields and unsure about the SV-Nummer. I'd rather just call someone to help me with this.×1, cant_grasp:I need to talk to someone to make sense of this, I can't decide between the options by myself.×1, too_much_effort:Ich fühle mich überfordert und weiß nicht, was ich auswählen soll.×1 |

_bnc/(t) = observed conditional bounce / ABANDON_PROBS target. Targets are eval-only; never in the prompt._