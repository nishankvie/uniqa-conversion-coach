"""Human capture stays in the persona-bot event vocabulary (format parity).

No 'collapse' step: a captured human ActivityLog is, by construction, the same
decision-level schema a persona bot emits — every event passes legal_events(step).
"""

import pytest

from calculator.capture import SessionRecorder
from calculator.contracts import EventType
from calculator.funnel import Step
from calculator.widget import legal_events

_STEP = {s.value: s for s in Step}


def test_recorded_session_is_bot_legal():
    rec = SessionRecorder(persona_hint="franz")
    rec.enter(Step.COVERAGE_TYPE.value)
    rec.select(Step.COVERAGE_TYPE.value, "bei_arztbesuchen")
    rec.enter(Step.PERSONAL_INFO.value)
    rec.keystrokes(Step.PERSONAL_INFO.value, "date_of_birth", 10)
    rec.select(Step.PERSONAL_INFO.value, "sv_number", value="ÖGK")
    rec.enter(Step.TARIFF_SELECT.value)
    rec.price_reveal(Step.TARIFF_SELECT.value, "optimal", 68.14)
    rec.select(Step.TARIFF_SELECT.value, "optimal")
    rec.enter(Step.PERSONAL_DATA.value)
    rec.price_reveal(Step.PERSONAL_DATA.value, "optimal_final", 68.14)  # S7 final price
    rec.convert(Step.PURCHASE.value)

    # every event is in the bot's per-step legal vocabulary — no collapse needed
    for e in rec.log.events:
        s = _STEP.get(e.step)
        if s in (Step.START, Step.PURCHASE):
            continue
        assert e.type.value in legal_events(s), f"{e.type.value} illegal on {e.step}"

    # timestamps are real + monotone
    ts = [e.t for e in rec.log.events]
    assert ts == sorted(ts)


def test_illegal_event_is_rejected():
    rec = SessionRecorder()
    with pytest.raises(ValueError, match="not a legal bot event"):
        rec.record(EventType.TARIFF_CLICK, Step.INSURED.value)  # tariff_click illegal on S2
