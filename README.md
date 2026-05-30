# UNIQA Conversion Coach

A detection-and-decision layer that sits on top of UNIQA's existing online
health-insurance calculator. It reads behavioural signals during the funnel,
intervenes only when an intervention is likely to help, and chooses the right
surface to do it on (in-page widget, email, WhatsApp, and more). The policy
improves itself against a persona simulator, and every accepted change is gated
by a formal proof of non-regression.

The calculator is not rebuilt. The Coach is a separate layer that observes the
user's activity log and issues bounded, auditable actions over a fixed contract.

---

## Overview

- **Conversion** is defined as online purchase completion of an in-scope tariff
  (Start or Optimal, private-doctor, "myself"). Routing to an advisor is a clean
  exit, not a conversion. The Coach only assists users who can complete online.
- **The Coach is detection + decision only.** It reads hesitation signals, infers
  the likely customer segment, and decides whether/what/where to intervene under a
  strict annoyance budget. It never alters the data the calculator collects.
- **It is validated in simulation before it ever touches a customer.** A persona
  simulator (three research-backed segments) generates realistic journeys; a
  Monte-Carlo A/B harness measures uplift, per-segment differentiation, and
  intervention quality.

---

## How it works

Three models exchange JSON over one contract (`src/uniqa/contracts.py`); each is
swappable behind a Protocol (`src/uniqa/sim.py`):

```
   PERSONA MODEL  ──user events──▶   SURFACE MODEL (the env)  ──signals──▶  PERSONA
   (LLM-driven:                      static UNIQA funnel screens,                │
    Judith / Franz / Peter)          one uniform interface across               │ activity log
        ▲                            on-page / email / WhatsApp / …             ▼
        └────────────────────────────  COACH MODEL  ◀──────────  observation → decision
                                        (intent × surface, bounded, auditable)
```

- **Persona model** — currently LLM-driven (the customer simulator); calibrated
  against published funnel anchors via a latent-state baseline (`psyche.py`).
- **Surface model** — the environment. The static funnel is one implementation of a
  uniform interface; alternative surfaces (email, WhatsApp bot, landing page,
  feedback form/survey) implement the same interface, so the Coach can land a user
  wherever conversion is most likely.
- **Coach model** — the product. Observes the activity log only (no persona label,
  no health data), infers the segment, and returns a typed action plus
  human-readable reasoning and falsifiable hypotheses.

The full design is in [`docs/PIPELINE_PLAN.md`](docs/PIPELINE_PLAN.md).

---

## Self-improvement, proven safe

The Coach policy lives in a prompt. An autoresearch loop proposes prompt/policy
changes, evaluates them against the persona simulator with paired A/B sampling, and
accepts a change only if a Z3 proof certifies it is a real improvement:

> If the simulator is within a measured fidelity budget of reality
> (`|U_sim − U_real| ≤ b`) and the acceptance margin satisfies `τ ≥ 2b`, then every
> accepted policy is a real improvement, real conversion is monotonically
> non-decreasing, and the loop converges.

`specs/z3/coach_autoimprove.py` discharges five theorems (soundness, no-regression,
monotonicity, termination, and tightness of the `τ ≥ 2b` bound). An outer feedback
loop re-grounds the simulator on production logs on each release, keeping `b` small
so the guarantee holds. Details: [`docs/AUTORESEARCH.md`](docs/AUTORESEARCH.md).

Once a policy is certified, the Coach is distilled into a **local 1B model
(MiniCPM5-1B, LoRA) fine-tuned on the CINECA Leonardo cluster** — input is the
current session log, output is the reasoning plus the action. This gives
low-latency, private, on-premise inference in production. (Persona models stay
LLM-driven; their local fine-tune is deferred.)

---

## Simulation results

Monte-Carlo A/B over the persona simulator (N = 4000, fixed seed). These are
simulated outcomes used to size and de-risk the policy before any live test.

| Metric | Coach off | Coach on |
|---|---|---|
| Overall online conversion | 5.6% | 14.5% |
| Purchase-intent cohort (coachable) | ~13% | ~28% |
| Avg. interventions per session | 0 | 1.2 (budget 3) |

Calibration anchors held throughout (baseline ≈ 5.6%; step drop-offs ≈ 66% / 24% /
78%). Uncoachable bounces (genuinely not-ready, distracted) are deliberately left
alone — that restraint is part of the intervention-quality story.

| Segment | Share | Profile | Coach strategy |
|---|---|---|---|
| Judith — Rising Hybrid | 30% | Trusts advisors, moderate price sensitivity | Reassure, reframe price, offer a graceful advisor path |
| Franz — Online Affine | 50% | High comprehension, low patience, online-only | Remove advisory-tariff confusion; never route to an advisor |
| Peter — Service Affine | 20% | Prefers human contact | Offer a callback before the price wall (WhatsApp recovery) |

---

## Repository layout

```
.
├── README.md
├── pyproject.toml                  src-layout package (uniqa-coach)
├── src/uniqa/
│   ├── contracts.py                JSON contract: events, effectors, Coach I/O, render envelopes
│   ├── funnel.py · scope.py        funnel state machine + in-scope guard
│   ├── widget.py                   static funnel screens + closed per-step action space
│   ├── psyche.py                   latent-state persona baseline (calibration / volume floor)
│   ├── personas.py · persona_datagen.py   LLM-driven personas (OpenRouter)
│   ├── sim.py                      turn-based simulator (persona ↔ surface ↔ coach)
│   ├── coach.py · coach_io.py      Coach policy + observation/decision adapter
│   ├── autoresearch.py             self-improvement loop (propose → evaluate → gate)
│   ├── simulation.py               Monte-Carlo A/B + uplift report
│   ├── app.py                      Streamlit demo
│   └── tests/                      93 tests (calibration, constraints, uplift, autoresearch, Z3)
├── specs/z3/coach_autoimprove.py   the Z3 certificate
└── docs/                           see Documentation below
```

---

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest -q                                 # full suite incl. the Z3 certificate
python -m uniqa.journey -n 4000           # baseline vs Coach A/B uplift report
python -m uniqa.autoresearch --rounds 30  # gated self-improvement on the simulator
python specs/z3/coach_autoimprove.py      # discharge the proof
streamlit run src/uniqa/app.py            # interactive demo (journey + A/B dashboards)
```

---

## Documentation

| Document | Contents |
|---|---|
| [`docs/PIPELINE_PLAN.md`](docs/PIPELINE_PLAN.md) | The master plan: LLM personas, multi-surface coach, prompt autoimprovement + Z3, the coach 1B fine-tune (Leonardo), and the outer loop. |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | App/Coach split, the JSON contract, and the dual learning loop. |
| [`docs/AUTORESEARCH.md`](docs/AUTORESEARCH.md) | The self-improvement loop and the formal certificate. |
| [`docs/FUNNEL_AUTOPSY.md`](docs/FUNNEL_AUTOPSY.md) | The real funnel, screen by screen, and where users drop off. |
| [`docs/PSYCHE_WALKTHROUGH.md`](docs/PSYCHE_WALKTHROUGH.md) | First-person trace of the funnel grounding the persona model. |
| [`docs/RESEARCH_insurance_conversion.md`](docs/RESEARCH_insurance_conversion.md) | Conversion-optimization research brief. |
| [`docs/deferred/`](docs/deferred/) | Deferred work (local persona models, trajectory-model design). Not needed to understand the current system. |

---

*Synthetic-data-only validation — no live customer experimentation. Conversion is
defined per the track's online-completion scope.*
