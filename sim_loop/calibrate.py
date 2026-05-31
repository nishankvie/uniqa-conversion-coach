"""
Calibrate persona behavioural dials so the simulated per-step ABANDON distribution
matches the UNIQA funnel anchors (FUNNEL_AUTOPSY.md). Focus: S4, S5, S6.

Method (as specified): the IMMUTABLE persona core is the system prompt (identical
across calls -> provider-cached); each run feeds the same system prompt a different
session instance -> a different sequence of actions. We run N sessions (coach OFF),
measure the conditional leave rate at each step (share of sessions that ENTER step
Sk and LEAVE at Sk), compare to the anchors, and (optionally) coordinate-descent the
driving dial per step until the gap closes. Tuned dials -> sim_loop/tuned_dials.json
(persona_prompt.dials() applies them on top of personas.json).

Anchors (conditional abandon hazard per step):
  S1 .18  S2 .06  S3 .10  S4 .30  S5 .05  S6 .12  S7 .08  S8 .11

Usage:
  python sim_loop/calibrate.py --n 100 --proportions real --concurrency 8        # measure
  python sim_loop/calibrate.py --n 100 --tune --rounds 3 --focus S4,S5,S6        # tune
"""
from __future__ import annotations
import argparse, json, sys, pathlib, random, collections
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FTimeout

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import widget
import run as runner
import persona_prompt

ANCHORS = {"S1_COVERAGE_TYPE": 0.18, "S2_INSURED_PERSONS": 0.06, "S3_PERSONAL_INFO": 0.10,
           "S4_TARIFF_SELECT": 0.30, "S5_ADDON_SELECT": 0.05, "S6_PERSONAL_DATA": 0.12,
           "S7_HEALTH_QUESTIONS": 0.08, "S8_REVIEW_PURCHASE": 0.11}

# step -> (driving dial, sign): sign=+1 means raising the dial raises leaving at the step
DRIVERS = {
    "S1_COVERAGE_TYPE": ("complexity_overwhelm", +1),
    "S2_INSURED_PERSONS": ("advisor_lean", +1),
    "S3_PERSONAL_INFO": ("patience", -1),
    "S4_TARIFF_SELECT": ("value_orientation", +1),
    "S5_ADDON_SELECT": ("complexity_overwhelm", +1),
    "S6_PERSONAL_DATA": ("commitment_anxiety", +1),
    "S7_HEALTH_QUESTIONS": ("uncertainty_aversion", +1),
    "S8_REVIEW_PURCHASE": ("budget_pressure", +1),
}
PERSONAS = ["judith", "franz", "peter"]


def measure(n, proportions, model, concurrency, temperature, seed, per_future_timeout=180):
    weights = runner.REAL if proportions == "real" else runner.BALANCED
    rng = random.Random(seed)
    pool = list(weights.keys()); wts = [weights[p] for p in pool]
    assign = [rng.choices(pool, wts)[0] for _ in range(n)]
    entered = collections.Counter(); left = collections.Counter()
    entered_p = collections.defaultdict(collections.Counter)
    left_p = collections.defaultdict(collections.Counter)
    outcomes = collections.Counter()
    done = 0
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futs = {ex.submit(runner.run_session, seg, "off", model, 0,
                          seed * 100000 + i, temperature): seg
                for i, seg in enumerate(assign)}
        for fut in as_completed(futs):
            seg = futs[fut]
            try:
                r = fut.result(timeout=per_future_timeout)
            except (FTimeout, Exception) as e:
                sys.stderr.write(f"[measure] {seg} failed: {type(e).__name__}\n")
                continue
            done += 1
            outcomes[r["outcome"]] += 1
            steps = r["steps"]
            left_here = r["outcome"] in ("abandon", "advisor_handoff")
            for j, st in enumerate(steps):
                s = st["step"]
                entered[s] += 1; entered_p[seg][s] += 1
                is_last = (j == len(steps) - 1)
                if is_last and left_here and st["persona_output"].get("decision") == "leave":
                    left[s] += 1; left_p[seg][s] += 1
    rate = {s: (left[s] / entered[s] if entered[s] else 0.0) for s in widget.STEP_ORDER}
    rate_p = {p: {s: (left_p[p][s] / entered_p[p][s] if entered_p[p][s] else 0.0)
                  for s in widget.STEP_ORDER} for p in PERSONAS}
    return {"n_done": done, "entered": dict(entered), "left": dict(left),
            "rate": rate, "rate_p": rate_p, "outcomes": dict(outcomes)}


def report(m):
    lines = [f"sessions completed: {m['n_done']}   outcomes: {m['outcomes']}", ""]
    lines.append(f"{'step':22s} {'entered':>7s} {'left':>5s} {'rate':>6s} {'target':>7s} {'gap':>7s}")
    sse = 0.0
    for s in widget.STEP_ORDER:
        r = m["rate"][s]; t = ANCHORS[s]; gap = r - t; sse += gap * gap
        flag = "  <" if s in ("S4_TARIFF_SELECT", "S5_ADDON_SELECT", "S6_PERSONAL_DATA") else ""
        lines.append(f"{s:22s} {m['entered'].get(s,0):7d} {m['left'].get(s,0):5d} "
                     f"{r:6.2f} {t:7.2f} {gap:+7.2f}{flag}")
    lines.append(f"\nRMSE vs anchors: {(sse/len(ANCHORS))**0.5:.3f}")
    conv = m["outcomes"].get("convert", 0)
    lines.append(f"overall conversion: {conv}/{m['n_done']} = {conv/max(m['n_done'],1):.2f}")
    return "\n".join(lines)


def tune(args):
    focus = [f if f.startswith("S") else f for f in args.focus.split(",")]
    focus = [s for s in widget.STEP_ORDER if any(s.startswith(f) for f in focus)]
    # load current overrides (start from baseline if none)
    ov_path = HERE / "tuned_dials.json"
    overrides = json.loads(ov_path.read_text()) if ov_path.exists() else {}
    history = []
    for rnd in range(args.rounds):
        m = measure(args.n, args.proportions, args.model, args.concurrency,
                    args.temperature, args.seed + rnd)
        print(f"\n===== ROUND {rnd} =====")
        print(report(m))
        history.append({"round": rnd, "rate": m["rate"], "outcomes": m["outcomes"]})
        # coordinate-descent the per-persona driving dial for each focus step
        for s in focus:
            dial, sign = DRIVERS[s]
            for p in PERSONAS:
                cur = persona_prompt.dials(p).get(dial)
                if cur is None:
                    continue
                gap = m["rate_p"][p][s] - ANCHORS[s]   # >0 => leaving too much
                step = args.lr * gap * sign            # move dial to reduce |gap|
                newv = min(1.0, max(0.0, cur - step))
                overrides.setdefault(p, {})[dial] = round(newv, 3)
        ov_path.write_text(json.dumps(overrides, ensure_ascii=False, indent=1))
        print(f"-> wrote {ov_path.name}: " +
              ", ".join(f"{p}.{DRIVERS[s][0]}={overrides[p][DRIVERS[s][0]]}"
                        for s in focus for p in PERSONAS if p in overrides and DRIVERS[s][0] in overrides[p]))
    # final measurement
    m = measure(args.n, args.proportions, args.model, args.concurrency,
                args.temperature, args.seed + args.rounds)
    print("\n===== FINAL =====")
    print(report(m))
    (HERE / "calibration_report.json").write_text(json.dumps(
        {"anchors": ANCHORS, "history": history, "final": m, "overrides": overrides},
        ensure_ascii=False, indent=2))
    print(f"\nsaved -> {HERE/'calibration_report.json'} and {ov_path.name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--proportions", choices=["real", "balanced"], default="real")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--temperature", type=float, default=0.6)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--model", default=None)
    ap.add_argument("--tune", action="store_true")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--lr", type=float, default=0.5)
    ap.add_argument("--focus", default="S4,S5,S6")
    args = ap.parse_args()
    if args.tune:
        tune(args)
    else:
        m = measure(args.n, args.proportions, args.model, args.concurrency,
                    args.temperature, args.seed)
        print(report(m))
        (HERE / "calibration_report.json").write_text(json.dumps(
            {"anchors": ANCHORS, "final": m}, ensure_ascii=False, indent=2))
        print(f"\nsaved -> {HERE/'calibration_report.json'}")


if __name__ == "__main__":
    main()
