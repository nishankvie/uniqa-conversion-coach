# The Coach model — detection + decision workflow

The Coach watches the event trace and decides whether to show ONE helpful widget, and which.
The runnable prompt is `src/uniqa/coach_prompt.py` (`build_coach_prompt`). This doc is the *why*.
Principles, not rigid rules — the model reasons.

## Conversion target is PERSONA-DEPENDENT (note this!)
Online purchase is **not** always the goal. Per UNIQA's per-segment definition the Coach
optimizes the RIGHT outcome:
| Persona | Conversion target |
|---|---|
| **Judith** (Rising Hybrid) | online purchase **OR** smooth advisor handoff — **both count** (don't force online for the ~81% who won't) |
| **Franz** (Online Affine) | **online purchase only** — advisor/offline handoff = FAILURE (Medienbruch is his pain) |
| **Peter** (Service Affine) | **qualified service contact** (callback booked / phone / WhatsApp) — online purchase is NOT the target |
So the same "bounce risk" routes to different *wins* per detected persona.

## The 5-step workflow (run on EVERY event increment)
1. **Persona belief** — a confidence distribution over {judith, franz, peter}, updated each event
   from: traffic_source (paid/comparison→Franz/Judith; display/social→Peter; direct→Judith),
   device/time, **speed of early steps** (fast S1→S3 → Franz; slow+overwhelm → Peter; deliberate
   research → Judith), and accumulating micro-signals. Sharpen over time; commit ~by S3/S4. As
   confidence rises, the intervention option set **narrows** to that persona's playbook.
2. **Pains & frustration** — infer current pains from micro-signals (price-shock freeze/exit-intent,
   form overwhelm, term confusion via text_select/copy, compare-intent via tab-away, forgot-a-field)
   + a frustration level 0..1, with a confidence per pain.
3. **Dropout likelihood → intervention temperature** — estimate P(bounce this step). Willingness to
   spend a widget = a **temperature** that rises with `dropout_likelihood × belief_confidence`. Low
   temp → WAIT; high temp + a clearly matching widget → act. `exit_intent` spikes temp (last chance).
   Always respect the ≤3 widgets/session annoyance budget.
4. **Widget match** (separate concern, reasoning-based) — pick the intervention whose *purpose*
   addresses the detected pain AND serves THIS persona's conversion target, on THIS step, for THIS
   device. Least-intrusive frontend pattern that works; escalate intrusiveness only with temperature.
5. **Feedback** — adapt to prior-widget feedback: `widget_dismiss` → back off / don't repeat / lower
   temp; `widget_dislike` → change tactic; `widget_cta`/`widget_like` → you read them right, may
   follow up once. (Like/dislike buttons render on every widget.)

## Predicting pains → concrete moves (examples)
- **Forgot SV number** (stall on the field) → `field_defer`: "skip it, add later" (note price impact if any).
- **Price-table shock** (freeze / mouse-to-leave / doesn't want to study) → ask "need help?" OR
  `package_nuance` overlay that strips redundant tariffs and arrows what's purchasable online, OR
  immediately surface `comparison_table` / alternative pricing. Routed by persona.
- **S5 add-on** → suggest **skipping** to proceed straight to online purchase (`addon_skip_ok`).
- **Big form** → `form_explainer` (why + how short) pre-emptively; `form_simplify` (split into steps)
  or `bucket_input` (pick `<170cm` vs `≥170cm` with price impact shown) instead of exact numbers.

## Form-tool widgets (front-end functionality)
- `form_simplify` — show only required fields + split into small steps (progressive disclosure).
- `field_defer` — defer a field (SV/weight/health) to finish now; **transparently flag if it moves
  the binding price** (honest defer).
- `bucket_input` — replace an exact field with a few **categories** and show the **price impact per
  bucket** (e.g. height `<170 / ≥170`), so the user picks a range instead of typing a precise value.

## Device-aware rendering (design BOTH)
| | Desktop | Mobile |
|---|---|---|
| Pattern | anchored popover / side drawer / inline | **bottom sheet** / full-width card / sticky bottom bar |
| Anchoring | hover/cursor-anchored, coachmarks | thumb-reachable, no hover; tap targets ≥44px |
| Motion | subtle slide/fade | minimal motion, no layout shift; respect reduced-motion |
| Exit-intent | cursor-to-edge overlay | scroll-up + app-switch / back-gesture heuristic |
| Forms | inline expand | `form_simplify`/`bucket_input` matter MORE (small screen) |
Mobile leans Peter (65% mobile) → favour bottom-sheet callback/WhatsApp + simplify.

## Output (strict JSON)
`persona_belief`, `belief_confidence`, `detected_pains`, `frustration`, `dropout_likelihood`,
`intervention_temperature`, `decide` (wait|intervene), and `intervention` {id, conversion_target,
fe_pattern, device_variant, copy, reasoning, hypotheses} or null. WAIT is the default.

## How it trains / improves
This is the policy the autoresearch loop optimizes against the persona simulator (Mode B): the
persona reacts to and **assesses** each widget (helpful/engaging vs distracting), and that signal
+ the realized outcome teach the coach which widget works for which persona/pain/device.
