# Coach hypotheses registry (H1…)

Living list of behavioural hypotheses the Coach reasons with. Each = **signal → reading →
move**. Referenced by `src/uniqa/coach_prompt.py` (the prompt tells the model to treat these as
*priors to test*, not rules). Grounded in `personas.json`, the funnel doc, and team ideas.
Add freely; keep numbered (the prompt cites H#).

## Persona detection
- **H1 — fast early steps → Franz.** Fast/mechanical S1→S3 = Online Affine: decisive, primary
  online target, drops at the FINAL price (not early). Move: DON'T interrupt early; save budget for S6.
- **H2 — slow + overwhelm early → Peter.** Long dwell, multi back-nav, hesitant/incorrect fields,
  mobile. Move: early warm service handoff; simplify.
- **H3 — deliberate research (hover/tooltip/compare-tab) → Judith.** Move: term help + comparison,
  then graceful advisor handoff (counts as conversion for her).
- **H4 — traffic source is a prior.** paid/comparison search → Franz/Judith (motivated); display/
  social → Peter (passive, wasn't looking); direct/portal → returning Judith.

## Conversion-likelihood / momentum
- **H5 — fast-fill → jump straight to pricing.** If the user breezes through forms, offer to skip
  optional detail and jump to the price (`jump_to_pricing`). Saves effort for the decisive.
- **H6 — confident tariff pick → high P(convert).** A decisive tariff `select` (low dwell, no
  back-nav) after seeing price ⇒ very likely to convert ⇒ DO NOT over-intervene; just smooth S6.
- **H7 — momentum is signal.** Steady advance = leave them alone; stall/regress = consider acting.

## Pains → moves
- **H8 — price-table shock.** Freeze / long dwell after `price_reveal` / `cancel_hover` / `exit_intent`
  = shocked, wants OUT (not to study). Move (persona-routed): ask "need help?", strip redundant
  tariffs + arrow what's purchasable online, OR instantly show comparison / alternative pricing.
- **H9 — leave-to-compare.** `tab_away/external_nav` then fast `compare_return` = compared externally
  → `comparison_table` ("we compared for you"). Long away = forgot → gentle re-orient.
- **H10 — term confusion.** `text_select`/`copy` of jargon, tooltip opens, `scroll_up` re-read →
  `coverage_explain`/`coverage_checker` OR `faq_cards` near the focused topic.
- **H11 — forgot a field (e.g. SV number).** Stall on a field → `field_defer` ("skip, add later" +
  flag if it affects price).
- **H12 — big-form scare.** High `hesitation`/time-to-first-action on S3/S6 → `form_explainer`
  (pre-emptive), `form_simplify` (split steps), or `bucket_input` (ranges not exact numbers).
- **H13 — premium dead end.** `premium_click` then `nav_back` → "Optimal is fully online" clarifier.

## Price transparency (avoid surprise)
- **H14 — pre-indicate price-affecting fields.** BEFORE the user fills a field that moves the
  binding price (health/weight), show its impact (`price_preview`) so the final price is never a
  surprise. **H14b** — if it IS a surprise (final > estimate), always explain WHY (`value_justification`/`health_explain`).
- **H15 — bucket instead of exact.** Tell the user how a field affects price by CATEGORY (e.g.
  `<170cm` vs `≥170cm`) so they pick a range, lowering effort while staying price-accurate (`bucket_input`).

## Channel / capture (persona + device)
- **H16 — Peter wants a human.** Early → `callback_offer` / `whatsapp_bot` / `voice_questions`
  (leave a number for a callback, or record/type questions). Online purchase is NOT his target.
- **H16b — Peter's PERFECT move = `contact_handoff`.** For the form-averse, service-affine user the
  ideal intervention is “Don't fill any of this — just leave your email/phone and we'll take it from
  here.” Skips ALL remaining forms/questions; a person finishes with them. This IS Peter's
  conversion (qualified service contact), so fire it the moment form-overwhelm is confident.
- **H17 — mobile = capture the lead.** On mobile, the natural ask is **phone capture** (callback /
  retarget) via bottom sheet — lower-friction than finishing a long form on a small screen.
- **H18 — ID Austria autofill.** Offer `id_austria_login` to auto-fill identity/SV details (eID) —
  removes the biggest form friction for those willing.
- **H19 — remember partial forms by default.** Always persist partially-filled fields; offer
  `save_progress`/resume so a bounce isn't a total loss (and enables retarget).

## S5 add-on
- **H20 — suggest skipping the add-on step.** At S5, nudge "skip to finish your online purchase"
  (`addon_skip_ok`) — the upsell+cost-bump is a 24% drop; skipping protects the conversion.

## Feedback micro-interactions
- **H21 — tooltip hover = it helped.** If the user hovers a shown tooltip/widget, surface a **Like**
  button (nice animation) to confirm it was helpful (positive signal). The **close** button is a
  negative signal. `widget_like`/`widget_dislike`/`widget_dismiss` feed back into the policy
  (dismiss → back off; dislike → change tactic; like/cta → may follow up once).

> The Coach treats these as priors to TEST against the live trace + the persona simulator's
> assessment — confirmed/refuted hypotheses recalibrate both the coach policy and the persona model.
