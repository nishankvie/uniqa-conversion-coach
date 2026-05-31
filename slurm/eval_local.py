"""
Eval the LOCAL fine-tuned persona models with the SAME statistical gate as the frontier
teacher. Each persona uses its own adapter; we generate that persona's sessions locally and
validate per-(persona,step) bounce + conversion vs the funnel.py anchors. Goal: local
inference statistically close to the frontier-generated dataset (the lock criterion).

    python leonardo/eval_local.py --base Qwen/Qwen2.5-1.5B-Instruct --adapters leonardo/out --n 100
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from persona.persona_datagen import generate_feed
from research.run import validate, format_md, PERSONAS
from leonardo.local_teacher import LocalTeacher


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="Qwen/Qwen2.5-1.5B-Instruct")
    ap.add_argument("--adapters", default="leonardo/out")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seed", type=int, default=500)
    args = ap.parse_args(argv)

    by_persona = {}
    for persona in PERSONAS:
        adapter = str(Path(args.adapters) / persona)
        print(f"loading local model for {persona}: {adapter}")
        teacher = LocalTeacher(args.base, adapter)
        by_persona[persona] = [generate_feed(persona, teacher, random.Random(args.seed + i))
                               for i in range(args.n)]
        del teacher

    report = validate(by_persona)
    print(format_md(report, {"mode": "eval:local-model", "teacher": f"local:{args.base}",
                             "n": args.n, "ts": "-"}))
    out_json = Path(args.adapters) / "eval_local.json"
    report["_base"] = args.base
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"wrote {out_json}")
    # Compare to the frontier dataset stats for "statistically close" verdict.
    ds = Path("datasets/persona_v1/stats.json")
    if ds.exists():
        front = json.loads(ds.read_text())["overall"]["epsilon_mean_abs_bounce"]
        print(f"\nfrontier ε={front}  vs  local ε={report['overall']['epsilon_mean_abs_bounce']}")
    return 0 if report["overall"]["eps_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
