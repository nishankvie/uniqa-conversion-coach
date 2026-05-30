# Persona Model — Train Plan (H1: fine-tune MiniCPM5-1B)

> Actionable training plan. **H1 (primary): distill an OpenRouter teacher into a
> fine-tuned [MiniCPM5-1B](https://huggingface.co/openbmb/MiniCPM5-1B) persona
> model.** The tiny from-scratch TLM (`docs/PERSONA_TLM_DESIGN.md`) is demoted to
> **baseline + the calibrated Z3 `b` anchor** — it still runs, it just isn't the
> headline model anymore.
>
> Grounded in code that already exists: `sim.py` (Protocol loop), `widget.py`
> (action space + reactive env), `persona_datagen.py` (OpenRouter teacher →
> schema-gated JSON), `contracts.py` (JSON I/O). This plan mostly **wires
> existing pieces into a distillation pipeline** — small blast radius.

---

## The whole pipeline (big picture)

The end-to-end program, stage by stage. Each stage drops a dependency or adds a
model; the through-line is **bootstrap on real human behaviour → close the loop in
simulation → go fully local → re-ground on production data.**

```
 STAGE 0 ─ RECORD REAL HUMAN            STAGE 1 ─ SEED THE SIM             STAGE 2 ─ DISTILL PERSONA
   I click the real UNIQA form;       3 persona profiles + the          OpenRouter teacher generates
   engine captures timing / dwell  →  STATIC WIDGET (real funnel      →  sessions; train local MiniCPM
   / hesitation patterns.             screens, §4) as the sim env       (LoRA) to imitate it, then
   Craft the sessions to match           = WidgetModel interface         ▶▶ DROP THE TEACHER.
   the 3 personas (real action          (one iface, swappable impl)      └─ local persona model stands
   timing priors).                                                          alone (H1, §1-§3,§5,§7,§8)
        │ real-timing seed                                                       │
        └──────────────────────────────────┬──────────────────────────────────────┘
                                            ▼
 STAGE 3 ─ COACH + ACTION SPACE         STAGE 4 ─ AUTORESEARCH (Loop A)    STAGE 5 ─ DISTILL COACH
   stand up the coach over its        propose coach prompt / policy     train a local coach (2nd LoRA,
   EXTENDED action space (§6).      →  changes; evaluate against the  →  §6) on the improved teacher
   Nuance: coach must IDENTIFY        persona sim; Z3 gate accepts        traces, then ▶▶ DROP THE
   the persona — modelled as          only real, monotone wins            TEACHER LLM.
   p_identify (sim param, §6.1)       (docs/AUTORESEARCH.md)            └─ FULLY LOCAL pipeline
        │ real: cookies/UTM/traffic/        │                                      │
        │ retargeting/lifestyle (§6.1)      │                                      │
        └──────────────────────────────────┴──────────────────────────────────────┘
                                            ▼
 STAGE 6 ─ PROD DEPLOY + LOOP B         STAGE 7 ─ FEATURES + IMPORTANCE
   ship the local pipeline; I click   feed as many persona features as
   through PROD; the engine captures  possible (lifestyle, income, NPS,
   real usage. Use it to RE-FIT    →  channel pref, …) and learn which
   persona models + tune coach        actually move page actions —
   interactions; keep improving       a feature-importance weighting
   the coach (continual).             scheme (§6.2). Lifestyle data may or
   (Loop B, docs/ARCHITECTURE.md §6)  may not affect on-page behaviour.
```

**Stage notes (the nuances that matter):**

0. **Record real human interactions first.** Before any model, I walk the real form
   and the engine logs the event stream with **real timing** (dwell, inter-event Δt,
   hesitation, re-edits). I craft a handful of these walk-throughs to *embody* each of
   the 3 personas (a rushed online-only Franz run, a hesitant advisor-leaning Judith
   run, a service-seeking Peter run). These become the **timing-realism seed** the
   synthetic teacher data is too smooth to provide (attacks risk R3, timing realism).
1. **Start with 3 personas + the static widget.** The sim env is the static widget
   (the *real* funnel screens, §4) behind the `WidgetModel` interface; the users are
   the 3 calibrated persona profiles.
2. **Train local persona → drop teacher.** H1: distill the OpenRouter teacher into a
   LoRA MiniCPM persona that emits the same JSON sessions, then stop calling the
   teacher. The local model is the persona engine from here on.
3. **Coach + extended action space.** Stand the coach up over its effector/intent
   action space (§6). **Key nuance: the coach does not know the persona label** — it
   must infer it. We model inference quality as a probability `p_identify` (§6.1).
4. **Autoresearch improves the coach (Loop A).** The existing gated hill-climb tunes
   coach prompts/policy against the persona sim; the Z3 certificate only ships real
   improvements.
5. **Train local coach → drop teacher LLM.** Distill the improved policy into a second
   LoRA adapter → the whole pipeline is now local (no external LLM calls).
6. **Prod deploy + Loop B.** Simulate shipping: I click through prod, the engine
   captures real `(activity, decision, outcome)` tuples, and we re-fit the persona
   models + adjust coach interactions on real data — continual improvement.
7. **Features + importance weighting.** Pour in all the persona features we have
   (lifestyle, income, NPS, channel preference, …) and learn which ones actually
   change on-page behaviour, via a feature-importance scheme (§6.2).

---

## 0. The three-model interface (one JSON contract, three players)

The simulation is three models talking over `contracts.py`. All three emit/consume
JSON. This is the frame the whole plan serves.

```
        ┌───────────────────────── SIMULATION LOOP  (sim.py, Protocol-typed) ─────────────────────────┐
        │                                                                                              │
        │   PERSONA-MODEL                user events JSON              WIDGET-MODEL  (environment)      │
        │   FT MiniCPM5-1B    ──{type,target,value,thought}[]──▶       deterministic, schema-driven     │
        │   system = persona.md                                       • render(step) → screen JSON      │
        │   in = screen JSON + history        ◀──screen JSON +────────• react(events) → signal events  │
        │   out = next events for THIS step      signal events          (price_reveal, validation_error,│
        │        ▲                              one WidgetModel Protocol; advisory_badge, idle_timeout)   │
        │        │                              Static & Generative impls   one uniform run-time iface   │
        │        │ activity log (events)                       effector cmd │                            │
        │        └───────────────────  COACH-MODEL  ◀───────────────────────┘                          │
        │                              FT MiniCPM5-1B (2nd LoRA adapter)                                │
        │                              in = CoachObservation JSON → out = CoachDecision JSON            │
        └──────────────────────────────────────────────────────────────────────────────────────────────┘
```

- **Persona-model** = the learned user. H1 = FT MiniCPM. Drop-in for `sim.LLMPersona`.
- **Widget-model** = the *environment*, behind one uniform `WidgetModel` interface so
  the harness talks to static and generative widgets identically. It "generates JSON
  given a schema" and is **reactive**: persona input (`select_tariff:premium`) →
  widget signal (`price_reveal` + `advisory_badge`). §4.
- **Coach-model** = the policy. H1 = 2nd LoRA adapter, trained *after* persona. §6.

All three are swappable behind their Protocol (`PersonaModel` / `WidgetModel` /
`CoachModel` in `sim.py`). Swapping the teacher LLM for the FT MiniCPM is a
**base-URL change**, zero contract churn.

---

## 1. Why fine-tune (vs the tiny TLM) — the H1 thesis

| | FT MiniCPM5-1B (H1) | tiny TLM 0.8M (baseline) |
|---|---|---|
| Path | SFT/LoRA on pretrained Llama-arch — **Layer-1 boring**, cookbook-documented | from-scratch GPT over custom event vocab — research-y |
| I/O | natural JSON + `thought` field, **same format the teacher already emits** | custom 110-token stream, bespoke encode/decode |
| Persona conditioning | `system = persona.md` — trivial | learned prefix embedding plumbing |
| Plumbing | reuse `persona_datagen` + `parse_session` + `sim.LLMPersona` | new trainer + vocab + calibration head |
| Calibration to anchors | **weak** (generative LLM, no logit-bias head) → that's why we keep the TLM | strong (40-scalar Stage-2 fit) |
| Jury story | "we fine-tuned a 1B model on an A100" | "we built a Decision-Transformer for funnels" |

**Division of labour:** FT MiniCPM is the *expressive* persona that drives the demo
and Loop A; the tiny TLM stays as the *calibratable* model that pins the Z3 safety
budget `b = ε_anchor` (see `docs/PERSONA_TLM_DESIGN.md §3.4`). They are complements,
not rivals.

---

## 2. I/O format (turn-based, drop-in for `sim.LLMPersona`)

Exactly the shape `persona_datagen.build_step_prompt` already produces — so the FT
model is a literal swap for the teacher.

```
SYSTEM:   persona_<seg>.md  +  personas.json[segment]  +  fixed intent for the session
USER:     { "screen": render_action_space(step),         # widget-model output (the schema)
            "history": [collapsed events so far],          # eventproc.collapse
            "budget_note": "..." }
ASSISTANT (target, loss here only):
          { "events": [ {"type","target","value","thought"}, ... ] }   # THIS step only
```

- **Loss mask = completion-only** (assistant tokens). Analog of the TLM USER-token mask.
- `type ∈ legal_events(step)`, `target ∈ STEP_ACTIONS[step]` — **the widget-model owns
  the schema**; anything outside it is dropped by `parse_session` / `legal_events`.
- Terminal events `convert | abandon | handoff` end the session.

---

## 3. Action space — finish the design (single source of truth)

Today the action space lives in **two** places that disagree:
`widget.STEP_ACTIONS` (rich, real targets) and `tlm.TARGETS` (12 ids with a wildcard
`"field"` that **loses Step-6 form-field signal** — which field churned matters for
`form_helper` targeting).

**Fix:** promote `widget.py` to the single registry; derive everything else from it.

```
widget.STEP_ACTIONS  ──┬─▶  legal_events(step)         (already)
   (source of truth)   ├─▶  render_action_space(step)  (already → the schema)
                       ├─▶  FT prompt "screen" block   (§2)
                       └─▶  tlm.TARGETS  (REPLACE wildcard "field" with the
                            per-step closed field set: date_of_birth, sv_number,
                            email, first_name, last_name, height, weight, sport,
                            doctor, health_answers, + tariff ids + tooltip rows)
```

Action-space invariants to enforce (test them, §8):
1. Every `(kind,target)` in `STEP_ACTIONS` maps to exactly one `EventType` in `legal_events`.
2. No event the teacher emits is outside the step's legal set (schema gate proves it).
3. `tlm.TARGETS` ⊇ every `target` appearing in `STEP_ACTIONS` (no wildcard collapse).
4. UX cost is measurable: each action carries a tap/keystroke count (already in `value`).

This is the "work more on action space" deliverable: **one closed, per-step,
typed action vocabulary** that the schema-gate, the FT prompt, and the TLM vocab all
consume identically.

---

## 4. Widget-as-model = a UNIFORM INTERFACE (not a particular implementation)

> Clarified intent: "widget should be a model" means we **interface with the static
> widget the exact same way we'd interface with a generative widget." The harness
> talks to *an interface*, never to a concrete widget. The run-time interface (RTI)
> for the simulation harness must be **uniform** across implementations.

This is the same move we already made for the persona: `sim.LLMPersona` (FT MiniCPM)
and `PsychePersona` both satisfy one `PersonaModel` Protocol, so the harness swaps
them with a base-URL change. The widget gets the identical treatment.

### 4.1 The screens the static widget models (the REAL funnel)

Grounded in the official funnel doc ([uniqa-funnel-doc_en.md](https://github.com/Lumos-Data/zero_one_hack_01/blob/main/tracks/insurance-uniqa/uniqa-funnel-doc_en.md)).
The calculator has **15 tracked steps across 4 phases** (Inputs → Product →
Recommendation → Closing). The **in-scope online path** (private doctor · "Myself" ·
Start/Optimal) is:

| Step | Phase | Screen | Drop | Signal the widget must emit |
|---|---|---|---|---|
| **S1** | Inputs | Where covered? `At doctor visits`✅ / `In hospital`❌ | — | branch; hospital → out-of-scope → advisor route |
| **S2** | Inputs | Who insured? `Myself`✅ / `Other persons`❌ | — | branch; others → advisor route |
| **S3** | Inputs | DOB + Sozialversicherung-Nr | — | **first PII, before any price** → trust barrier |
| **S4** | Product | Tariff table — **provisional** premium (Start €38.74 / Optimal €68.14 online; Opt.Plus/Premium advisory) | **66%** | `price_reveal` (provisional) + `advisory_badge` on Opt.Plus/Premium |
| ~~S5~~ | Product | Add-on coverage | (24%) | **hospital path only → OUT of scope**, private-doctor users skip it |
| **S6** | Inputs | Health questions | — | health data for the *final* premium (coach never receives these as features) |
| **S7** | Recommendation | **Final** premium after health assessment | **78%** | `price_reveal` (final, usually higher than S4) → the trust-collapse moment |
| **S12+** | Closing | name/address · start date · payment · consents · confirm | — | the actual online conversion |

**Two corrections this forces on the current `StaticWidget` (`widget.py` today):**
1. There are **two price walls**, not one: S4 *provisional* (66%) and S7 *final* (78%).
   The gap between them (final > provisional after the health surcharge) is the single
   biggest trust-killer. `widget.py` currently conflates S4 with a merged
   personal+health+submit step and has **no S7 final-price reveal** — add it.
2. The **closing block S12+** (payment / consents / confirm) is where conversion
   actually happens and is **not modelled yet** — add a minimal closing screen so a
   session can reach a real `convert`.

> Action item (extends `widget.py`, not this plan's critical path): add `S7_final_price`
> and a collapsed `S12_closing` to `STEP_ACTIONS` / `legal_events`, with `price_reveal`
> carrying both provisional and final values so the persona can react to the *delta*.
> Out-of-scope branches (hospital, other-persons, Opt.Plus/Premium) emit an
> `advisor_route` signal and end the session as a clean (non-conversion) exit.

**The interface (the contract the harness depends on):**

```
WidgetModel (Protocol, sim.py) — the ONLY thing the harness knows about a widget
  render(step, ctx)        -> screen JSON       # produce the screen the persona sees
  legal(step)              -> action schema     # closed action space (§3)
  react(step, user_events) -> signal events     # price_reveal / validation_error / advisory_badge / idle_timeout
  apply(decision)          -> effector events   # coach effector cmd mutates the screen
```

**Two interchangeable implementations behind that one interface:**

```
              WidgetModel (Protocol)  ◀── harness only ever sees this
             /                       \
  StaticWidget                        GenerativeWidget
  (deterministic, schema-templated    (a model that GENERATES screen JSON
   over widget.py — ships now)          given the schema — drops in later,
                                        ZERO harness change)
```

- **Both must produce byte-identical-shaped JSON** for the same `(step, ctx)` — the
  schema (§3) is the contract, not the producer. A harness test asserts the static
  and generative widgets are **substitutable**: same `legal(step)`, same event types
  out of `react()`, same `RenderEnvelope.kind`.
- The harness, the persona prompt (§2 `screen` block), and the coach observation all
  consume `render()`/`legal()` output **without knowing which implementation produced
  it**. That uniformity is the deliverable, not the producer's internals.

**What we build now vs later (an implementation choice, not an interface choice):**
- Now: `StaticWidget` — deterministic schema-templating over `widget.py`. Sufficient
  for the fixed UNIQA funnel; cheap; the funnel screens are known.
- Later (interface-ready, not blocked): `GenerativeWidget` — a model that emits screen
  JSON for unseen products. It plugs into the **same** `WidgetModel` Protocol, so
  nothing in the harness, persona, or coach changes when it arrives.

Why this matters for training: the widget's `react()` signals are **conditioning**
the persona-model learns to respond to (price shock → bounce). Because the interface
is uniform, the persona is trained against the interface — not against the static
widget — so a future generative widget needs **no persona retrain** as long as it
honours the same schema + signal vocabulary.

---

## 5. Data generation (TONIGHT — gates the Leonardo window)

```
OpenRouter teacher (strong model)
   │  persona_datagen Flow A: whole-session, system=persona.md, schema=widget.render
   ▼
raw JSONL sessions ──parse_session (schema gate)──▶ valid sessions ──┐
   │  drop malformed; log validity rate (must be high)               │
   ├─ counterfactual pairs: re-gen X% with one atom removed (R6)      ├─▶ train shards
   └─ reasoning/thought stored inline (distil into coach later, §6)   │
                                                                       │
psyche.py synthetic (volume floor, calibrated 5.6/66/24/78) ──α_mix──┘
```

- **Target volume:** 6–10k teacher sessions @ 30/50/20 mix + ~20k psyche sessions
  (`α_mix` ≈ 0.5). Each session ~1–2k tokens → ~30M training tokens.
- **Mix-in psyche data** is the cheap insurance against teacher drift (R1): it pins
  the marginals while the teacher provides shape/voice/`thought`.
- **Cost/throughput:** ~10k sessions × ~1.5k output tok. Generate on laptop/login now;
  cap by wall-clock, not perfection. Start immediately — this is the critical path.
- **Source C — real-human seed (Stage 0):** a handful of *my own* recorded walk-throughs
  of the real form, captured by the engine as `ActivityLog`s with **real timing**
  (dwell, Δt, hesitation, re-edits), each crafted to embody one of the 3 personas.
  Tiny count, outsized value: it injects the timing realism teacher data lacks
  (attacks R3) and gives the model genuine human action examples to anchor on.
  *Needs a capture harness:* a thin browser hook that emits `contracts.Event`s into an
  `ActivityLog` (the same format the sim and a future prod deployment use — §Loop B).
  This same harness is reused in Stage 6 to capture production clicks.

---

## 6. Coach model (2nd LoRA adapter, trained after persona)

Same recipe, same base, **separate adapter** (swap adapters at serve time):

```
in:  CoachObservation JSON  (activity window, form_state, budget) — NO latent/persona
out: CoachDecision JSON     (EffectorCommand + reasoning + hypotheses + value_estimate)
teacher data:
   • OpenRouter generating coach decisions from observations (with reasoning)
   • + existing RuleCoachModel.decide traces as additional SFT pairs (distil the rules)
loss: completion-only on the decision JSON
drop-in: replaces RuleCoachModel.decide(obs) in coach_io.py — zero contract change
```

Sequence: persona first (it's the environment the coach is optimised against in Loop
A). Coach FT is a fast follow once persona lands and the sim loop is green.

### 6.1 Persona identification — `p_identify` (a simulation parameter)

The coach observation deliberately **omits the persona label** (`CoachObservation`
carries no latent/persona — §2) because in production the coach doesn't get told who
the user is. It must **infer** the persona to tailor strategy (Franz: never route to
advisor; Peter: early callback before the price wall; Judith: reassure + graceful
advisor option). We model that inference as one knob:

```
p_identify ∈ [0,1]   (simulation parameter, swept)
  with prob p_identify        coach sees the TRUE persona class → tailored policy
  with prob (1 - p_identify)   coach sees a wrong / "unknown" class → generic policy
```

- **In sim:** sweep `p_identify` from 0.33 (random over 3) to 1.0 and plot uplift vs
  identification accuracy. Shows how much conversion depends on getting the segment
  right, and how gracefully the coach degrades when it's wrong (it must not *harm* a
  misidentified user — e.g. never push Franz to an advisor even under a wrong guess).
- **In production (how `p_identify` is realised):** a classifier over first-party
  signals produces a posterior over {Judith, Franz, Peter}; its accuracy *is*
  `p_identify`. Signals: cookie history (returning vs new), retargeting-audience
  membership, traffic source / referrer, **UTM** campaign/medium/content, device +
  daypart, and any first-party segment/lifestyle data. The coach acts on the argmax
  (or stays generic when the posterior is flat). We do **not** train on this now; we
  expose the knob and document the realisation path.

### 6.2 Feature space + importance weighting

We have far more about each persona than behaviour: `personas.json` carries income,
NPS, KV ownership, purchase intent, switch willingness, products owned, online-share,
channel preference, age (§ data provenance in `PERSONA_MODEL_PLAN.md`). Two consumers
want features: the **persona model** (what conditions behaviour) and the **coach's
identifier** (§6.1). Open question the user named: *lifestyle data may or may not
affect what a user actually does on the page.* So weight features by measured effect.

```
feature tiers (initial weights, then learned):
  behavioural  (dwell, hover, re-edits, backtracks, Δt)   → weight 1.0  (direct causal link to actions)
  segment      (persona class, intent)                    → weight 1.0  (conditioning axis)
  lifestyle    (income, NPS, products owned, online-share)→ weight LEARNED (may be ~0)
```

**Importance scheme (cheap, auditable):**
1. **Ablation in the sim** — drop/shuffle one feature, re-sample cohorts, measure Δ in
   the G2 funnel-fit + G3 separability + coach uplift. No movement → the feature is
   inert for on-page behaviour → down-weight toward 0.
2. **Probe model** — fit a small logistic / gradient-boosted model predicting
   `bounce vs convert` (and bounce-step) from the full feature vector; use
   permutation importance / SHAP magnitudes as the weights.
3. **Keep-if-it-helps gate** — retain a lifestyle feature only if it improves a gate
   beyond noise; otherwise pin its weight to ~0. This directly de-risks **R5 (persona
   leakage / spurious lifestyle correlation)** and keeps the model from leaning on
   demographics that don't actually drive clicks.

Report the learned weight vector as an artifact (`feature_importance.json`) so the
"which lifestyle signals actually matter" question has a data answer, not a guess.

---

## 7. Leonardo job (no-internet staging + the 12:00 cutoff)

**Hard constraints:** reservation `s_tra_ncc` (account `euhpc_d30_031`) **ends
2026-05-31 12:00**; compute nodes have **NO internet**.

```
TONIGHT (laptop / login node — login HAS internet):
  1. generate + schema-gate teacher data (§5) → push shards to $WORK
  2. pre-download openbmb/MiniCPM5-1B to $WORK (no HF pull on compute node)
  3. stage env: torch + peft + trl + flash-attn (pixi/conda), or set proxy in job script

TOMORROW AM (single sbatch, well inside the window):
  partition boost_usr_prod · reservation s_tra_ncc · 1×A100 64GB · ~1.5h walltime
  PEFT LoRA: r=16 α=32 dropout=0.05, targets [q,k,v,o,gate,up,down]
  bf16 + FlashAttention-2 + grad-checkpointing; TRL SFTTrainer, completion-only loss
  seq 2048 · batch 16 + grad-accum · lr 1e-4 cosine · 2–3 epochs (~30M tok ≈ 1.1h)
  artifacts: persona_lora/ (adapter), eval_report.json, samples_per_persona.jsonl
SERVE:
  merge or load base+adapter → OpenAI-compatible endpoint → point sim.LLMPersona
  base_url at it. Sim runs unchanged.
```

**Laptop fallback (real, de-risks the cutoff):** `MiniCPM5-1B-MLX` 4-bit exists →
LoRA on Apple Silicon if the queue is deep or the window closes. Plan stays alive
without Leonardo.

---

## 8. Eval gates (reuse TLM gates + FT-specific G0)

| Gate | Metric | Threshold | Note |
|---|---|---|---|
| **G0 JSON validity** | % teacher-format sessions that `parse_session` accepts | **≥ 98%** | NEW + critical: a FT model that emits malformed JSON is useless |
| **G1 distillation fidelity** | student vs teacher next-event distribution on held-out sessions | JS ≤ 0.15 | "did the student learn the teacher" |
| **G2 funnel match** | sample 5k/persona → per-step survival vs anchors (5.6/66/24/78) | TV ≤ 0.08 | calibration via sampling temp + intent prior (weak on LLM → TLM owns the calibrated `b`) |
| **G3 persona separability** | JS of next-event dist at S4 entry across J/F/P pairs; 2-sample classifier AUC | JS ≥ 0.10, AUC ≥ 0.65 | hold under `persona:unknown` dropout (R5) |

ε feeds the Z3 safety budget `b` (`docs/PERSONA_TLM_DESIGN.md §3.4`). Because FT-LLM
calibration is weak, the **tiny TLM remains the model whose `ε_anchor` sets `b`** —
the FT model is graded against the same gates but the Z3 story leans on the TLM.

---

## 9. Failure modes (per codepath: failure → guard)

| Codepath | Realistic prod failure | Guard / does it exist |
|---|---|---|
| FT model output | malformed JSON → sim crash / empty session | `parse_session` schema gate + retry; **`sim.LLMPersona` already falls back to psyche stepping** ✅ |
| Data-gen tonight | OpenRouter slow/expensive → miss window | cap sessions by wall-clock; psyche volume floor; start NOW |
| Distillation | student ≠ teacher (large ε) | mix-in psyche (`α_mix`); report ε honestly; Loop B refit later |
| Calibration | LLM won't hit exact 5.6/66/24/78 | TLM owns calibrated `b`; report uncalibrated + sampled stats (transparency) |
| Leonardo | reservation missed / queue deep | MLX 4-bit laptop LoRA fallback (§7) |
| Action space | teacher emits illegal action | `legal_events` drops it; invariant tests (§8) catch registry drift |

**Critical-gap check:** no failure mode is both *silent* AND *unhandled* — the schema
gate + psyche fallback make bad FT output loud and recoverable.

---

## 10. Test plan (what implementation must add)

- `test_action_space.py` — the 4 invariants in §3 (registry single-source, legal-event
  mapping, TARGETS ⊇ STEP_ACTIONS targets, no wildcard collapse). **[regression risk:
  `tlm.TARGETS` change can desync the TLM vocab — guard it.]**
- `test_widget_react.py` — `react()` emits the right signals (premium→advisory_badge+
  price_reveal; bad dob→validation_error; idle→timeout).
- `test_widget_substitutable.py` — **interface-uniformity guard**: `StaticWidget` and a
  stub `GenerativeWidget` are interchangeable behind `WidgetModel` — same `legal(step)`,
  same `react()` event-type set, same `render()` shape for a given `(step, ctx)`. This is
  the test that proves the RTI is uniform; the harness must pass with either plugged in.
- `test_persona_ft_io.py` — prompt assembler round-trips; FT-format output parses;
  FT persona is a valid `PersonaModel` Protocol drop-in (behind a stub/local endpoint).
- `test_eval_metrics.py` — TV / JS / funnel-survival functions correct on toy fixtures.
- Reuse: `test_persona_datagen.py`, `test_sim.py`, `test_widget_session.py` already
  cover the teacher pipeline + Flow A/B loop.

---

## 11. Timeline vs the 12:00 cutoff

```
NOW ──────────────────────────────────────────────────────────────▶ 2026-05-31 12:00
 │ tonight                          │ tomorrow AM          │ cutoff
 ├─ §3 action-space registry (1-2h) │                      │
 ├─ §5 data-gen + schema gate ▶▶▶▶▶▶│ (runs overnight)     │
 ├─ §7 stage MiniCPM weights + env  │                      │
 │                                  ├─ sbatch LoRA (~1.5h)  │
 │                                  ├─ G0–G3 eval (30 min)  │
 │                                  ├─ serve + sim swap     │
 │                                  └─ coach adapter (§6, fast follow if time)
```

**Critical path = data-gen tonight.** Everything downstream is fast. If data-gen
slips, the MLX laptop fallback keeps H1 alive past the reservation.

---

## 12. NOT in scope (deferred, with reason)

- **`GenerativeWidget` implementation** (§4) — the *interface* is built now so it drops in later with zero harness change; the concrete generative producer itself is deferred (static funnel is fixed, doesn't need it yet).
- **Full fine-tune** of MiniCPM — LoRA is sufficient and safer; full FT spends risk for no gain.
- **Multimodal persona-TLM** (CLIP on screenshots) — only if G3 fails; see TLM_DESIGN v1.
- **Loop B online refit** (PersonaFit + IPS off-policy eval) — post-hack; needs real logs.
- **Coach RL beyond SFT distillation** (GRPO on conversion reward) — after SFT coach lands.

## What already exists (reuse, don't rebuild)

`sim.py` Protocols + Flow A/B loop · `widget.py` action space + reactive signals ·
`persona_datagen.py` OpenRouter teacher + `parse_session` schema gate ·
`contracts.py` JSON I/O · `psyche.py` calibrated volume floor ·
`karpathy-experiment/` nanoGPT trainer (for the tiny-TLM baseline) ·
`leonardo-connect` skill (SSH + SLURM templates).
