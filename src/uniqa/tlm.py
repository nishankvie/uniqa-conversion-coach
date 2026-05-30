"""
TLM — Trajectory Language Model token space.

A TLM is a small autoregressive model over JOURNEY TOKENS (not natural language).
A journey is serialised the way Decision/Trajectory Transformers serialise RL
trajectories: discretise everything into a small vocabulary and predict the next
token. Two heads share one vocab:

  • Persona-TLM:  predicts the next USER token (behaviour) given history + persona tag
                  → a learned stand-in for the prompt-driven LLM persona.
  • Coach-TLM:    predicts the next COACH token (action / NO_ACTION) given the
                  user-token history → the trainable policy.

Vocabulary (small, ~120 tokens) =
    special      : PAD BOS EOS SEP
    persona tags : <persona:judith|franz|peter|unknown>
    step markers : <step:S0..S7>
    event types  : every EventType, as <ev:...>
    targets      : a closed set of element ids, <tgt:...>
    buckets      : discretised continuous values  <dwell:b> <hover:b> <dt:b>
    coach        : <coach:none|price_reframe|...>  (action tokens)

`encode()` turns an ActivityLog (+ optional persona / coach actions) into ids;
`decode()` inverts. Sequences are short (≤ a few hundred tokens), so a tiny GPT
is enough — see docs/deferred/TLM_RESEARCH.md for the feasibility math.
"""

from __future__ import annotations

from dataclasses import dataclass

from uniqa.contracts import Event, EventType, ActivityLog
from uniqa.funnel import Step
from uniqa.coach import CoachAction


# ─── discretisation buckets (continuous → token) ──────────────────────────────

DWELL_EDGES = [1, 3, 6, 10, 15, 25, 45]      # seconds
COUNT_EDGES = [1, 2, 3, 5, 8]                # hover / edit counts
DT_EDGES    = [0.3, 1, 2, 5, 10, 30]         # inter-event delta seconds


def _bucket(x: float, edges: list[float]) -> int:
    b = 0
    for e in edges:
        if x >= e:
            b += 1
        else:
            break
    return b   # 0..len(edges)


# ─── closed target vocabulary (extend as the app grows) ───────────────────────

TARGETS = [
    "none", "price", "premium_tariff", "start_tariff", "optimal_tariff",
    "sv_number", "dob", "email", "cancel", "cta", "addon", "field",
]


# ─── Vocab ────────────────────────────────────────────────────────────────────

class TLMVocab:
    def __init__(self):
        toks: list[str] = ["<pad>", "<bos>", "<eos>", "<sep>"]
        toks += [f"<persona:{p}>" for p in ("judith", "franz", "peter", "unknown")]
        toks += [f"<step:{s.value}>" for s in Step]
        toks += [f"<ev:{e.value}>" for e in EventType]
        toks += [f"<tgt:{t}>" for t in TARGETS]
        toks += [f"<dwell:{i}>" for i in range(len(DWELL_EDGES) + 1)]
        toks += [f"<count:{i}>" for i in range(len(COUNT_EDGES) + 1)]
        toks += [f"<dt:{i}>"    for i in range(len(DT_EDGES) + 1)]
        toks += [f"<coach:{a.value}>" for a in CoachAction]
        self.itos = toks
        self.stoi = {t: i for i, t in enumerate(toks)}

    def __len__(self) -> int:
        return len(self.itos)

    def id(self, tok: str) -> int:
        return self.stoi[tok]

    def tok(self, i: int) -> str:
        return self.itos[i]


VOCAB = TLMVocab()


# ─── encode / decode ──────────────────────────────────────────────────────────

def _event_tokens(ev: Event, prev_t: float) -> list[str]:
    toks = [f"<ev:{ev.type.value}>"]
    tgt = ev.target if ev.target in TARGETS else ("field" if ev.target else "none")
    toks.append(f"<tgt:{tgt}>")
    # delta-time bucket since previous event
    dt = max(0.0, ev.t - prev_t)
    toks.append(f"<dt:{_bucket(dt, DT_EDGES)}>")
    # value bucket: dwell-like vs count-like
    if ev.type in (EventType.IDLE, EventType.PAUSE) and isinstance(ev.value, (int, float)):
        toks.append(f"<dwell:{_bucket(ev.value, DWELL_EDGES)}>")
    elif isinstance(ev.value, (int, float)) and not isinstance(ev.value, bool):
        toks.append(f"<count:{_bucket(ev.value, COUNT_EDGES)}>")
    return toks


def encode(log: ActivityLog, persona: str | None = None,
           coach_actions: dict[int, str] | None = None) -> list[int]:
    """
    Serialise a journey to token ids.

    persona: optional tag the Persona-TLM is conditioned on (None → 'unknown').
    coach_actions: optional {event_index: CoachAction.value} to interleave coach
                   tokens after the event at that index (for Coach-TLM training).
    """
    seq: list[str] = ["<bos>", f"<persona:{persona or 'unknown'}>"]
    cur_step = None
    prev_t = log.events[0].t if log.events else 0.0
    for idx, ev in enumerate(log.events):
        if ev.step != cur_step:
            seq.append(f"<step:{ev.step}>")
            cur_step = ev.step
        seq += _event_tokens(ev, prev_t)
        prev_t = ev.t
        if coach_actions and idx in coach_actions:
            seq.append("<sep>")
            seq.append(f"<coach:{coach_actions[idx]}>")
    seq.append("<eos>")
    return [VOCAB.id(t) for t in seq]


def decode(ids: list[int]) -> list[str]:
    return [VOCAB.tok(i) for i in ids]


@dataclass
class TLMConfig:
    """Reference config for the tiny TLM (see docs/deferred/TLM_RESEARCH.md)."""
    vocab_size: int = len(VOCAB)
    n_layer:    int = 4
    n_head:     int = 4
    n_embd:     int = 128
    block_size: int = 512        # max journey length in tokens

    @property
    def approx_params(self) -> int:
        # ~ 12 * n_layer * n_embd^2  + vocab*n_embd (rough GPT param count)
        return 12 * self.n_layer * self.n_embd ** 2 + self.vocab_size * self.n_embd
