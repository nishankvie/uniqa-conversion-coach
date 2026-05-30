"""Schema-identity + TLM token roundtrip.

The deep eventproc (collapse/features/detections) and TLM-config tests were
dropped as deferred (tlm.py / eventproc.py are the deferred trajectory-token path,
see docs/deferred/). Kept here: the contract guard that the human trace and the
simulator share one EventType vocabulary, plus a single TLM encode/decode roundtrip.
"""

import random

from uniqa.funnel import Step, generate_signals, STEP_ORDER
from uniqa.contracts import EventType, ActivityLog, new_session_id
from uniqa.coach_io import activity_from_signals
from uniqa.tlm import VOCAB, encode, decode
from uniqa.play import human_trace


def test_encode_decode_roundtrip():
    log = human_trace()
    ids = encode(log, persona="franz")
    toks = decode(ids)
    assert toks[0] == "<bos>" and toks[1] == "<persona:franz>" and toks[-1] == "<eos>"
    assert all(isinstance(i, int) for i in ids)
    assert all(0 <= i < len(VOCAB) for i in ids)


def test_human_and_sim_share_event_schema():
    """Human trace and simulator draw from the SAME EventType vocabulary (the contract)."""
    sim = ActivityLog(new_session_id())
    rng = random.Random(7)
    t = 0.0
    for step in STEP_ORDER[1:]:
        if step in (Step.PURCHASE,):
            continue
        t = activity_from_signals(sim, step, generate_signals(step, "franz", rng), t0=t)
    sim_types = {e.type for e in sim.events}
    human_types = {e.type for e in human_trace().events}

    assert sim_types <= set(EventType)
    assert human_types <= set(EventType)
    assert {EventType.STEP_ENTER} <= sim_types & human_types
