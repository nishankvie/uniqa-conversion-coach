"""
BATCHED eval of the local fine-tuned persona models — same statistical gate as the frontier
teacher, but generations are batched per step (cohort lockstep) for a big throughput win.
Reports wall-time + sessions/sec so we can see the speedup vs the sequential eval.

    python leonardo/eval_local_batched.py --base $HOME/models/qwen2.5-1.5b \
        --adapters leonardo/out --n 100 --batch_size 48
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from research.run import validate, format_md, PERSONAS
from leonardo.batched_teacher import BatchedLocalTeacher


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--adapters", default="leonardo/out")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--batch_size", type=int, default=100)
    ap.add_argument("--max_new_tokens", type=int, default=448)
    ap.add_argument("--seed", type=int, default=500)
    args = ap.parse_args(argv)

    out_json = Path(args.adapters) / "eval_local_batched.json"
    by_persona, timing = {}, {}
    for persona in PERSONAS:
        adapter = str(Path(args.adapters) / persona)
        print(f"[{persona}] loading {adapter} ...", flush=True)
        try:
            teacher = BatchedLocalTeacher(args.base, adapter, batch_size=args.batch_size,
                                          max_new_tokens=args.max_new_tokens)
            t0 = time.time()
            by_persona[persona] = teacher.generate_cohort(persona, args.n, seed=args.seed)
            dt = time.time() - t0
            timing[persona] = {"sec": round(dt, 1), "sessions_per_sec": round(args.n / dt, 2)}
            print(f"[{persona}] {args.n} sessions in {dt:.1f}s  ({args.n/dt:.2f}/s)", flush=True)
            del teacher
        except Exception as e:
            print(f"[{persona}] FAILED: {type(e).__name__}: {e}", flush=True)
            continue
        # incremental partial write (survive a later crash)
        if by_persona:
            part = validate(by_persona)
            part["_base"] = args.base; part["_timing"] = timing; part["_partial"] = True
            out_json.write_text(json.dumps(part, indent=2, ensure_ascii=False))

    if not by_persona:
        print("no personas evaluated — aborting", flush=True)
        return 1
    report = validate(by_persona)
    report["_base"] = args.base
    report["_timing"] = timing
    report["_mode"] = f"batched(bs={args.batch_size})"
    total = sum(t["sec"] for t in timing.values()) or 1
    print(format_md(report, {"mode": f"eval:local-batched bs={args.batch_size}",
                             "teacher": f"local:{args.base}", "n": args.n, "ts": "-"}))
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nwrote {out_json}")
    print(f"TOTAL gen wall-time: {total:.1f}s for {3*args.n} sessions  "
          f"({3*args.n/total:.2f} sessions/s)")
    ds = Path("datasets/persona_v1/stats.json")
    if ds.exists():
        front = json.loads(ds.read_text())["overall"]["epsilon_mean_abs_bounce"]
        print(f"frontier ε={front}  vs  local-batched ε={report['overall']['epsilon_mean_abs_bounce']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
