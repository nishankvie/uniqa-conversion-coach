"""Run the persona <-> widget <-> coach loop and generate a dataset.

Two arms, written to two files:
  sessions_coach_off.jsonl  — coach ALWAYS skips (control)
  sessions_coach_on.jsonl   — coach is active (LLM policy, annoyance budget)

Loop (observe-then-act):
  session start
   for step in funnel:
     widget.render(step, state, history, session_instance, intent, coach_injection)
     persona.step()            -> events + decision + new state + feeling (may LEAVE)
     coach.decide(FILTERED log) -> effector | NO_ACTION  (applies to NEXT screen)
     advance / terminate
  session end  (convert | abandon | advisor_handoff)

Usage:
  python sim_loop/run.py --sessions 30 --proportions real --out sim_loop/out
  python sim_loop/run.py --sessions 6 --arms off,on --coach-budget 2 --concurrency 4
"""
from __future__ import annotations
import argparse, json, os, random, sys, pathlib, time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import widget
from persona import LLMPersona
from coach import CoachModel

POOLS = json.loads((pathlib.Path(__file__).resolve().parent / "session_pools.json").read_text())
PERSONAS = ["judith", "franz", "peter"]
# normalized real segment shares (segment_share 0.155/0.305/0.292 -> renormalized)
REAL = {"judith": 0.206, "franz": 0.406, "peter": 0.388}
BALANCED = {"judith": 1 / 3, "franz": 1 / 3, "peter": 1 / 3}


def sample_session_instance(rng: random.Random) -> dict:
    p = POOLS["pools"]
    return {k: rng.choice(v) for k, v in p.items()}


def filtered_event(e: dict) -> dict:
    """Coach-visible view: drop thought; keep observable fields only."""
    return {k: e.get(k) for k in ("step", "type", "target", "value", "t") if k in e}


# Persona-dependent CONVERSION (the formalization's reward ρ): the RIGHT outcome differs by
# segment. Judith: online OR a clean advisor handoff. Franz: online ONLY (advisor = failure).
# Peter: a qualified service contact (callback / WhatsApp / phone) — his handoff IS his conversion.
SUCCESS = {
    "judith": {"convert", "advisor_handoff"},
    "franz": {"convert"},
    "peter": {"advisor_handoff", "convert"},
}


def is_success(persona: str, outcome: str) -> bool:
    return outcome in SUCCESS.get(persona, {"convert"})


def classify_outcome(decision: str, reason: str, last_step: bool) -> str:
    if decision == "continue" and last_step:
        return "convert"
    if decision == "leave":
        r = (reason or "").lower()
        if any(k in r for k in ("advisor", "person", "call", "human", "whatsapp",
                                "phone", "contact", "agent", "berat")):
            return "advisor_handoff"   # = a service contact / human handoff
        return "abandon"
    return "in_progress"


def run_session(seg: str, arm: str, model: str, coach_budget: int, seed: int,
                temperature: float = 0.8, coach_system: str | None = None,
                coach_temperature: float | None = None) -> dict:
    rng = random.Random(seed)
    si = sample_session_instance(rng)
    persona = LLMPersona(seg, si, POOLS["start_state"], model=model,
                         temperature=temperature)
    coach = CoachModel(mode=("active" if arm == "on" else "skip"),
                       model=model, budget=coach_budget, system=coach_system,
                       temperature=(coach_temperature if coach_temperature is not None else 0.4))
    activity_log: list = []
    steps_rec: list = []
    outcome = "abandon"
    step = widget.first_step()
    while step is not None:
        # ANTICIPATORY coaching: the coach observes the trajectory SO FAR and may PRE-PLACE one
        # widget on THIS screen — so a well-timed intervention is present WHEN the persona decides
        # this step (it can pre-empt the wall it's about to hit), not uselessly on the next screen.
        coach_dec = coach.decide([filtered_event(e) for e in activity_log if isinstance(e, dict)],
                                 step=step)
        coach_injection = coach_dec["command"] if coach_dec.get("_acted") else None

        screen = widget.render(step, persona.state, list(persona.history_brief),
                               si, persona.initial_intent, coach_injection)
        out = persona.step(screen)
        evs = out.get("events", []) or []
        for e in evs:
            if isinstance(e, dict):
                e.setdefault("step", step)
                activity_log.append(e)
        decision = out.get("decision", "leave")
        last = widget.next_step(step) is None

        steps_rec.append({
            "step": step,
            "shown_coach": screen.get("coach_intervention_shown"),
            "persona_output": out,
            "coach_decision": coach_dec,
        })

        outcome = classify_outcome(decision, out.get("reason", ""), last)
        if decision == "leave":
            break
        if last:
            outcome = "convert"
            break
        step = widget.next_step(step)

    return {
        "persona": seg,
        "arm": arm,
        "session_instance": si,
        "outcome": outcome,
        "n_steps": len(steps_rec),
        "coach_interventions": coach.used,
        "steps": steps_rec,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sessions", type=int, default=20, help="sessions PER ARM")
    ap.add_argument("--arms", default="off,on")
    ap.add_argument("--proportions", choices=["real", "balanced"], default="real")
    ap.add_argument("--coach-budget", type=int, default=2)
    ap.add_argument("--model", default=None)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="sim_loop/out")
    args = ap.parse_args()

    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    weights = REAL if args.proportions == "real" else BALANCED
    rng = random.Random(args.seed)
    pool = list(weights.keys())
    wts = [weights[p] for p in pool]

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # pre-sample the persona assignment so both arms share the SAME persona mix
    assign = [rng.choices(pool, wts)[0] for _ in range(args.sessions)]

    summary = {}
    for arm in arms:
        fname = out_dir / f"sessions_coach_{'off' if arm=='off' else 'on'}.jsonl"
        jobs = []
        with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
            for i, seg in enumerate(assign):
                jobs.append(ex.submit(run_session, seg, arm, args.model,
                                      args.coach_budget, args.seed * 100000 + i))
            results = []
            for fut in as_completed(jobs):
                try:
                    results.append(fut.result())
                except Exception as e:
                    sys.stderr.write(f"[session] failed: {e}\n")
        with open(fname, "w") as f:
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        # arm summary
        n = len(results)
        conv = sum(1 for r in results if r["outcome"] == "convert")
        adv = sum(1 for r in results if r["outcome"] == "advisor_handoff")
        ab = sum(1 for r in results if r["outcome"] == "abandon")
        succ = sum(1 for r in results if is_success(r["persona"], r["outcome"]))
        interv = sum(r["coach_interventions"] for r in results)
        summary[arm] = {"file": str(fname), "n": n,
                        "convert": conv, "convert_rate": round(conv / n, 3) if n else 0,
                        "success": succ, "success_rate": round(succ / n, 3) if n else 0,
                        "advisor": adv, "abandon": ab, "coach_interventions": interv}
        print(f"[arm {arm}] n={n} convert={conv} ({summary[arm]['convert_rate']}) "
              f"success={succ} ({summary[arm]['success_rate']}) "
              f"advisor={adv} abandon={ab} interventions={interv} -> {fname}")

    (out_dir / "summary.json").write_text(json.dumps({
        "args": vars(args), "persona_mix": dict(zip(*[pool, [assign.count(p) for p in pool]])),
        "arms": summary,
    }, ensure_ascii=False, indent=2))
    if "off" in summary and "on" in summary:
        d = summary["on"]["convert_rate"] - summary["off"]["convert_rate"]
        ds = summary["on"]["success_rate"] - summary["off"]["success_rate"]
        print(f"\nUPLIFT (on - off): online convert {d:+.3f}  |  persona-success {ds:+.3f}  "
              f"(coach interventions: {summary['on']['coach_interventions']})")
    print(f"summary -> {out_dir/'summary.json'}")


if __name__ == "__main__":
    main()
