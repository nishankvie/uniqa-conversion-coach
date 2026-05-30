"""
Compare a captured HUMAN session against PERSONA-BOT generated sessions.

    python -m uniqa.compare _local/captures/<file>.json            # vs bot (offline teacher)
    python -m uniqa.compare _local/captures/<file>.json --persona franz --n 20

Prints per-session metrics (duration, per-step dwell, event-type mix, terminal) for
the human log and an aggregate over N bot logs, then a short delta read-out. The
point: surface where synthetic feeds differ from a real human (esp. TIMING).
"""

from __future__ import annotations

import argparse
import statistics as stats
from collections import Counter

from uniqa.contracts import ActivityLog, EventType
from uniqa.capture import load_log


# ─── metrics over one ActivityLog ─────────────────────────────────────────────

def duration(log: ActivityLog) -> float:
    return round(log.events[-1].t - log.events[0].t, 2) if log.events else 0.0

def terminal(log: ActivityLog) -> str:
    for e in reversed(log.events):
        if e.type in (EventType.CONVERT, EventType.ABANDON):
            return e.type.value + (f":{e.value}" if e.value else "")
    return "incomplete"

def per_step_dwell(log: ActivityLog) -> dict[str, float]:
    """Seconds spent on each step = time from its STEP_ENTER to the next step's STEP_ENTER."""
    enters = [(e.step, e.t) for e in log.events if e.type is EventType.STEP_ENTER]
    end = log.events[-1].t if log.events else 0.0
    out: dict[str, float] = {}
    for i, (step, t) in enumerate(enters):
        nxt = enters[i + 1][1] if i + 1 < len(enters) else end
        out[step] = round(nxt - t, 2)
    return out

def inter_event_dt(log: ActivityLog) -> list[float]:
    ts = [e.t for e in log.events]
    return [round(b - a, 2) for a, b in zip(ts, ts[1:])]

def type_mix(log: ActivityLog) -> Counter:
    return Counter(e.type.value for e in log.events)

def profile(log: ActivityLog) -> dict:
    dt = inter_event_dt(log)
    return {
        "events": len(log.events),
        "duration_s": duration(log),
        "terminal": terminal(log),
        "n_steps": sum(1 for e in log.events if e.type is EventType.STEP_ENTER),
        "dt_mean": round(stats.mean(dt), 2) if dt else 0.0,
        "dt_median": round(stats.median(dt), 2) if dt else 0.0,
        "dt_max": round(max(dt), 2) if dt else 0.0,
        "per_step_dwell": per_step_dwell(log),
        "type_mix": dict(type_mix(log)),
    }


# ─── bot generation ───────────────────────────────────────────────────────────

def bot_logs(persona: str, n: int, seed: int = 0):
    import random
    from uniqa.persona_datagen import generate_feed, OfflineTeacher
    teacher = OfflineTeacher()
    return [generate_feed(persona, teacher, random.Random(seed + i)) for i in range(n)]


def aggregate(profiles: list[dict]) -> dict:
    def m(key): return round(stats.mean(p[key] for p in profiles), 2)
    terminals = Counter(p["terminal"].split(":")[0] for p in profiles)
    return {
        "events": m("events"), "duration_s": m("duration_s"), "n_steps": m("n_steps"),
        "dt_mean": m("dt_mean"), "dt_median": m("dt_median"), "dt_max": m("dt_max"),
        "terminals": dict(terminals),
    }


def _fmt_mix(mix: dict) -> str:
    return ", ".join(f"{k}×{v}" for k, v in sorted(mix.items(), key=lambda kv: -kv[1]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("human_log")
    ap.add_argument("--persona", default=None, help="bot persona (default: the log's persona_hint)")
    ap.add_argument("--n", type=int, default=20, help="number of bot sessions")
    args = ap.parse_args(argv)

    human, meta = load_log(args.human_log)
    persona = args.persona or (meta["persona_hint"] if meta["persona_hint"] in ("judith", "franz", "peter") else "franz")
    hp = profile(human)
    bots = bot_logs(persona, args.n)
    bp = [profile(b) for b in bots]
    agg = aggregate(bp)

    print(f"\n══ HUMAN ({meta['source']}, hint={meta['persona_hint']}) vs BOT persona={persona} (offline teacher, N={args.n}) ══\n")
    print(f"{'metric':<16}{'HUMAN':>12}{'BOT (mean)':>14}")
    for k, label in [("events", "events"), ("duration_s", "duration s"), ("n_steps", "# steps"),
                     ("dt_mean", "Δt mean s"), ("dt_median", "Δt median s"), ("dt_max", "Δt max s")]:
        print(f"{label:<16}{hp[k]:>12}{agg[k]:>14}")
    print(f"\nterminal   human={hp['terminal']!r}   bot={agg['terminals']}")

    print("\nper-step dwell (s):")
    steps = list(dict.fromkeys(list(hp["per_step_dwell"]) + [s for p in bp for s in p["per_step_dwell"]]))
    bot_dwell = {s: round(stats.mean([p["per_step_dwell"].get(s, 0.0) for p in bp]), 2) for s in steps}
    print(f"  {'step':<22}{'HUMAN':>10}{'BOT':>10}")
    for s in steps:
        print(f"  {s:<22}{hp['per_step_dwell'].get(s, 0.0):>10}{bot_dwell.get(s, 0.0):>10}")

    print(f"\nhuman event-type mix: {_fmt_mix(hp['type_mix'])}")
    print(f"bot   event-type mix: {_fmt_mix(bp[0]['type_mix'])}  (one sample)")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
