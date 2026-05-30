"""
DEFERRED (not part of the current scope). The live autoresearch gate is empirical
(Δuplift > τ); this script is the drafted formal proof kept for later. Needs the
optional `deferred` extra: pip install -e ".[deferred]".

Z3 formal certificate: the autoresearch loop self-improves the Coach.

We do NOT ask Z3 to prove the persona model is realistic — that is an *empirical*
assumption, validated separately by comparing synthetic vs. real funnel statistics.
We TAKE that assumption as a hypothesis and prove that, given it, the loop's
acceptance gate is sound: it can only ever ratchet real-world conversion upward.

────────────────────────────────────────────────────────────────────────────
MAIN ASSUMPTION (empirical, given as hypothesis A1)

    The persona simulator generates synthetic sessions whose statistics are
    ε-close to reality. Concretely, the paired-uplift estimator U_sim(policy)
    has bounded bias vs. the true real-world uplift U_real(policy):

        ∀ policy:  | U_sim(policy) − U_real(policy) |  ≤  b ,   b = L·ε

    where ε is the statistical distance (e.g. total-variation) between the
    synthetic and real session distributions, and L is the sensitivity
    (Lipschitz constant) of the uplift functional w.r.t. that distance.

ACCEPTANCE GATE (the algorithm, in autoresearch.py)

        accept(cand)  ⇔  U_sim(cand) − U_sim(incumbent) > τ

THEOREMS (each discharged by Z3 below)

  T1  SOUNDNESS      τ ≥ 2b  ∧  accept  ⇒  U_real(cand) > U_real(incumbent)
                     (every accepted candidate is a REAL improvement)
  T2  NO-REGRESSION  τ ≥ 2b  ∧  U_real(cand) ≤ U_real(incumbent)  ⇒  ¬accept
                     (a real regression can NEVER be accepted)
  T3  MONOTONICITY   the incumbent's real uplift is non-decreasing each round
                     (accept ⇒ increase; reject ⇒ unchanged)
  T4  TERMINATION    real uplift is bounded ∧ each accept adds ≥ δ>0
                     ⇒ the number of acceptances is finite ⇒ the loop converges

CONCLUSION
    When (A1) the user model is right, and (T1–T4) the experimentation +
    autoresearch + evals engine are built around this gate, the Coach's real
    conversion improves monotonically and converges — i.e. AUTOMATIC,
    provably-safe Coach model improvement.
────────────────────────────────────────────────────────────────────────────

Run:  python specs/z3/coach_autoimprove.py
"""

from z3 import Real, Int, Solver, And, Or, Not, Implies, sat, unsat


def prove(name: str, hypotheses, conclusion) -> bool:
    """Prove  (∧ hypotheses) ⇒ conclusion  by checking the negation is UNSAT."""
    s = Solver()
    for h in hypotheses:
        s.add(h)
    s.add(Not(conclusion))
    r = s.check()
    if r == unsat:
        print(f"  ✅ PROVED   {name}")
        return True
    print(f"  ❌ FAILED   {name}")
    if r == sat:
        print(f"     counterexample: {s.model()}")
    return False


def main() -> int:
    print("\nZ3 certificate — Coach autoresearch self-improvement")
    print("=" * 60)

    ok = True

    # Shared symbols ─────────────────────────────────────────────────────────
    eps  = Real("eps")    # statistical distance synthetic↔real  (≥0)
    L    = Real("L")      # sensitivity of the uplift functional (≥0)
    tau  = Real("tau")    # acceptance margin
    b    = L * eps        # estimator bias bound

    u_sim_inc  = Real("u_sim_inc")    # measured uplift, incumbent
    u_sim_cand = Real("u_sim_cand")   # measured uplift, candidate
    u_real_inc = Real("u_real_inc")   # true uplift, incumbent
    u_real_cand= Real("u_real_cand")  # true uplift, candidate

    # A1: closeness ⇒ bounded estimator bias for BOTH policies.
    closeness = [
        eps >= 0, L >= 0,
        u_sim_inc  - u_real_inc  <=  b,  u_real_inc  - u_sim_inc  <=  b,
        u_sim_cand - u_real_cand <=  b,  u_real_cand - u_sim_cand <=  b,
    ]
    gate_accept = u_sim_cand - u_sim_inc > tau
    tau_big     = tau >= 2 * b           # margin dominates total bias budget

    # ── T1  SOUNDNESS ─────────────────────────────────────────────────────────
    # accept ∧ τ≥2b  ⇒  real improvement
    ok &= prove(
        "T1 soundness: accepted candidate is a real improvement",
        closeness + [tau_big, gate_accept],
        u_real_cand > u_real_inc,
    )

    # ── T2  NO-REGRESSION ──────────────────────────────────────────────────────
    # τ≥2b ∧ (real candidate not better)  ⇒  gate rejects
    ok &= prove(
        "T2 no-regression: a real regression is never accepted",
        closeness + [tau_big, u_real_cand <= u_real_inc],
        Not(gate_accept),
    )

    # ── T3  MONOTONICITY (one round, both branches) ────────────────────────────
    # Next incumbent's real uplift ≥ current incumbent's real uplift.
    accepted   = Real("accepted_flag")  # 1 if accept else 0 (modelled by cases)
    u_real_next = Real("u_real_next")
    # Case split encoded directly: if accept then next=cand (and cand>inc by T1);
    # if reject then next=inc.
    branch = Or(
        And(gate_accept,      u_real_next == u_real_cand),   # accept branch
        And(Not(gate_accept), u_real_next == u_real_inc),    # reject branch
    )
    ok &= prove(
        "T3 monotonicity: incumbent real uplift never decreases in a round",
        closeness + [tau_big, branch],
        u_real_next >= u_real_inc,
    )

    # ── T4  TERMINATION / CONVERGENCE ──────────────────────────────────────────
    # Each accept raises real uplift by ≥ δ>0; real uplift ∈ [lo, hi] bounded.
    # ⇒ the count k of accepted improvements is finite (k ≤ (hi−lo)/δ).
    delta = Real("delta")
    lo    = Real("lo")
    hi    = Real("hi")
    k     = Int("k")            # number of acceptances so far
    u_start = Real("u_start")
    u_now   = Real("u_now")

    term_hyps = [
        delta > 0,
        hi > lo,
        u_start >= lo, u_start <= hi,
        u_now <= hi,                       # real uplift is bounded above (≤ hi)
        k >= 0,
        u_now >= u_start + k * delta,      # k accepts each added ≥ δ
    ]
    # Conclusion: the number of acceptances is bounded ⇒ loop cannot accept forever.
    ok &= prove(
        "T4 termination: number of accepted improvements is finite/bounded",
        term_hyps,
        k <= (hi - lo) / delta,
    )

    # ── Bonus: the gate is VACUOUS if the model is too weak (honesty check) ─────
    # If τ < 2b, soundness can FAIL — i.e. the bound τ≥2b is not just sufficient
    # but necessary. We show a model exists where accept holds yet real regresses.
    s = Solver()
    for h in closeness:
        s.add(h)
    s.add(tau >= 0, tau < 2 * b, gate_accept, u_real_cand < u_real_inc)
    witness = s.check()
    if witness == sat:
        print("  ✅ PROVED   T5 tightness: τ<2b admits a false accept "
              "(so τ≥2b is necessary)")
    else:
        print("  ⚠️  T5 tightness: no witness found (bound may be loose)")
        ok = False

    print("=" * 60)
    if ok:
        print("ALL THEOREMS DISCHARGED ✅")
        print("Given A1 (persona model statistically close to real), the gated")
        print("autoresearch loop yields monotone, convergent, REAL Coach improvement.")
        return 0
    print("SOME THEOREMS FAILED ❌")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
