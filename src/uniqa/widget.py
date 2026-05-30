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

from uniqa.funnel import Step
from uniqa.contracts import EventType

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
    Step.PERSONAL_DATA: [
        (ActionKind.TYPE_FIELD, f) for f in
        ("first_name", "last_name", "email", "sv_number", "height", "weight",
         "sport", "doctor", "health_answers")
    ] + [(ActionKind.SUBMIT, None), (ActionKind.NAV_BACK, None)],
}

# Which event types a teacher/persona may legally emit on each step.
def legal_events(step: Step) -> set[str]:
    base = {EventType.STEP_ENTER.value, EventType.IDLE.value, EventType.PAUSE.value,
            EventType.HOVER.value, EventType.MOUSE_MOVE.value, EventType.NAV_BACK.value,
            EventType.SESSION_GAP.value,                      # tab-away / returned after a pause
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
        Step.PERSONAL_DATA: {EventType.KEYSTROKE.value, EventType.FIELD_EDIT.value,
                             EventType.VALIDATION_ERROR.value, EventType.CANCEL_HOVER.value,
                             EventType.SUBMIT.value, EventType.TAP.value,
                             EventType.PRICE_REVEAL.value},   # S7 final-price reveal
    }
    return base | per_step.get(step, set())


def tariff_by_id(tid: str) -> dict | None:
    return next((t for t in TARIFFS if t["id"] == tid), None)


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
