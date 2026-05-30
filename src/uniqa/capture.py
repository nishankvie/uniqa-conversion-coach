"""
Real-time human session capture.

The simulator emits an `ActivityLog` of `contracts.Event`s; so does a person at a
keyboard — but only if we timestamp their actions with REAL wall-clock time. This
is the Stage-0 capture harness from docs/PIPELINE_PLAN.md: it lets us record genuine
human timing (dwell, inter-event Δt) and compare it against persona-bot feeds.

`SessionRecorder` is UI-agnostic: the Streamlit "Play & capture" view and any future
browser hook both drive the same `.record(...)` calls, producing one ActivityLog.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from uniqa.contracts import Event, EventType, ActivityLog, new_session_id


# Captured sessions land here (gitignored — under _local/).
CAPTURE_DIR = Path(__file__).resolve().parents[2] / "_local" / "captures"


@dataclass
class SessionRecorder:
    """Wraps an ActivityLog and stamps every event with seconds since session start."""
    persona_hint: str = "human"          # self-declared persona, for later comparison
    source: str = "human"
    session_id: str = field(default_factory=new_session_id)
    _t0: float = field(default_factory=time.monotonic)
    log: ActivityLog = field(init=False)

    def __post_init__(self) -> None:
        self.log = ActivityLog(self.session_id)

    def now(self) -> float:
        return round(time.monotonic() - self._t0, 2)

    def record(self, etype: EventType, step: str, *, target: str | None = None,
               value=None, thought: str | None = None) -> Event:
        ev = Event(etype, step, self.now(), target=target, value=value,
                   source=self.source, thought=thought)
        self.log.append(ev)
        return ev

    # convenience wrappers (the funnel's real action vocabulary)
    def enter(self, step: str):                 return self.record(EventType.STEP_ENTER, step)
    def select(self, step, target, value=None): return self.record(EventType.SELECT, step, target=target, value=value)
    def tap(self, step, target, n=1):           return self.record(EventType.TAP, step, target=target, value=n)
    def keystrokes(self, step, field_, n):      return self.record(EventType.KEYSTROKE, step, target=field_, value=n)
    def price_reveal(self, step, tariff, eur):  return self.record(EventType.PRICE_REVEAL, step, target=tariff, value=eur)
    def nav_back(self, step):                   return self.record(EventType.NAV_BACK, step)
    def convert(self, step):                    return self.record(EventType.CONVERT, step, value="online_purchase")
    def abandon(self, step, reason):            return self.record(EventType.ABANDON, step, value=reason)

    def to_dict(self) -> dict:
        d = self.log.to_dict()
        d["persona_hint"] = self.persona_hint
        d["source"] = self.source
        return d

    def save(self, path: Path | None = None) -> Path:
        CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
        path = path or (CAPTURE_DIR / f"{self.session_id}_{self.persona_hint}.json")
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))
        return path


def load_log(path: str | Path) -> tuple[ActivityLog, dict]:
    """Load a captured (or bot-generated) session JSON back into an ActivityLog."""
    raw = json.loads(Path(path).read_text())
    log = ActivityLog(raw.get("session_id", "loaded"))
    for e in raw.get("events", []):
        log.append(Event(
            EventType(e["type"]), e["step"], float(e.get("t", 0.0)),
            target=e.get("target"), value=e.get("value"),
            source=e.get("source", "user"), thought=e.get("thought"),
        ))
    meta = {"persona_hint": raw.get("persona_hint", "?"), "source": raw.get("source", "?")}
    return log, meta
