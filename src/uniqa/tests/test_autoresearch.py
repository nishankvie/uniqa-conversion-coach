"""Tests for the self-improving autoresearch loop (empirical gate).

The formal Z3 certificate is DEFERRED (specs/deferred/coach_autoimprove_z3.py);
this suite covers the runtime loop + its acceptance gate, not the proof.
"""

from uniqa.autoresearch import (
    CoachPolicy, evaluate_policy, propose, autoresearch, POLICY_KEYS, GAIN_MAX,
)
from uniqa.psyche import set_coach_gain, COACH_GAIN


def teardown_function():
    set_coach_gain(None)  # never leak global policy state between tests


def test_gain_actually_changes_outcome():
    """A zero-gain coach must convert no better than the calibrated coach."""
    base = evaluate_policy(CoachPolicy.baseline(), n=1500, seed=1)
    dead = evaluate_policy(CoachPolicy({k: 0.0 for k in POLICY_KEYS}), n=1500, seed=1)
    assert base.uplift > dead.uplift          # the coach effect is real & tunable
    assert COACH_GAIN == {}                   # global state cleaned up after eval


def test_propose_stays_in_bounds():
    rng = __import__("random").Random(0)
    p = CoachPolicy.baseline()
    for _ in range(50):
        p = propose(p, rng)
        assert all(0.0 <= v <= GAIN_MAX for v in p.gains.values())


def test_autoresearch_never_regresses_and_can_improve():
    res = autoresearch(rounds=25, tau=0.004, n=2000, seed=42)
    # Monotonicity: best ≥ start (gate guarantees no accepted regression).
    assert res.best_uplift >= res.start_uplift
    # Every accepted round strictly beat the incumbent by > tau.
    for r in res.rounds:
        if r.accepted:
            assert r.gain_over_incumbent > 0.004
    # Incumbent uplift is non-decreasing across the recorded rounds.
    seen = [r.incumbent_uplift for r in res.rounds]
    assert all(b >= a - 1e-9 for a, b in zip(seen, seen[1:]))


def test_annoyance_guardrail_respected():
    res = autoresearch(rounds=15, tau=0.004, annoyance_ceiling=1.6, n=1500, seed=7)
    for r in res.rounds:
        if r.accepted:
            assert r.annoyance_proxy <= 1.6



