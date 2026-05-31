# Coach hypotheses — grounded in UNIQA's churn model + persona segments

Sources: UNIQA funnel analysis slide (`_local/Analyse KV ambulant…pptx`) + segment booklet
(`_local/Segment Prototypen…pptx`). This drives where/how the Coach intervenes.

## The official churn model (ground truth — conditional)
Funnel sample on the 4 critical steps: **1000 → 333 → 253 → 56**
- **S4** first price display: 1000→333 = **66.7%** drop
- **S5** add-on selection: 333→253 = **24.0%** drop
- **S6** final price (after personal+health): 253→56 = **77.9%** drop
- conversion = 56/1000 = **5.6%** (each % is conditional on reaching that step)

Traffic: ~80% from search; 70%+ between 9–20h. ROPO side-effect (look online, buy via advisor)
is real and unmeasurable.

## Step roles
| Steps | Role | Coach |
|---|---|---|
| **S1 coverage · S2 insured** | **persona DETECTION** | observe only (which card, dwell, hover) → infer persona; ~no churn |
| **S3 personal info** | intervention | big-form scare → pre-emptive explainer |
| **S4 first price** | intervention | price reframe / package nuance / Premium-online clarifier |
| **S5 add-on** | intervention | "skip is fine" reassurance / value framing (don't let the upsell+cost bump scare) |
| **S6 final price + big form** | intervention | explain price jump, form rationale, graceful options |

## Persona pain-points → coach moves (from the segment booklet)
- **Judith (Rising Hybrid, 30%)** — pains: too-complex/intransparent products, *too many steps*,
  weak individualization; values price↔performance, advisor trust. → S4 `package_nuance` +
  `upgrade_path` ("start now, upgrade later"); S6 graceful `advisor_handoff` (she's advisor-affine
  — high S4/S6 online drop is *expected*, recover via callback not force-online).
- **Franz (Online Affine, 50%)** — pains: complex offers, intransparent prices, **Medienbrüche
  (online→offline switches)**. → NEVER hand to a human (Medienbruch is his pain); S4
  `upgrade_explain` (Optimal is fully online) + `pricing_explain`; S6 `health_explain` for the jump.
- **Peter (Service Affine, 20%)** — pains: complexity, advisor-skeptic *but* needs guidance,
  tight budget, doesn't want to self-manage. → early `quick_quiz`/guidance at S3; `whatsapp_bot`/
  `callback_offer` before the price wall; `form_explainer` on the big forms.

## Two new mechanisms added this pass
1. **Hesitation flag** — the persona now emits `hesitation` (0..1: how unmotivated-to-continue it
   is right now). This is the behavioural signal the Coach detects *before* the user acts.
2. **Big-form pre-emptive nudge** — UNIQA users are scared off by long forms (S3, S6). New
   `form_explainer` intervention fires the moment a long form appears (high `ux_complexity` +
   high hesitation) and explains WHY the form is needed / how short it is, before they bail.
   Wired in `ReactiveCoach` (S3/S6 + hesitation≥0.5 or feeling=too_much_effort → `form_explainer`).

## Eval policy (corrected)
PRIMARY gate = survival-weighted **population aggregate vs UNIQA** (S4 66.7% · S5 24% · S6 77.9% ·
conversion 5.6%), conditional. Per-persona `ABANDON_PROBS` are OUR decomposition → SECONDARY
diagnostic only (their *shape* must stay consistent with the segment descriptions, e.g. judith
> franz at S4). S5 is back in scope (intervention surface + 24% drop).
