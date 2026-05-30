"""
Build the locked persona dataset (STEPWISE) for distillation into local models.

Stepwise is the foundation: the dynamic coach widget will intervene PER STEP, so the
persona model must be a per-step function (context + running state [+ coach action] →
events + state update + stay/leave). We therefore capture the per-step prompt->completion
pairs (the SFT data), plus the full session traces (for the statistical eval).

    python -m research.build_dataset --n 100 --out datasets/persona_v1 --workers 18

Writes <out>/:
  sft_steps.jsonl   per-step {persona, step, input_messages, output} \u2014 the fine-tune data
  sessions.jsonl    full session traces (events + thoughts) per persona \u2014 for eval/analysis
  stats.json        per-persona + overall conformance vs funnel.py anchors
  report.md         human-readable stats report
  manifest.json     counts, params snapshot, teacher, timestamp
"""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

from uniqa.persona_datagen import LLMTeacher, OfflineTeacher, generate_feed, agent_persona_prompt
from research.run import validate, format_md, PERSONAS
from research.tune import load_params


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="build locked stepwise persona dataset")
    ap.add_argument("--n", type=int, default=100, help="sessions per persona")
    ap.add_argument("--out", default="datasets/persona_v1")
    ap.add_argument("--workers", type=int, default=18)
    ap.add_argument("--model", default=None)
    ap.add_argument("--seed", type=int, default=100)
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args(argv)

    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    teacher = (OfflineTeacher() if args.offline else
               LLMTeacher(args.model, include_params=True, stepwise=True,
                          include_state=True, capture_steps=True))

    # NOTE: capture_steps writes to teacher.step_log; the LLM client is thread-safe but the
    # shared list is appended from worker threads — fine for our volume (GIL-protected append).
    by_persona = {}
    sessions_fh = (out / "sessions.jsonl").open("w")
    for persona in PERSONAS:
        print(f"generating {args.n}x {persona} (stepwise, capture) ...")
        logs = [generate_feed(persona, teacher, random.Random(args.seed + i)) for i in range(args.n)] \
            if args.workers <= 1 else _parallel(persona, args.n, teacher, args.seed, args.workers)
        by_persona[persona] = logs
        for log in logs:
            sessions_fh.write(json.dumps({"persona": persona,
                                          "events": [e.to_dict() for e in log.events]}) + "\n")
    sessions_fh.close()

    # per-step SFT pairs
    with (out / "sft_steps.jsonl").open("w") as fh:
        for s in teacher.step_log:
            fh.write(json.dumps(s, ensure_ascii=False) + "\n")

    report = validate(by_persona)
    ts = time.strftime("%Y%m%d_%H%M%S")
    (out / "stats.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    (out / "report.md").write_text(format_md(report, {"mode": "dataset", "teacher": teacher.name,
                                                       "n": args.n, "ts": ts}))
    (out / "manifest.json").write_text(json.dumps({
        "ts": ts, "teacher": teacher.name, "n_per_persona": args.n,
        "n_sessions": sum(len(v) for v in by_persona.values()),
        "n_sft_steps": len(teacher.step_log),
        "params": {p: load_params(p) for p in PERSONAS},
        "persona_prompt_chars": {p: len(agent_persona_prompt(p)) for p in PERSONAS},
    }, indent=2, ensure_ascii=False))

    print(f"\n=== dataset {out} ===")
    print(f"sessions={sum(len(v) for v in by_persona.values())}  sft_steps={len(teacher.step_log)}")
    print(format_md(report, {"mode": "dataset", "teacher": teacher.name, "n": args.n, "ts": ts}))
    return 0


def _parallel(persona, n, teacher, seed, workers):
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(lambda i: generate_feed(persona, teacher, random.Random(seed + i)), range(n)))


if __name__ == "__main__":
    raise SystemExit(main())
