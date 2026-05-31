"""
Student-view trimmer for prompt/context distillation into ONE tagged adapter.

Teacher generated each step with the FULL prompt (persona.md + dials + cognitive_model + rules
+ schema + ...). The student learns `minimal tagged input -> teacher output`, internalizing the
STATIC scaffold (persona prose + task rules/schema/cognitive_model) into weights. We keep only:
  • a persona TAG (so ONE adapter serves all personas → batchable populations), and
  • the DYNAMIC per-step context (step, real prices, running_state, disposition instance,
    history, [coach_widget], action_space legality, output schema).
Dropped (internalized): persona.md, params/dials block, consciousness preamble, cognitive_model,
rules prose, widget_response_model, conversion_definition, ux_complexity.

NOTE on dials: v2.1 internalizes dials WITH the persona tag (fixed per persona) — outlier fixes
go through regenerate+retrain. Post-hoc dial-tunability (dials in the prompt) needs dial-AUGMENTED
training data (varied dials per persona) — deferred to v2.2.

    python -m research.student_view --in datasets/persona_v2/sft_steps.jsonl --out leonardo/data_tagged
"""
from __future__ import annotations

import argparse, json, random
from pathlib import Path

# dynamic keys to KEEP from the teacher's user dict (everything else is static → internalized)
_KEEP = {"you_are_on", "ui_ascii", "action_space", "your_running_state", "history_brief",
         "session_instance", "your_initial_intent", "output_schema", "coach_widget_shown",
         "tariff_economics_for_your_age", "final_price", "tariff_coverage_brief"}
# level 2 (aggressive) also internalizes legality/schema/ascii
_DROP_L2 = {"action_space", "output_schema", "ui_ascii"}

_SYS = ("You are simulating a real user going through the UNIQA online health-insurance "
        "calculator, ONE step at a time. persona: {tag}. Emit this step's events + state + "
        "stay/leave decision as JSON, in character.")


def student_messages(row: dict, level: int = 1) -> dict:
    persona = row["persona"]
    full = json.loads(row["input_messages"][1]["content"])
    keep = set(_KEEP) - (_DROP_L2 if level >= 2 else set())
    user = {k: v for k, v in full.items() if k in keep}
    return {"messages": [{"role": "system", "content": _SYS.format(tag=persona)},
                         {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
                         {"role": "assistant", "content": row["output"]}],
            "persona": persona, "step": row["step"], "decision": row.get("decision")}


def _toks(msgs):
    return round(sum(len(m["content"]) for m in msgs) / 4)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="datasets/persona_v2/sft_steps.jsonl")
    ap.add_argument("--out", default="leonardo/data_tagged")
    ap.add_argument("--level", type=int, default=1)
    ap.add_argument("--val_frac", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)

    rows = [json.loads(l) for l in Path(args.inp).open()]
    # validity gate: only well-formed teacher JSON outputs
    rows = [r for r in rows if _valid(r.get("output"))]
    sv = [student_messages(r, args.level) for r in rows]

    # token reduction report (sample 200)
    k = min(200, len(rows))
    full_avg = round(sum(round((len(r["input_messages"][0]["content"]) +
                                len(r["input_messages"][1]["content"])) / 4) for r in rows[:k]) / k)
    lean_avg = round(sum(_toks(s["messages"][:2]) for s in sv[:k]) / k)
    print(f"rows={len(sv)}  level={args.level}  prompt tokens: full~{full_avg} -> student~{lean_avg} "
          f"({100*(full_avg-lean_avg)/full_avg:.0f}% smaller, {full_avg/max(lean_avg,1):.1f}x)")

    # ONE combined tagged train/val set (all personas)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed); rng.shuffle(sv)
    n_val = max(1, int(len(sv) * args.val_frac))
    for split, data in (("val", sv[:n_val]), ("train", sv[n_val:])):
        with (out / f"{split}.jsonl").open("w") as fh:
            for s in data:
                fh.write(json.dumps({"messages": s["messages"]}, ensure_ascii=False) + "\n")
    from collections import Counter
    summ = {"n_train": len(sv) - n_val, "n_val": n_val, "level": args.level,
            "persona_mix": dict(Counter(s["persona"] for s in sv)),
            "decision_mix": dict(Counter(s["decision"] for s in sv)),
            "prompt_tokens_full": full_avg, "prompt_tokens_student": lean_avg}
    (out / "summary.json").write_text(json.dumps(summ, indent=2, ensure_ascii=False))
    print(json.dumps(summ, indent=2, ensure_ascii=False))
    return 0


def _valid(o):
    try:
        json.loads(o if isinstance(o, str) else "{}"); return True
    except Exception:
        return False


if __name__ == "__main__":
    raise SystemExit(main())
