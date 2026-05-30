"""
UNIQA Coach — system contracts (JSON-render backbone).

Two components, one wire format:

  ┌─────────────────────────────┐         activity log (events)        ┌──────────┐
  │  APP  (IMMUTABLE)           │ ───────────────────────────────────▶ │  COACH   │
  │  11-step form + renderer    │                                      │ (MUTABLE,│
  │  emits Events, executes      │ ◀─────────────────────────────────── │  trained)│
  │  Effector commands           │        effector commands + reasoning  └──────────┘
  └─────────────────────────────┘

The APP is a fixed surface: it renders screens, emits a user **activity log**, and
executes a fixed set of **effector commands**. It never changes during research.

The COACH is the only thing we train. Contract:
    observe(ActivityLog) ──▶ CoachDecision { effector cmd | NO_ACTION,
                                             human-readable reasoning,
                                             testable hypotheses }

Everything here is JSON-serialisable. The Streamlit demo and a future React app are
just two renderers of the SAME envelopes. Prove it in simulation now; swap the
renderer later — zero contract change.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional

SCHEMA_VERSION = "1.0"


# ════════════════════════════════════════════════════════════════════════════
#  1. ACTIVITY LOG  — what the APP emits, the COACH's input
# ════════════════════════════════════════════════════════════════════════════

class EventType(Enum):
    STEP_ENTER     = "step_enter"
    MOUSE_MOVE     = "mouse_move"        # low-level; collapsed by eventproc
    HOVER          = "hover"             # cursor dwell over an element
    PAUSE          = "pause"             # no input for a while (micro)
    FIELD_FOCUS    = "field_focus"
    FIELD_BLUR     = "field_blur"
    FIELD_EDIT     = "field_edit"
    FIELD_INVALID  = "field_invalid"
    PRICE_HOVER    = "price_hover"
    TARIFF_CLICK   = "tariff_click"
    PREMIUM_CLICK  = "premium_click"     # clicked an advisory-only tariff
    NAV_BACK       = "nav_back"
    SCROLL         = "scroll"
    IDLE           = "idle"              # dwell with no input
    SESSION_GAP    = "session_gap"       # returned after a long pause
    CANCEL_HOVER   = "cancel_hover"
    WIDGET_SHOWN   = "widget_shown"      # coach-originated, echoed back
    WIDGET_CTA     = "widget_cta"        # user clicked the widget CTA
    WIDGET_DISMISS = "widget_dismiss"
    SUBMIT         = "submit"
    ABANDON        = "abandon"           # terminal
    CONVERT        = "convert"           # terminal (online purchase)


@dataclass
class Event:
    """One atomic, timestamped thing that happened in the APP."""
    type:   EventType
    step:   str                       # Step.value
    t:      float = 0.0               # seconds since session start
    target: Optional[str] = None      # field id / tariff id / element id
    value:  Any = None
    source: str = "user"              # "user" | "app" | "coach"

    def to_dict(self) -> dict:
        return {"type": self.type.value, "step": self.step, "t": round(self.t, 2),
                "target": self.target, "value": self.value, "source": self.source}


@dataclass
class ActivityLog:
    """Append-only event stream. The COACH reads a window of this."""
    session_id: str
    events: list[Event] = field(default_factory=list)

    def append(self, ev: Event) -> None:
        self.events.append(ev)

    def window(self, step: Optional[str] = None, last_n: Optional[int] = None) -> list[Event]:
        evs = [e for e in self.events if step is None or e.step == step]
        return evs[-last_n:] if last_n else evs

    def to_dict(self) -> dict:
        return {"schema": SCHEMA_VERSION, "session_id": self.session_id,
                "events": [e.to_dict() for e in self.events]}


# ════════════════════════════════════════════════════════════════════════════
#  2. EFFECTORS  — the APP's fixed capability surface, what the COACH may do
# ════════════════════════════════════════════════════════════════════════════

class Effector(Enum):
    """Mechanical capabilities the immutable APP exposes to the Coach."""
    NO_ACTION        = "no_action"        # the most important one
    SHOW_WIDGET      = "show_widget"      # overlay a coach card (payload = intent + copy)
    FOCUS_FIELD      = "focus_field"      # move focus to a field
    SCROLL_TO        = "scroll_to"        # scroll viewport to an element
    HIGHLIGHT        = "highlight"        # visually emphasise an element
    AUTOFILL         = "autofill"         # fill a field with the user's known/derived value
    FILL_SAMPLE      = "fill_sample"      # fill placeholder data so user can click through to explore
    PRESELECT_TARIFF = "preselect_tariff" # pre-select Start/Optimal (online-completable)
    SAVE_PROGRESS    = "save_progress"    # capture email → resume-later / channel handoff


# Effectors that are passive (never mutate the user's real data or screen content).
PASSIVE_EFFECTORS = {Effector.NO_ACTION, Effector.SCROLL_TO,
                     Effector.HIGHLIGHT, Effector.FOCUS_FIELD}

# AUTOFILL/FILL_SAMPLE guardrails: never autofill identity/health/legal-consent fields.
NEVER_AUTOFILL = {"sv_number", "first_name", "last_name", "email",
                  "health_answers", "date_of_birth", "consent"}
# Fields the coach MAY sample-fill to let a user click through and explore the flow.
SAMPLE_FILLABLE = {"coverage", "insured", "tariff"}


@dataclass
class EffectorCommand:
    """A single command the COACH issues; the APP executes it verbatim."""
    effector: Effector
    step:     str
    target:   Optional[str] = None        # field/element/tariff id
    payload:  dict = field(default_factory=dict)   # e.g. widget intent + copy
    render:   dict = field(default_factory=dict)   # JSON-render spec for the frontend

    def to_dict(self) -> dict:
        return {"effector": self.effector.value, "step": self.step,
                "target": self.target, "payload": self.payload, "render": self.render}

    def validate(self) -> None:
        """Guardrails the APP enforces regardless of what the coach asked for."""
        if self.effector in (Effector.AUTOFILL,) and self.target in NEVER_AUTOFILL:
            raise ValueError(f"AUTOFILL forbidden on protected field '{self.target}'")
        if self.effector is Effector.FILL_SAMPLE and self.target not in SAMPLE_FILLABLE:
            raise ValueError(f"FILL_SAMPLE only allowed on {SAMPLE_FILLABLE}, not '{self.target}'")


# ════════════════════════════════════════════════════════════════════════════
#  3. HYPOTHESES  — the COACH's testable beliefs about the user
# ════════════════════════════════════════════════════════════════════════════

class HypoStatus(Enum):
    OPEN      = "open"
    CONFIRMED = "confirmed"
    REFUTED   = "refuted"


@dataclass
class Hypothesis:
    """
    A falsifiable belief the coach holds, with a prediction that future events
    confirm or refute. This is the bridge that lets us SCORE the coach's model of
    the user and re-fit persona models against reality.
    """
    id:        str
    claim:     str                  # human-readable: "user is price-shocked"
    latent:    str                  # which psyche axis: "price_readiness"
    p:         float                # coach's probability the claim is true
    predicts:  EventType            # the event expected if the claim holds & we DON'T act
    counters:  str                  # CoachAction.value that would address it
    status:    HypoStatus = HypoStatus.OPEN

    def evaluate(self, subsequent: list[Event]) -> HypoStatus:
        """Confirm if the predicted event occurred; refute if the user converted instead."""
        kinds = {e.type for e in subsequent}
        if self.predicts in kinds or EventType.ABANDON in kinds:
            self.status = HypoStatus.CONFIRMED
        elif EventType.CONVERT in kinds or EventType.WIDGET_CTA in kinds:
            self.status = HypoStatus.REFUTED
        return self.status

    def to_dict(self) -> dict:
        return {"id": self.id, "claim": self.claim, "latent": self.latent,
                "p": round(self.p, 3), "predicts": self.predicts.value,
                "counters": self.counters, "status": self.status.value}


# ════════════════════════════════════════════════════════════════════════════
#  4. COACH I/O  — observation in, decision out
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class CoachObservation:
    """Everything the coach is allowed to see. NO ground-truth latent state."""
    session_id:       str
    step:             str
    activity:         list[dict]            # ActivityLog.window() as dicts
    form_state:       dict                  # which fields filled/valid (no values)
    budget_remaining: int                   # interventions left (annoyance ceiling)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CoachDecision:
    """
    The trained Coach's output. The action token is what we optimise; the reasoning
    is mandatory and human-readable; hypotheses make the belief auditable + scorable.
    """
    command:    EffectorCommand
    reasoning:  str                          # MANDATORY, human-readable
    hypotheses: list[Hypothesis] = field(default_factory=list)
    confidence: float = 0.0
    value_estimate: float = 0.0              # coach's predicted P(convert | act)

    def is_action(self) -> bool:
        return self.command.effector is not Effector.NO_ACTION

    def to_dict(self) -> dict:
        return {
            "schema": SCHEMA_VERSION,
            "command": self.command.to_dict(),
            "reasoning": self.reasoning,
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "confidence": round(self.confidence, 3),
            "value_estimate": round(self.value_estimate, 3),
        }


# ════════════════════════════════════════════════════════════════════════════
#  5. RENDER ENVELOPE  — one frontend message format (drives ANY renderer)
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class RenderEnvelope:
    """
    The single message the frontend consumes. Streamlit renders it today; a React
    app renders the same JSON tomorrow. `kind` selects the component.
    """
    kind:    str                    # "step_screen" | "coach_widget" | "effector" | "outcome"
    step:    str
    spec:    dict = field(default_factory=dict)
    hud:     Optional[dict] = None  # optional mind readout (demo only)

    def to_dict(self) -> dict:
        d = {"schema": SCHEMA_VERSION, "kind": self.kind, "step": self.step, "spec": self.spec}
        if self.hud is not None:
            d["hud"] = self.hud
        return d


def new_session_id() -> str:
    return f"sess_{int(time.time()*1000)}"
