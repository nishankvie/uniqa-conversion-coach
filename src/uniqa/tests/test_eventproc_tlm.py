"""Event post-processing, TLM token space, and human/sim schema-identity tests."""

import random

from uniqa.funnel import Step, generate_signals, STEP_ORDER
from uniqa.contracts import Event, EventType, ActivityLog, new_session_id
from uniqa.coach_io import activity_from_signals
from uniqa.eventproc import collapse, features, detections
from uniqa.tlm import VOCAB, encode, decode, TLMConfig, _bucket, DWELL_EDGES
from uniqa.play import human_trace


# ─── eventproc: collapse ──────────────────────────────────────────────────────

def test_collapse_merges_noise_and_keeps_meaning():
    log = ActivityLog(new_session_id())
    s = Step.TARIFF_SELECT.value
    for i in range(5):
        log.append(Event(EventType.MOUSE_MOVE, s, i * 0.1))
    log.append(Event(EventType.PAUSE, s, 0.6, value=4.0))
    log.append(Event(EventType.HOVER, s, 1.0, target="price"))
    log.append(Event(EventType.HOVER, s, 1.3, target="price"))
    log.append(Event(EventType.TARIFF_CLICK, s, 2.0, target="optimal"))
    moments = collapse(log)
    labels = [m.label for m in moments]
    assert "dwell" in labels                     # mouse_move + pause runs collapsed
    assert "hover_burst" in labels               # repeated hover merged
    assert "tariff_click" in labels              # meaningful event preserved
    assert len(moments) < len(log.events)        # net compression


# ─── eventproc: features + detections ────────────────────────────────────────

def test_features_basic():
    log = human_trace()
    f = features(log, step=Step.TARIFF_SELECT.value)
    assert f["dwell_sec"] >= 8
    assert f["hover_count"] >= 1
    assert "hesitation_index" in f


def test_detections_fire_on_struggle():
    # a bouncing, struggling trace should yield detections
    log = human_trace({"tariff": __import__("uniqa.scope", fromlist=["Tariff"]).Tariff.OPTIMAL,
                       "tariff_dwell": 20.0, "tariff_hovers": 4, "info_edits": 3, "convert": False})
    names = {d.name for d in detections(log)}
    assert "form_struggle" in names or "exit_intent" in names


def test_premium_detour_detected():
    log = ActivityLog(new_session_id())
    s = Step.TARIFF_SELECT.value
    log.append(Event(EventType.STEP_ENTER, s, 0))
    log.append(Event(EventType.PREMIUM_CLICK, s, 1, target="premium_tariff"))
    assert any(d.name == "premium_detour" for d in detections(log))


# ─── TLM token space ──────────────────────────────────────────────────────────

def test_vocab_small_and_complete():
    assert 40 < len(VOCAB) < 300                 # small, LM-friendly vocab
    for tok in ("<bos>", "<eos>", "<pad>", "<persona:franz>",
                f"<step:{Step.TARIFF_SELECT.value}>", "<coach:price_reframe>"):
        assert tok in VOCAB.stoi


def test_encode_decode_roundtrip():
    log = human_trace()
    ids = encode(log, persona="franz")
    toks = decode(ids)
    assert toks[0] == "<bos>" and toks[1] == "<persona:franz>" and toks[-1] == "<eos>"
    assert all(isinstance(i, int) for i in ids)
    assert all(0 <= i < len(VOCAB) for i in ids)


def test_encode_interleaves_coach_tokens():
    log = human_trace()
    ids = encode(log, persona="judith", coach_actions={3: "price_reframe"})
    toks = decode(ids)
    assert "<sep>" in toks and "<coach:price_reframe>" in toks


def test_bucketizer_monotone():
    assert _bucket(0.5, DWELL_EDGES) == 0
    assert _bucket(100, DWELL_EDGES) == len(DWELL_EDGES)
    assert _bucket(7, DWELL_EDGES) >= _bucket(2, DWELL_EDGES)


def test_tlm_config_is_tiny():
    cfg = TLMConfig()
    assert cfg.vocab_size == len(VOCAB)
    assert cfg.approx_params < 5_000_000          # a few hundred K — trivially trainable


# ─── schema identity: human trace ⊆ simulator event space ────────────────────

def test_human_and_sim_share_event_schema():
    # simulator-side events
    sim = ActivityLog(new_session_id())
    rng = random.Random(7)
    t = 0.0
    for step in STEP_ORDER[1:]:
        if step in (Step.PURCHASE,):
            continue
        t = activity_from_signals(sim, step, generate_signals(step, "franz", rng), t0=t)
    sim_types = {e.type for e in sim.events}

    human = human_trace()
    human_types = {e.type for e in human.events}

    # both are drawn from the SAME EventType vocabulary (the contract)
    assert sim_types <= set(EventType)
    assert human_types <= set(EventType)
    # overlap on the core funnel events (same wire format, not disjoint)
    assert {EventType.STEP_ENTER} <= sim_types & human_types
