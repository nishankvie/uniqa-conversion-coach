# Pipeline Plan — LLM personas, coach prompt autoimprovement, multi-surface coach, outer loop

> **Z3 status: DEFERRED.** The self-improvement gate is **empirical** for now
> (accept iff `Δuplift > τ` under an annoyance ceiling). The formal Z3 safety
> certificate is drafted at `specs/deferred/coach_autoimprove_z3.py` and is out of
> scope this round; mentions of "Z3-certified" below describe that deferred proof.

> **Scope now.** Personas stay **LLM-driven** (OpenRouter teacher *is* the persona —
> no local fine-tune yet). Build the **full pipeline + project structure**, prove
> **basic coach-prompt autoimprovement** (empirical gate now; formal Z3 certificate
> deferred), then **generalize the
> coach to multiple surfaces** (on-page widget, email, WhatsApp bot, landing page,
> feedback form, survey) and wire the **outer feedback loop** (periodic model
> re-evals/updates from production logs).
>
> **The coach is the training subject.** After the prompt is accepted by the gate we **fine-tune
> a 1B model (MiniCPM5-1B, LoRA) as the coach on CINECA Leonardo** — input = current
> session logs, output = reasoning + action log (§5.1). This is where the HPC budget is
> spent. **Persona** stays LLM-driven; its local fine-tune is **deferred** (§9 +
> `deferred/PERSONA_TLM_DESIGN.md` / `deferred/PERSONA_MODEL_PLAN.md` / `deferred/TLM_RESEARCH.md`).
>
> Grounded in code that exists: `sim.py` (Protocol loop), `widget.py` (static widget +
> action space), `persona_datagen.py` (OpenRouter persona/teacher), `contracts.py`
> (JSON I/O), `autoresearch.py` + `specs/deferred/coach_autoimprove_z3.py` (Loop A + proof).

---

## The whole pipeline (big picture)

Through-line: **bootstrap on real human behaviour → close the loop in simulation with
LLM personas → prove coach self-improvement with Z3 → generalize the coach across
surfaces → re-ground continuously on production data.** Going fully local is a later
optimization, not a prerequisite.

```
 STAGE 0 ─ RECORD REAL HUMAN            STAGE 1 ─ SEED THE SIM             STAGE 2 ─ COACH + SURFACES
   I click the real UNIQA form;       3 personas, LLM-DRIVEN             stand up the coach over a
   engine captures timing / dwell  →  (OpenRouter) + the STATIC      →  GENERALIZED, multi-surface
   / hesitation. Craft sessions to     WIDGET (real funnel screens,      action space (on-page widget,
   embody the 3 personas.              §"static widget") as the env       email, WhatsApp, LP, survey).
        │ real-timing seed                = Surface interface              Coach must infer persona →
        │                                 (one iface, swappable impl)      p_identify (§"persona id")
        └────────────────────────────────────┬──────────────────────────────────┬──────────────────────┘
                                              ▼                                  │
 STAGE 3 ─ COACH PROMPT AUTOIMPROVE  (PROVE THIS NOW)                             │
   propose coach-prompt/policy variants → eval vs LLM-persona sim (paired A/B) →  │
   EMPIRICAL gate accepts only Δuplift > τ wins. [formal Z3 proof DEFERRED]       │
        │ certified-better coach prompt                                           │
        └────────────────────────────────────┬──────────────────────────────────┘
                                              ▼
 STAGE 4 ─ PROD DEPLOY + OUTER LOOP (Loop B)            STAGE 5 ─ FEATURES + IMPORTANCE
   ship the pipeline; I click through PROD; the         feed as many persona features as
   engine captures real (activity, decision,         →  possible (lifestyle, NPS, income,
   outcome, surface-outcome). PERIODIC re-eval:          channel pref…); learn which actually
   re-fit persona priors, off-policy eval the            move actions — importance weighting
   coach (IPS), re-run Stage 3 → Z3 gate → ship.         (§"features").
        │
        └───▶ STAGE 6 ─ FINE-TUNE THE COACH (Leonardo, ACTIVE): distill the Z3-certified
              coach into a 1B LoRA (MiniCPM5-1B). in = session logs → out = reasoning +
              action log. Runs local in prod. [Persona fine-tune stays DEFERRED, §9.]
```

**Stage notes:**

0. **Record real human interactions first.** I walk the real form; the engine logs the
   event stream with **real timing** (dwell, Δt, hesitation, re-edits), crafted to
   embody each persona. This is the timing-realism seed synthetic data lacks.
1. **3 LLM personas + static widget.** Personas are prompted LLMs (`persona_datagen` /
   `sim.LLMPersona`); the env is the static widget behind the Surface interface.
2. **Coach + multi-surface action space.** The coach decides *whether*, *with what
   intent*, and now *on which surface* to intervene (§"multi-surface coach").
3. **Coach prompt autoimprovement + Z3 — the thing to prove now.** Loop A tunes the
   coach *prompt/policy* against the LLM-persona sim; the Z3 certificate guarantees
   only real improvements ship (§"autoimprove").
4. **Prod deploy + outer loop (Loop B).** Real logs periodically re-fit personas +
   re-eval the coach, then re-run Stage 3 (§"outer loop").
5. **Features + importance weighting** (§"features").
6. **Fine-tune the coach on Leonardo — ACTIVE** (§5.1): distill the Z3-certified coach
   into a 1B LoRA (session logs → reasoning + action log); it runs local in prod. The
   *persona* local fine-tune stays deferred (§9).

---

## 1. Project structure (the general scaffold)

Map the pipeline to modules. `(new)` = to build; everything else exists.

```
src/uniqa/
  contracts.py        events · effectors+SURFACES · Coach I/O · render envelopes
  funnel.py / scope.py  funnel state machine + in-scope guard
  widget.py           StaticWidget: real funnel screens + action space (the env)
  surfaces/ (new)     Surface impls: on_page, email, whatsapp, landing, survey
                      — each = render(schema)→JSON + outcome semantics, one iface
  psyche.py           calibrated latent persona (volume floor / baseline / Z3 b-anchor)
  personas.py +
  persona_datagen.py  LLM-driven personas (OpenRouter) — the persona engine NOW
  sim.py              turn-based loop: persona ↔ Surface ↔ coach (Protocol-typed)
  coach.py +
  coach_io.py         coach policy (PROMPT + decision rules) + observation/decision adapter
  autoresearch.py     Loop A: propose coach-prompt → eval vs personas → Z3 gate → accept
  simulation.py       Monte-Carlo A/B uplift report
  loopb/ (new)        Loop B: prod-log ingest · persona refit · IPS off-policy eval
  app.py              Streamlit demo
specs/deferred/coach_autoimprove_z3.py   the certificate (T1–T5)
docs/                 this plan · ARCHITECTURE · AUTORESEARCH · FUNNEL_AUTOPSY · …
```

The three players still talk over **one JSON contract** (`contracts.py`); each is
swappable behind its Protocol (`PersonaModel` / `SurfaceModel` / `CoachModel` in
`sim.py`). LLM-persona ↔ future local persona is a base-URL swap; on-page widget ↔
email ↔ WhatsApp is a Surface-impl swap. Uniform interfaces are the whole point.

---

## 2. Personas — LLM-driven now (local later)

- **Now:** the persona is a prompted LLM over OpenRouter. `persona_datagen` already
  assembles the prompt (system = `persona_<seg>.md` + `personas.json` attrs + fixed
  intent; user = the widget's screen JSON + history) and parses the emitted events
  through the `parse_session` schema gate. `sim.LLMPersona` is the drop-in.
- **Mix-in `psyche.py`** synthetic sessions as the calibrated volume floor (5.6 / 66 /
  24 / 78 anchors) and the baseline the LLM persona is sanity-checked against.
- **No training now.** We do not fine-tune a local persona model this round (§9).

I/O per turn (drop-in for `sim.LLMPersona`):

```
SYSTEM:   persona_<seg>.md + personas.json[segment] + session intent
USER:     { "screen": Surface.render(step), "history": [collapsed events] }
ASSISTANT:{ "events": [ {type,target,value,thought}, ... ] }   # this step only
          type ∈ legal_events(step), target ∈ action space (§3)
```

---

## 3. The static widget (env) + action space — single source of truth

The **static widget spec** = the real funnel screens + the closed per-step action
space. It is `src/uniqa/widget.py` (executable) plus this table; drop-off analysis is
in `FUNNEL_AUTOPSY.md`. The funnel starts at the **intro screens**, not the tariff
table.

| Step | Phase | Screen | Drop | Signal the surface emits |
|---|---|---|---|---|
| **S1** | Inputs | Where covered? `At doctor visits`✅ / `In hospital`❌ | low | branch; hospital → `advisor_route` |
| **S2** | Inputs | Who insured? `Myself`✅ / `Other persons`❌ | low | branch; others → `advisor_route` |
| **S3** | Inputs | DOB + Sozialversicherung-Nr | low-med | first PII before any price → trust barrier |
| **S4** | Product | Tariff table — **provisional** premium (Start €38.74 / Optimal €68.14; Opt.Plus/Premium advisory) | **66%** | `price_reveal`(provisional) + `advisory_badge` |
| ~~S5~~ | Product | Add-on (Sonderklasse) | (24%) | **hospital path → OUT of scope**; private-doctor users skip |
| **S6** | Inputs | Health questions | — | health data for *final* premium (coach never sees these as features) |
| **S7** | Recommendation | **Final** premium after health assessment | **78%** | `price_reveal`(final, usually > S4) → trust-collapse moment |
| **S12+** | Closing | name/address · start date · payment · consents · confirm | — | the actual online `convert` |

**`widget.py` gaps to close (extends the static widget, not the critical path):**
1. **Two price walls**, not one: add the **S7 final-price** reveal (today's code conflates
   S4 with a merged personal+health step and has no S7). `price_reveal` should carry
   both provisional and final values so the persona reacts to the *delta*.
2. **Closing block S12+** (payment/consents/confirm) is unmodeled — add a minimal
   closing screen so a session can reach a real `convert`.
3. Out-of-scope branches (hospital, other-persons, Opt.Plus/Premium) emit
   `advisor_route` and end as a clean (non-conversion) exit.

**Action-space invariants (test them):** (a) every `(kind,target)` in `STEP_ACTIONS`
maps to exactly one `EventType` in `legal_events`; (b) no emitted event is outside the
step's legal set (schema gate proves it); (c) the per-step closed target set has no
wildcard collapse (`tlm.TARGETS` must ⊇ every `STEP_ACTIONS` target).

---

## 4. Multi-surface coach (the generalization)

Today the effector surface is **on-page only** (`contracts.Effector`: SHOW_WIDGET,
FOCUS_FIELD, HIGHLIGHT, AUTOFILL, SAVE_PROGRESS, …). Generalize so the coach can **land
the user on a different surface** — the same uniform-interface move we made for the
widget, now applied to *where* the coach speaks.

```
              SurfaceModel (Protocol) ◀── coach/harness only see this
   on_page ─ email ─ whatsapp ─ landing_page ─ feedback_form ─ survey ─ advisor_booking
   each impl:  render(spec) -> JSON   ·   deliver(payload)   ·   outcome() -> events
```

- **Action space becomes `(intent × surface)`.** A `CoachDecision` carries a `surface`
  (default `on_page`) alongside the existing intent + effector + reasoning. One new
  effector `LAND_ON_SURFACE` (or a `surface` field on `SHOW_WIDGET`) covers it.
- **Per-surface contract + outcome semantics:**

  | Surface | When the coach picks it | Outcome signal |
  |---|---|---|
  | `on_page` widget | live hesitation, in-funnel | widget_cta / dismiss / convert |
  | `email` | exit-intent / 30s idle / S6 form fatigue → resume link + quote | open / click / async-resume |
  | `whatsapp` bot | Peter (service-affine) before the price wall; conversational handoff | reply / booked-callback |
  | `landing_page` | tailored micro-LP for a segment from an ad click (UTM) | LP→funnel re-entry |
  | `feedback_form` / `survey` | terminal exit-intent → capture *why* they're leaving | submit (reason label) |
  | `advisor_booking` | hospital / other-persons / Opt.Plus/Premium (clean out-of-scope exit) | booking (not a conversion) |

- **Guardrails (the APP enforces, regardless of policy):** consent required for
  `email`/`whatsapp`/`survey`; surface availability gated per step/persona; one shared
  **annoyance budget across all surfaces** (an email + a widget both count). Health
  (S6) data never crosses into any surface payload.
- **Why it matters:** conversion isn't only "finish now on-page." For Peter a WhatsApp
  callback *is* the win-path; for an S6 bouncer an email resume-link recovers the lead;
  a survey on a terminal exit feeds Loop B with refusal reasons. The coach's job is to
  pick the right surface, not just the right copy.

---

## 5. Coach prompt autoimprovement (prove this now; formal Z3 certificate deferred)

The coach is **LLM-driven**: its policy lives in a **prompt** (system role + decision
rules + per-surface copy templates + thresholds). Loop A improves *that prompt*.

```
PROPOSE  prompt variant Δ (reword trigger, reorder rules, shift a threshold,
         swap surface for a persona, tighten budget)
   │
SIMULATE run N sessions/persona through the LLM-persona sim (paired, same seeds)
   │
EVALUATE Δuplift = conversion(variant) − conversion(current);  annoyance, surface mix
   │
GATE     accept iff Δuplift > τ  (empirical margin) AND annoyance ≤ ceiling
REPEAT
         [DEFERRED: the formal Z3 certificate that τ ≥ 2b makes every accepted
          change a real, monotone improvement — specs/deferred/coach_autoimprove_z3.py]
```

- `autoresearch.py` already implements the gated hill-climb; here the **mutation space
  is coach-prompt edits** (not hand-tuned scalars). Keep mutations small + auditable so
  each accepted change is explainable.
- **Formal safety proof — DEFERRED:** the Z3 certificate (*if `|U_sim − U_real| ≤ b`
  and `τ ≥ 2b`, every accepted prompt is a real, monotone improvement and the loop
  converges*) is drafted in `specs/deferred/coach_autoimprove_z3.py` and written up in
  `AUTORESEARCH.md`, but is out of scope this round. For now the gate is purely
  empirical (`Δuplift > τ`); choose `τ` conservatively from the persona-sim's anchor TV.
- **Demo deliverable:** show a before/after coach prompt where Loop A found a real,
  Z3-certified uplift (e.g. moving Peter's callback to a WhatsApp surface *before* S4).

### 5.1 Coach fine-tune — MiniCPM5-1B on Leonardo (the HPC step)

Once the coach *prompt* is Z3-certified, **distill it into a local 1B model** so the
coach runs on our own GPU in prod (cheap, low-latency, private) — and so the project
actually uses the Leonardo allocation. **The coach, not the persona, is the model we
train.**

```
model:  openbmb/MiniCPM5-1B  (standard LlamaForCausalLM, LoRA r=16, bf16+FA2)
INPUT:  current session logs  — CoachObservation JSON (activity window, form_state,
        budget, surface availability).  NO persona label, NO health (S6) data.
OUTPUT: reasoning + action log — CoachDecision JSON:
          { reasoning: "...",                 # human-readable chain (the 'reasoning')
            command: {effector, surface, target, payload},   # the action ('log')
            hypotheses: [...], value_estimate }
loss:   completion-only on the decision JSON (reasoning + command).
data:   traces of the Z3-certified prompt (the OpenRouter coach) over the sim
        (obs → reasoning+decision) + RuleCoachModel traces. ~10–30k pairs.
```

- **Leonardo job:** 1×A100 64GB, partition `boost_usr_prod`, reservation `s_tra_ncc`
  (account `euhpc_d30_031`, **window ends 2026-05-31 12:00**). Pre-stage MiniCPM weights
  + the trace dataset on a login node (compute nodes have **no internet**); LoRA SFT
  ~1–1.5h. Artifacts: `coach_lora/`, `eval_report.json`. Laptop MLX 4-bit fallback if
  the window closes.
- **Eval gates:** G0 JSON validity (decision parses + `EffectorCommand.validate()`
  passes) ≥ 98%; agreement with the teacher's decisions on held-out obs; and — the gate
  that matters — **sim uplift of the FT coach ≥ the prompt's uplift** (distillation must
  not regress the Z3-certified behaviour).
- **Drop-in:** the FT coach replaces `RuleCoachModel.decide(obs)` behind `CoachModel`
  (`coach_io.py`) — zero contract change. Personas stay LLM-driven at sim time.
- **Why the coach (not the persona):** the coach is the shipped product; making *it*
  local gives real-time prod inference + the HPC story. Personas are only needed at sim
  time, so they stay on the LLM and don't need a GPU.

---

## 6. Outer feedback loop (Loop B) — periodic re-eval/update from prod logs

Stage 3 is the fast inner loop on synthetic personas. Loop B is the slow outer loop
that keeps the synthetic world honest with real data. (Extends `ARCHITECTURE.md §6`.)

```
PROD deploy (local pipeline) ──▶ engine captures real tuples:
        (activity_log, coach_decision, surface, outcome)         [the capture harness, §0/§2]
   │
PERIODIC batch (per release / weekly):
   ├─ (1) RE-FIT persona priors  : intent mix, timing, surface-response rates so the
   │       LLM-persona sim's funnel stats match real → shrinks b
   ├─ (2) OFF-POLICY EVAL coach   : IPS / counterfactual estimate of the live coach on
   │       real logs → ground-truth uplift vs the synthetic estimate
   ├─ (3) HYPOTHESIS hit-rate     : score contracts.Hypothesis vs what actually happened
   │       → recalibrate the user model + surface-choice priors
   └─ (4) RE-RUN Stage 3 on the refreshed sim → propose new coach prompt
            → Z3 gate → shadow deploy → next batch
```

- **Cadence:** every prod batch (or weekly). Each cycle re-measures `b`, re-runs Loop A,
  ships only Z3-certified prompts. Loop B's entire job is to **keep `b` small so the
  Stage-3 proof stays valid**.
- **Multi-surface outcomes feed it:** email opens, WhatsApp replies, survey reasons,
  and on-page conversions are all outcome signals that refit persona surface-response
  priors and grade the coach's surface choices.
- **Re-eval, not just retrain:** the periodic job re-scores the coach against fresh logs
  *before* proposing changes, so regressions surface as a failed gate, not in prod.

---

## 7. Persona identification — `p_identify` (a simulation parameter)

The coach observation omits the persona label (prod doesn't tell it who the user is);
it must **infer** the persona to pick intent + surface (Franz: never advisor; Peter:
early WhatsApp callback; Judith: reassure + graceful advisor option).

```
p_identify ∈ [0,1]   (simulation parameter, swept)
  with prob p_identify       coach sees the TRUE persona class → tailored policy + surface
  with prob (1 - p_identify) coach sees wrong / "unknown" class → generic, do-no-harm policy
```

- **In sim:** sweep `p_identify` 0.33→1.0; plot uplift vs identification accuracy and
  verify graceful degradation (a misidentified Franz is never pushed to an advisor).
- **In prod (how it's realised):** a classifier over first-party signals — cookie
  history (returning/new), retargeting-audience membership, traffic source / referrer,
  **UTM** campaign/medium/content, device + daypart, first-party segment data — emits a
  posterior over {Judith, Franz, Peter}; its accuracy *is* `p_identify`. Documented now,
  not trained now.

---

## 8. Features + importance weighting

`personas.json` carries far more than behaviour: income, NPS, KV ownership, purchase
intent, switch willingness, products owned, online-share, channel preference, age
(see `deferred/PERSONA_MODEL_PLAN.md` data provenance). Two consumers: the LLM-persona prompt
(conditioning) and the coach's identifier (§7). Open question: *lifestyle data may or
may not affect on-page actions.* So weight by measured effect.

```
behavioural (dwell, hover, re-edits, backtracks, Δt) → weight 1.0  (direct causal link)
segment     (persona class, intent)                  → weight 1.0  (conditioning axis)
lifestyle   (income, NPS, products owned, online-share) → weight LEARNED (may be ~0)
```

**Importance scheme (cheap, auditable):** (1) **ablation in the sim** — drop/shuffle a
feature, re-sample cohorts, measure Δ in funnel-fit + uplift; no movement → inert →
down-weight to ~0. (2) **probe model** — logistic / GBM predicting bounce-vs-convert
from the full vector; permutation importance / SHAP magnitudes = weights. (3)
**keep-if-it-helps gate** — retain a lifestyle feature only if it beats noise on a
gate; else pin to ~0 (de-risks leaning on spurious demographics). Emit
`feature_importance.json` so "which lifestyle signals matter" has a data answer.

---

## 9. DEFERRED — local PERSONA fine-tune

The **coach** fine-tune is active (§5.1). The **persona** local fine-tune is the part
that stays deferred: distill the OpenRouter teacher into a LoRA **MiniCPM5-1B** persona
that emits the same JSON sessions, then drop the teacher. Feasibility (1×A100,
no-internet staging, reservation window), the tiny-TLM alternative, and the calibration
→ Z3 `b` connection are preserved in `deferred/PERSONA_TLM_DESIGN.md` /
`deferred/PERSONA_MODEL_PLAN.md` / `deferred/TLM_RESEARCH.md`.

**Why deferred:** personas are only needed at *sim* time, so the LLM is fine; a local
persona is a cost optimization, not a correctness requirement. The coach is the product
that ships to prod, so the coach is what we make local first (§5.1).

---

## NOT in scope (now) / What already exists

**NOT now:** local *persona* fine-tune (§9; the *coach* fine-tune IS active, §5.1) ·
trained/generative widget (the *interface* is uniform, the producer stays static) ·
multimodal persona · deposit-first / eID structural funnel changes (pitch only, see
`FUNNEL_AUTOPSY.md`).

**Reuse, don't rebuild:** `sim.py` Protocol loop (persona ↔ surface ↔ coach) ·
`widget.py` action space + reactive signals · `persona_datagen.py` OpenRouter persona +
schema gate · `contracts.py` JSON I/O · `psyche.py` calibrated floor + `b`-anchor ·
`autoresearch.py` + `specs/deferred/coach_autoimprove_z3.py` (Loop A + certificate) ·
`leonardo-connect` skill (SSH + SLURM templates for the §5.1 coach job).
