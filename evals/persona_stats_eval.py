"""
Persona statistical conformance eval — the CANONICAL, regularly-run gate.

Generates a population sampled to the GIVEN persona distribution (PERSONA_WEIGHTS,
30/50/20) and checks the emergent funnel stats against the funnel.py anchors:
per-(persona,step) conditional bounce + per-persona conversion + overall conversion.

Same eval is used for (a) the LLM persona agent now, and (b) the future local/distilled
model — swap the `--generator`. Run it regularly (CI/cron) to catch drift.

    python -m evals.persona_stats_eval --n 150            # LLM agent, population 30/50/20
    python -m evals.persona_stats_eval --n 150 --seeds 3  # pooled multi-seed (low variance)

Writes evals/reports/<ts>.md and exits non-zero on FAIL (CI-friendly).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

from uniqa.funnel import PERSONA_WEIGHTS
from uniqa.persona_datagen import LLMTeacher, OfflineTeacher
from research.run import generate, validate, format_md, PERSONAS


def population_counts(n: int, seed: int) -> dict:
    draws = random.Random(seed).choices(
        PERSONAS, weights=[PERSONA_WEIGHTS[p] for p in PERSONAS], k=n)
    return {p: max(1, draws.count(p)) for p in PERSONAS}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="persona statistical conformance eval (population 30/50/20)")
    ap.add_argument("--n", type=int, default=150, help="total population size (sampled to 30/50/20)")
    ap.add_argument("--seeds", type=int, default=1, help="pool this many seeds (lower variance)")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--model", default=None)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--generator", default="llm-agent", help="label for the report (e.g. local-model)")
    args = ap.parse_args(argv)

    teacher = (OfflineTeacher() if args.offline
               else LLMTeacher(args.model, include_params=True, stepwise=True, include_state=True))
    counts = population_counts(args.n, seed=0)
    print(f"population N={args.n} → {counts} (weights {PERSONA_WEIGHTS}); pooling {args.seeds} seed(s)")

    by_persona = {p: [] for p in PERSONAS}
    for s in range(args.seeds):
        for p in PERSONAS:
            by_persona[p].extend(generate(p, counts[p], teacher, seed=s * 1000, workers=args.workers))

    report = validate(by_persona)
    ts = time.strftime("%Y%m%d_%H%M%S")
    meta = {"mode": f"eval:{args.generator}", "teacher": teacher.name,
            "n": sum(len(v) for v in by_persona.values()) // len(PERSONAS), "ts": ts}
    md = format_md(report, meta)
    out = Path(__file__).resolve().parent / "reports" / f"{ts}_{args.generator}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md)
    (out.with_suffix(".json")).write_text(json.dumps({"meta": meta, **report}, indent=2, ensure_ascii=False))
    print("\n" + md + f"\n\n→ {out}")
    return 0 if report["overall"]["PASS"] else 1


if __name__ == "__main__":
    sys.exit(main())
