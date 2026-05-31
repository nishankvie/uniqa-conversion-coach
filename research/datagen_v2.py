"""
Persona distillation v2 — per-step, state-covering, K-sampled datagen (OpenRouter teacher).

Reframe: the persona model is a PER-STEP MARKOV POLICY, not a trajectory imitator. We sample
contexts (disposition + plausible running_state) that COVER the state space — including the
leave-prone region — and query the teacher K times per context to get a soft leave-rate.
Targets (66/24/78) are NEVER in the prompt; conformance comes from the state sampler + later
Stage-2 calibration. See docs/PERSONA_DISTILL_V2_PLAN.md.

CLI:
  python -m research.datagen_v2 probe   --M 20 --K 5         # T3a balance probe (S4+S6)
  python -m research.datagen_v2 build   --M 150 --K 5 --out datasets/persona_v2
"""
from __future__ import annotations

import argparse
import json
import random
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from uniqa.funnel import Step, PERSONA_WEIGHTS
from uniqa.persona_datagen import (
    LLMTeacher, _sample_disposition, _strip_fences, build_step_decision_prompt,
)

PERSONAS = ["judith", "franz", "peter"]
# in-scope per-step flow (S5/add-on excluded). probe focuses on the price walls S4 + S6.
FLOW = [Step.COVERAGE_TYPE, Step.INSURED, Step.PERSONAL_INFO, Step.TARIFF_SELECT, Step.PERSONAL_DATA]
PROBE_STEPS = [Step.TARIFF_SELECT, Step.PERSONAL_DATA]

_STEP_BRIEF = {
    Step.COVERAGE_TYPE:  [],
    Step.INSURED:        ["S1_COVERAGE_TYPE: doctor_visits"],
    Step.PERSONAL_INFO:  ["S1_COVERAGE_TYPE: doctor_visits", "S2_INSURED_PERSONS: myself"],
    Step.TARIFF_SELECT:  ["S1_COVERAGE_TYPE: doctor_visits", "S2_INSURED_PERSONS: myself", "S3_PERSONAL_INFO: dob, sv"],
    Step.PERSONAL_DATA:  ["S1_COVERAGE_TYPE: doctor_visits", "S2_INSURED_PERSONS: myself",
                          "S3_PERSONAL_INFO: dob, sv", "S4_TARIFF_SELECT: optimal"],
}

# journey wear: later steps trend lower on attention/effort. "mood" buckets give coverage of
# the leave-prone region without going off-manifold (we don't sample axes independently uniform).
_STEP_WEAR = {Step.COVERAGE_TYPE: 0.0, Step.INSURED: 0.05, Step.PERSONAL_INFO: 0.12,
              Step.TARIFF_SELECT: 0.18, Step.PERSONAL_DATA: 0.30}


def sample_running_state(step: Step, rng: random.Random) -> dict:
    """Plausible, leave-INCLUSIVE running state. mood ∈ {fresh,neutral,worn}; worn covers the
    leave-prone tail. Wear lowers attention/effort as the journey progresses."""
    # more 'fresh' mass: realistic (most users aren't worn-out) + gives the leave-heavy personas
    # (judith/peter) enough 'continue' coverage; marginals are then fixed by Stage-2 calibration.
    mood = rng.choices(["fresh", "neutral", "worn"], weights=[0.5, 0.3, 0.2])[0]
    base = {"fresh": (0.75, 1.0), "neutral": (0.45, 0.8), "worn": (0.1, 0.5)}[mood]
    wear = _STEP_WEAR[step]

    def s(lo_hi, floor=0.0):
        lo, hi = lo_hi
        return round(max(floor, min(1.0, rng.uniform(lo, hi) - wear * rng.uniform(0, 1))), 2)

    return {
        "attention":       s(base),
        "satisfaction":    s(base),
        "effort_left":     s((base[0] - 0.1, base[1])),
        "grasp":           s(base),
        "effort_vs_reward": s(base),
        "_mood": mood,
    }


def sample_context(persona: str, step: Step, rng: random.Random) -> dict:
    disp = _sample_disposition(persona, rng)
    state = sample_running_state(step, rng)
    tariff = rng.choice(["start", "optimal"]) if step is Step.PERSONAL_DATA else None
    intent = disp.get("visit_goal")
    return {"persona": persona, "step": step, "disposition": disp,
            "state": {k: v for k, v in state.items() if not k.startswith("_")},
            "mood": state["_mood"], "brief": list(_STEP_BRIEF[step]),
            "intent": intent, "selected_tariff": tariff}


_LEAN = True   # set by main(); lean trims cognitive_model + compresses feeling rules (~20%)


def build(ctx: dict) -> list[dict]:
    return build_step_decision_prompt(
        ctx["persona"], ctx["step"], ctx["brief"], ctx["state"],
        include_quant=False, include_params=True, include_state=True,
        disposition=ctx["disposition"], intent=ctx["intent"],
        selected_tariff=ctx["selected_tariff"], lean=_LEAN)


def classify(raw: str) -> str | None:
    """Return 'leave' | 'continue' | None (unparseable) from a teacher step output."""
    try:
        out = json.loads(_strip_fences(raw))
    except Exception:
        return None
    if isinstance(out, list):
        out = {"events": out}
    if not isinstance(out, dict):
        return None
    dec = str(out.get("decision", "")).lower()
    if "leave" in dec:
        return "leave"
    if "continue" in dec:
        return "continue"
    # fall back to terminal event types
    types = {str(e.get("type", "")).lower() for e in out.get("events", []) if isinstance(e, dict)}
    if "abandon" in types:
        return "leave"
    if "convert" in types or types:
        return "continue"
    return None


def _k_sample(teacher: LLMTeacher, ctx: dict, K: int) -> dict:
    msgs = build(ctx)
    outs, labels = [], []
    for _ in range(K):
        raw = None
        for _retry in range(3):                # crash-safe under high concurrency (429/backoff)
            try:
                raw = teacher._call(msgs); break
            except Exception:
                time.sleep(1.5 * (_retry + 1))
        outs.append(raw)
        labels.append(classify(raw) if raw else None)
    valid = [x for x in labels if x]
    leave = sum(1 for x in valid if x == "leave")
    return {"persona": ctx["persona"], "step": ctx["step"].value, "mood": ctx["mood"],
            "intent": ctx["intent"], "K": K, "valid": len(valid),
            "leave": leave, "leave_rate": round(leave / len(valid), 3) if valid else None,
            "messages": msgs, "labels": labels, "outputs": outs}


def run(personas, steps, M, K, workers, seed) -> list[dict]:
    teacher = LLMTeacher(stepwise=True, include_params=True, include_state=True)
    print(f"teacher = {teacher.name}")
    ctxs = []
    for p in personas:
        for st in steps:
            for i in range(M):
                ctxs.append(sample_context(p, st, random.Random(seed + hash((p, st.value, i)) % 10**6)))
    print(f"{len(ctxs)} contexts × K={K} = {len(ctxs)*K} teacher calls")
    with ThreadPoolExecutor(max_workers=workers) as ex:
        rows = list(ex.map(lambda c: _k_sample(teacher, c, K), ctxs))
    return rows


def _report(rows):
    by = {}
    for r in rows:
        by.setdefault((r["persona"], r["step"]), []).append(r)
    print("\n=== per-(persona,step) leave-rate (target = honest, NOT in prompt) ===")
    for (p, s), rs in sorted(by.items()):
        lr = [r["leave_rate"] for r in rs if r["leave_rate"] is not None]
        agg = round(sum(lr) / len(lr), 3) if lr else None
        # balance of step-level samples (every K-sample counted)
        leaves = sum(r["leave"] for r in rs); valid = sum(r["valid"] for r in rs)
        bal = round(leaves / valid, 3) if valid else None
        # leave-rate by mood (should rise fresh→worn if state matters)
        mood = {}
        for m in ("fresh", "neutral", "worn"):
            v = [r["leave_rate"] for r in rs if r["mood"] == m and r["leave_rate"] is not None]
            mood[m] = round(sum(v) / len(v), 2) if v else None
        print(f"  {p:7} {s:18} mean_leave_rate={agg}  token_balance(leave/all)={bal}  "
              f"by_mood {mood}  (n_ctx={len(rs)}, valid={valid})")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["probe", "build"])
    ap.add_argument("--M", type=int, default=20)
    ap.add_argument("--K", type=int, default=5)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="datasets/persona_v2")
    ap.add_argument("--full", action="store_true", help="use the full (untrimmed) prompt for A/B")
    ap.add_argument("--personas", default="", help="csv subset, e.g. judith (default all)")
    args = ap.parse_args(argv)
    global _LEAN; _LEAN = not args.full
    print("prompt:", "FULL" if args.full else "LEAN")

    personas = [p.strip() for p in args.personas.split(",") if p.strip()] or PERSONAS
    steps = PROBE_STEPS if args.mode == "probe" else FLOW
    t0 = time.time()
    rows = run(personas, steps, args.M, args.K, args.workers, args.seed)
    _report(rows)
    print(f"\n{len(rows)} contexts in {time.time()-t0:.1f}s")

    if args.mode == "build":
        out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
        n, dec = 0, Counter()
        with (out / "sft_steps.jsonl").open("w") as fh:
            for r in rows:
                # one SFT row per valid K-sample → natural leave/stay balance per context
                for raw, lab in zip(r["outputs"], r["labels"]):
                    if raw is None or lab is None:
                        continue
                    fh.write(json.dumps({"persona": r["persona"], "step": r["step"],
                                         "input_messages": r["messages"], "output": _strip_fences(raw),
                                         "decision": lab, "leave_rate": r["leave_rate"]},
                                        ensure_ascii=False) + "\n")
                    n += 1; dec[lab] += 1
        (out / "soft_labels.jsonl").write_text(
            "\n".join(json.dumps({k: r[k] for k in ("persona", "step", "mood", "intent",
                                                    "leave_rate", "valid")}) for r in rows) + "\n")
        from uniqa.persona_datagen import agent_persona_prompt
        from research.tune import load_params
        (out / "manifest.json").write_text(json.dumps({
            "mode": "per-step state-covering K-sampled (lean prompt)", "teacher": "openrouter:gpt-4o-mini",
            "M": args.M, "K": args.K, "n_contexts": len(rows), "n_sft_rows": n,
            "decision_balance": dict(dec), "prompt": "FULL" if args.full else "LEAN",
            "params": {p: load_params(p) for p in PERSONAS},
            "persona_prompt_chars": {p: len(agent_persona_prompt(p)) for p in PERSONAS},
        }, indent=2, ensure_ascii=False))
        print(f"\n=== dataset {out} ===  sft_rows={n}  decision_balance={dict(dec)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
