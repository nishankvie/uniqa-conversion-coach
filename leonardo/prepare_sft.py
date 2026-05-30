"""
Prepare per-persona SFT files from the stepwise dataset for LoRA fine-tuning on Leonardo.

Distillation target: a PER-STEP persona model (the coach widget will intervene per step, so
the local model must be a per-step function). Each training example = the step's
input_messages (system persona+dials+cognitive_model, user step-context) + the teacher's
JSON output as the assistant turn. One file per persona -> three specialised local models.

    python leonardo/prepare_sft.py --in datasets/persona_v1/sft_steps.jsonl --out leonardo/data

Writes leonardo/data/<persona>.{train,val}.jsonl in chat format: {"messages":[...]}.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="datasets/persona_v1/sft_steps.jsonl")
    ap.add_argument("--out", default="leonardo/data")
    ap.add_argument("--val_frac", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)

    rows = [json.loads(l) for l in Path(args.inp).open()]
    by_persona: dict[str, list] = {}
    for r in rows:
        # only keep well-formed completions (valid JSON the model should learn to emit)
        try:
            json.loads(r["output"])
        except Exception:
            continue
        by_persona.setdefault(r["persona"], []).append(r)

    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    summary = {}
    for persona, items in by_persona.items():
        rng.shuffle(items)
        n_val = max(1, int(len(items) * args.val_frac))
        splits = {"val": items[:n_val], "train": items[n_val:]}
        for split, data in splits.items():
            with (out / f"{persona}.{split}.jsonl").open("w") as fh:
                for r in data:
                    msgs = list(r["input_messages"]) + [{"role": "assistant", "content": r["output"]}]
                    fh.write(json.dumps({"messages": msgs}, ensure_ascii=False) + "\n")
        summary[persona] = {"train": len(splits["train"]), "val": len(splits["val"]),
                            "steps": dict(Counter(x["step"] for x in items))}
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
