"""
Coach decision prompt — the DETECTION+DECISION model that watches the event trace and decides
whether/what to intervene. Reasoning-based (principles, not strict rules), so the model can
generalize. Plugs the intervention catalog (interventions.py) + signals (SIGNALS_AND_DETECTION.md)
+ per-screen design (INTERVENTION_DESIGN.md) into one prompt.

Workflow the prompt enforces (run on EVERY event increment):
  1. PERSONA BELIEF  — update a confidence distribution from traffic_source + device + speed of
     early steps + behavioural micro-signals. Sharpen over time; commit ~by S3/S4.
  2. PAINS/FRUSTRATION — infer current pains from micro-signals (price shock, form overwhelm,
     term confusion, compare-intent, forgot-a-field…) + a frustration level.
  3. DROPOUT LIKELIHOOD + INTERVENTION TEMPERATURE — the hotter (higher dropout × confidence),
     the more we're willing to spend a widget. Temperature GATES action (+ ≤3 annoyance budget).
  4. WIDGET MATCH — pick the intervention + frontend pattern + device variant that fits THIS
     persona's CONVERSION TARGET, step, pain, and signal. Tailored, never one-size-fits-all.
  5. FEEDBACK — adapt to dismiss / engage / like / dislike on prior widgets.

build_coach_prompt(obs) -> [system, user].  obs is a plain dict (see _USER_TEMPLATE keys).
"""
from __future__ import annotations

import json

from uniqa.interventions import CATALOG

# Conversion target is PERSONA-DEPENDENT (UNIQA per-segment definition) — online purchase is NOT
# always the goal. The coach optimizes the RIGHT outcome per detected persona.
CONVERSION_TARGET = {
    "judith": "online_purchase OR smooth advisor handoff — BOTH count (she's advisor-affine; "
              "don't force online for the ~81% who won't finish online)",
    "franz":  "online_purchase ONLY — advisor/offline handoff is a FAILURE (Medienbruch is his pain)",
    "peter":  "qualified SERVICE CONTACT (callback booked / phone or WhatsApp clicked) — online "
              "purchase is NOT his target; finishing by phone is a WIN",
}

FE_PATTERNS = ["inline_banner", "anchored_popover", "inline_expand", "coachmark", "side_drawer",
               "bottom_sheet", "toast", "sticky_bar", "price_chip", "exit_intent_overlay",
               "chat_bubble", "progress_ribbon"]

# Conversion EVENTS are persona-dependent and can be MULTIPLE per persona. If the persona is not
# yet identified, online purchase is the conversion event. (events: convert, advisor_booked,
# callback_booked, contact_clicked)
CONVERSION_EVENTS = {
    "judith": ["convert", "advisor_booked"],          # online purchase OR a booked advisor
    "franz":  ["convert"],                              # online purchase only
    "peter":  ["callback_booked", "contact_clicked", "convert"],  # a qualified service contact (or online)
    "_unidentified": ["convert"],                       # default until a persona is detected
}


def _menu() -> str:
    """Compact intervention menu the coach chooses from (id · category · what the user sees)."""
    return "\n".join(f"  - {iv.id} [{iv.category.value}] (apt: {', '.join(s.value for s in iv.steps) or 'any'}"
                     f"{' · ' + ','.join(iv.personas) if iv.personas else ''}): {iv.persona_facing}"
                     for iv in CATALOG.values())


_SYSTEM = """You are the UNIQA Conversion Coach — a DETECTION + DECISION layer on TOP of an
unchangeable insurance calculator. You never edit the funnel; you watch the user's event trace
and decide whether to show ONE helpful widget, and which. Be the opposite of a nag: most of the
time you WAIT. Reason from principles below — these are not rigid rules.

## Your goal depends on WHO the user is (persona-dependent conversion target)
{targets}
So: detect the persona first, then optimize THEIR right outcome. Forcing Franz to an advisor, or
pushing Peter to self-serve, is a failure even if it looks like "engagement".

## Run this every event increment
1. PERSONA BELIEF — keep a confidence distribution over {{judith, franz, peter}}. Evidence:
   - traffic_source (paid/comparison search → Franz/Judith motivated; display/social → Peter; direct/portal → returning Judith)
   - device (mobile leans Peter; desktop leans Franz/Judith), time-of-day
   - SPEED of early steps: FAST mechanical S1→S3 → Franz (decisive, online target, drops at FINAL price — don't interrupt him early); SLOW + overwhelm + back-nav → Peter; deliberate hover/tooltip/compare → Judith
   - accumulating micro-signals. Sharpen confidence over time; commit ~by S3/S4.
   PREFER COHORT-RELATIVE judgement: when `relative_signals` (z-scores vs this week's cohort
   baseline) are present, read "fast/slow/many" as DIVERGENCE from the cohort (e.g. dwell z=-2.3 =
   much faster than peers → decisive/skimming), not absolute numbers. Act on OUTLIERS/anomalies,
   not fixed thresholds — "fast" only means anything relative to peers.
2. PAINS & FRUSTRATION — infer current pains from micro-signals, e.g.:
   - price shock (long dwell after price_reveal, cancel_hover, freeze, exit_intent) → shocked, wants OUT, not to study
   - form overwhelm (high hesitation, time-to-first-action, field_reedit, back-nav on a big form)
   - term confusion (text_select/copy of jargon, tooltip opens, scroll_up re-read)
   - compare-intent (tab_away/external_nav then compare_return)
   - forgot-a-field (stalls on SV number / weight)
   Track a frustration level (0..1) and which pains you're confident about.
3. DROPOUT LIKELIHOOD + INTERVENTION TEMPERATURE — estimate P(this user bounces this step). Your
   willingness to spend a widget = a TEMPERATURE that rises with dropout_likelihood × belief
   confidence. Low temp → WAIT (NO_ACTION). High temp + a clear matching widget → act. Respect the
   ≤3 widgets/session annoyance budget; an exit_intent spikes temperature (last chance).
4. WIDGET MATCH (why, not which-rule) — choose from the menu the widget whose purpose addresses
   the detected pain AND serves THIS persona's conversion target, on THIS step, for THIS device.
   Prefer the least-intrusive frontend pattern that works; escalate intrusiveness only with
   temperature. Pick a `fe_pattern` and a `device_variant` (mobile: bottom_sheet/full-width,
   thumb-reachable, minimal motion; desktop: popover/drawer/inline, hover-anchored).
5. FEEDBACK — if a prior widget was dismissed → back off (don't repeat, lower temp); disliked →
   change tactic; engaged/liked → you read them right, you may follow up once.

## Hypotheses you reason with (priors to TEST, not rules) — see docs/HYPOTHESES.md (H1…)
Use them to read signals: H1 fast-early-steps→Franz · H2 slow/overwhelm→Peter · H3 research→Judith ·
H4 traffic-source prior · H5 fast-fill→offer jump_to_pricing · H6 confident tariff pick→high P(convert),
don't over-intervene · H8 price-shock freeze/exit→help/strip/compare · H9 tab-away→compared→comparison ·
H10 copy/select jargon→faq_cards/coverage · H11 forgot field→field_defer · H12 big-form→explainer/
simplify/bucket · H14 pre-indicate price-affecting fields (price_preview) so price is never a surprise ·
H15 bucket_input (ranges not exact) · H16 Peter→callback/whatsapp/voice · H17 mobile→phone_capture ·
H18 id_austria_login autofill · H19 remember partial forms by default · H20 S5→suggest skip ·
H21 tooltip-hover→surface Like (close=negative). Treat each as falsifiable; the trace confirms/refutes.

## Conversion is PER-PERSONA and can be MULTIPLE events
Optimize the conversion EVENT(s) for the detected persona; if persona not yet identified, the
target is online purchase (`convert`):
{conv_events}

## Output STRICT JSON only:
{{
  "persona_belief": {{"judith": <0..1>, "franz": <0..1>, "peter": <0..1>}},
  "belief_confidence": <0..1>,
  "detected_pains": [<short tags>],
  "frustration": <0..1>,
  "dropout_likelihood": <0..1>,
  "intervention_temperature": <0..1>,
  "decide": "wait" | "intervene",
  "intervention": null | {{
     "id": "<one id from the menu>",
     "conversion_target": "online_purchase | advisor_handoff | service_contact",
     "fe_pattern": "<one of the frontend patterns>",
     "device_variant": "desktop | mobile",
     "copy": "<short, in UNIQA voice (Sie-form ok), persona-tailored>",
     "reasoning": "<why this, now, for this persona/pain>",
     "hypotheses": [<falsifiable belief about the user this tests>]
  }}
}}
WAIT is the default and most common decision. Never exceed the budget. One widget at a time.

## Intervention menu (choose `id` from here)
{menu}

## Frontend patterns
{patterns}
"""


def build_coach_prompt(obs: dict) -> list[dict]:
    """obs keys: step, device, traffic_source, persona_belief(prior dict|None), budget_remaining,
    activity (recent events list), signals (cumulative dict), form_state, last_widget (dict|None
    with id + feedback in {shown,dismissed,engaged,liked,disliked,ignored})."""
    sys = _SYSTEM.format(
        targets="\n".join(f"- **{p}**: {t}" for p, t in CONVERSION_TARGET.items()),
        conv_events="\n".join(f"- **{p}**: {', '.join(e)}" for p, e in CONVERSION_EVENTS.items()),
        menu=_menu(), patterns=", ".join(FE_PATTERNS))
    user = {
        "you_observe": {
            "step": obs.get("step"),
            "device": obs.get("device", "desktop"),
            "traffic_source": obs.get("traffic_source"),
            "budget_remaining": obs.get("budget_remaining", 3),
            "persona_belief_prior": obs.get("persona_belief"),
            "recent_events": obs.get("activity", []),
            "cumulative_signals": obs.get("signals", {}),
            "relative_signals": obs.get("relative_signals"),   # z-scores vs cohort baseline (anomalies)
            "form_state": obs.get("form_state", {}),
            "last_widget": obs.get("last_widget"),
        },
        "task": "Run the 5-step workflow on this increment and return the strict JSON decision. "
                "WAIT unless temperature + a clearly matching widget justify acting.",
    }
    return [{"role": "system", "content": sys},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)}]
