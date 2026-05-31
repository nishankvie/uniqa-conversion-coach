"""Autoresearch (Loop A) — self-improve the COACH policy against the persona sim.

    PROPOSE  a coach-policy variant Δ (add/remove a directive, shift budget/temperature)
    SIMULATE the on-arm over a FIXED paired persona assignment (the off-arm = shared control)
    EVALUATE Δ̂uplift = conv_rate(on, variant) − conv_rate(off, control)
    GATE     accept iff  Δ̂uplift > incumbent_uplift + τ   AND   annoyance ≤ ceiling
    REPEAT   accepted variant becomes the incumbent

Efficiency: the off control is run ONCE (same assignment + seeds), so every variant's
conv_on is directly comparable and we never re-pay for the baseline. Mutations are small
and auditable (the formalization's requirement). The empirical gate stands in for the
deferred Z3 certificate (accept iff Δ̂ > τ); τ should exceed the sim's noise band.

Ledger: out/autoresearch/{ledger.jsonl, best_policy.json, report.md}.

Usage:
  python sim_loop/autoresearch.py --rounds 6 --sessions 12 --tau 0.02 --concurrency 8
  python sim_loop/autoresearch.py --rounds 8 --sessions 16 --proposer llm --concurrency 8
"""
from __future__ import annotations
import argparse, json, pathlib, random, sys, time
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run as R                       # run_session, POOLS, REAL, BALANCED
from coach import COACH_SYSTEM, EFFECTORS
from llm import chat, extract_json

# ── auditable tactic library the proposer toggles ────────────────────────────────
DIRECTIVES = [
    "At the price walls (S4 first price, S7 final price), prefer price_reframe or pricing_explain over a generic nudge.",
    "If the user moves fast and decisively through the early steps, STAY SILENT early and save the budget for the final price (S7).",
    "On the long forms (S3 personal info, S6 personal data), use form_explainer pre-emptively or form_simplify — not a weak nudge.",
    "Only offer advisor_handoff or callback_offer after repeated hesitation or back-navigation — never as a first move, never for Franz.",
    "When the log shows tooltip opens / term selection / copying, use coverage_explain or coverage_checker on that exact term.",
    "Spend at most one intervention before S4; the price walls are where help matters most.",
    "If the final price likely jumped at S7, lead with health_explain or value_justification to defuse the surprise.",
    "When the log shows long dwell + repeated tariff hovers without a selection, use package_nuance or preselect_optimal.",
    "For an overwhelmed, slow, mobile-looking user (Peter), prefer an early handoff: callback_offer, whatsapp_bot, or contact_handoff before the price wall.",
]


@dataclass(frozen=True)
class Policy:
    directives: tuple[str, ...] = ()
    budget: int = 2
    temperature: float = 0.4

    @property
    def system(self) -> str:
        if not self.directives:
            return COACH_SYSTEM
        body = "\n".join(f"- {d}" for d in self.directives)
        return COACH_SYSTEM + "\n\nADDITIONAL POLICY DIRECTIVES (current experiment):\n" + body

    @property
    def label(self) -> str:
        return f"budget={self.budget} temp={self.temperature} directives={len(self.directives)}"

    def to_dict(self) -> dict:
        return {"budget": self.budget, "temperature": self.temperature,
                "directives": list(self.directives)}


BASE = Policy()


# ── proposers ────────────────────────────────────────────────────────────────────
def propose_mutate(p: Policy, rng: random.Random, pool: list[str]) -> Policy:
    """One small, reversible edit: toggle a directive, or nudge budget/temperature."""
    for _ in range(8):
        op = rng.choice(["toggle", "toggle", "budget", "temp"])
        dirs, b, t = list(p.directives), p.budget, p.temperature
        if op == "toggle" and pool:
            d = rng.choice(pool)
            dirs.remove(d) if d in dirs else dirs.append(d)
        elif op == "budget":
            b = max(1, min(3, b + rng.choice([-1, 1])))
        else:
            t = round(max(0.2, min(0.7, t + rng.choice([-0.1, 0.1]))), 1)
        cand = Policy(tuple(dirs), b, t)
        if cand != p:
            return cand
    return p


def propose_llm(p: Policy, on_results: list[dict], model: str | None, rng: random.Random,
                pool: list[str]) -> Policy:
    """Read the incumbent's traces (which effectors → which outcomes) and ask an LLM for
    ONE directive to add. Falls back to a structured mutation on any failure."""
    traces = []
    for r in on_results:
        acts = [s["coach_decision"]["command"]["effector"]
                for s in r["steps"] if s.get("coach_decision", {}).get("_acted")]
        traces.append({"persona": r["persona"], "outcome": r["outcome"], "interventions": acts})
    sys_msg = ("You tune a sales-coach policy for an insurance funnel. Given traces of which "
               "coach interventions (effectors) were used per session and the outcome "
               "(convert / advisor_handoff / abandon), propose ONE short, concrete policy "
               "DIRECTIVE that should raise conversion. Be specific about WHEN to use WHICH "
               f"effector. Effectors: {', '.join(EFFECTORS)}. Reply as JSON "
               '{"directive": "<one sentence>"}.')
    try:
        raw = chat([{"role": "system", "content": sys_msg},
                    {"role": "user", "content": json.dumps({"current_directives": list(p.directives),
                     "traces": traces}, ensure_ascii=False)}],
                   model=model, temperature=0.7, max_tokens=120)
        d = (extract_json(raw).get("directive") or "").strip()
        if d and d not in p.directives:
            return Policy(p.directives + (d,), p.budget, p.temperature)
    except Exception as e:
        sys.stderr.write(f"[propose_llm] fell back ({type(e).__name__})\n")
    return propose_mutate(p, rng, pool)


# ── evaluation (shared off-control, paired on-arm) ───────────────────────────────
def run_arm(assign: list[str], arm: str, policy: Policy, model: str | None,
            concurrency: int, base_seed: int) -> list[dict]:
    jobs, results = [], []
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        for i, seg in enumerate(assign):
            jobs.append(ex.submit(R.run_session, seg, arm, model, policy.budget,
                                  base_seed * 100000 + i,
                                  coach_system=policy.system,
                                  coach_temperature=policy.temperature))
        for fut in as_completed(jobs):
            try:
                results.append(fut.result())
            except Exception as e:
                sys.stderr.write(f"[session] {e}\n")
    return results


def metrics(results: list[dict]) -> dict:
    n = len(results) or 1
    conv = sum(1 for r in results if r["outcome"] == "convert")
    adv = sum(1 for r in results if r["outcome"] == "advisor_handoff")
    interv = sum(r["coach_interventions"] for r in results)
    return {"n": len(results), "convert": conv, "convert_rate": round(conv / n, 3),
            "advisor": adv, "interventions_per_session": round(interv / n, 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=6)
    ap.add_argument("--sessions", type=int, default=12, help="sessions per arm (paired)")
    ap.add_argument("--tau", type=float, default=0.02, help="acceptance margin over incumbent")
    ap.add_argument("--annoyance-ceiling", type=float, default=2.0, help="max interventions/session")
    ap.add_argument("--proposer", choices=["mutate", "llm"], default="mutate")
    ap.add_argument("--proportions", choices=["real", "balanced"], default="real")
    ap.add_argument("--model", default=None)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="sim_loop/out/autoresearch")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    weights = R.REAL if args.proportions == "real" else R.BALANCED
    pool = list(weights.keys()); wts = [weights[p] for p in pool]
    assign = [rng.choices(pool, wts)[0] for _ in range(args.sessions)]

    est = (1 + args.rounds) * args.sessions * 16
    print(f"≈ {est} teacher calls ({1 + args.rounds} arms × {args.sessions} sessions × ~16) "
          f"@ {args.concurrency} workers → ~{est / args.concurrency * 2.5 / 60:.0f} min\n")

    outd = pathlib.Path(args.out); outd.mkdir(parents=True, exist_ok=True)
    ledger = (outd / "ledger.jsonl").open("w")

    def log(rec): ledger.write(json.dumps(rec, ensure_ascii=False) + "\n"); ledger.flush()

    t0 = time.time()
    # 1) shared control (coach off) — run ONCE
    off = run_arm(assign, "off", BASE, args.model, args.concurrency, args.seed)
    m_off = metrics(off); conv_off = m_off["convert_rate"]
    print(f"[control off] convert_rate={conv_off}  (n={m_off['n']})")
    log({"round": 0, "kind": "control_off", **m_off})

    # 2) incumbent = base coach policy
    on = run_arm(assign, "on", BASE, args.model, args.concurrency, args.seed)
    m_on = metrics(on); inc_uplift = round(m_on["convert_rate"] - conv_off, 3)
    incumbent = BASE; inc_metrics = m_on; inc_results = on
    print(f"[incumbent base] conv_on={m_on['convert_rate']} uplift={inc_uplift:+.3f} "
          f"annoy={m_on['interventions_per_session']}")
    log({"round": 0, "kind": "incumbent_base", "policy": incumbent.to_dict(),
         "conv_off": conv_off, "uplift": inc_uplift, **m_on})

    # 3) propose → evaluate → gate
    for rnd in range(1, args.rounds + 1):
        cand = (propose_llm(incumbent, inc_results, args.model, rng, pool)
                if args.proposer == "llm" else propose_mutate(incumbent, rng, pool))
        res = run_arm(assign, "on", cand, args.model, args.concurrency, args.seed)
        m = metrics(res); uplift = round(m["convert_rate"] - conv_off, 3)
        annoy = m["interventions_per_session"]
        accept = (uplift > inc_uplift + args.tau) and (annoy <= args.annoyance_ceiling)
        flag = "✅ ACCEPT" if accept else "·  reject"
        print(f"[round {rnd}] {flag}  conv_on={m['convert_rate']} uplift={uplift:+.3f} "
              f"(inc {inc_uplift:+.3f}+τ{args.tau}) annoy={annoy}  | {cand.label}")
        log({"round": rnd, "kind": "candidate", "policy": cand.to_dict(),
             "conv_off": conv_off, "conv_on": m["convert_rate"], "uplift": uplift,
             "incumbent_uplift": inc_uplift, "annoyance": annoy, "tau": args.tau,
             "accepted": accept, **{f"m_{k}": v for k, v in m.items()}})
        if accept:
            incumbent, inc_uplift, inc_metrics, inc_results = cand, uplift, m, res

    ledger.close()
    (outd / "best_policy.json").write_text(json.dumps(
        {"policy": incumbent.to_dict(), "system_prompt": incumbent.system,
         "conv_off": conv_off, "uplift": inc_uplift, "metrics": inc_metrics,
         "rounds": args.rounds, "sessions_per_arm": args.sessions}, ensure_ascii=False, indent=2))
    report = (f"# Autoresearch result\n\n"
              f"- rounds: {args.rounds} · sessions/arm: {args.sessions} · proposer: {args.proposer} · τ={args.tau}\n"
              f"- control (coach off) conversion: **{conv_off}**\n"
              f"- best coach uplift: **{inc_uplift:+.3f}** (conv_on {inc_metrics['convert_rate']}, "
              f"annoyance {inc_metrics['interventions_per_session']}/session)\n"
              f"- wall: {time.time() - t0:.0f}s\n\n## Best policy\n"
              f"- budget {incumbent.budget} · temperature {incumbent.temperature}\n"
              + ("".join(f"- {d}\n" for d in incumbent.directives) or "- (base prompt, no directives added)\n")
              + f"\nLedger: `{outd / 'ledger.jsonl'}` · best: `{outd / 'best_policy.json'}`\n")
    (outd / "report.md").write_text(report)
    print(f"\nBEST uplift {inc_uplift:+.3f} over {conv_off} control · "
          f"{len(incumbent.directives)} directives · artifacts → {outd}")


if __name__ == "__main__":
    main()
