"""Tests for the self-improving autoresearch loop and its formal certificate."""

import subprocess
import sys
from pathlib import Path

import pytest

from uniqa.autoresearch import (
    CoachPolicy, evaluate_policy, propose, autoresearch, POLICY_KEYS, GAIN_MAX,
)
from uniqa.psyche import set_coach_gain, COACH_GAIN


def teardown_function():
    set_coach_gain(None)  # never leak global policy state between tests


def test_baseline_policy_is_all_ones():
    p = CoachPolicy.baseline()
    assert set(p.gains) == set(POLICY_KEYS)
    assert all(v == 1.0 for v in p.gains.values())


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


def test_determinism():
    a = autoresearch(rounds=10, n=1500, seed=3)
    b = autoresearch(rounds=10, n=1500, seed=3)
    assert a.best_uplift == b.best_uplift
    assert [r.accepted for r in a.rounds] == [r.accepted for r in b.rounds]


@pytest.mark.skipif(
    __import__("importlib").util.find_spec("z3") is None, reason="z3 not installed"
)
def test_z3_certificate_passes():
    """The formal proof script must discharge all theorems (exit 0)."""
    spec = Path(__file__).resolve().parents[3] / "specs" / "z3" / "coach_autoimprove.py"
    assert spec.exists(), spec
    out = subprocess.run([sys.executable, str(spec)], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "ALL THEOREMS DISCHARGED" in out.stdout
