"""
Research runner — persona session generation + statistical validation.

Generates N whole-session feeds per persona with the LLM teacher (the prompt now
carries the widget RESPONSE state machine so the model knows how the widget reacts),
then validates the emergent statistics against the calibration anchors in funnel.py
(ABANDON_PROBS per (persona, step) + implied per-persona conversion). Targets are the
EVAL reference only — never injected into the prompt.

    # iteration 0 — base prompt (hand-scrubbed persona + widget state machine)
    python -m research.run --n 30

    # iteration 1 — escalate: add curated behavioural quantitative metrics
    python -m research.run --n 30 --quant

    python -m research.run --n 30 --offline      # pipeline smoke test (no API/cost)

Writes research/runs/<ts>_<mode>/: logs.jsonl + report.md + report.json, prints summary.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import statistics as stats
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import random as _random
from uniqa.funnel import Step, PERSONA_WEIGHTS, ABANDON_PROBS
from uniqa.contracts import EventType
from uniqa.persona_datagen import (
    LLMTeacher, OfflineTeacher, default_teacher, generate_feed,
)

# in-scope bounce steps (S5 add-on is out of scope per scope.py → excluded)
BOUNCE_STEPS = [Step.PERSONAL_INFO, Step.TARIFF_SELECT, Step.PERSONAL_DATA]
PERSONAS = ("judith", "franz", "peter")

# pass tolerances (loose — small-N research loop, not production gating)
EPS_GATE = 0.12       # mean abs per-cell bounce diff vs ABANDON_PROBS
CONV_TOL = 0.06       # |observed - implied| conversion rate per persona


# ─── generation ───────────────────────────────────────────────────────────────

def generate(persona: str, n: int, teacher, seed: int, workers: int = 8):
    def one(i):
        return generate_feed(persona, teacher, random.Random(seed + i))
    if workers <= 1:
        return [one(i) for i in range(n)]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(one, range(n)))


# ─── per-persona statistics ───────────────────────────────────────────────────

def _terminal(log):
    for e in reversed(log.events):
        if e.type in (EventType.CONVERT, EventType.ABANDON):
            return e.type.value, (e.value or "")
    return "incomplete", ""


def persona_stats(logs) -> dict:
    n = len(logs)
    reach = Counter(); bounce = Counter(); convert = 0
    reasons = Counter(); durations = []
    for log in logs:
        seen = set()
        for e in log.events:
            if e.type is EventType.STEP_ENTER and e.step not in seen:
                reach[e.step] += 1; seen.add(e.step)
        term, why = _terminal(log)
        if term == "convert":
            convert += 1
        elif term == "abandon":
            bstep = next((e.step for e in reversed(log.events) if e.type is EventType.ABANDON), None)
            if bstep:
                bounce[bstep] += 1
            reasons[why or "?"] += 1
        if log.events:
            durations.append(round(log.events[-1].t - log.events[0].t, 1))
    cond_bounce = {s.value: round(bounce[s.value] / reach[s.value], 3)
                   for s in BOUNCE_STEPS if reach.get(s.value)}
    return {
        "n": n, "convert": convert, "conv_rate": round(convert / n, 3) if n else 0.0,
        "cond_bounce": cond_bounce,
        "reach": {s.value: reach.get(s.value, 0) for s in BOUNCE_STEPS},
        "terminal_reasons": dict(reasons.most_common()),
        "duration_s_median": round(stats.median(durations), 1) if durations else 0.0,
    }


def implied_conv_target(persona: str) -> float:
    """Conversion implied by the in-scope ABANDON_PROBS chain (S3·S4·S6)."""
    p = ABANDON_PROBS[persona]
    surv = 1.0
    for s in BOUNCE_STEPS:
        surv *= (1 - p.get(s, 0.0))
    return round(surv, 4)


# ─── validation vs anchors ────────────────────────────────────────────────────

def validate(by_persona: dict) -> dict:
    cells = []
    report = {"personas": {}, "overall": {}}
    obs_overall = 0.0
    present = [p for p in PERSONAS if p in by_persona]   # robust to partial / failed personas
    for persona in present:
        st = persona_stats(by_persona[persona])
        ref = ABANDON_PROBS[persona]
        cell_rows = {}
        for s in BOUNCE_STEPS:
            obs = st["cond_bounce"].get(s.value)
            tgt = round(ref.get(s, 0.0), 3)
            if obs is not None:
                d = round(abs(obs - tgt), 3)
                cells.append(d)
                cell_rows[s.value] = {"observed": obs, "target": tgt, "abs_diff": d}
            else:
                cell_rows[s.value] = {"observed": None, "target": tgt, "abs_diff": None}
        conv_t = implied_conv_target(persona)
        report["personas"][persona] = {
            **st,
            "conv_target": conv_t,
            "conv_abs_diff": round(abs(st["conv_rate"] - conv_t), 3),
            "converts_at_least_once": st["convert"] >= 1,
            "bounce_cells": cell_rows,
        }
        obs_overall += PERSONA_WEIGHTS[persona] * st["conv_rate"]
    eps = round(sum(cells) / len(cells), 4) if cells else None
    tgt_overall = round(sum(PERSONA_WEIGHTS[p] * implied_conv_target(p) for p in present), 4)
    report["overall"] = {
        "epsilon_mean_abs_bounce": eps,
        "obs_conv_weighted": round(obs_overall, 4),
        "target_conv_weighted": tgt_overall,
        "personas_present": present,
        "all_personas_convert": all(report["personas"][p]["converts_at_least_once"] for p in present),
        "eps_pass": (eps is not None and eps <= EPS_GATE),
        "conv_pass": all(report["personas"][p]["conv_abs_diff"] <= CONV_TOL for p in present),
    }
    report["overall"]["PASS"] = bool(
        report["overall"]["eps_pass"] and report["overall"]["conv_pass"]
        and report["overall"]["all_personas_convert"] and len(present) == len(PERSONAS))
    return report


# ─── report formatting ────────────────────────────────────────────────────────

def format_md(report: dict, meta: dict) -> str:
    o = report["overall"]
    L = [f"# Session-gen validation — {meta['mode']} (teacher={meta['teacher']}, N={meta['n']}/persona)",
         f"_generated {meta['ts']}_\n",
         f"**VERDICT: {'✅ PASS' if o['PASS'] else '❌ FAIL'}**  "
         f"(ε={o['epsilon_mean_abs_bounce']} ≤{EPS_GATE}: {o['eps_pass']} · "
         f"conv: {o['conv_pass']} · each-converts: {o['all_personas_convert']})\n",
         f"Overall conversion: observed **{o['obs_conv_weighted']:.3f}** vs target "
         f"**{o['target_conv_weighted']:.3f}** (weighted {PERSONA_WEIGHTS}).\n",
         "| persona | n | conv | (target) | S3 bnc/(t) | S4 bnc/(t) | S6 bnc/(t) | reasons |",
         "|---|---|---|---|---|---|---|---|"]
    for p in PERSONAS:
        r = report["personas"][p]; bc = r["bounce_cells"]
        def cell(sv):
            c = bc[sv]; o_ = "–" if c["observed"] is None else f"{c['observed']:.2f}"
            return f"{o_}/{c['target']:.2f}"
        reasons = ", ".join(f"{k}×{v}" for k, v in list(r["terminal_reasons"].items())[:3])
        L.append(f"| {p} | {r['n']} | {r['conv_rate']:.2f} ({r['convert']}) | {r['conv_target']:.2f} "
                 f"| {cell('S3_PERSONAL_INFO')} | {cell('S4_TARIFF_SELECT')} | {cell('S6_PERSONAL_DATA')} "
                 f"| {reasons} |")
    L.append("\n_bnc/(t) = observed conditional bounce / ABANDON_PROBS target. "
             "Targets are eval-only; never in the prompt._")
    return "\n".join(L)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="persona session-gen + stats validation")
    ap.add_argument("--n", type=int, default=30, help="sessions per persona")
    ap.add_argument("--model", default=None)
    ap.add_argument("--stepwise", action="store_true", help="step-based generation (one LLM turn per step)")
    ap.add_argument("--quant", action="store_true", help="inject curated behavioural metrics")
    ap.add_argument("--params", action="store_true", help="parameter-driven dials (whole-session)")
    ap.add_argument("--state", action="store_true", help="stepwise: track state vars + felt distract/dissatisfy decision")
    ap.add_argument("--population", action="store_true", help="sample personas per the given 30/50/20 distribution (N total) instead of equal-N each")
    ap.add_argument("--offline", action="store_true", help="offline stub (no API)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8, help="concurrent LLM calls")
    args = ap.parse_args(argv)

    pre = "step" if args.stepwise else "ws"
    suff = "state" if args.state else ("quant" if args.quant else ("params" if args.params else "base"))
    mode = "offline" if args.offline else f"{pre}-{suff}"
    if args.offline:
        teacher = OfflineTeacher()
    elif os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY"):
        teacher = LLMTeacher(args.model, include_quant=args.quant, include_params=args.params,
                             stepwise=args.stepwise, include_state=args.state)
    else:
        teacher = OfflineTeacher()
    workers = 1 if args.offline else args.workers

    ts = time.strftime("%Y%m%d_%H%M%S")
    out = Path(__file__).resolve().parent / "runs" / f"{ts}_{mode}"
    out.mkdir(parents=True, exist_ok=True)

    # per-persona counts: equal-N (default, stable cell estimates) or sampled to 30/50/20
    if args.population:
        draws = _random.Random(args.seed).choices(
            PERSONAS, weights=[PERSONA_WEIGHTS[p] for p in PERSONAS], k=args.n)
        counts = {p: draws.count(p) for p in PERSONAS}
        print(f"population mode: N={args.n} sampled to {PERSONA_WEIGHTS} → {counts}")
    else:
        counts = {p: args.n for p in PERSONAS}

    by_persona = {}
    with (out / "logs.jsonl").open("w") as fh:
        for persona in PERSONAS:
            print(f"generating {counts[persona]}× {persona} (teacher={teacher.name}, mode={mode}) …")
            logs = generate(persona, counts[persona], teacher, args.seed, workers)
            by_persona[persona] = logs
            for log in logs:
                fh.write(json.dumps({"persona": persona, "events": [e.to_dict() for e in log.events]}) + "\n")

    report = validate(by_persona)
    meta = {"mode": mode, "teacher": teacher.name, "n": args.n, "ts": ts}
    (out / "report.json").write_text(json.dumps({"meta": meta, **report}, indent=2, ensure_ascii=False))
    md = format_md(report, meta)
    (out / "report.md").write_text(md)
    print("\n" + md + f"\n\n→ {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
