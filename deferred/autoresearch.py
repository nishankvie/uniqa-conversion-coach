"""
UNIQA Coach — Autoresearch loop (self-improving Coach).

The Coach improves itself without touching production traffic:

    ┌─────────────────────────────────────────────────────────────┐
    │  1. PROPOSE   perturb the current policy vector (COACH_GAIN)  │
    │  2. SIMULATE  run the psyche persona model → synthetic cohort │
    │  3. EVALUATE  evals engine measures conversion uplift         │
    │  4. GATE      accept ONLY if sim-uplift gain > τ (margin)     │
    │  5. REPEAT    accepted policy becomes the new incumbent       │
    └─────────────────────────────────────────────────────────────┘

Central claim (proved in deferred/coach_autoimprove_z3.py):

    IF the persona model is statistically close to reality
       (estimator bias |U_sim − U_real| ≤ L·ε),
    AND the acceptance margin τ exceeds that bias (τ > L·ε),
    THEN every accepted policy is a *real* improvement, the incumbent's
    real conversion is monotonically non-decreasing, and (policy space
    being finite/compact) the loop converges to a local optimum.

This module is the executable evals + experimentation engine; the Z3 spec is the
formal certificate of the gating rule that makes the loop sound.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Optional

from persona.psyche import set_coach_gain
from calculator.journey import run_batch

# The 11 coachable effects form the policy vector (NONE has no effect).
POLICY_KEYS = [
    "price_reframe", "upgrade_explain", "coverage_explain", "health_explain",
    "trust_signal", "upgrade_path", "form_helper", "progress_saver",
    "callback_offer", "advisor_handoff", "feature_highlight",
]

# Search bounds for each gain. 1.0 == hand-calibrated baseline.
GAIN_MIN, GAIN_MAX = 0.0, 2.0


# ─── Policy ───────────────────────────────────────────────────────────────────

@dataclass
class CoachPolicy:
    """A tunable Coach policy = a gain multiplier per coach effect."""
    gains: dict[str, float] = field(default_factory=lambda: {k: 1.0 for k in POLICY_KEYS})

    def clamped(self) -> "CoachPolicy":
        return CoachPolicy({k: max(GAIN_MIN, min(GAIN_MAX, v)) for k, v in self.gains.items()})

    def install(self) -> None:
        set_coach_gain(self.gains)

    @staticmethod
    def baseline() -> "CoachPolicy":
        return CoachPolicy()


# ─── Evals engine ─────────────────────────────────────────────────────────────

@dataclass
class EvalResult:
    uplift: float            # primary objective: coach_on − coach_off conversion
    conv_on: float
    conv_off: float
    annoyance_proxy: float   # avg messages (intervention cost) — guardrail
    whatsapp_leads: int


def evaluate_policy(policy: CoachPolicy, n: int = 4000, seed: int = 42) -> EvalResult:
    """
    Evaluate a policy on the synthetic persona cohort.

    The SAME persona draws (seed) are used for coach-on and coach-off, so the
    measured uplift is a paired estimate — this is the evals engine the Z3 proof
    refers to as U_sim(policy).
    """
    # baseline conversion never depends on coach gains (coach off)
    set_coach_gain(None)
    off = run_batch(n=n, seed=seed, coach_on=False)

    policy.clamped().install()
    on = run_batch(n=n, seed=seed, coach_on=True)
    set_coach_gain(None)  # leave global state clean

    return EvalResult(
        uplift=on.conversion_rate - off.conversion_rate,
        conv_on=on.conversion_rate,
        conv_off=off.conversion_rate,
        annoyance_proxy=on.avg_messages,
        whatsapp_leads=on.whatsapp_leads,
    )


# ─── Experimentation: propose a neighbour ──────────────────────────────────────

def propose(policy: CoachPolicy, rng: random.Random, step: float = 0.25,
            k: int = 2) -> CoachPolicy:
    """Perturb k randomly chosen gains by ±step (a local search proposal)."""
    g = dict(policy.gains)
    for key in rng.sample(POLICY_KEYS, k=min(k, len(POLICY_KEYS))):
        g[key] += rng.choice([-step, step])
    return CoachPolicy(g).clamped()


# ─── The loop ───────────────────────────────────────────────────────────────

@dataclass
class Round:
    i: int
    accepted: bool
    incumbent_uplift: float
    candidate_uplift: float
    gain_over_incumbent: float
    annoyance_proxy: float


@dataclass
class AutoResearchResult:
    rounds: list[Round]
    start_policy: CoachPolicy
    best_policy: CoachPolicy
    start_uplift: float
    best_uplift: float

    @property
    def total_gain(self) -> float:
        return self.best_uplift - self.start_uplift


def autoresearch(
    rounds: int = 30,
    tau: float = 0.004,                 # acceptance margin τ (must exceed L·ε)
    annoyance_ceiling: float = 1.6,     # guardrail: avg messages/session
    n: int = 4000,
    seed: int = 42,
    start: Optional[CoachPolicy] = None,
    on_round: Optional[Callable[[Round], None]] = None,
) -> AutoResearchResult:
    """
    Hill-climb the Coach policy under a sound acceptance gate.

    Acceptance rule (the part the Z3 proof certifies):
        accept candidate  ⇔  (U_sim(cand) − U_sim(incumbent) > τ)
                              ∧ (annoyance(cand) ≤ annoyance_ceiling)

    Because acceptance requires a sim-gain strictly greater than τ, and (by the
    closeness assumption) the sim estimator's bias is ≤ L·ε < τ, every accepted
    candidate is a real improvement ⇒ the incumbent's real uplift is monotone
    non-decreasing.
    """
    rng = random.Random(seed)
    incumbent = (start or CoachPolicy.baseline()).clamped()
    inc_eval = evaluate_policy(incumbent, n=n, seed=seed)
    start_uplift = inc_eval.uplift

    history: list[Round] = []
    for i in range(1, rounds + 1):
        cand = propose(incumbent, rng)
        ce = evaluate_policy(cand, n=n, seed=seed)
        gain = ce.uplift - inc_eval.uplift
        accept = (gain > tau) and (ce.annoyance_proxy <= annoyance_ceiling)
        r = Round(
            i=i, accepted=accept,
            incumbent_uplift=inc_eval.uplift,
            candidate_uplift=ce.uplift,
            gain_over_incumbent=gain,
            annoyance_proxy=ce.annoyance_proxy,
        )
        history.append(r)
        if on_round:
            on_round(r)
        if accept:
            incumbent, inc_eval = cand, ce

    set_coach_gain(None)
    return AutoResearchResult(
        rounds=history,
        start_policy=(start or CoachPolicy.baseline()),
        best_policy=incumbent,
        start_uplift=start_uplift,
        best_uplift=inc_eval.uplift,
    )


# ─── CLI ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Self-improving Coach autoresearch loop")
    ap.add_argument("--rounds", type=int, default=30)
    ap.add_argument("--tau", type=float, default=0.004)
    ap.add_argument("-n", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    print(f"\nAutoresearch: {args.rounds} rounds · τ={args.tau} · N={args.n} · seed={args.seed}")
    print("─" * 64)

    def show(r: Round):
        flag = "✓ ACCEPT" if r.accepted else "·"
        print(f"  r{r.i:02d}  inc={r.incumbent_uplift*100:5.2f}%  "
              f"cand={r.candidate_uplift*100:5.2f}%  Δ={r.gain_over_incumbent*100:+5.2f}pp  "
              f"msgs={r.annoyance_proxy:.2f}  {flag}")

    res = autoresearch(rounds=args.rounds, tau=args.tau, n=args.n, seed=args.seed, on_round=show)
    print("─" * 64)
    print(f"  start uplift: {res.start_uplift*100:.2f}pp")
    print(f"  best  uplift: {res.best_uplift*100:.2f}pp   (total gain +{res.total_gain*100:.2f}pp)")
    print(f"  best policy gains (≠1.0):")
    for k, v in res.best_policy.gains.items():
        if abs(v - 1.0) > 1e-9:
            print(f"    {k:18s}: {v:.2f}")
