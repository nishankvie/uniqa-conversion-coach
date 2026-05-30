"""
UNIQA Conversion Coach — Monte Carlo Simulation

Runs N sessions × 2 conditions (coach_on / coach_off).
Uses RuleBasedPersona for speed (no API calls).
Produces conversion uplift statistics for all 3 evaluation dimensions:
  1. Conversion uplift (overall + per step)
  2. Persona differentiation (per-persona conversion)
  3. Intervention quality (annoyance rate, trigger precision)
"""

from __future__ import annotations

import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Optional

from uniqa.funnel import Step, PERSONA_WEIGHTS, STEP_ORDER, PERSONAS
from uniqa.coach import CoachAction
from uniqa.personas import RuleBasedPersona, SessionResult, run_session


PERSONA_LIST = list(PERSONA_WEIGHTS.keys())
PERSONA_WEIGHT_LIST = list(PERSONA_WEIGHTS.values())


# ─── Simulation Results ───────────────────────────────────────────────────────

@dataclass
class SimResult:
    n_runs:             int
    coach_on:           bool

    conversion_rate:    float
    per_persona_conv:   dict[str, float]
    per_step_abandon:   dict[str, float]   # step_value → fraction abandoning there

    annoyance_rate:     float              # % sessions with annoyance_peak > 0.30
    avg_message_count:  float             # avg interventions per session
    action_distribution: dict[str, int]   # action.value → count
    whatsapp_sent_count: int              # Peter WA re-engagements

    sessions:           list[SessionResult] = field(default_factory=list, repr=False)

    @property
    def conversion_pct(self) -> str:
        return f"{self.conversion_rate * 100:.2f}%"

    def summary(self) -> str:
        coach_str = "WITH Coach" if self.coach_on else "WITHOUT Coach (baseline)"
        lines = [
            f"\n{'='*60}",
            f"  {coach_str}  |  N={self.n_runs:,}",
            f"{'='*60}",
            f"  Overall conversion rate:   {self.conversion_pct}",
            f"  Per-persona conversion:",
        ]
        for p in PERSONAS:
            lines.append(f"    {p.capitalize():8s}: {self.per_persona_conv.get(p, 0)*100:.1f}%")
        lines += [
            f"  Per-step abandon (conditional):",
        ]
        for step in STEP_ORDER[1:]:
            if step == Step.PURCHASE:
                continue
            rate = self.per_step_abandon.get(step.value, 0.0)
            lines.append(f"    {step.value:30s}: {rate*100:.1f}%")
        lines += [
            f"  Annoyance rate (>0.30):    {self.annoyance_rate*100:.1f}%",
            f"  Avg interventions/session: {self.avg_message_count:.2f}",
            f"  WhatsApp leads (Peter):    {self.whatsapp_sent_count}",
            f"{'='*60}",
        ]
        return "\n".join(lines)


# ─── Main Simulation ──────────────────────────────────────────────────────────

def run_simulation(
    n: int = 1_000,
    seed: int = 42,
    coach_on: bool = True,
) -> SimResult:
    """
    Run N sessions. Returns SimResult.
    Deterministic: same seed → same results.
    """
    rng = random.Random(seed)
    sessions: list[SessionResult] = []

    for _ in range(n):
        persona = rng.choices(PERSONA_LIST, weights=PERSONA_WEIGHT_LIST, k=1)[0]
        pb = RuleBasedPersona(persona, rng)
        result = run_session(persona, rng, coach_on=coach_on, persona_impl=pb)
        sessions.append(result)

    return _aggregate(sessions, n, coach_on)


def run_ab_simulation(
    n: int = 1_000,
    seed: int = 42,
) -> tuple[SimResult, SimResult]:
    """
    Run both conditions with the SAME persona draw sequence.
    Ensures fair comparison.
    Returns (baseline, with_coach).
    """
    baseline   = run_simulation(n=n, seed=seed, coach_on=False)
    with_coach = run_simulation(n=n, seed=seed, coach_on=True)
    return baseline, with_coach


def _aggregate(sessions: list[SessionResult], n: int, coach_on: bool) -> SimResult:
    conversions = sum(1 for s in sessions if s.converted)
    conversion_rate = conversions / n

    # Per-persona conversion
    per_persona: dict[str, list[bool]] = defaultdict(list)
    for s in sessions:
        per_persona[s.persona].append(s.converted)
    per_persona_conv = {p: (sum(v) / len(v) if v else 0.0) for p, v in per_persona.items()}

    # Per-step conditional abandon rate
    step_arrivals  = Counter()
    step_abandons  = Counter()
    for s in sessions:
        for step in s.steps_reached:
            step_arrivals[step.value] += 1
        if s.abandoned_at:
            step_abandons[s.abandoned_at.value] += 1
    per_step_abandon = {
        sv: step_abandons[sv] / step_arrivals[sv]
        for sv in step_arrivals
        if step_arrivals[sv] > 0
    }

    # Intervention quality
    annoyance_rate    = sum(1 for s in sessions if s.annoyance_peak > 0.30) / n
    avg_message_count = sum(s.message_count for s in sessions) / n
    action_dist: Counter = Counter()
    for s in sessions:
        for _, a in s.coach_actions:
            action_dist[a.value] += 1
    whatsapp_count = sum(1 for s in sessions if s.whatsapp_sent)

    return SimResult(
        n_runs=n,
        coach_on=coach_on,
        conversion_rate=conversion_rate,
        per_persona_conv=per_persona_conv,
        per_step_abandon=per_step_abandon,
        annoyance_rate=annoyance_rate,
        avg_message_count=avg_message_count,
        action_distribution=dict(action_dist),
        whatsapp_sent_count=whatsapp_count,
        sessions=sessions,
    )


# ─── Uplift Report ────────────────────────────────────────────────────────────

def uplift_report(baseline: SimResult, coached: SimResult) -> str:
    delta     = coached.conversion_rate - baseline.conversion_rate
    uplift_pct = (delta / baseline.conversion_rate * 100) if baseline.conversion_rate > 0 else 0

    lines = [
        "\n" + "="*60,
        "  UPLIFT REPORT",
        "="*60,
        f"  Baseline conversion:  {baseline.conversion_pct}",
        f"  Coach conversion:     {coached.conversion_pct}",
        f"  Absolute uplift:      +{delta*100:.2f}pp",
        f"  Relative uplift:      +{uplift_pct:.1f}%",
        "",
        "  Per-persona uplift:",
    ]
    for p in PERSONAS:
        b = baseline.per_persona_conv.get(p, 0)
        c = coached.per_persona_conv.get(p, 0)
        d = c - b
        lines.append(f"    {p.capitalize():8s}: {b*100:.1f}% → {c*100:.1f}%  ({'+' if d>=0 else ''}{d*100:.2f}pp)")
    lines += [
        "",
        "  Drop-off reduction at critical steps:",
    ]
    for step_val in [Step.TARIFF_SELECT.value, Step.PERSONAL_DATA.value]:
        b = baseline.per_step_abandon.get(step_val, 0)
        c = coached.per_step_abandon.get(step_val, 0)
        d = c - b
        lines.append(f"    {step_val:30s}: {b*100:.1f}% → {c*100:.1f}%  ({'+' if d>=0 else ''}{d*100:.2f}pp)")
    lines += [
        "",
        "  Intervention quality:",
        f"    Avg interventions/session: {coached.avg_message_count:.2f}",
        f"    Annoyance rate:            {coached.annoyance_rate*100:.1f}%",
        f"    Peter WA re-engagements:   {coached.whatsapp_sent_count}",
        "="*60,
    ]
    return "\n".join(lines)


# ─── CLI entry ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="UNIQA Coach Simulation")
    parser.add_argument("-n", "--runs", type=int, default=1_000, help="Number of sessions")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    print(f"\nRunning {args.runs:,} sessions × 2 conditions (seed={args.seed})...")

    baseline, coached = run_ab_simulation(n=args.runs, seed=args.seed)

    print(baseline.summary())
    print(coached.summary())
    print(uplift_report(baseline, coached))
