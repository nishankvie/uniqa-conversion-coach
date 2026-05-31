"""A1-probe harness: prompt assembly, schema gate, batch, ε computation."""

import json
import random

from calculator.funnel import Step
from calculator.contracts import EventType
from persona.persona_datagen import (
    build_step_prompt, build_session_prompt, parse_events, OfflineTeacher,
    generate_feed, generate_batch, epsilon_teacher_vs_psyche,
    agent_persona_prompt,
)


# ─── prompt assembly contains the 4 required inputs ───────────────────────────

def test_step_prompt_has_all_inputs():
    atoms = [{"intent": "price_reframe", "phase": "offered"}]
    msgs = build_step_prompt("franz", Step.TARIFF_SELECT, atoms=atoms,
                             coach_reasoning="price dwell high")
    assert msgs[0]["role"] == "system" and "Franz" in msgs[0]["content"]
    user = json.loads(msgs[1]["content"])
    assert "low_res_ui_ascii" in user                 # (a) low-res UI
    assert "json_render_static_ui" in user            # (b) json-render
    assert user["intervention_atoms"] == atoms        # (c) atoms
    assert user["coach_tlm_reasoning"] == "price dwell high"   # (d) reasoning
    # event vocabulary is advertised so the teacher emits our schema
    assert "price_hover" in user["instruction"]


# ─── schema gate ──────────────────────────────────────────────────────────────

def test_parse_events_drops_malformed():
    good = [{"type": "idle", "value": 4.0}, {"type": "abandon"}]
    evs = parse_events(good, Step.TARIFF_SELECT, 0.0)
    assert [e.type for e in evs] == [EventType.IDLE, EventType.ABANDON]

    # unknown type, missing type, junk → all dropped
    bad = [{"type": "teleport"}, {"foo": 1}, "nonsense"]
    assert parse_events(bad, Step.TARIFF_SELECT, 0.0) == []

    # invalid JSON string → []
    assert parse_events("{not json", Step.TARIFF_SELECT, 0.0) == []

    # valid events get the step stamped + monotone timestamps
    seq = parse_events([{"type": "step_enter"}, {"type": "price_hover", "target": "price"}],
                       Step.PERSONAL_DATA, 10.0)
    assert all(e.step == Step.PERSONAL_DATA.value for e in seq)
    assert seq[1].t > seq[0].t


# ─── feed generation ──────────────────────────────────────────────────────────

def test_generate_feed_is_terminal_and_parseable():
    log = generate_feed("franz", OfflineTeacher(), random.Random(1))
    types = {e.type for e in log.events}
    assert EventType.STEP_ENTER in types
    assert (EventType.CONVERT in types) or (EventType.ABANDON in types)
    # all events carry a valid step + known type (schema-clean)
    assert all(isinstance(e.type, EventType) for e in log.events)


# ─── batch + ε ────────────────────────────────────────────────────────────────

def test_batch_and_epsilon():
    logs, stats = generate_batch(200, OfflineTeacher(bias=0.08), seed=0)
    assert len(logs) == 200
    assert stats.teacher == "offline-stub"
    eps = epsilon_teacher_vs_psyche(stats)
    assert 0.0 <= eps["epsilon_mean_abs"] <= 1.0
    assert eps["n_cells"] >= 8                      # 3 personas × ~4 steps
    # every reported cell has teacher/psyche/diff
    for cells in eps["per_cell"].values():
        for c in cells.values():
            assert {"teacher", "psyche", "abs_diff"} <= set(c)


def test_zero_bias_teacher_closer_to_psyche_than_high_bias():
    _, lo = generate_batch(300, OfflineTeacher(bias=0.0), seed=2)
    _, hi = generate_batch(300, OfflineTeacher(bias=0.5), seed=2)
    e_lo = epsilon_teacher_vs_psyche(lo)["epsilon_mean_abs"]
    e_hi = epsilon_teacher_vs_psyche(hi)["epsilon_mean_abs"]
    assert e_lo < e_hi                              # ε tracks teacher disagreement


# ── anti-leakage: the HAND-SCRUBBED prompt files must carry no funnel targets ──
# Guard only (read-only assertion) — scrubbing is done manually in prompts/personas/,
# not by a runtime regex. This fails loudly if a target sneaks back into a file.

def test_agent_prompt_files_have_no_funnel_targets():
    for persona in ("judith", "franz", "peter"):
        sysmsg = agent_persona_prompt(persona).lower()
        assert persona.split()[0] in sysmsg or persona in sysmsg   # real file loaded
        for tok in ("66%", "78%", "drop-off", "drop off", "5.6%", "34% survive"):
            assert tok not in sysmsg, f"{persona}: leaked {tok!r}"


def test_session_prompt_has_thought_rules():
    rules = " ".join(json.loads(build_session_prompt("franz")[1]["content"])["rules"]).lower()
    assert "first event" in rules and "context" in rules     # 1st thought = context
    assert "expectation" in rules                            # price expectation vs reality
