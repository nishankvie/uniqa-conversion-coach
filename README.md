# 🧭 UNIQA Conversion Coach

> **Zero One Hack — Vienna · Insurance / UNIQA track.**
> A detection + decision layer on top of UNIQA's *existing* health-insurance
> calculator chatbot. It reads the customer's mind, intervenes only when it
> helps, and **proves its lift with synthetic persona simulation** — then
> improves itself automatically through a formally-certified autoresearch loop.

---

## The challenge (one sentence)

> Build a Conversion Coach that detects when users are about to abandon UNIQA's
> health-insurance calculator and intervenes in real time — then prove it works
> using synthetic persona simulations.

**Conversion = online purchase completion** (Start or Optimal tariff). Advisor
handoff is a clean exit, *not* a conversion. The Coach only helps users who
*can* finish online actually finish.

---

## The idea in three moves

1. **The chatbot already exists.** We do not rebuild it. The Coach sits *on top*
   — pure **detection + decision**: read hesitation signals → decide whether/what
   to intervene with → respect a strict annoyance budget.
2. **Prove it in simulation.** A psyche-driven persona model (Judith / Franz /
   Peter) generates realistic synthetic journeys. A Monte-Carlo A/B harness
   measures conversion uplift, persona differentiation, and intervention quality.
3. **Let it improve itself.** An **autoresearch loop** tunes the Coach policy
   against the simulator and ships only changes a **Z3 proof** certifies as real,
   monotone improvements — *given* the persona model is statistically faithful.

---

## Headline numbers (synthetic A/B, N = 4 000, seed 42)

| Metric | Coach OFF | Coach ON |
|---|---|---|
| Overall conversion | **5.65 %** | **14.5 %**  (+157 %) |
| Purchase-intent cohort (coachable) | ~13 % | **~28 %** |
| WhatsApp leads recovered (Peter) | 0 | ~790 |
| Avg interventions / session | 0 | **1.23** (budget = 3) |

Calibration anchors held: baseline ≈ 5.6 %, Step-4 drop ≈ 66 %, Step-5 ≈ 24 %,
Step-6 ≈ 78 %.

> **Honest framing.** We report overall uplift *and* the coachable cohort.
> `not_ready` / `distraction` bounces are deliberately left alone — that
> restraint *is* the intervention-quality story.

---

## The three personas

| Persona | Share | Profile | Coach strategy |
|---|---|---|---|
| **Judith** — Rising Hybrid | 30 % | Trusts advisors, moderate price comfort | Reassure, price-reframe, graceful advisor option |
| **Franz** — Online Affine | 50 % | High comprehension, low patience, **online-only** | Remove Premium-needs-advisor confusion. **Never** hand to advisor (hard constraint) |
| **Peter** — Service Affine | 20 % | Wants human contact | Offer callback *before* the price wall → WhatsApp recovery |

---

## Repository layout

```
.
├── README.md                     ← you are here
├── pyproject.toml                ← src-layout package (uniqa-coach)
├── src/uniqa/
│   ├── funnel.py                 ← funnel state machine + hesitation signals
│   ├── scope.py                  ← in-scope funnel + form logic registry
│   ├── coach.py                  ← Coach policy: 12 actions, decision tree, hard gates, widget copy
│   ├── psyche.py                 ← persona MIND model (6 latent vars, intent mix, hazard bounce)
│   ├── personas.py               ← rule-based + LLM persona drivers, session runner
│   ├── contracts.py              ← JSON contracts: events, effectors+guardrails, Coach I/O, envelopes
│   ├── coach_io.py               ← psyche signals → activity log → observation → decision adapter
│   ├── journey.py                ← composable token harness (demo + batch) + JSON-render twin
│   ├── eventproc.py              ← event post-processing
│   ├── tlm.py                    ← trajectory-token space (VOCAB / encode / decode)
│   ├── widget.py                 ← per-step action spaces + json-render widget twin
│   ├── play.py                   ← human-playable journey (ASCII screens)
│   ├── persona_datagen.py        ← persona data-gen pipeline + LLM teacher + ε measurement
│   ├── sim.py                    ← turn-based simulator (App↔Coach↔persona, both flows)
│   ├── simulation.py             ← Monte-Carlo A/B + uplift report
│   ├── autoresearch.py           ← self-improving loop (propose → eval → gate → accept)
│   ├── app.py                    ← Streamlit demo (Live journey + A/B uplift)
│   └── tests/                    ← 93 tests (calibration, constraints, uplift, autoresearch, Z3)
├── specs/z3/coach_autoimprove.py ← Z3 proof the autoresearch loop self-improves (T1–T5)
└── docs/
    ├── ARCHITECTURE.md           ← App/Coach split, contracts, dual learning loop, UI tokens
    ├── AUTORESEARCH.md           ← self-improving Coach: loop, assumption A1, certificate
    ├── PSYCHE_WALKTHROUGH.md     ← first-person trace of the real screenshotted funnel
    ├── FUNNEL_AUTOPSY.md         ← screen-by-screen drop-off analysis
    ├── PIPELINE_PLAN.md          ← MASTER PLAN: LLM personas, coach autoimprove+Z3, multi-surface, outer loop
    ├── PERSONA_MODEL_PLAN.md     ← (deferred) local persona model build plan + data provenance
    ├── PERSONA_TLM_DESIGN.md     ← (deferred) tiny-TLM design + Z3 calibration anchor
    ├── TLM_RESEARCH.md           ← (deferred) trajectory-language-model prior art + feasibility
    └── RESEARCH_insurance_conversion.md  ← conversion-optimization research brief
```

---

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# tests (incl. the Z3 certificate)
pytest -q                                   # 93 passed

# A/B simulation
python -m uniqa.journey -n 4000             # baseline vs coach uplift report
python -m uniqa.journey --trace             # one demo journey, token by token

# live demo
streamlit run src/uniqa/app.py              # Live journey + A/B uplift dashboards

# self-improving loop + proof
python -m uniqa.autoresearch --rounds 30    # gated hill-climb on synthetic data
python specs/z3/coach_autoimprove.py        # ALL THEOREMS DISCHARGED ✅
```

---

## Self-improving Coach (the differentiator)

The Coach tunes itself without ever experimenting on live customers:

```
PROPOSE → SIMULATE (psyche) → EVALUATE (paired A/B) → GATE (accept iff Δuplift > τ) → REPEAT
```

**Central claim** (proved in `specs/z3/coach_autoimprove.py`):

> *If the persona model is statistically close to reality
> (estimator bias `|U_sim − U_real| ≤ b = L·ε`), and the acceptance margin
> satisfies `τ ≥ 2b`, then every accepted policy is a **real** improvement, the
> Coach's real conversion is **monotonically non-decreasing**, and the loop
> **converges**.*

Z3 discharges five theorems: **soundness**, **no-regression**, **monotonicity**,
**termination**, and **tightness** (the `τ ≥ 2b` bound is necessary). The whole
problem reduces to one measurable condition — *model fidelity (A1)*. Make the
simulator faithful and the optimisation is provably safe. Full write-up:
[`docs/AUTORESEARCH.md`](docs/AUTORESEARCH.md).

---

## How we're judged (and where we score)

| Jury dimension | Our evidence |
|---|---|
| **Conversion uplift** | +157 % overall / 13 %→28 % coachable, paired A/B, deterministic |
| **Persona differentiation** | distinct policies + outcomes per persona; Franz never-advisor hard gate |
| **Intervention quality** | ≤ 3 messages, ~1.23 avg, uncoachable bounces left alone, annoyance guardrail |

---

## Status (hackathon, Day 2)

- ✅ Funnel state machine, Coach policy, psyche persona model — calibrated to anchors
- ✅ Composable journey-token harness (demo + batch) with JSON-render twin
- ✅ Monte-Carlo A/B simulation + uplift report
- ✅ Streamlit demo — Live journey (mind HUD, widgets, WhatsApp) + A/B dashboards
- ✅ Self-improving autoresearch loop + **Z3 certificate (5 theorems)**
- ✅ 93 tests passing
- ▢ Roadmap: fidelity dashboard (live ε), richer policy space, LLM-proposed experiments, shadow deployment (see `docs/AUTORESEARCH.md`)

---

*Built at Zero One Hack, Vienna. Synthetic-data-only — no live customer
experimentation. Conversion defined per the track's online-completion scope.*
