"""Print per-persona S4/S5/S6 conditional churn + ε for the local-model eval JSONs,
side-by-side with the funnel.py ABANDON_PROBS targets. Usage: python leonardo/show_eval.py"""
import json
from pathlib import Path

from uniqa.funnel import ABANDON_PROBS, Step

S4, S5, S6 = Step.TARIFF_SELECT.value, Step.ADDON_SELECT.value, Step.PERSONAL_DATA.value
FILES = [("QWEN2.5-1.5B", "leonardo/out/eval_local_batched.json"),
         ("MiniCPM5-1B", "leonardo/out_minicpm/eval_local_batched.json")]


def tgt(p, step):
    return ABANDON_PROBS[p].get(step)


for name, f in FILES:
    if not Path(f).exists():
        print(f"=== {name}: not ready"); continue
    r = json.load(open(f))
    o = r.get("overall", {})
    tag = "PARTIAL" if r.get("_partial") else "FINAL"
    print(f"=== {name} [{tag}]  ε={round(o.get('epsilon_mean_abs_bounce',0),4)} "
          f"(gate 0.12 → {o.get('eps_pass')})  overall_conv={round(o.get('conversion',0),3)}")
    P = r.get("personas", {})
    for p in ("judith", "franz", "peter"):
        d = P.get(p)
        if not d:
            print(f"    {p:7} (pending)"); continue
        cb = d.get("cond_bounce", {})
        s4, s6 = cb.get(S4), cb.get(S6)
        s5 = cb.get(S5)
        s4s = f"{s4:.2f}/{tgt(p,Step.TARIFF_SELECT):.2f}" if s4 is not None else "—"
        s6s = f"{s6:.2f}/{tgt(p,Step.PERSONAL_DATA):.2f}" if s6 is not None else "—"
        s5s = f"{s5:.2f}/{tgt(p,Step.ADDON_SELECT):.2f}" if s5 is not None else "excluded(out-of-scope)"
        print(f"    {p:7} conv={d.get('conversion',0):.2f}  S4 {s4s}  S5 {s5s}  S6 {s6s}")
    t = r.get("_timing", {})
    if t:
        print("    timing:", {k: v.get("sec") for k, v in t.items()})
