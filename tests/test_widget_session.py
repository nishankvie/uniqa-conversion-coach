"""Widget twin action-space, whole-session generation, UX cost + engagement."""

import json

from calculator.funnel import Step
from calculator.contracts import Event, EventType, ActivityLog, new_session_id
from calculator.widget import STEP_ACTIONS, legal_events, render_action_space, tariff_by_id
from calculator.eventproc import ux_cost, engagement
from persona.persona_datagen import build_session_prompt, parse_session


def test_each_step_has_action_space_and_legal_events():
    for step in (Step.COVERAGE_TYPE, Step.INSURED, Step.PERSONAL_INFO,
                 Step.TARIFF_SELECT, Step.PERSONAL_DATA):
        assert STEP_ACTIONS[step]
        le = legal_events(step)
        assert EventType.STEP_ENTER.value in le and EventType.ABANDON.value in le


def test_tariff_step_exposes_select_and_tooltip_and_prices():
    spec = render_action_space(Step.TARIFF_SELECT)
    kinds = {a["kind"] for a in spec["actions"]}
    assert "select_tariff" in kinds and "open_tooltip" in kinds
    assert {t["id"] for t in spec["tariffs"]} == {"start", "optimal", "opt_plus", "premium"}
    assert tariff_by_id("optimal")["price_eur"] == 68.14
    assert tariff_by_id("premium")["online"] is False


def test_personal_info_exposes_searchable_sv_dropdown():
    spec = render_action_space(Step.PERSONAL_INFO)
    assert "ÖGK" in spec["sv_options"]
    le = legal_events(Step.PERSONAL_INFO)
    assert {EventType.KEYSTROKE.value, EventType.DROPDOWN_OPEN.value,
            EventType.SELECT.value, EventType.VALIDATION_ERROR.value} <= le


def test_session_prompt_embeds_widget_twin():
    msgs = build_session_prompt("franz")
    user = json.loads(msgs[1]["content"])
    assert "widget" in user
    assert Step.TARIFF_SELECT.value in user["widget"]
    w = user["widget"][Step.TARIFF_SELECT.value]
    assert "ui_ascii" in w and "action_space" in w
    rules = " ".join(user["rules"]).lower()
    assert "keystroke" in rules and "timestamp" in rules and "advisor" in rules


def test_parse_session_gates_illegal_events_and_keeps_timing_and_thought():
    raw = {"events": [
        {"step": "S4_TARIFF_SELECT", "type": "step_enter", "t": 0.0},
        {"step": "S4_TARIFF_SELECT", "type": "select", "target": "optimal", "t": 3.0, "thought": "optimal fits"},
        {"step": "S4_TARIFF_SELECT", "type": "keystroke", "t": 4.0},   # ILLEGAL on tariff step → dropped
        {"step": "S4_TARIFF_SELECT", "type": "teleport", "t": 5.0},    # unknown type → dropped
        {"step": "S7_PURCHASE", "type": "convert", "t": 9.0, "thought": "done"},
    ]}
    evs = parse_session(raw)
    types = [e.type for e in evs]
    assert EventType.KEYSTROKE not in types
    assert EventType.SELECT in types and EventType.CONVERT in types
    sel = next(e for e in evs if e.type is EventType.SELECT)
    assert sel.t == 3.0 and sel.thought == "optimal fits"
    assert [e.t for e in evs] == sorted(e.t for e in evs)
    # unknown step / bad json → empty
    assert parse_session({"events": [{"step": "S99", "type": "tap", "t": 1}]}) == []
    assert parse_session("{not json") == []


def test_ux_cost_sums_keystrokes_and_taps():
    log = ActivityLog(new_session_id())
    s = Step.PERSONAL_DATA.value
    log.append(Event(EventType.KEYSTROKE, s, 0, target="email", value=22))
    log.append(Event(EventType.KEYSTROKE, s, 1, target="first_name", value=6))
    log.append(Event(EventType.TAP, s, 2, target="submit", value=1))
    c = ux_cost(log, step=s)
    assert c["keystrokes"] == 28 and c["taps"] == 1 and c["total"] == 29
    assert c["by_field"]["email"] == 22


def test_engagement_labels_from_timing():
    r = ActivityLog(new_session_id()); s = Step.TARIFF_SELECT.value
    r.append(Event(EventType.STEP_ENTER, s, 0.0))
    r.append(Event(EventType.PRICE_REVEAL, s, 1.0, target="optimal", value=68.14))
    r.append(Event(EventType.SELECT, s, 2.0, target="optimal"))
    r.append(Event(EventType.TARIFF_CLICK, s, 3.5, target="optimal"))
    assert engagement(r)["label"] in ("reactive", "engaged")

    d = ActivityLog(new_session_id())
    d.append(Event(EventType.STEP_ENTER, s, 0.0))
    d.append(Event(EventType.SELECT, s, 2.0, target="optimal"))
    d.append(Event(EventType.SESSION_GAP, s, 5.0, value=True))
    d.append(Event(EventType.TARIFF_CLICK, s, 120.0, target="optimal"))
    assert engagement(d)["label"] == "distracted"
