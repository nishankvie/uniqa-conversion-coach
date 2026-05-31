# Coach intervention design — per screen × frontend pattern (demo brainstorming)

Exhaustive map of *what* the Coach can do, on *which screen*, triggered by *which signal*, for
*which persona*, rendered as *which frontend pattern*. Grounded in `personas.json`
`online_funnel_behavior_hypotheses` (definitive per-persona signals + best interventions),
`SIGNALS_AND_DETECTION.md`, and the funnel doc. This is a brainstorming doc for the demo FE —
not a locked design system.

Screens (intervention areas): **S3** personal info form · **S4** first price / tariff table ·
**S5** add-on selection · **S6** personal+health form → **final price reveal** (the funnel doc's
"Step 7" moment lives inside our S6). S1–S2 = detection only.

---

## 0. The detection signal that drives everything: speed of early steps
| Early-step behaviour | Persona signal | Coach stance |
|---|---|---|
| **FAST progression S1→S3** (mechanical, low dwell) | **Franz** (Online Affine) — decisive, primary online target, drops at FINAL price | DON'T interrupt early; **save budget for S6**; never advisor |
| **SLOW + overwhelm early** (long dwell, multiple back-nav, hesitant/incorrect fields) | **Peter** (Service Affine) — overwhelmed, may bail before S4 | **early warm handoff** (callback/WhatsApp), simplify form |
| **Deliberate research** (hover, tooltip, external-tab compare) | **Judith** (Rising Hybrid) — researches then wants advisor | term help + comparison; offer advisor (counts as conversion) |
Combine with **traffic source** (§0 of SIGNALS) + device for the prior.

---

## 1. Definitive per-persona signals → best interventions (from personas.json)
| Persona | Primary drop | Behavioural signals | Best interventions (UNIQA-stated) |
|---|---|---|---|
| **Judith** | initial price (S4) | long dwell on price table · repeated tariff hover/click w/o select · back-nav after "advisory required" · opens external compare tab | market comparison ("Optimal < 80% of comparable") · price reframe (€68 ≈ €2.20/day) · term-on-hover · **smooth advisor handoff (counts as conversion)** |
| **Franz** | final price (S6) | **fast early steps** · comparison-tab opens (session gaps) · sticks on final price when > expectation · clicks cancel if price-perf poor | value justification when final diverges · comparable cheaper tariff w/ feature compare · **save-progress (no advisor)** · AVOID advisor |
| **Peter** | early / before tariff | early overwhelm (long dwell low progress) · multiple back-nav · hesitant/incorrect fields · "too much, I'll call" | detect overwhelm early · **proactive warm service handoff** · simplify form drastically · "not finishing online is OK" + phone callback · conversion = qualified service contact |

---

## 2. Frontend pattern library (HOW an intervention renders)
The same intent can be drawn many ways. Demo-ready render patterns:

| Pattern | Form | Best for | Intrusiveness |
|---|---|---|---|
| **Inline banner** | strip above/below an element | contextual explain, reassurance | low |
| **Anchored popover / tooltip** | bubble pinned to a term/field | term explain, field hint | very low |
| **Inline expand** | accordion reveal in place | package nuance, "what differs" | low |
| **Coachmark / spotlight** | dim + highlight one element | guide the eye, preselect hint | medium |
| **Side drawer** | right panel, persistent helper | comparison table, running assistant | medium |
| **Bottom sheet** | slides up (mobile-first → Peter) | callback/WhatsApp, simplify offer | medium |
| **Toast / snackbar** | transient corner | micro-reassurance, "saved" | very low |
| **Sticky action bar** | pinned bottom CTA | save-progress, callback, price chip | low |
| **Price-reframe chip** | €/day badge beside the price | price reframe at S4/S6 | very low |
| **Exit-intent overlay** | modal on `exit_intent` only | last-chance (save / advisor / reframe) | high (rare) |
| **Chat bubble / avatar** | conversational corner widget | Peter guidance, open-question answers | low–medium |
| **Progress ribbon** | "2 quick fields left · ~40s" | big-form pre-emptive (form_explainer) | very low |

Demo rule: **intrusiveness scales with churn-imminence** — passive chips/banners for early hints,
exit-intent overlay only when `exit_intent` fires. Respect the ≤3 annoyance budget.

---

## 3. Per-screen intervention matrix (trigger → intervention → FE pattern → persona)

### S3 — personal info form (DOB + SV number) — *trust barrier, before any price*
| Trigger signal | Intervention | FE pattern | Persona |
|---|---|---|---|
| landing `hesitation`≥.5 / high time-to-first-action on a big form | **form_explainer** — "Why we ask + ~3 fields, ~40s, needed to compute YOUR price" | progress ribbon / inline banner | all (esp. Peter) |
| `field_reedit`/`validation_error` on SV number | **form_helper** — "Your SV-Nr is top-right on your e-card" | anchored popover on the field | all |
| early overwhelm (slow, multi back-nav, mobile) | **callback_offer / whatsapp_bot** — warm, "prefer to do this by phone?" | bottom sheet / chat bubble | **Peter** |
| `copy`/`text_select` of a term | **term explain** | anchored popover | Judith/Peter |

### S4 — first price / tariff table — *66% drop; Judith's wall*
| Trigger | Intervention | FE pattern | Persona |
|---|---|---|---|
| dwell-after-`price_reveal` + `cancel_hover` (price shock) | **price_reframe** (€/day) | price-reframe chip beside number | Judith/Franz |
| `tab_away`→`compare_return` (short) / external_nav | **market_comparison** ("Optimal < 80% of comparable") | side drawer / inline compare | **Judith/Franz** |
| repeated tariff hover/click w/o select + tooltip opens | **package_nuance** ("Start vs Optimal — 3 real differences") | inline expand | all |
| `premium_click` then `nav_back` (advisory-only dead end) | **upgrade_explain** ("Optimal is fully online") | inline banner on the Premium column | Franz/Judith |
| `copy`/`text_select` of jargon (Heilbehelfe, refractive) | **coverage_explain / coverage_checker** | anchored popover | all |
| back-nav after "advisory required" + advisor-affine prior | **advisor_handoff** (smooth, counts as conversion) | bottom sheet CTA | **Judith** |

### S5 — add-on selection — *24% drop; upsell + cost bump*
| Trigger | Intervention | FE pattern | Persona |
|---|---|---|---|
| dwell + running-price climbs + `hesitation` | **"skip is fine"** reassurance — add-ons are optional, you can add later | inline banner / toast | all (esp. Franz, price-perf) |
| `slow_mouse` over many toggles (overload) | **quick_quiz / simplify** — "answer 2 questions, we'll suggest" | bottom sheet | Peter |
| value doubt on an add-on | **value framing** — what each add-on covers in real terms | inline expand per toggle | Judith |

### S6 — personal+health form → FINAL PRICE reveal — *78% drop; Franz's wall*
| Trigger | Intervention | FE pattern | Persona |
|---|---|---|---|
| big-form `hesitation` before filling | **form_explainer** — "last step · ~1 min · then your binding price" | progress ribbon | all (esp. Peter) |
| **final price > provisional** (health loading) + stick/`cancel_hover` | **value_justification / health_explain** — why it changed, still online | inline banner under the price + price chip | **Franz** |
| price-perf doubt at final | **comparable cheaper tariff** w/ feature compare | side drawer | Franz |
| clearly not finishing now | **save_progress** (email resume, NO advisor) | sticky bar | **Franz** |
| `exit_intent` on the final price | **last-chance overlay** — reframe + save + (Judith) advisor / (Peter) callback | exit-intent overlay | persona-routed |
| height/weight friction (`recalls_measurements`=unsure) | **form_helper** — "estimate is fine, you can update later" | anchored popover | all |

---

## 4. Early-detection → per-persona tailoring (the "do not unify" rule)
By S3/S4 the Coach has committed a `persona_belief`; the SAME trigger routes differently:
- **Franz**: never advisor/callback; price chips, comparison, value-justification, save-progress.
- **Judith**: term help + comparison, then **graceful advisor handoff = conversion**.
- **Peter**: **early** warm handoff (callback/WhatsApp bottom sheet), drastic form simplify,
  "calling is fine"; online purchase is NOT his target (qualified service contact is).

---

## 5. Demo frontend notes
- Build on the React funnel twin (`webapp/src/twin/`) + coach overlay (`webapp/src/coach/`): the
  overlay renders these patterns from the coach's JSON decision (effector + intent + payload).
- Show the **persona belief + live signal trace** in a side HUD so judges SEE detection happening.
- Scripted autoplay per persona: Franz fast→S6 price-justify+save; Peter slow→early callback;
  Judith research→S4 comparison→advisor handoff. Each shows a DIFFERENT pattern firing.
- Intrusiveness ladder: chip/banner (early) → drawer/bottom-sheet (mid) → exit-intent overlay
  (only on `exit_intent`). Never exceed 3 widgets/session.
