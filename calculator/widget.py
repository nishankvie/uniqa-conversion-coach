"""
UNIQA widget twin — per-step action spaces + json-render specs.

Grounded in the real calculator screenshots (/tmp/uniqa_step*.png):
  • global chrome: progress bar  Angaben › Produkt › Empfehlung › Abschluss
  • S1 coverage / S2 insured : ChoiceCards (tap to select)
  • S3 personal info         : date field (keystrokes) + searchable SV dropdown
                              (open → type-filter keystrokes → option click) + inline validation
  • S4 tariff               : 4-column table; per-column SELECT reveals the monthly price;
                              online/Beratung badges; (i) TOOLTIP per coverage row
  • S6 personal+health      : long form (many fields → high keystroke/tap UX cost) + submit

Each step exposes a CLOSED ACTION SPACE (what a user — or the persona-TLM — may do
here) so generated event feeds stay legal and UX cost (taps/keystrokes) is measurable.
This is the twin the teacher and the persona-TLM both condition on; keep it as close
to the live widget as possible.
"""

from __future__ import annotations

from calculator.funnel import Step
from calculator.contracts import EventType
from calculator.scope import TARIFF_PRICE_EUR, Tariff

PROGRESS = ["Angaben", "Produkt", "Empfehlung", "Abschluss"]

# Real searchable Sozialversicherung options (from uniqa_s3c.png).
SV_OPTIONS = ["ÖGK", "BVAEB-OEB", "SVS Landwirtschaft", "SVS gew.Wirtschaft Sach",
              "BVAEB-EB", "KFA Wien,NÖ,Sbg,Ktn"]

TARIFFS = [
    {"id": "start",    "name": "Start",    "price_eur": 38.74,  "online": True,  "max_year": 1400},
    {"id": "optimal",  "name": "Optimal",  "price_eur": 68.14,  "online": True,  "max_year": 2800},
    {"id": "opt_plus", "name": "Opt. Plus","price_eur": 96.66,  "online": False, "max_year": 4200},
    {"id": "premium",  "name": "Premium",  "price_eur": 140.15, "online": False, "max_year": 8400},
]

# Coverage rows with (i) tooltips (the things users hover/expand on the tariff table).
TARIFF_ROWS = ["hoechstbetrag", "arztleistungen", "medikamente", "therapien",
               "hilfsmittel", "augen_op"]

# ── UX-complexity HYPOTHESIS (per step) ───────────────────────────────────────
# A graded guess at how 'heavy' each screen feels: field count, jargon density,
# decision load, scannability. Fed to the persona so a heavy screen × low
# ux_willingness/comprehension can trigger subconscious effort≫reward / can't-grasp
# disengagement. These grades are tunable hypotheses, NOT funnel targets.
UX_COMPLEXITY: dict[Step, dict] = {
    Step.COVERAGE_TYPE: {"grade": "low", "load": 0.2,
        "note": "two choice cards, one decision, no jargon"},
    Step.INSURED: {"grade": "low", "load": 0.15,
        "note": "single radio choice"},
    Step.PERSONAL_INFO: {"grade": "medium", "load": 0.5,
        "note": "date field (format-strict) + searchable SV dropdown (type-to-filter), inline validation errors"},
    Step.TARIFF_SELECT: {"grade": "high", "load": 0.9,
        "note": "4 tariff columns × 6 coverage rows, dense jargon (refractive eye surgery, Heilbehelfe), advisory-only badges, price comparison — high decision + comprehension load, no 'recommended for you'"},
    Step.ADDON_SELECT: {"grade": "medium", "load": 0.55,
        "note": "~6 optional add-on modules (toggles) each adding €/mo, with footnotes/cross-refs; raises the running price and adds another decision. Survivors of S4 are more determined, but it's another upsell + cost bump"},
    Step.PERSONAL_DATA: {"grade": "high", "load": 0.85,
        "note": "long personal + health questionnaire (many fields) right before the binding step — high effort"},
    Step.PURCHASE: {"grade": "medium", "load": 0.6,
        "note": "S7 closing: the BINDING FINAL price is revealed (may be higher than the S4 estimate after a health loading) + payment method + consents + confirm. The second price wall and the actual conversion moment"},
}


def ux_complexity(step: Step) -> dict:
    return UX_COMPLEXITY.get(step, {"grade": "medium", "load": 0.5, "note": ""})


# S6 health-questionnaire influence on the binding FINAL price: a random 6-10% loading, or
# none (confirmed: the health answers DO move the binding premium). The screen shows the new
# number but gives NO explanation of why / which answer caused it.
HEALTH_SURCHARGE_RANGE = (6.0, 10.0)


def tariff_coverage_brief() -> dict:
    """Compact, REAL coverage facts (Private_Doctor_Tariff_Product_Reference) so the persona
    can reason about whether THEIR specific need is met — and notice there's no way to ask a
    custom coverage question. Grounds content-driven drop-offs (mismatch / package confusion)."""
    return {
        "start_covers": "GP & specialist visits (conventional + alternative medicine), telemedicine, "
            "diagnostics (X-ray/CT/MRI/lab), outpatient surgery (NOT eye laser), preventive checkups, "
            "medications €280/yr, vaccinations. Annual max €1,400.",
        "start_excludes": "physiotherapy, psychotherapy, occupational/speech therapy, osteopathy/massage, "
            "medical aids (Heilbehelfe), glasses/contacts, laser eye surgery.",
        "optimal_adds": "therapies incl. physio & psychotherapy (€560/yr), medical aids + glasses/contacts "
            "+ laser eye surgery, double medications (€560), higher doctor cover (€1,400). Annual max €2,800.",
        "never_covered_any_tariff": "dental / oral surgery, cosmetic procedures, gym memberships, "
            "standalone psychotherapy, strength training, alcohol/substance conditions.",
        "jargon": {"Refraktive Augen-OP": "laser eye surgery", "Heilbehelfe": "medical aids (crutches, braces)",
                   "Schulmedizin": "conventional medicine", "Alternativmedizin": "alternative/complementary medicine"},
        "gotchas": "9-month waiting period for pregnancy/childbirth; premiums can rise ~0–13%/yr; "
            "upgrade Start→Optimal allowed only after 3 years. There is NO interface here to ask a "
            "custom question (e.g. 'is my treatment covered?', 'is my doctor in-network?').",
    }


# ─── Action space ─────────────────────────────────────────────────────────────

class ActionKind:
    SELECT_CARD   = "select_card"     # ChoiceCards
    TYPE_FIELD    = "type_field"      # keystrokes into a text/date field
    OPEN_DROPDOWN = "open_dropdown"
    FILTER_TYPE   = "filter_type"     # keystrokes to filter a searchable dropdown
    SELECT_OPTION = "select_option"   # click a dropdown option
    SELECT_TARIFF = "select_tariff"   # click a tariff column → reveals price
    OPEN_TOOLTIP  = "open_tooltip"    # (i) on a coverage row
    NAV_NEXT      = "nav_next"        # Weiter
    NAV_BACK      = "nav_back"        # Zurück
    SUBMIT        = "submit"


# step → list of (ActionKind, target | None). Closed set per step.
STEP_ACTIONS: dict[Step, list[tuple[str, str | None]]] = {
    Step.COVERAGE_TYPE: [
        (ActionKind.SELECT_CARD, "bei_arztbesuchen"),
        (ActionKind.SELECT_CARD, "im_krankenhaus"),     # → out of scope
        (ActionKind.NAV_NEXT, None),
    ],
    Step.INSURED: [
        (ActionKind.SELECT_CARD, "ich_selbst"),
        (ActionKind.SELECT_CARD, "andere_personen"),    # → out of scope
        (ActionKind.NAV_NEXT, None), (ActionKind.NAV_BACK, None),
    ],
    Step.PERSONAL_INFO: [
        (ActionKind.TYPE_FIELD, "date_of_birth"),
        (ActionKind.OPEN_DROPDOWN, "sv_number"),
        (ActionKind.FILTER_TYPE, "sv_number"),
        (ActionKind.SELECT_OPTION, "sv_number"),
        (ActionKind.NAV_NEXT, None), (ActionKind.NAV_BACK, None),
    ],
    Step.TARIFF_SELECT: [
        *[(ActionKind.SELECT_TARIFF, t["id"]) for t in TARIFFS],
        *[(ActionKind.OPEN_TOOLTIP, r) for r in TARIFF_ROWS],
        (ActionKind.NAV_NEXT, None), (ActionKind.NAV_BACK, None),
    ],
    Step.ADDON_SELECT: [
        *[(ActionKind.SELECT_CARD, a) for a in
          ("fit_fuehlen", "eltern_werden", "mental_wachsen", "akut_versorgt", "baby_option", "vitalplan")],
        (ActionKind.OPEN_TOOLTIP, "addon_info"),
        (ActionKind.NAV_NEXT, None),    # 'Weiter' with no add-on = skip (most common)
        (ActionKind.NAV_BACK, None),
    ],
    Step.PERSONAL_DATA: [
        (ActionKind.TYPE_FIELD, f) for f in
        ("first_name", "last_name", "email", "sv_number", "height", "weight",
         "sport", "doctor", "health_answers")
    ] + [(ActionKind.SUBMIT, None), (ActionKind.NAV_BACK, None)],
    Step.PURCHASE: [
        (ActionKind.OPEN_TOOLTIP, "price_breakdown"),    # why the final price (health loading)
        (ActionKind.SELECT_CARD, "payment_sepa"),
        (ActionKind.SELECT_CARD, "payment_card"),
        (ActionKind.SELECT_CARD, "consent_terms"),
        (ActionKind.SUBMIT, "confirm_purchase"),         # Abschließen → convert
        (ActionKind.NAV_BACK, None),
    ],
}

# Which event types a teacher/persona may legally emit on each step.
def legal_events(step: Step) -> set[str]:
    base = {EventType.STEP_ENTER.value, EventType.IDLE.value, EventType.PAUSE.value,
            EventType.HOVER.value, EventType.MOUSE_MOVE.value, EventType.NAV_BACK.value,
            EventType.FIELD_FOCUS.value, EventType.FIELD_BLUR.value,  # focus/blur on any field
            EventType.SUBMIT.value,                           # 'Weiter' is legal on every step
            EventType.SESSION_GAP.value, EventType.SCROLL.value, EventType.SCROLL_UP.value,
            EventType.TAB_BLUR.value, EventType.TAB_FOCUS.value,  # tab switch away / re-activate
            # rich behavioural repertoire — legal on ANY step (the coach reads these over time)
            EventType.EXIT_INTENT.value, EventType.TEXT_SELECT.value, EventType.COPY.value,
            EventType.EXTERNAL_NAV.value, EventType.COMPARE_RETURN.value, EventType.SLOW_MOUSE.value,
            EventType.RAGE_CLICK.value,
            EventType.ABANDON.value, EventType.CONVERT.value}
    per_step = {
        Step.COVERAGE_TYPE: {EventType.SELECT.value, EventType.TAP.value},
        Step.INSURED:       {EventType.SELECT.value, EventType.TAP.value},
        Step.PERSONAL_INFO: {EventType.KEYSTROKE.value, EventType.FIELD_EDIT.value,
                             EventType.DROPDOWN_OPEN.value, EventType.SELECT.value,
                             EventType.VALIDATION_ERROR.value, EventType.SUBMIT.value, EventType.TAP.value},
        Step.TARIFF_SELECT: {EventType.SELECT.value, EventType.TARIFF_CLICK.value,
                             EventType.PREMIUM_CLICK.value, EventType.PRICE_REVEAL.value,
                             EventType.PRICE_HOVER.value, EventType.TOOLTIP_OPEN.value, EventType.TAP.value},
        Step.ADDON_SELECT:  {EventType.SELECT.value, EventType.TAP.value, EventType.PRICE_REVEAL.value,
                             EventType.PRICE_HOVER.value, EventType.TOOLTIP_OPEN.value},
        Step.PERSONAL_DATA: {EventType.KEYSTROKE.value, EventType.FIELD_EDIT.value,
                             EventType.VALIDATION_ERROR.value, EventType.CANCEL_HOVER.value,
                             EventType.SUBMIT.value, EventType.TAP.value},
        Step.PURCHASE:      {EventType.PRICE_REVEAL.value, EventType.PRICE_HOVER.value,    # S7 final price
                             EventType.CANCEL_HOVER.value, EventType.SELECT.value, EventType.TAP.value,
                             EventType.KEYSTROKE.value, EventType.FIELD_EDIT.value,
                             EventType.TOOLTIP_OPEN.value, EventType.SUBMIT.value},
    }
    return base | per_step.get(step, set())


def tariff_by_id(tid: str) -> dict | None:
    return next((t for t in TARIFFS if t["id"] == tid), None)


def widget_response_model() -> dict:
    """How the STATIC widget reacts to each action — the funnel state machine the LLM
    must reason against, so generated sessions respect real widget responses (what
    advances, what blocks, what reveals a price, what hands off to an advisor).

    This is UI mechanics (the immutable app), NOT a churn/conversion target.
    """
    start, optimal = TARIFF_PRICE_EUR[Tariff.START], TARIFF_PRICE_EUR[Tariff.OPTIMAL]
    return {
        "conversion_definition": (
            "A conversion = ONLINE purchase of Start or Optimal on the "
            "'Bei Arztbesuchen' + 'Ich selbst' path. Advisor handoff or leaving the "
            "page is NOT a conversion."
        ),
        "transitions": {
            "S1_COVERAGE_TYPE": {
                "select bei_arztbesuchen, then Weiter": "advances to S2",
                "select im_krankenhaus": "OUT OF SCOPE → advisor handoff; online session ends, no online purchase",
                "Weiter with nothing selected": "inline validation_error, stays on S1",
            },
            "S2_INSURED_PERSONS": {
                "select ich_selbst, then Weiter": "advances to S3",
                "select andere_personen": "OUT OF SCOPE → advisor handoff",
            },
            "S3_PERSONAL_INFO": {
                "valid DOB + pick Sozialversicherung, then Weiter": "advances to S4 (the price step)",
                "invalid/empty DOB or SV, then Weiter": "inline validation_error, stays on S3",
            },
            "S4_TARIFF_SELECT": {
                "select start": f"reveals Start ≈€{start}/mo (price_reveal; depends on your AGE) and advances to S5 (add-ons)",
                "select optimal": f"reveals Optimal ≈€{optimal}/mo (price_reveal; depends on your AGE) and advances to S5 (add-ons)",
                "click opt_plus or premium": "shows 'Beratung erforderlich' (advisory-only) — does NOT advance; must pick Start/Optimal to finish online",
                "open (i) tooltip on a coverage row": "shows a one-line explanation; stays on S4",
                "Weiter with no tariff selected": "validation_error",
            },
            "S5_ADDON_SELECT": {
                "Weiter with no add-on selected": "advances to S6 (most common — skip the upsell)",
                "toggle an add-on module": "adds its €/mo to the running premium (price_reveal); stays on S5 until Weiter",
                "open (i) on an add-on": "one-line explanation; stays on S5",
            },
            "S6_PERSONAL_DATA": {
                "fill name/email/SV + health answers, then submit": "advances to S7 (the final price / closing). Asks height/weight (friction if not recalled). The long form + the impending binding commitment are the bounce triggers here",
            },
            "S7_PURCHASE": {
                "the final price is revealed": "the BINDING final price/proposal: usually = the S4 provisional, but the S6 health answers MAY add a ~6-10% risk loading so the final is HIGHER (the screen does NOT explain why). A higher-than-expected final is the SECOND price-wall bounce trigger",
                "pick payment + accept consents + Abschließen": "ONLINE PURCHASE → convert",
                "leave at the final price": "abandon (price shock / commitment) — not a conversion",
            },
            "any_step": {
                "close tab / external link / leave": "abandon (not a conversion)",
                "switch browser tab and return": "tab_blur then tab_focus (time away is captured)",
            },
        },
    }


def render_action_space(step: Step) -> dict:
    """JSON-render of the step's action space — fed to the teacher + persona-TLM."""
    return {
        "step": step.value,
        "progress": PROGRESS,
        "actions": [{"kind": k, "target": t} for k, t in STEP_ACTIONS.get(step, [])],
        "legal_event_types": sorted(legal_events(step)),
        **({"tariffs": TARIFFS, "tooltip_rows": TARIFF_ROWS} if step == Step.TARIFF_SELECT else {}),
        **({"sv_options": SV_OPTIONS} if step == Step.PERSONAL_INFO else {}),
    }
