# UNIQA Conversion Coach — Executive Overview

**One line.** A detection+decision layer on top of UNIQA's existing calculator
that reads the customer's behaviour, intervenes only when it helps, proves its
lift in simulation, and improves itself under a formal safety proof.

**Three claims, each backed by running code:**
1. **It works** — synthetic A/B shows online conversion ~5.6% → ~14.5% (+157%),
   coachable cohort 13%→28%, with ≤3 interventions/session.
2. **It's an app, not a slide** — one JSON contract drives the sim, the demo, and
   a future React app; a human can walk the same flow and emit the same event log.
3. **It gets better by itself** — a synthetic autoresearch loop tunes the coach
   under a Z3-certified gate; an online loop keeps the simulator honest.

---

## The whole picture (ASCII)

```
                                  ┌──────────────────────────────────────────────┐
                                  │            UNIQA CONVERSION COACH              │
                                  └──────────────────────────────────────────────┘

  ┌───────────────────────────── APP  (IMMUTABLE) ─────────────────────────────┐
  │  11-step in-scope funnel (Privatarzt · Ich selbst · Start/Optimal online)   │
  │  scope.py routes hospital / other-persons / Opt.Plus|Premium → ADVISOR exit │
  │                                                                             │
  │  renders SCREENS (JSON / ASCII wireframe)   ·   executes EFFECTOR commands   │
  └───────────────┬───────────────────────────────────────────▲────────────────┘
                  │ emits                                       │ effector cmd
                  │ ActivityLog: [Event]                        │ (+ reasoning)
                  │  step_enter, mouse_move, hover, pause,      │
                  │  field_edit, price_hover, premium_click,    │
                  │  nav_back, cancel_hover, session_gap,        │
                  │  submit, convert, abandon                    │
                  ▼                                              │
       ┌──────────────────────┐    USER is one of:               │
       │  EVENT POST-PROCESS   │    ┌───────────────────────────┐ │
       │  eventproc.py         │    │ PERSONA  (sim user)        │ │
       │  • collapse → moments │◀───│  psyche Mind (6 latents)   │ │
       │  • features (dwell,   │    │  OR prompt-LLM persona     │ │
       │    hesitation_index…) │    │  OR learned persona-TLM    │ │
       │  • detections         │    │  OR a real human (play.py) │ │
       └──────────┬───────────┘    └───────────────────────────┘ │
                  │ collapsed moments + features + detections      │
                  ▼                                                │
       ┌──────────────────────┐                                   │
       │  TLM TOKENISER        │  tlm.py — small vocab (~83),       │
       │  encode(log,persona)  │  buckets dwell/Δt/counts           │
       │  → ids (≤ ~300/sess)  │  shared by persona-TLM & coach-TLM │
       └──────────┬───────────┘                                   │
                  │ observation (NO latent ground truth)           │
                  ▼                                                │
       ┌──────────────────────────────────────────────┐           │
       │  COACH  (MUTABLE — the only thing we train)    │───────────┘
       │  coach_io.RuleCoachModel.decide(obs) →          │
       │    CoachDecision { effector cmd | NO_ACTION,    │
       │                    reasoning (mandatory),       │
       │                    hypotheses (falsifiable),    │
       │                    confidence, value_estimate } │
       └──────────┬───────────────────────────────────┬─┘
                  │ outcome (+hypothesis hits)          │ effector cmd → APP
                  ▼                                     │
  ┌─────────────────────────── LEARNING ────────────────────────────────────────┐
  │                                                                              │
  │  LOOP A — synthetic autoresearch (cheap, runs forever, CPU)                  │
  │    persona model → app → coach → reward → GATE(Δuplift>τ) → π'               │
  │    autoresearch.py        gate certified by specs/z3/coach_autoimprove.py     │
  │    (T1 soundness · T2 no-regress · T3 monotone · T4 terminate · T5 tight)     │
  │                                                                              │
  │  LOOP B — online feedback (periodic, real data)                              │
  │    real (log, decision, outcome) ─▶ (1) re-fit persona model (shrink ε)       │
  │                                     (2) off-policy eval coach (IPS)           │
  │                                     (3) hypothesis hit-rate recalibration     │
  │                                     (4) re-run Loop A ─▶ gate ─▶ shadow ship   │
  └──────────────────────────────────────────────────────────────────────────────┘

  RENDERERS of the same JSON:  Streamlit demo (app.py)  ·  future React app  ·  ASCII (play.py)
```

---

## Component map (where everything lives)

| Layer | Module | Role |
|------|--------|------|
| App / funnel | `funnel.py`, `scope.py` | immutable 11-step flow, scope routing, form validation |
| Contracts | `contracts.py` | Event, ActivityLog, Effector(+guardrails), Hypothesis, Coach I/O, RenderEnvelope |
| User sim | `psyche.py`, `personas.py` | latent-mind persona; (future) persona-TLM |
| Human play | `play.py` | walk the journey, emit identical events, ASCII screens |
| Post-process | `eventproc.py` | collapse → moments, features, detections |
| Tokeniser | `tlm.py` | trajectory token space for persona-TLM + coach-TLM |
| Coach | `coach.py`, `coach_io.py` | action space, decision, reasoning, hypotheses |
| Sim/A-B | `journey.py`, `simulation.py` | Monte-Carlo uplift |
| Learning A | `autoresearch.py`, `specs/z3/` | gated self-improvement + proof |
| Demo | `app.py` | Streamlit renderer of the contract |

---

## Inputs / outputs at each boundary

| Boundary | Input | Output |
|---|---|---|
| App → world | screen render request | `RenderEnvelope` JSON |
| User → App | intent (click/type/scroll) | `Event`s appended to `ActivityLog` |
| App → Coach | `ActivityLog` window | `CoachObservation` (no latent) |
| Coach → App | `CoachObservation` | `CoachDecision` (effector cmd + reasoning + hypotheses) |
| Post-process | raw `ActivityLog` | moments + features + detections |
| Tokeniser | `ActivityLog` (+persona, +coach actions) | token id sequence |
| Loop A | persona model + coach π | gated π′ |
| Loop B | real (log, decision, outcome) | re-fit persona model + evaluated π |

---

## Status

69 tests passing. Built: app/funnel + scope + form logic, contracts, event
post-processing, TLM token space, human play harness, rule-coach baseline, Loop A
+ Z3 proof, Streamlit demo. Designed, not yet built: persona-TLM / coach-TLM
training (see `TLM_RESEARCH.md`), Loop B re-fit + off-policy eval, React renderer.
