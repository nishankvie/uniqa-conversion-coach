"""
Dial auto-tuner — coordinate descent on the persona behavioural dials.

Each round: generate N stepwise+state sessions/persona, validate vs the funnel.py
anchors, then nudge the single most-responsible dial per failing cell:

  S3 bounce off  → complexity_overwhelm (+ ux_willingness, inverse)
  S4 bounce off  → price_shock_s4
  S6 bounce off  → final_price_sensitivity_s6
  conversion off → online_completion (and advisor_lean, inverse)

Dials are persona TRAITS; the anchors are held-out validation. We tune the trait
until the funnel stats emerge — targets are never injected into the prompt.

    python -m research.tune --n 40 --rounds 3

Writes prompts/personas/<persona>.params.json after every round (progress persists),
keeps the best-ε params at the end, and logs research/runs/tune_<ts>.md.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from uniqa.persona_datagen import LLMTeacher
from research.run import generate, validate, PERSONAS

_PARAM_DIR = Path(__file__).resolve().parents[1] / "prompts" / "personas"
# cell → [(dial, signed weight)]  (too-HIGH bounce, e>0, moves each dial by sign*w*k*e)
# Fundamental-factor mapping (S4/S6 reactions emerge from these, not synthetic sensitivities).
BOUNCE_DIALS = {
    "S3_PERSONAL_INFO": [("complexity_overwhelm", -1.0), ("ux_willingness", +0.5)],
    "S4_TARIFF_SELECT": [("budget_pressure", -0.7), ("value_orientation", -0.5), ("advisor_lean", -0.5)],
    "S6_PERSONAL_DATA": [("commitment_anxiety", -1.0), ("uncertainty_aversion", -0.5)],
}
CELL_TOL = 0.08
CONV_TOL = 0.04
LO, HI = 0.05, 0.95


def load_params(persona: str) -> dict:
    return json.loads((_PARAM_DIR / f"{persona}.params.json").read_text())


def save_params(persona: str, params: dict) -> None:
    (_PARAM_DIR / f"{persona}.params.json").write_text(json.dumps(params, indent=2) + "\n")


def _clamp(x: float) -> float:
    return round(max(LO, min(HI, x)), 3)


GLOBAL_BEST = Path(__file__).resolve().parent / "runs" / "_global_best.json"


def propose(prep: dict, k: float = 0.22) -> dict:    # damped (codex P2: k=0.15–0.25)
    """Return {dial: delta} for one coordinate-descent step from a persona's stats."""
    upd: dict[str, float] = {}

    def bump(dial, d):
        upd[dial] = upd.get(dial, 0.0) + d

    for sv, dials in BOUNCE_DIALS.items():
        c = prep["bounce_cells"].get(sv, {})
        if c.get("observed") is None:
            continue
        e = c["observed"] - c["target"]           # >0 = bounce too high
        if abs(e) > CELL_TOL:
            for dial, w in dials:
                bump(dial, w * k * e)
    # conversion
    ce = prep["conv_rate"] - prep["conv_target"]  # >0 = converts too much
    if abs(ce) > CONV_TOL:
        bump("advisor_lean", 0.5 * ce)            # too high → lean harder to advisor (fewer convert)
        bump("commitment_anxiety", 0.4 * ce)      # too high → more last-step hesitation
    return upd


def apply(params: dict, upd: dict) -> dict:
    out = dict(params)
    for dial, d in upd.items():
        if dial in out:
            out[dial] = _clamp(out[dial] + d)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="coordinate-descent dial tuner")
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--model", default=None)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)

    teacher = LLMTeacher(args.model, include_params=True, stepwise=True, include_state=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    log = [f"# Dial tuning — N={args.n}, rounds={args.rounds}, teacher={teacher.name}, {ts}\n"]
    # persisted global best across runs (codex P2: don't let a noisy re-run regress)
    gbest = {"eps": 1e9}
    if GLOBAL_BEST.exists():
        try:
            gbest = json.loads(GLOBAL_BEST.read_text())
        except Exception:
            pass
    best = {"eps": 1e9, "params": {p: load_params(p) for p in PERSONAS}, "round": -1}

    for rnd in range(args.rounds):
        seed = args.seed + rnd * 1000
        by_persona = {p: generate(p, args.n, teacher, seed, args.workers) for p in PERSONAS}
        report = validate(by_persona)
        eps = report["overall"]["epsilon_mean_abs_bounce"] or 9.9
        conv = report["overall"]["obs_conv_weighted"]
        line = (f"\n## round {rnd} — ε={eps} · conv={conv} · "
                f"PASS={report['overall']['PASS']}")
        print(line)
        log.append(line)
        for p in PERSONAS:
            r = report["personas"][p]
            bc = r["bounce_cells"]
            def cell(sv):
                c = bc[sv]; o = "–" if c["observed"] is None else f"{c['observed']:.2f}"
                return f"{o}/{c['target']:.2f}"
            row = (f"  {p:7s} conv {r['conv_rate']:.2f}/{r['conv_target']:.2f}  "
                   f"S3 {cell('S3_PERSONAL_INFO')}  S4 {cell('S4_TARIFF_SELECT')}  "
                   f"S6 {cell('S6_PERSONAL_DATA')}")
            print(row); log.append(row)

        if eps < best["eps"]:
            best = {"eps": eps, "params": {p: load_params(p) for p in PERSONAS}, "round": rnd}

        # propose + apply (skip on the last round — nothing to re-measure)
        if rnd < args.rounds - 1:
            for p in PERSONAS:
                upd = propose(report["personas"][p])
                if upd:
                    new = apply(load_params(p), upd)
                    save_params(p, new)
                    diff = {d: f"{round(v,3):+}" for d, v in upd.items()}
                    msg = f"    tune {p}: {diff}"
                    print(msg); log.append(msg)

    # reconcile with the persisted global best: keep whichever ε is lower
    if best["eps"] <= gbest["eps"]:
        GLOBAL_BEST.write_text(json.dumps({"eps": best["eps"], "params": best["params"]}, indent=2))
        chosen, src = best["params"], f"this run (round {best['round']}, ε={best['eps']})"
    else:
        chosen, src = gbest["params"], f"persisted global best (ε={gbest['eps']})"
    for p in PERSONAS:
        save_params(p, chosen[p])
    foot = f"\n→ kept {src}."
    print(foot); log.append(foot)

    out = Path(__file__).resolve().parent / "runs" / f"tune_{ts}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(log))
    print(f"log → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
