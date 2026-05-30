# UNIQA Conversion Coach — Widget-Driven UI Design
**Zero One Hackathon | Design + technical scoping | 2026-05-30**

> **Premise**: The Coach never emits raw text. Every Coach turn is a typed JSON payload describing one or more widgets. A renderer interprets the JSON into UI. A persona simulator interprets the same JSON into a behavioral reaction. Same payload, same semantics, two consumers.

---

## TABLE OF CONTENTS
1. [UNIQA Design System Extraction](#1-uniqa-design-system-extraction)
2. [Widget Component Schema (JSON-Render Spec)](#2-widget-component-schema-json-render-spec)
3. [Conversation Mechanics — Atomic Coach Moves](#3-conversation-mechanics--atomic-coach-moves)
4. [Hormozi Framework Application](#4-hormozi-framework-application)
5. [Technical Scope, Degrees of Freedom, Challenges](#5-technical-scope-degrees-of-freedom-challenges)

---

# 1. UNIQA Design System Extraction

## 1.1 Visual identity (inferred from UNIQA's public funnel + brand guidelines)

| Token | Value | Use |
|---|---|---|
| `color.primary` | `#0046A0` (UNIQA blue) | Headings, primary CTA, progress fill |
| `color.primary.dark` | `#002D6A` | Hover/active CTA states |
| `color.accent` | `#E2001A` (UNIQA red) | Urgency, "save" badges, hesitation flag |
| `color.success` | `#1FA971` | Coverage included, confirmations |
| `color.warning` | `#F0A028` | "Advisory required" tags, soft alerts |
| `color.surface` | `#FFFFFF` | Card background |
| `color.surface.alt` | `#F4F6FA` | Page background, muted cards |
| `color.ink` | `#1A1F2C` | Body text |
| `color.ink.muted` | `#5C6479` | Captions, secondary labels |
| `color.border` | `#D6DBE5` | Card borders, dividers |
| `radius.card` | `12px` | All cards/widgets |
| `radius.pill` | `999px` | Badges, tags, progress dots |
| `shadow.card` | `0 2px 8px rgba(0,0,0,0.06)` | Resting cards |
| `shadow.elevated` | `0 8px 24px rgba(0,70,160,0.12)` | Coach-emitted intervention widgets (so they read as "from UNIQA") |

## 1.2 Typography

| Token | Value | Use |
|---|---|---|
| `font.family` | `"UNIQA Sans", "Inter", system-ui, sans-serif` | Whole product |
| `font.display` | 28/34 600 | Hero numbers (€68.14/mo) |
| `font.h1` | 22/28 600 | Card titles |
| `font.h2` | 18/24 600 | Section labels |
| `font.body` | 15/22 400 | Coach text content |
| `font.body.strong` | 15/22 600 | Emphasis in coach text |
| `font.caption` | 13/18 400 | Disclaimers, "estimated", footnotes |
| `font.numeric` | tabular-nums | All price displays |

## 1.3 Tone of voice — Austrian + digital + trust

UNIQA's funnel copy reads as:
- **Sie-form (formal "you")** in German — never duzen (informal). MVP can stay EN but tone parameter must encode formality.
- **Concrete numbers first, reassurance second**: "€38,74/Monat – ab heute versichert."
- **No marketing superlatives** ("revolutionary", "best"). Soft proof instead ("seit 1811", "AAA-rated").
- **Austrian conservatism**: legal disclaimers visible, not hidden behind tooltips. Trust comes from transparency, not from hiding fine print.
- **No emojis in coach voice. No exclamation marks except for urgency widgets (rare).**

## 1.4 Brand attributes (used as tone vector in widget props)

```
trustworthy    : 0.95  → social proof, transparency, conservative claims
clear          : 0.90  → one-idea-per-widget, no walls of text
austrian       : 0.85  → formal address, € prices with comma, Sie-form
digital_forward: 0.80  → calculator-first UX, "instant" framings
warm           : 0.55  → present but restrained; not a consumer app
urgency_default: 0.20  → almost never urgent; reserved for time-sensitive offers only
```

These map directly to widget `tone` props (see §2).

## 1.5 UX patterns UNIQA already uses (component reuse opportunities)

From the 15-step funnel doc, UNIQA's calculator already renders:
- **Stepper / progress bar** (Steps 1–15) → reuse as `ProgressIndicator` widget.
- **Coverage cards** (Step 1: doctor / hospital / both) → maps to a `ChoiceCard` family.
- **Comparison table** (Step 4: Start / Optimal / Opt. Plus / Premium) → maps to `PriceCard` array.
- **"Advisory required" overlay** on Opt. Plus / Premium → reuse styling for `AdvisorHandoff` widget.
- **Inline error / validation** (Step 3 forms) → reuse for `ObjectionPreempt` chrome.

The Coach should **render in the same visual register** as the native UI so users do not perceive a "chatbot bolt-on". A widget is just a card emitted by the funnel itself — but driven by Coach intelligence.

---

# 2. Widget Component Schema (JSON-Render Spec)

## 2.1 Envelope schema

Every Coach turn is a single JSON document:

```json
{
  "turn_id": "uuid",
  "ts": "2026-05-30T14:22:01Z",
  "funnel_step": "STEP_4_TARIFF",
  "policy": {
    "intervention_type": "price_reframe",
    "policy_source": "ppo",
    "policy_confidence": 0.81,
    "expected_uplift": 0.18,
    "reason_codes": ["high_dwell_step4", "hover_opt_plus", "p_abandon>0.7"]
  },
  "audience": {
    "segment_posterior": {"S1": 0.12, "S2": 0.81, "S3": 0.07},
    "dominant_segment": "S2"
  },
  "widgets": [ /* ordered array of typed components — see below */ ],
  "fallback_text": "Optional — only used if renderer fails to parse a widget."
}
```

**Hard rule**: `widgets[]` is always non-empty. Even a "thinking" pause is a widget. There is no other channel.

## 2.2 Common widget envelope

Every widget inherits:

```json
{
  "type": "<widget_type>",
  "id": "uuid",
  "tone": "neutral | warm | urgent | analytic",
  "intent": "inform | reassure | reveal | nudge | reframe | offer | handoff | acknowledge",
  "hormozi_axis": "dream_up | likelihood_up | time_down | effort_down",
  "render_hint": { "placement": "inline | overlay | sidebar | toast", "priority": 0-10 },
  "a11y": { "aria_label": "string", "screen_reader_text": "string" },
  "props": { /* widget-specific */ }
}
```

## 2.3 The 13 atomic widgets

### W1. `TextMessage` — the Coach voice

Even plain prose is a typed widget so it can carry tone + axis metadata.

```json
{
  "type": "TextMessage",
  "tone": "warm",
  "intent": "reassure",
  "hormozi_axis": "likelihood_up",
  "props": {
    "speaker": "coach",
    "body_md": "Sie können heute mit **Start** beginnen und in 3 Jahren ohne neue Gesundheitsprüfung auf **Optimal** wechseln.",
    "max_chars": 180,
    "emphasis_spans": [{"start": 40, "end": 45, "kind": "strong"}],
    "delivery": "instant | typewriter_140cps"
  }
}
```
**Renders as**: small left-aligned card with UNIQA blue rule on the left, body text, no avatar (the Coach is the system, not a character).
**Hormozi role**: vehicle for any axis — the `hormozi_axis` annotation tells the persona simulator what driver this message targets.

---

### W2. `ThinkingIndicator` — coach is processing

```json
{
  "type": "ThinkingIndicator",
  "tone": "neutral",
  "intent": "acknowledge",
  "hormozi_axis": "time_down",
  "props": {
    "label": "Vorschlag wird vorbereitet…",
    "max_duration_ms": 1200,
    "show_after_ms": 300
  }
}
```
**Why a widget**: makes Coach latency *part of the protocol* rather than a UI hack. The persona bot can also reason about it ("Coach is hesitating — am I being analyzed?"). Shown only after 300ms so fast turns stay instant.
**Hormozi role**: minimizes perceived `time_down` by showing progress instead of blank wait.

---

### W3. `PriceCard` — tariff display with framing hooks

```json
{
  "type": "PriceCard",
  "tone": "neutral",
  "intent": "reveal",
  "hormozi_axis": "effort_down",
  "props": {
    "tariff_id": "optimal",
    "tariff_name": "Optimal",
    "price_monthly_eur": 68.14,
    "price_daily_eur": 2.25,
    "price_daily_anchor": "weniger als zwei Kaffees pro Tag",
    "annual_max_eur": 2800,
    "coverage_premium_ratio": 3.4,
    "badges": [
      {"kind": "best_value", "label": "Bestes Preis-Leistungs-Verhältnis"},
      {"kind": "new_2025", "label": "Augenlaser ab 09/2025 inkludiert"}
    ],
    "primary_cta": {"label": "Optimal wählen", "action": "select_tariff:optimal"},
    "secondary_cta": {"label": "Was ist enthalten?", "action": "expand_coverage:optimal"},
    "framing": {
      "anchor_against_tariff_id": "start",
      "delta_monthly_eur": 29.40,
      "delta_daily_eur": 0.97,
      "delta_value_per_year_eur": 1400,
      "phrasing": "+€0,97/Tag für +€1.400 Jahresleistung"
    }
  }
}
```
**Hormozi role**: `effort_down` (one click decides) **and** `likelihood_up` (anchored comparison removes "is this worth it?" doubt). The `framing.delta_daily_eur` is the core trick: comparing to the *cheaper* tariff in daily euros makes the upgrade feel near-zero.

---

### W4. `BenefitBar` — progressive benefit reveal

```json
{
  "type": "BenefitBar",
  "tone": "analytic",
  "intent": "reveal",
  "hormozi_axis": "dream_up",
  "props": {
    "compared": [
      {"tariff_id": "start",   "label": "Start"},
      {"tariff_id": "optimal", "label": "Optimal"}
    ],
    "categories": [
      {"key": "cat3_therapy", "label": "Physio / Psychotherapie",
       "values": {"start": 0, "optimal": 560}, "unit": "€/Jahr"},
      {"key": "cat4_aids",    "label": "Sehhilfen, Augenlaser",
       "values": {"start": 0, "optimal": 280}, "unit": "€/Jahr",
       "highlight": "new_2025"}
    ],
    "reveal_mode": "stagger_400ms",
    "summary_line": "Optimal deckt €1.400/Jahr mehr ab als Start."
  }
}
```
**Hormozi role**: `dream_up` — concrete picture of "what I get" via diff against the cheaper option. Staggered reveal creates the "more, more, more" effect (Hormozi bonus-stack pattern) without feeling like marketing.

---

### W5. `ValueReveal` — animated daily-cost reframe

```json
{
  "type": "ValueReveal",
  "tone": "warm",
  "intent": "reframe",
  "hormozi_axis": "effort_down",
  "props": {
    "headline": "€2,25 pro Tag.",
    "subline": "Das ist weniger als zwei Kaffees.",
    "comparators": [
      {"icon": "coffee",   "label": "2 Kaffees",   "amount_eur": 2.40},
      {"icon": "newspaper","label": "Tageszeitung","amount_eur": 2.80},
      {"icon": "parking",  "label": "1h Parken",   "amount_eur": 3.00}
    ],
    "anchor_price_monthly_eur": 68.14,
    "animation": "count_up_800ms"
  }
}
```
**Hormozi role**: `effort_down` via psychological reframe (Hormozi: "psychological > logical"). Monthly price reframed against daily lifestyle expenses the user already accepts without thought.

---

### W6. `UpgradePath` — 3-year lock-in resolution

```json
{
  "type": "UpgradePath",
  "tone": "neutral",
  "intent": "reassure",
  "hormozi_axis": "likelihood_up",
  "props": {
    "current_choice": "start",
    "target_choice": "optimal",
    "timeline": [
      {"year": 0, "label": "Heute", "tier": "Start", "note": "Sofortige Deckung"},
      {"year": 3, "label": "Ab Jahr 3", "tier": "Optimal",
       "note": "Upgrade ohne neue Gesundheitsprüfung"}
    ],
    "guarantee_badge": {
      "name": "Upgrade-Sicherheit",
      "body": "Garantierter Wechsel ohne erneute Gesundheitsfragen."
    },
    "primary_cta": {"label": "Mit Start beginnen", "action": "select_tariff:start"}
  }
}
```
**Hormozi role**: pure `likelihood_up` + risk-reversal (Hormozi: "named guarantee"). Resolves the #1 Step-4 frustration: users who *want* a better tier but hit "Beratung erforderlich". They can commit now and the upgrade is contractually safe.

---

### W7. `TrustSignal` — social proof + provenance

```json
{
  "type": "TrustSignal",
  "tone": "neutral",
  "intent": "reassure",
  "hormozi_axis": "likelihood_up",
  "props": {
    "items": [
      {"kind": "members",    "value": "3,7 Mio.", "label": "Versicherte in CEE"},
      {"kind": "founded",    "value": "1811",     "label": "Seit über 200 Jahren"},
      {"kind": "rating",     "value": "A",        "label": "S&P Rating"},
      {"kind": "test_award", "value": "ÖGVS 2024","label": "Testsieger Krankenversicherung"}
    ],
    "density": "compact | full"
  }
}
```
**Hormozi role**: `likelihood_up` — Hormozi's "10,000th patient vs 1st patient" pattern. Cheap to render, never urgent, always passive presence on price-display screens.

---

### W8. `AdvisorHandoff` — persona-specific routing offer

```json
{
  "type": "AdvisorHandoff",
  "tone": "warm",
  "intent": "handoff",
  "hormozi_axis": "effort_down",
  "props": {
    "trigger_reason": "S1_hybrid_research_done",
    "advisor_mode": "callback | video | in_person",
    "reason_line": "Sie haben sich gut informiert — möchten Sie das Gespräch mit einer Beraterin abschließen?",
    "slot_preview": [
      {"slot_id": "2026-05-30T16:00", "label": "Heute, 16:00"},
      {"slot_id": "2026-05-31T10:00", "label": "Morgen, 10:00"}
    ],
    "primary_cta": {"label": "Termin sichern", "action": "book_advisor"},
    "dismiss_cta": {"label": "Online fortfahren", "action": "dismiss_handoff"},
    "do_not_show_to_segments": ["S2"]
  }
}
```
**Hormozi role**: `effort_down` for Judith (skip the "decide alone" load) and **conversion-equivalent** for Peter (his preferred channel anyway). Hard constraint `do_not_show_to_segments: ["S2"]` is enforced by the policy layer — Franz's −0.30 p_continue penalty on advisor pushes (from UNIQA_ANALYSIS §B.4) means it is policy-illegal to emit this widget when `dominant_segment == "S2"`.

---

### W9. `ObjectionPreempt` — addresses unstated concern

```json
{
  "type": "ObjectionPreempt",
  "tone": "analytic",
  "intent": "reframe",
  "hormozi_axis": "likelihood_up",
  "props": {
    "objection_key": "price_will_rise_later",
    "preempt_line": "Wird der Beitrag stark steigen?",
    "evidence": [
      {"year": 2021, "delta_pct": 0.0},
      {"year": 2022, "delta_pct": 6.6},
      {"year": 2023, "delta_pct": 12.9},
      {"year": 2024, "delta_pct": 8.3}
    ],
    "interpretation": "Im Schnitt 6,5%/Jahr. Wir zeigen alle Anpassungen offen.",
    "visual": "sparkline_4yr"
  }
}
```
**Hormozi role**: `likelihood_up` via Hormozi's "the pain is the pitch" — naming the objection out loud disarms it. Honest disclosure outperforms hidden numbers (UNIQA brand attribute: trustworthy via transparency).

---

### W10. `ProgressIndicator` — funnel position + time-to-go

```json
{
  "type": "ProgressIndicator",
  "tone": "neutral",
  "intent": "inform",
  "hormozi_axis": "time_down",
  "props": {
    "current_step": 4,
    "total_steps": 7,
    "step_labels": ["Leistung","Wer","Daten","Tarif","Gesundheit","Preis","Abschluss"],
    "completed_steps": [1,2,3],
    "eta_remaining_seconds": 180,
    "eta_phrasing": "Noch ca. 3 Minuten"
  }
}
```
**Hormozi role**: `time_down` via *perceived* time delay shrinkage (London Underground dotted-map effect cited in Hormozi frameworks). A 3-minute ETA shrinks "this might take forever" anxiety even if actual time is unchanged.

---

### W11. `GuaranteeBadge` — risk reversal

```json
{
  "type": "GuaranteeBadge",
  "tone": "warm",
  "intent": "reassure",
  "hormozi_axis": "likelihood_up",
  "props": {
    "guarantee_name": "30-Tage-Rücktrittsrecht",
    "body_short": "30 Tage Rücktritt ohne Angabe von Gründen.",
    "icon": "shield_check",
    "applies_to": ["closing"]
  }
}
```
**Hormozi role**: pure `likelihood_up` via named guarantee (Hormozi: "name your guarantee something memorable"). MVP scope: just the legal 30-day Rücktrittsrecht — but named and badge-styled so it functions as offer mechanic, not fine print.

---

### W12. `HesitationSignal` — admin / persona-bot channel (not user-facing in prod)

```json
{
  "type": "HesitationSignal",
  "tone": "analytic",
  "intent": "inform",
  "hormozi_axis": "likelihood_up",
  "props": {
    "audience": "admin | persona_bot",
    "user_visible": false,
    "p_abandon": 0.74,
    "p_abandon_ci90": [0.58, 0.86],
    "drivers": [
      {"feature": "dwell_step4_seconds", "value": 142, "shap": +0.31},
      {"feature": "hover_opt_plus_count", "value": 4, "shap": +0.19},
      {"feature": "back_nav_count",       "value": 1, "shap": +0.08}
    ],
    "predicted_exit_step": 4,
    "persona_state_hint": "Franz hesitating between Optimal and Opt. Plus"
  }
}
```
**Why this exists as a widget**: in the demo + simulation loop, the *persona bot* reads the same JSON the user UI reads. By making the hesitation signal a typed widget gated by `user_visible: false`, the persona bot can update its internal state coherently ("the system thinks I'm hesitating") and the admin dashboard can render the SHAP bar chart. Same payload, two consumers. No side channel.

---

### W13. `InterventionTrigger` — meta-widget: why this turn fired

```json
{
  "type": "InterventionTrigger",
  "tone": "analytic",
  "intent": "inform",
  "hormozi_axis": "likelihood_up",
  "props": {
    "audience": "admin",
    "user_visible": false,
    "policy_source": "ppo | rules | sybilion_gated",
    "intervention_type": "price_reframe",
    "selected_widgets": ["TextMessage","PriceCard","ValueReveal"],
    "policy_confidence": 0.81,
    "expected_uplift_pp": 18,
    "alternative_actions": [
      {"action": "noop",             "q_value": 0.12},
      {"action": "upgrade_path",     "q_value": 0.34},
      {"action": "price_reframe",    "q_value": 0.51},
      {"action": "service_handoff",  "q_value": -0.22}
    ]
  }
}
```
**Use**: jury demo + offline eval. Lets you show the RL agent's full decision (Q-values per action) for any given turn — a "training really happened" artifact.

---

## 2.4 Widget composition rules

1. **One primary widget per turn.** A turn may chain (`ThinkingIndicator` → `TextMessage` → `PriceCard`) but only one widget carries the `policy.intervention_type`. The renderer treats the rest as supporting context.
2. **Maximum 3 user-visible widgets per turn.** Above that, the user perceives spam. The policy is penalized in PPO via the existing `-0.05` per intervention cost — extended to per-widget.
3. **`hormozi_axis` must be present on every widget.** This is the eval hook: we can measure "what % of axis-up interventions actually moved persona p_continue up".
4. **Same envelope, two consumers.** The renderer ignores `user_visible: false` widgets entirely. The persona bot consumes everything. The admin dashboard consumes everything plus the policy metadata.
5. **No raw text channel.** If the LLM fails to produce valid JSON, the harness falls back to emitting a single `TextMessage` with `tone:"neutral"`, `fallback: true` — never to free prose.

---

# 3. Conversation Mechanics — Atomic Coach Moves

Each Coach turn is the loop **DETECT → DECIDE → RENDER → REACT**. Each step has a typed schema. The LLM is constrained to the RENDER step only; DETECT and DECIDE are deterministic.

## 3.1 DETECT — behavioral event JSON

The funnel state machine emits events. Detection is rolling — re-evaluated every 5s or on event boundary.

```json
{
  "session_id": "uuid",
  "funnel_step": "STEP_4_TARIFF",
  "since_step_entry_s": 142,
  "events_window": [
    {"t": 12.1, "kind": "hover",   "target": "tariff_row_optimal",  "duration_s": 18.5},
    {"t": 34.2, "kind": "hover",   "target": "tariff_row_opt_plus", "duration_s": 22.1},
    {"t": 58.0, "kind": "click",   "target": "advisory_required_opt_plus"},
    {"t": 64.3, "kind": "back_nav","from": "advisory_overlay"},
    {"t": 121.0,"kind": "window_blur"}
  ],
  "derived_signals": {
    "dwell_step4_s": 142,
    "hover_opt_plus_count": 4,
    "back_nav_count": 1,
    "external_tab_open": true,
    "advisory_required_blocked": true
  }
}
```

## 3.2 DECIDE — intervention policy output

The policy (rules MVP or PPO) consumes `(funnel_step, segment_posterior, derived_signals, p_abandon, interventions_already_shown)` and returns:

```json
{
  "intervention_type": "upgrade_path",
  "rationale_codes": ["advisory_required_blocked", "hover_opt_plus>=3", "S2_dominant"],
  "widgets_to_render": ["TextMessage", "UpgradePath", "PriceCard:optimal"],
  "hormozi_targets": ["likelihood_up", "effort_down"],
  "policy_confidence": 0.78,
  "must_not_render": ["AdvisorHandoff"]
}
```

`must_not_render` is the hard-constraint channel — segment-specific bans (Franz never sees AdvisorHandoff) are enforced *before* the LLM is invoked. The LLM cannot violate them because they are filtered from the widget vocabulary it sees.

## 3.3 RENDER — LLM prompt template (constrained JSON output)

```
SYSTEM:
You are the UNIQA Conversion Coach renderer.
You receive a DECIDE payload and must output a single JSON envelope conforming to the
WidgetEnvelope schema. You MUST emit only widget types listed in `widgets_to_render`.
You MUST NOT emit any widget type in `must_not_render`.
You MUST set `hormozi_axis` on every widget to one of the values in `hormozi_targets`.
Tone must match the dominant segment:
  S1 Judith → warm, respectful, advisor-friendly
  S2 Franz  → analytic, terse, data-first, never warm-pushy
  S3 Peter  → simple, one-step-at-a-time, reassuring
Language: de-AT, Sie-form. All prices with comma decimal (€68,14).
Length budget: each TextMessage.body_md ≤ 180 chars.

You MUST output valid JSON. No prose. No code fences. No commentary.

USER:
DECIDE = <decide_json>
CONTEXT = {
  "tariff_facts": <product reference subset>,
  "funnel_step_facts": <step constraints>,
  "segment_posterior": <...>,
  "prior_widgets_in_session": [<types already shown>]
}
SCHEMA = <WidgetEnvelope JSON Schema, draft-2020-12>
```

**Generation parameters**:
- Constrained decoding via JSON-schema-grammar (e.g. `outlines`, `llguidance`, OpenAI `response_format: json_schema`).
- Temperature 0.3 for prose fields, temperature 0.0 for structural fields (enforced by grammar).
- Max tokens 800 (envelope is small).
- Stop tokens: `]\n}` close of envelope.

**Fallback ladder** if generation fails:
1. Schema-invalid JSON → retry once with stricter prompt + raised grammar constraint.
2. Second failure → emit `noop` envelope: `widgets: [{type:"TextMessage", tone:"neutral", props:{body_md:"<canned line keyed by intervention_type>"}}]`.
3. Log failure for offline eval.

## 3.4 REACT — persona state delta the bot is expected to produce

For each widget type, we define an *expected reaction distribution* per segment. The persona bot consumes the widget JSON and outputs a state update:

```json
{
  "session_id": "uuid",
  "turn_id": "uuid",
  "persona": "franz",
  "delta_p_continue": +0.22,
  "delta_p_abandon_next_step": -0.14,
  "delta_intent": {"select_tariff:optimal": +0.31},
  "behavioral_response": {
    "dwell_extra_s": 18.0,
    "next_event": "click:select_tariff:optimal",
    "narrative": "Daten überzeugen. Upgrade-Pfad nicht relevant für mich."
  }
}
```

The behavioral_response.narrative is **for logs only** — the simulation uses the numeric deltas. This separation is what makes simulations reproducible (UNIQA_ANALYSIS §B.4 "deterministic enough to reproduce, stochastic enough to simulate variance").

## 3.5 The DETECT→DECIDE→RENDER→REACT loop, compact

```
funnel_state_machine.emit_events()
    → detector.derive_signals()
        → abandonment_model.predict(p_abandon, ci)
            → sybilion_gate(p_abandon, ci_width)  [optional]
                → policy.decide()  [rules or PPO]
                    → llm.render(decide_payload, schema)  [constrained JSON]
                        → widget_envelope
                            ├→ ui_renderer.draw(widgets where user_visible)
                            └→ persona_bot.react(all widgets)
                                → behavioral_response
                                    → funnel_state_machine.apply()
                                        → loop
```

Every arrow is a typed schema. The LLM is invoked at exactly one node, with constrained output. Everywhere else is code.

---

# 4. Hormozi Framework Application

Mapping each critical funnel moment to Value Equation drivers and to widgets.

## 4.1 Step 4 — initial tariff price (66% drop-off, primary target)

**What's happening psychologically**: User sees 4 tariffs. The two attractive ones (Opt. Plus, Premium) are blocked by "Beratung erforderlich". User feels: confusion (effort up), gating frustration (likelihood down), price uncertainty (dream unclear).

| Hormozi driver | Direction | Widgets | Why |
|---|---|---|---|
| **Dream Outcome ↑** | UP | `BenefitBar` (Optimal vs Start diff) | Concrete picture of +€1,400/yr coverage delta |
| **Perceived Likelihood ↑** | UP | `UpgradePath`, `TrustSignal`, `ObjectionPreempt` | "I can start now and upgrade later — risk-free" + 200-year brand + price-rise transparency |
| **Time Delay ↓** | DOWN | `ProgressIndicator` ("3 minutes left"), `ValueReveal` (instant daily reframe) | Shrinks perceived completion time + reframes monthly to daily for instant cognitive resolution |
| **Effort/Sacrifice ↓** | DOWN | `PriceCard` with `framing.delta_daily_eur`, `AdvisorHandoff` (S1/S3 only) | One-click choice with anchored daily delta; handoff offloads effort entirely for hybrid/service-affine personas |

**Per-segment Step-4 playbook**:

- **S2 Franz (analytic, online-affine)**: Emit `BenefitBar` + `PriceCard:optimal` + `ObjectionPreempt`. Tone: analytic. Never emit `AdvisorHandoff`. He responds to **data density**, not warmth. PPO learns this via the −0.30 p_continue penalty.
- **S1 Judith (hybrid, advisor-curious)**: Emit `UpgradePath` first (resolves Opt. Plus frustration), then *optional* soft `AdvisorHandoff` if dwell > 90s. Tone: warm. The handoff is offered, not pushed — she chose to research online, give her credit for that.
- **S3 Peter (service-affine, overwhelm)**: Emit `AdvisorHandoff` *early* — ideally before Step 4. At Step 4, if he's still here, emit `ValueReveal` + `TrustSignal` only. Tone: simple. Strip everything else.

## 4.2 Step 7 — final price after health questions (78% drop-off, primary target)

**What's happening**: Final price > provisional price. The gap is the abandonment driver. User feels: betrayal (likelihood crashes), surprise (effort spikes — "I have to re-evaluate"), suspicion (trust drops).

| Hormozi driver | Direction | Widgets | Why |
|---|---|---|---|
| **Dream Outcome ↑** | UP | `BenefitBar` (annual ceiling vs. premium), `ValueReveal` (daily reframe on final price) | Re-anchor on what they get, not what they pay extra |
| **Perceived Likelihood ↑** | UP | `ObjectionPreempt` ("Why is the final price higher?"), `TrustSignal`, `GuaranteeBadge` (30-day Rücktritt) | Honesty disarms betrayal; the named guarantee reverses risk on the spot |
| **Time Delay ↓** | DOWN | `ProgressIndicator` ("Letzter Schritt — 60s") | Loss-aversion frame: "you've invested 6 minutes already" |
| **Effort/Sacrifice ↓** | DOWN | `PriceCard` with new delta phrasing: "+€0,23/Tag mehr als geschätzt" | Reframes the shock numerically. €7/mo extra → €0,23/day — psychological > logical (Hormozi's elevator-mirror move) |

**Critical move**: `ObjectionPreempt` fires *before* the user has time to formulate the complaint. The widget says "Why is this higher than the estimate?" and answers it (pre-conditions = individualized risk pricing = fair). Hormozi: "the pain is the pitch" — naming the betrayal disarms it.

**Avoid**: any `AdvisorHandoff` here unless the user is S3 and has not yet been routed. For S2 (the segment that owns Step 7 abandonment), handoff is destructive — they came to finish online.

## 4.3 Step 3 / early Peter exit (~35% S3 specific)

**What's happening**: Peter is filling personal data, feeling overwhelmed, and is going to leave for the call center. He's not lost — he's in the wrong channel. The Coach goal here is *conversion-equivalent routing*, not online completion.

| Hormozi driver | Direction | Widgets | Why |
|---|---|---|---|
| **Dream Outcome ↑** | UP | `TextMessage` ("Wir rufen Sie zurück — Sie geben nichts auf") | Reframes "leave the form" not as failure but as a *better* path to his goal |
| **Perceived Likelihood ↑** | UP | `TrustSignal` (compact), `AdvisorHandoff` with `advisor_mode: callback` | He believes a human will get it right. Lean into that. |
| **Time Delay ↓** | DOWN | `AdvisorHandoff.slot_preview` (next slot in 20 min) | Concrete time, not "we'll be in touch" |
| **Effort/Sacrifice ↓** | DOWN | `AdvisorHandoff` itself — DFY vs DIY | This is the entire Hormozi DFY > DIY argument applied to channel choice |

**The S3 widget bundle is Hormozi's DFY playbook**: take the work off the user's hands. The "conversion" reward for the policy here is `+0.3` (UNIQA_ANALYSIS §B.4) — not 1.0, because it's a routed not online sale, but strictly positive because it counts for the business.

## 4.4 Hormozi axis assignment summary

| Widget | Primary axis | Secondary | Where used |
|---|---|---|---|
| `TextMessage` | (vehicle) | any | everywhere |
| `ThinkingIndicator` | time_down | — | latency masking |
| `PriceCard` | effort_down | likelihood_up | Step 4, Step 7 |
| `BenefitBar` | dream_up | — | Step 4 (mostly), Step 7 |
| `ValueReveal` | effort_down | dream_up | Step 4, Step 7 |
| `UpgradePath` | likelihood_up | dream_up | Step 4 (S1/S2 with Opt. Plus interest) |
| `TrustSignal` | likelihood_up | — | always-on, low-priority |
| `AdvisorHandoff` | effort_down | likelihood_up (for S3) | Step 3 (S3), Step 4 (S1), never S2 |
| `ObjectionPreempt` | likelihood_up | — | Step 4, Step 7 |
| `ProgressIndicator` | time_down | — | always-on |
| `GuaranteeBadge` | likelihood_up | — | Step 7, closing |
| `HesitationSignal` | (admin) | — | admin/persona-bot only |
| `InterventionTrigger` | (admin) | — | admin/persona-bot only |

---

# 5. Technical Scope, Degrees of Freedom, Challenges

## 5.1 Required vs aspirational

### MVP (required, 12–18h to build)

- **WidgetEnvelope JSON Schema** + the 13 widget schemas (draft-2020-12, ~600 LOC).
- **React renderer** for 7 user-visible widgets (`TextMessage`, `PriceCard`, `BenefitBar`, `ValueReveal`, `UpgradePath`, `AdvisorHandoff`, `ProgressIndicator`). Tailwind + the UNIQA design tokens from §1. ~1500 LOC.
- **LLM constrained generation** wired to OpenAI structured-output mode (`response_format: {type:"json_schema", schema: WidgetEnvelope}`). Falls back to canned envelope on failure.
- **Rule-based DECIDE policy** (20 rules, segment × step × signal matrix). Pure Python.
- **Persona bot** consuming the WidgetEnvelope and returning a `REACT` payload via prompted GPT-4 (system prompt = persona markdown + widget consumption protocol).
- **Single demo flow**: Franz at Step 4, no Coach → abandons. Same Franz, Coach fires `PriceCard + BenefitBar + ObjectionPreempt` → converts. Side-by-side.

### Production-quality (aspirational, beyond hackathon)

- All 13 widgets rendered, including the 2 admin-only.
- PPO policy trained on synthetic data (per UNIQA_ANALYSIS §C).
- Fine-tuned 7B persona bots (Mistral-7B LoRA × 3 personas).
- Sybilion-gated triggering (CI-width threshold).
- Multilingual de-AT / en-US / it-IT (the doc tokens already support `lang` param).
- A/B test infrastructure: 10k synthetic runs per condition with statistical significance.
- Live event-stream version (currently the simulation is turn-based; live mode needs WebSocket plumbing).

## 5.2 Key engineering decisions

### D1. Schema versioning

`WidgetEnvelope` carries `schema_version: "1.0"`. Renderer and persona-bot both pin to a version. Widgets gain optional props additively; required-prop changes bump major. **Decision for hackathon**: freeze schema at hour 4, never bump. All later iteration is in `props` enums.

### D2. Constrained generation strategy

Three viable options:
- **OpenAI `response_format` JSON schema** (cheapest, easiest, demo-grade). Pro: zero infra. Con: ties to API; some schema features (oneOf, conditional required) only partially supported.
- **`outlines` / `llguidance` grammar-constrained sampling** on a local 7B/8B model. Pro: 100% schema valid, deterministic structure. Con: needs GPU at inference.
- **Two-stage: free-text LLM → strict JSON validator + re-asker**. Pro: model-agnostic. Con: latency cost on failure; can loop.

**Decision for MVP**: option 1 with retry-and-fallback. Migrate to option 2 once fine-tuned Mistral-7B persona bots exist (the same GPU rig can host the renderer).

### D3. Renderer fallback

The renderer must handle:
- Unknown widget `type` → render the widget's own `a11y.screen_reader_text` as a neutral `TextMessage`-equivalent card. Never crash.
- Missing required prop → log + render a placeholder (e.g., PriceCard without `price_monthly_eur` → "Preis wird geladen…").
- `user_visible: false` → ignore silently. This is how admin widgets pass through transparently.

### D4. Persona-bot widget consumption protocol

The persona bot is *not* asked "react to this text". It is asked:

> "You are <persona>. You just received this WidgetEnvelope: `<json>`. For each widget, update your internal state per the reaction rules. Output a REACT payload."

Reaction rules are encoded as a per-(persona × widget_type × hormozi_axis) lookup table — same idea as UNIQA_ANALYSIS §B.4 `franz_bot_decide`. The LLM generates narrative and refines magnitudes; the *direction* is deterministic.

### D5. Policy → widget selection mapping

The PPO action space is the intervention *type*, not the widget set. A separate deterministic map expands intervention type → widget bundle:

```python
INTERVENTION_TO_BUNDLE = {
  "price_reframe":       ["TextMessage","ValueReveal","PriceCard"],
  "upgrade_path":        ["TextMessage","UpgradePath","PriceCard:start"],
  "service_handoff":     ["TextMessage","AdvisorHandoff"],
  "transparency":        ["ObjectionPreempt","PriceCard"],
  "trust_reinforcement": ["TrustSignal","GuaranteeBadge"],
  ...
}
```

This keeps the PPO action space small (10 discrete actions, per §C.1 of analysis) while letting widget composition be tuned without retraining. Bundles are filtered by `must_not_render` before LLM call.

## 5.3 Specific challenges

### C1. LLM JSON validity rate

Even with `response_format: json_schema`, ~2–5% of generations have semantic errors (right shape, wrong values — e.g., `hormozi_axis: "price_down"`). Mitigation: post-validation enum check + retry. Track invalid rate as eval metric.

### C2. Persona-bot reaction calibration

If reactions are too deterministic (lookup table) the bot is a markov chain in a costume. If reactions are pure LLM, runs are unreproducible. **Resolution**: structured reaction (deterministic delta_p_continue) + LLM-generated narrative + small stochastic noise term (~N(0, 0.05)) on the delta. Reproducibility via seeded RNG.

### C3. Evaluation: did the widget work?

Per-widget uplift is the holy-grail metric. Operational definition:
```
uplift(widget_type, segment, step) =
    P(continue | widget shown, signals=X) − P(continue | noop, signals=X)
```
estimated by importance-sampling reweighted simulation. Hackathon-scope eval: just `P(convert | coach_on) − P(convert | coach_off)` per persona, with widget attribution from the `InterventionTrigger` log.

### C4. Hormozi axis is fuzzy

We assert each widget targets a specific axis, but the axis labels are interpretive. **Mitigation**: treat the `hormozi_axis` field as an *attribution* tag, not a causal claim. In eval, compute correlation between observed `delta_p_continue` and asserted axis to validate the taxonomy. Re-label widgets if correlations are wrong.

### C5. Schema breadth vs PPO sample efficiency

13 widget types × 4 tones × 4 intents × 4 axes × props = effectively unbounded surface. PPO over the *widget* space would not converge. **That's why** the PPO action space is at the **intervention-type** level (10 discrete actions) and the widget bundle is deterministic from the intervention. This is a deliberate dimensionality reduction.

### C6. Persona-bot must respect `do_not_render`

The persona bot also reads the schema. If the LLM persona generates "I clicked the advisor button" but the envelope contained no `AdvisorHandoff`, the simulation is incoherent. **Mitigation**: REACT output is validated against the input envelope — actions that reference widgets not in the envelope are rejected and resampled.

### C7. Multi-language

For hackathon: pick *one* language (de-AT recommended — UNIQA is Austrian; alternately en-US for jury legibility). The schema carries `lang` everywhere but renderer/LLM are pinned. Production: per-language prompt suites + per-language price formatting (`€68,14` vs `€68.14`).

## 5.4 Degrees of freedom

| Dimension | MVP choice | Range of expansion |
|---|---|---|
| Widget library breadth | 13 widgets, 7 visible | up to ~40 (per-step micro-widgets, video, charts) |
| Persona adaptation | tone + bundle filter | per-persona fine-tuned generator, per-persona widget skins |
| Language | de-AT or en-US | de-AT + en-US + it-IT (UNIQA CEE markets) |
| Policy sophistication | 20 rules | rules → bandit → PPO → MCTS+PPO |
| Trigger gating | fixed p_abandon > 0.6 | Sybilion CI-aware gating |
| Eval framework | 100 simulated runs | 10k simulated + bootstrap CI + Mann-Whitney U |
| Widget composition | static bundles | learned composition (separate policy over widget set) |
| Renderer fidelity | Tailwind cards | full UNIQA design system, motion design, a11y AA |

## 5.5 Interaction with the abandonment predictor and PPO policy

Per UNIQA_ANALYSIS §B, the pipeline is:

```
events → abandonment_predictor → (p_abandon, ci)
                                     ↓
                            sybilion gate (optional)
                                     ↓
       (state) ──→  PPO policy  ──→  intervention_type ∈ {10}
                                     ↓
                       intervention→widget bundle map (deterministic)
                                     ↓
                       must_not_render filter (segment-aware)
                                     ↓
                       LLM constrained renderer  →  WidgetEnvelope
                                     ↓
                             ┌───────┴───────┐
                          renderer        persona_bot
                                              ↓
                                          REACT payload
                                              ↓
                                      state machine update
```

**Key insight for the demo**: the PPO action space is intentionally coarse (10 intervention types). The fine-grained design choices live in:
1. The deterministic intervention→widget bundle map (engineering knob).
2. The LLM renderer (creative knob, prompted, swappable).
3. The `must_not_render` segment-aware filter (safety knob, hard rules).

This three-layer separation means: the **PPO model is small and trainable**, the **widget catalog can grow without retraining**, and **segment-safety constraints are guaranteed** (Franz cannot receive AdvisorHandoff — not because PPO learned it, but because it is filtered before the LLM sees the option).

## 5.6 Hackathon MVP — what to ship by Sunday 10:00

1. **WidgetEnvelope JSON Schema** + 7 widget schemas (`TextMessage`, `PriceCard`, `BenefitBar`, `ValueReveal`, `UpgradePath`, `AdvisorHandoff`, `ProgressIndicator`). ~4h.
2. **React + Tailwind renderer** with UNIQA design tokens. ~5h.
3. **20-rule DECIDE policy** + intervention→bundle map. ~2h.
4. **OpenAI structured-output RENDER** with prompts per intervention type. ~3h.
5. **Persona-bot REACT** with deterministic delta-table + GPT-4 narrative wrapper. ~3h.
6. **Side-by-side demo**: Franz no-Coach vs Franz with Coach, narrated. Streamlit or React app. ~3h.
7. **Eval table**: 100 runs × 3 personas × {Coach on/off}, conversion deltas. ~2h.

Total ~22h of focused work — fits the remaining hackathon window with margin.

## 5.7 Production quality — what shipping this for real takes

- Real funnel event-stream integration (not state machine simulation).
- GDPR review: what behavioral signals can be persisted; widget logs as PII.
- Legal review of every `ObjectionPreempt`, `GuaranteeBadge`, `UpgradePath` claim — these are insurance product statements.
- de-AT localization audit by UNIQA copy team.
- A/B framework on live traffic with per-segment guardrails (no advisor pushes to S2 — enforced server-side, not just policy-side).
- Operational dashboard (admin widgets become a real product).
- Model monitoring: abandonment predictor drift, PPO policy drift, LLM JSON-validity rate.

---

## Appendix A — Hormozi axis quick-reference per widget

```
DREAM_UP     : BenefitBar, ValueReveal(secondary), TextMessage(framing)
LIKELIHOOD_UP: UpgradePath, TrustSignal, ObjectionPreempt, GuaranteeBadge
TIME_DOWN    : ProgressIndicator, ThinkingIndicator, ValueReveal(daily reframe)
EFFORT_DOWN  : PriceCard, AdvisorHandoff, ValueReveal(primary)
ADMIN-ONLY   : HesitationSignal, InterventionTrigger
```

## Appendix B — Example full Coach turn (Franz, Step 4, dwell=142s, hovered Opt. Plus)

```json
{
  "turn_id": "01HXYZ...",
  "ts": "2026-05-30T14:22:01Z",
  "funnel_step": "STEP_4_TARIFF",
  "policy": {
    "intervention_type": "upgrade_path",
    "policy_source": "rules",
    "policy_confidence": 0.78,
    "expected_uplift": 0.18,
    "reason_codes": ["advisory_required_blocked","hover_opt_plus>=3","S2_dominant"]
  },
  "audience": {
    "segment_posterior": {"S1":0.08,"S2":0.86,"S3":0.06},
    "dominant_segment": "S2"
  },
  "widgets": [
    {
      "type":"TextMessage","id":"w1","tone":"analytic","intent":"reframe",
      "hormozi_axis":"likelihood_up",
      "props":{
        "speaker":"coach",
        "body_md":"Opt. Plus erfordert Beratung. **Optimal heute, Wechsel zu Opt. Plus in 3 Jahren ohne neue Gesundheitsprüfung.**",
        "max_chars":180
      }
    },
    {
      "type":"UpgradePath","id":"w2","tone":"neutral","intent":"reassure",
      "hormozi_axis":"likelihood_up",
      "props":{
        "current_choice":"optimal","target_choice":"opt_plus",
        "timeline":[
          {"year":0,"label":"Heute","tier":"Optimal","note":"Sofortige Deckung €2.800/Jahr"},
          {"year":3,"label":"Ab Jahr 3","tier":"Opt. Plus","note":"Upgrade ohne neue Gesundheitsprüfung"}
        ],
        "guarantee_badge":{"name":"Upgrade-Sicherheit","body":"Vertraglich garantiert."}
      }
    },
    {
      "type":"PriceCard","id":"w3","tone":"neutral","intent":"reveal",
      "hormozi_axis":"effort_down",
      "props":{
        "tariff_id":"optimal","tariff_name":"Optimal",
        "price_monthly_eur":68.14,"price_daily_eur":2.25,
        "price_daily_anchor":"weniger als zwei Kaffees pro Tag",
        "annual_max_eur":2800,"coverage_premium_ratio":3.4,
        "badges":[{"kind":"best_value","label":"Bestes Preis-Leistungs-Verhältnis"}],
        "primary_cta":{"label":"Optimal wählen","action":"select_tariff:optimal"}
      }
    },
    {
      "type":"HesitationSignal","id":"w4","tone":"analytic","intent":"inform",
      "hormozi_axis":"likelihood_up",
      "props":{
        "audience":"admin","user_visible":false,
        "p_abandon":0.74,"p_abandon_ci90":[0.58,0.86],
        "drivers":[
          {"feature":"dwell_step4_seconds","value":142,"shap":0.31},
          {"feature":"hover_opt_plus_count","value":4,"shap":0.19}
        ],
        "predicted_exit_step":4,
        "persona_state_hint":"Franz hesitating, wants Opt. Plus but blocked by advisory wall"
      }
    },
    {
      "type":"InterventionTrigger","id":"w5","tone":"analytic","intent":"inform",
      "hormozi_axis":"likelihood_up",
      "props":{
        "audience":"admin","user_visible":false,
        "policy_source":"rules","intervention_type":"upgrade_path",
        "selected_widgets":["TextMessage","UpgradePath","PriceCard"],
        "policy_confidence":0.78,"expected_uplift_pp":18,
        "alternative_actions":[
          {"action":"noop","q_value":0.10},
          {"action":"price_reframe","q_value":0.40},
          {"action":"upgrade_path","q_value":0.51},
          {"action":"service_handoff","q_value":-0.22}
        ]
      }
    }
  ],
  "fallback_text":"Optimal heute wählen, in 3 Jahren ohne Gesundheitsprüfung zu Opt. Plus wechseln."
}
```

---

*Design doc compiled by Claude Code | Sources: UNIQA_ANALYSIS.md, Hormozi $100M Offers framework (SKILL.md + frameworks.md) | Date: 2026-05-30*
