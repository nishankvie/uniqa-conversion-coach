"""
Cohort baseline + relative (divergence) signals.

The coach shouldn't use absolute thresholds ("dwell > 8s = slow"). "Fast" only means anything
RELATIVE to a cohort (e.g. this week's sessions on this device). So we:
  1. extract per-step metrics from each session (dwell, #price-hovers, #field-focuses, #back-nav,
     #cancel-hover, #tooltip, keystrokes, validation-errors, tab-away, idle, exit-intent, ...),
  2. build a cohort BASELINE (mean/std/p50/p90 per (step, metric)) over many sessions,
  3. score a live session as DIVERGENCE from baseline (z-scores) → find OUTLIERS / anomalies.

The coach then reasons on "this user is −2.3σ on step-speed vs cohort" (decisive/skimming),
not on a magic number. Baselines are cohort- and time-window-scoped → recompute per window.

CLI:  python -m coach.baseline datasets/persona_v1/sessions.jsonl  [--out baseline.json]
"""
from __future__ import annotations

import argparse, json, math
from collections import defaultdict
from pathlib import Path

# event type -> the metric it increments (count). dwell + keystrokes handled separately.
_COUNT_METRICS = {
    "price_hover": "price_hover_n", "hover": "hover_n", "field_focus": "field_focus_n",
    "nav_back": "back_nav_n", "cancel_hover": "cancel_hover_n", "tooltip_open": "tooltip_n",
    "validation_error": "validation_err_n", "field_edit": "field_reedit_n",
    "tab_blur": "tab_away_n", "idle": "idle_n", "pause": "pause_n", "tap": "tap_n",
    "exit_intent": "exit_intent_n", "text_select": "text_select_n", "copy": "copy_n",
    "slow_mouse": "slow_mouse_n", "scroll_up": "scroll_up_n", "dropdown_open": "dropdown_n",
    "premium_click": "premium_click_n", "external_nav": "external_nav_n",
}
METRICS = sorted(set(_COUNT_METRICS.values()) | {"dwell_sec", "keystrokes", "tab_away_sec", "n_events"})


def _events(session) -> list[dict]:
    if isinstance(session, dict):
        return session.get("events", [])
    return [e if isinstance(e, dict) else e.to_dict() for e in getattr(session, "events", [])]


def session_metrics(session) -> dict[str, dict[str, float]]:
    """Per-step metric dict for one session: {step: {metric: value}}."""
    by_step: dict[str, dict[str, float]] = defaultdict(lambda: {m: 0.0 for m in METRICS})
    ts: dict[str, list[float]] = defaultdict(list)
    for e in _events(session):
        step = e.get("step", "?"); m = by_step[step]
        t = e.get("type")
        m["n_events"] += 1
        try:
            ts[step].append(float(e.get("t", 0.0)))
        except (TypeError, ValueError):
            pass
        if t in _COUNT_METRICS:
            m[_COUNT_METRICS[t]] += 1
        if t == "keystroke":
            try: m["keystrokes"] += float(e.get("value") or 0)
            except (TypeError, ValueError): pass
        if t == "tab_focus":
            try: m["tab_away_sec"] += float(e.get("value") or 0)
            except (TypeError, ValueError): pass
    for step, tl in ts.items():
        if tl:
            by_step[step]["dwell_sec"] = round(max(tl) - min(tl), 2)
    return dict(by_step)


def build_baseline(sessions: list) -> dict:
    """Cohort baseline: per (step, metric) → {n, mean, std, p50, p90}."""
    acc: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for s in sessions:
        for step, mm in session_metrics(s).items():
            for metric, v in mm.items():
                acc[step][metric].append(v)

    def stats(xs):
        n = len(xs)
        if n == 0:
            return {"n": 0, "mean": 0.0, "std": 0.0, "p50": 0.0, "p90": 0.0}
        mean = sum(xs) / n
        std = math.sqrt(sum((x - mean) ** 2 for x in xs) / n) if n > 1 else 0.0
        sx = sorted(xs)
        return {"n": n, "mean": round(mean, 3), "std": round(std, 3),
                "p50": round(sx[n // 2], 3), "p90": round(sx[min(n - 1, int(0.9 * n))], 3)}

    return {"per_step": {step: {m: stats(v) for m, v in mm.items()} for step, mm in acc.items()},
            "n_sessions": len(sessions)}


def divergence(session, baseline: dict, z_outlier: float = 2.0) -> dict:
    """Score a session as z-divergence from the cohort baseline; flag outliers (|z|>=z_outlier).
    NEGATIVE z on dwell_sec = FASTER than cohort; positive = slower. etc."""
    out = {"per_step": {}, "outliers": []}
    bp = baseline.get("per_step", {})
    for step, mm in session_metrics(session).items():
        zr = {}
        for metric, v in mm.items():
            b = bp.get(step, {}).get(metric)
            if not b or b["std"] == 0:
                continue
            z = round((v - b["mean"]) / b["std"], 2)
            zr[metric] = z
            if abs(z) >= z_outlier:
                out["outliers"].append({"step": step, "metric": metric, "value": v,
                                        "cohort_mean": b["mean"], "z": z})
        out["per_step"][step] = zr
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("sessions", help="sessions.jsonl (one {persona,events} per line)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    rows = [json.loads(l) for l in Path(args.sessions).open()]
    bl = build_baseline(rows)
    txt = json.dumps(bl, indent=2)
    if args.out:
        Path(args.out).write_text(txt)
    # human summary: key metrics per step
    print(f"cohort baseline over {bl['n_sessions']} sessions:")
    for step, mm in bl["per_step"].items():
        d = mm.get("dwell_sec", {}); bk = mm.get("back_nav_n", {}); ph = mm.get("price_hover_n", {})
        print(f"  {step:18} dwell mean={d.get('mean')} (p90 {d.get('p90')})  "
              f"back_nav mean={bk.get('mean')}  price_hover mean={ph.get('mean')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
