"""
UNIQA — event-log post-processing.

Raw activity logs are noisy (mouse moves, micro-pauses, repeated hovers). This
module turns the raw stream into things humans and models can use:

  collapse(log)    → drop noise, merge micro-events into meaningful MOMENTS
  features(log,..) → numeric feature vector (dwell, hover bursts, churn, …)
  detections(log)  → named, timestamped "moments" (price_shock_dwell, premium_detour…)

The collapsed moments + detections are what the demo DISPLAYS and what the coach /
persona TLM consume as a compact, information-dense sequence (vs. raw mouse spam).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import Counter

from calculator.contracts import Event, EventType, ActivityLog
from calculator.funnel import Step

# events considered low-level noise unless they form a burst
_NOISE = {EventType.MOUSE_MOVE, EventType.PAUSE}


# ─── Collapse ─────────────────────────────────────────────────────────────────

@dataclass
class Moment:
    """A collapsed, meaningful unit of the journey (what we display)."""
    label:  str
    step:   str
    t0:     float
    t1:     float
    detail: dict = field(default_factory=dict)

    @property
    def duration(self) -> float:
        return round(self.t1 - self.t0, 2)

    def to_dict(self) -> dict:
        return {"label": self.label, "step": self.step, "t0": round(self.t0, 2),
                "t1": round(self.t1, 2), "duration": self.duration, "detail": self.detail}


def collapse(log: ActivityLog) -> list[Moment]:
    """
    Compress the raw event stream into Moments:
      • runs of mouse_move/pause → a single 'dwell' moment (with total seconds)
      • repeated hover on same target → one 'hover_burst' moment (with count)
      • meaningful events (clicks, edits, nav, premium, gaps, terminals) → kept 1:1
    """
    moments: list[Moment] = []
    i, evs = 0, log.events
    n = len(evs)
    while i < n:
        e = evs[i]
        # collapse a run of noise into one dwell moment
        if e.type in _NOISE:
            j = i
            while j < n and evs[j].type in _NOISE and evs[j].step == e.step:
                j += 1
            secs = sum((evs[k].value or 0) for k in range(i, j) if isinstance(evs[k].value, (int, float)))
            moments.append(Moment("dwell", e.step, e.t, evs[j-1].t, {"seconds": round(secs, 1)}))
            i = j
            continue
        # collapse repeated hover on the same target
        if e.type == EventType.HOVER:
            j = i
            while j < n and evs[j].type == EventType.HOVER and evs[j].target == e.target and evs[j].step == e.step:
                j += 1
            if j - i >= 2:
                moments.append(Moment("hover_burst", e.step, e.t, evs[j-1].t,
                                      {"target": e.target, "count": j - i}))
                i = j
                continue
        # keep meaningful event as its own moment
        moments.append(Moment(e.type.value, e.step, e.t, e.t, {"target": e.target, "value": e.value}))
        i += 1
    return moments


# ─── Features ─────────────────────────────────────────────────────────────────

def features(log: ActivityLog, step: str | None = None) -> dict:
    """Derived numeric features over the (optionally step-scoped) log window."""
    evs = log.window(step=step)
    kinds = Counter(e.type for e in evs)
    times = [e.t for e in evs]
    span = (max(times) - min(times)) if len(times) >= 2 else 0.0

    dwell = sum((e.value or 0) for e in evs
                if e.type in (EventType.IDLE, EventType.PAUSE) and isinstance(e.value, (int, float)))
    interact = sum(kinds[k] for k in (EventType.FIELD_EDIT, EventType.TARIFF_CLICK,
                                      EventType.WIDGET_CTA, EventType.SUBMIT))
    # time to first real interaction
    ttfi = 0.0
    t0 = times[0] if times else 0.0
    for e in evs:
        if e.type in (EventType.FIELD_EDIT, EventType.TARIFF_CLICK, EventType.SUBMIT):
            ttfi = round(e.t - t0, 2); break

    hover = kinds[EventType.HOVER] + kinds[EventType.PRICE_HOVER]
    backtrack = kinds[EventType.NAV_BACK]
    churn = kinds[EventType.FIELD_EDIT]
    # hesitation index: dwell + hover + backtracking, normalised against interaction
    hesitation = round((dwell / 10.0) + 0.5 * hover + 1.0 * backtrack + 0.5 * churn - interact, 2)

    return {
        "n_events": len(evs),
        "span_sec": round(span, 1),
        "dwell_sec": round(float(dwell), 1),
        "idle_ratio": round(float(dwell) / span, 2) if span else 0.0,
        "hover_count": hover,
        "backtrack_count": backtrack,
        "edit_churn": churn,
        "interactions": interact,
        "time_to_first_interaction": ttfi,
        "premium_detour": kinds[EventType.PREMIUM_CLICK] > 0,
        "cancel_hover": kinds[EventType.CANCEL_HOVER],
        "session_gap": kinds[EventType.SESSION_GAP] > 0,
        "hesitation_index": hesitation,
    }


# ─── Detections (named moments worth surfacing / coaching on) ─────────────────

@dataclass
class Detection:
    name:   str
    step:   str
    t:      float
    score:  float       # 0..1 salience
    note:   str

    def to_dict(self) -> dict:
        return {"name": self.name, "step": self.step, "t": round(self.t, 2),
                "score": round(self.score, 2), "note": self.note}


def detections(log: ActivityLog) -> list[Detection]:
    """Extract the meaningful, displayable detections from the raw log."""
    out: list[Detection] = []
    by_step: dict[str, list[Event]] = {}
    for e in log.events:
        by_step.setdefault(e.step, []).append(e)

    for step, evs in by_step.items():
        f = features(_sublog(log, evs), step=step)
        t_step = evs[0].t if evs else 0.0
        if f["premium_detour"]:
            out.append(Detection("premium_detour", step, t_step, 0.8,
                                  "clicked an advisory-only tariff → confusion"))
        if step == Step.TARIFF_SELECT.value and f["dwell_sec"] >= 8 and f["interactions"] == 0:
            out.append(Detection("price_shock_dwell", step, t_step, 0.7,
                                  f"{f['dwell_sec']}s on the price with no action"))
        if f["edit_churn"] >= 2:
            out.append(Detection("form_struggle", step, t_step, 0.6,
                                  f"{f['edit_churn']} field re-edits"))
        if f["cancel_hover"] >= 2:
            out.append(Detection("exit_intent", step, t_step, 0.72,
                                  f"{f['cancel_hover']} hovers near cancel/close"))
        if f["session_gap"]:
            out.append(Detection("attention_drop", step, t_step, 0.55,
                                  "returned after a long pause"))
    return out


def _sublog(parent: ActivityLog, evs: list[Event]) -> ActivityLog:
    s = ActivityLog(parent.session_id)
    s.events = evs
    return s


# ─── UX cost (taps + keystrokes) ─────────────────────────────────────────────

def ux_cost(log: ActivityLog, step: str | None = None) -> dict:
    """Interaction effort: keystrokes + taps the user spent (per step or whole session).
    High cost on a step is a friction signal — long forms frustrate impatient personas."""
    evs = log.window(step=step)
    def _sum(et):
        return sum(int(e.value) for e in evs
                   if e.type is et and isinstance(e.value, (int, float)) and not isinstance(e.value, bool))
    ks, taps = _sum(EventType.KEYSTROKE), _sum(EventType.TAP)
    by_field: dict[str, int] = {}
    for e in evs:
        if e.type in (EventType.KEYSTROKE, EventType.TAP) and e.target and isinstance(e.value, (int, float)):
            by_field[e.target] = by_field.get(e.target, 0) + int(e.value)
    return {"keystrokes": ks, "taps": taps, "total": ks + taps, "by_field": by_field}


# ─── Engagement (read the timestamps) ─────────────────────────────────────────

# a user event the timing of which is meaningful (excludes app/coach-side markers)
_USER_ACTS = {EventType.SELECT, EventType.TAP, EventType.KEYSTROKE, EventType.FIELD_EDIT,
              EventType.TARIFF_CLICK, EventType.PRICE_HOVER, EventType.HOVER,
              EventType.SUBMIT, EventType.NAV_BACK, EventType.TOOLTIP_OPEN}


def engagement(log: ActivityLog) -> dict:
    """
    Interpret timestamps into an engagement read. Timing is the signal:
      • reactivity = how fast the user acts after a price_reveal / widget (low latency = reactive)
      • cadence    = median gap between user actions (steady, small = engaged)
      • idle / session_gap = distraction
    Returns a label + the supporting numbers.
    """
    evs = sorted(log.events, key=lambda e: e.t)
    acts = [e for e in evs if e.type in _USER_ACTS]
    gaps = [b.t - a.t for a, b in zip(acts, acts[1:]) if b.t >= a.t]
    cadence = _median(gaps)

    triggers = [e for e in evs if e.type in (EventType.PRICE_REVEAL, EventType.WIDGET_SHOWN, EventType.STEP_ENTER)]
    lat = []
    for tr in triggers:
        nxt = next((a for a in acts if a.t >= tr.t), None)
        if nxt is not None:
            lat.append(nxt.t - tr.t)
    reactivity_latency = _median(lat)

    idle_total = sum((e.value or 0) for e in evs
                     if e.type in (EventType.IDLE, EventType.PAUSE) and isinstance(e.value, (int, float)))
    distracted = any(e.type == EventType.SESSION_GAP for e in evs) or idle_total >= 25 or cadence >= 12

    if distracted:
        label = "distracted"
    elif reactivity_latency <= 2.5 and cadence <= 5:
        label = "reactive"
    elif cadence <= 8:
        label = "engaged"
    else:
        label = "deliberate"

    return {
        "label": label,
        "cadence_sec": round(cadence, 2),
        "reactivity_latency_sec": round(reactivity_latency, 2),
        "idle_total_sec": round(float(idle_total), 1),
        "n_user_acts": len(acts),
    }


def _median(xs: list[float]) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    m = len(s) // 2
    return s[m] if len(s) % 2 else (s[m-1] + s[m]) / 2
