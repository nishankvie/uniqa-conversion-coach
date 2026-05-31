"""Exact statistics of the persona_v2 per-step dataset: per-(persona,step) leave-rate with
Wilson 95% CI + n, decision balance, and the IMPLIED in-scope funnel (reach / conditional
churn / implied conversion) vs the funnel.py anchors. These are the dataset's own per-step
rates over the SAMPLED state mix — the coherent-rollout marginal is measured separately
(research/compare_gen.py / the rollout eval)."""
import json, math
from collections import defaultdict
from pathlib import Path
from uniqa.funnel import ABANDON_PROBS, PERSONA_WEIGHTS, Step

F = "datasets/persona_v2/sft_steps.jsonl"
ORDER = [Step.COVERAGE_TYPE, Step.INSURED, Step.PERSONAL_INFO, Step.TARIFF_SELECT, Step.PERSONAL_DATA]
BOUNCE = [Step.PERSONAL_INFO, Step.TARIFF_SELECT, Step.PERSONAL_DATA]  # cells used in ε (S3/S4/S6)


def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None)
    p = k / n; d = 1 + z*z/n
    c = (p + z*z/(2*n)) / d
    h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return (round(c-h, 3), round(c+h, 3))


def main():
    rows = [json.loads(l) for l in Path(F).open()]
    cnt = defaultdict(lambda: [0, 0])   # (persona,step) -> [leave, total]
    dec = defaultdict(int)
    for r in rows:
        cnt[(r["persona"], r["step"])][r["decision"] == "leave"] += 0  # noop init
    cnt = defaultdict(lambda: {"leave": 0, "n": 0})
    for r in rows:
        c = cnt[(r["persona"], r["step"])]; c["n"] += 1; c["leave"] += (r["decision"] == "leave")
        dec[r["decision"]] += 1

    print(f"rows={len(rows)}  decision balance: {dict(dec)}  "
          f"(leave share {dec['leave']/(dec['leave']+dec['continue']):.3f})\n")

    print("per-(persona,step) leave-rate  [obs / target]  (n, 95% CI):")
    eps_cells = []
    implied = {}
    for persona in ("judith", "franz", "peter"):
        surv = 1.0; conv = 1.0
        print(f"\n {persona}:")
        for st in ORDER:
            c = cnt[(persona, st.value)]
            if c["n"] == 0:
                print(f"    {st.value:18} (no data)"); continue
            obs = c["leave"]/c["n"]
            tgt = ABANDON_PROBS[persona].get(st)
            ci = wilson(c["leave"], c["n"])
            mark = ""
            if st in BOUNCE and tgt is not None:
                d = abs(obs - tgt); eps_cells.append(d)
                mark = f"  Δ={d:.3f}"
            tstr = f"{tgt:.2f}" if tgt is not None else "—"
            print(f"    {st.value:18} {obs:.3f} / {tstr}   (n={c['n']}, CI {ci}){mark}")
            conv *= (1 - obs)
        implied[persona] = conv
        print(f"    → implied online conversion (∏ survive) = {conv:.3f}  "
              f"(anchor-implied {_anchor_conv(persona):.3f})")

    eps = sum(eps_cells)/len(eps_cells) if eps_cells else None
    overall = sum(PERSONA_WEIGHTS[p]*implied[p] for p in implied)
    anchor_overall = sum(PERSONA_WEIGHTS[p]*_anchor_conv(p) for p in implied)
    print(f"\nε (mean |obs−target| over S3/S4/S6 cells) = {eps:.4f}  (gate 0.12)")
    print(f"implied weighted conversion = {overall:.3f}   (anchor-implied {anchor_overall:.3f})")
    print("\nNOTE: these are per-step rates over the SAMPLED state mix (mood 0.5/0.3/0.2), NOT a "
          "coherent rollout. The rollout marginal + Stage-2 calibration are evaluated separately.")


def _anchor_conv(persona):
    p = 1.0
    for st in BOUNCE:
        p *= (1 - ABANDON_PROBS[persona].get(st, 0.0))
    return p


if __name__ == "__main__":
    main()
