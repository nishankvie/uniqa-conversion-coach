# Sub-plan: the Persona Model

How we build a persona model that emits realistic event feeds and is **trainable
against the known funnel metrics**. Full model design is in
[`PERSONA_TLM_DESIGN.md`](PERSONA_TLM_DESIGN.md) (Opus). This doc is the build
plan + the critical-next-steps / assumptions register the work now rests on.

Status: PLAN. Code today = `psyche.py` (latent-mind persona) + `tlm.py` (token
space) + `contracts.py` (event schema). The persona-TLM replaces/augments the
hand-coded psyche engine with a learned one.

---

## Step 0 — scope

**Goal in one line:** a persona model whose generated event feeds (a) match real
samples closely enough and (b) can be calibrated to hit conversion 5.6% +
drop-offs 66/24/78 + the 30/50/20 persona mix, so Loop A autoresearch has a
faithful simulator with a measured ε.

**What already exists (reuse, don't rebuild):**
- `contracts.Event/ActivityLog` — the feed schema the LLM must emit (schema gate).
- `tlm.encode/decode/VOCAB` — token space (needs the §1.6 deltas from the design).
- `psyche.py` — calibrated latent engine → the volume data source + the
  behavioural baseline the TLM must match.
- `eventproc.collapse` — granularity (train on Moments, not mouse spam).
- `karpathy-experiment/` nanoGPT adapter — the trainer.
- `leonardo-connect` skill — the 1×A100 job runner.

**Minimum change:** two new things only — (1) a **data-gen pipeline** (LLM teacher
→ event feeds), (2) a **TLM train+calibrate** path. Everything else is reuse.
No new services. Scope is tight; not over-built.

---

## 1. Data generation pipeline (the committed approach)

For each step the user is on, prompt an LLM to play the persona and emit the next
event(s) in our `contracts.Event` schema:

```
   ┌──────────────────────── DATA-GEN STEP PROMPT ────────────────────────┐
   │ SYSTEM:  persona.md  +  persona.json fields  (+ sampled Intent)        │
   │ WORKFLOW (per step), the LLM sees what the user sees:                   │
   │   (a) low-res schematic UI image     ── play.ascii_screen / PNG thumb   │
   │   (b) json-render of the static UI   ── journey.STEP_SCREENS / Envelope │
   │   (c) intervention atoms             ── coach widget/effector, embedded │
   │        embedded in BOTH (a) and (b)     in the json-render AND the image│
   │   (d) short "Coach TLM reasoning"    ── one line, why the atom fired    │
   │ OUTPUT: next user event(s) as contracts.Event JSON                      │
   └────────────────────────────────────────────────────────────────────────┘
                              │  validate against contracts.Event (schema gate)
                              ▼  drop non-parsing feeds
                    ActivityLog  ──collapse──▶ Moments ──tlm.encode──▶ token ids
```

Key properties:
- The LLM emits **collapsed-granularity** events (step_enter, hover, idle/dwell,
  field_edit, nav_back, tariff_click, premium_click, cancel_hover, submit,
  convert/abandon) — not raw mouse moves. Matches `eventproc` output.
- **Intervention atoms are first-class inputs**: the same coach widget/effector
  appears in the json-render, in the low-res UI, and as an `<atom:intent:phase>`
  token — so the persona learns how each atom shifts behaviour (supervised analog
  of `psyche.apply_coach_effect`).
- **Counterfactual pairs** (risk R6): for X% of sessions, re-generate with the
  atom removed → contrast pairs make atom-effect identifiable, not spurious.
- Reasoning field (d) is stored out-of-band by `session_id` → distilled into the
  coach-TLM in v2 (don't waste the signal; don't model it in v0).

**Why this lets us train against known metrics (the task's core claim):**
> If the feeds match real samples (assumption A1), then the *shape* of behaviour
> is right, and the few *marginal* numbers we know (5.6% / 66 / 24 / 78 / mix) can
> be hit by calibrating a tiny set of free parameters — not by retraining. See §3.

---

## 2. Model + proof (folded from PERSONA_TLM_DESIGN.md)

- **v0 = tiny decoder-only GPT** over the token stream (`TLMConfig` 4L/4H/128d,
  ~0.8M params). **Text-token only** (no UI patches yet). nanoGPT trainer, 1×A100.
- **Persona conditioning = learned prefix embedding** from `(persona, intent,
  attrs)` — subsumes the current tag token, injects the psyche `Intent` axis.
- **Vocab deltas** (lock before training): add `<ui:STEP:layout>` (~15),
  `<atom:coach:phase>` (~44), `<intent:…>` (4), `<outcome:…>` (3); expand
  `TARGETS` to a per-step closed set (~25); reserve 32 unused ids. → vocab ~110.
- **Loss mask = the shared-vocab trick:** persona-TLM trains loss on USER tokens;
  coach-TLM (v2) trains loss on `<atom:*:offered>`. Same backbone, two heads.
- **Proof = 3 gates, one Leonardo afternoon** (full detail in design §2.4):
  - **G1 next-token:** val PPL < 0.85 × n-gram-4 baseline.
  - **G2 funnel match:** TV ≤ 0.08 vs anchors (5.6/66/24/78).
  - **G3 persona separability:** pairwise JS ≥ 0.10 + 2-sample classifier AUC ≥ 0.65,
    and must hold under persona-tag dropout (R5).

---

## 3. Train-against-known-metrics (two stages)

```
Stage 1 (gradient, on A100):  cross-entropy on USER tokens. No metric loss.
Stage 2 (black-box, on CPU):  hold transformer FIXED; fit 40 free scalars
                              (T_persona[3], π_intent[3×4], b_outcome[3×8], α_mix)
                              with CMA-ES to minimise:
   L = 1.0·TV(funnel_sim, anchors)         # overall + S4/S5/S6 conditional
     + 0.5·Σ_persona KL(survival_sim ‖ psyche_anchors)
     + 0.3·TV(persona_mix_sim, [.30,.50,.20])
     + 0.2·TV(bounce_reason_sim, psyche)
```

- **Teacher provides shape** (persona voice, reactions to atoms); **calibration
  provides marginals** (we do NOT ask the LLM to be metric-accurate).
- **ε for the Z3 gate falls out here:** `ε_anchor = TV(sim, anchors)` after Stage 2
  → this is the budget `b` in `specs/z3/coach_autoimprove.py` (`τ ≥ 2b`). The
  persona-model plan and the autoresearch safety proof connect exactly here.
- Also report **ε_teacher_vs_psyche** = "how much do we trust the LLM teacher"
  (uncalibrated TV between teacher and psyche on identical (persona,step) cells).

---

## 4. Test / eval plan (what proves it works)

| Path | Test | Gate |
|---|---|---|
| schema gate | every LLM feed parses to `contracts.Event` or is dropped | hard |
| tokenizer | `encode/decode` round-trip on generated feeds (extend `test_eventproc_tlm.py`) | hard |
| next-token | val PPL vs n-gram-4 | G1 |
| funnel match | sampled-cohort TV vs anchors (calibrated AND uncalibrated reported) | G2 |
| separability | pairwise JS + classifier AUC, with tag-dropout | G3 |
| atom effect | counterfactual contrast pairs show identifiable atom shift | diagnostic |
| determinism | fixed seed → same cohort stats (parity with existing sim tests) | hard |
| calibration | Stage-2 produces `tlm_v0.calib.json`, ε_anchor ≤ 0.05 | G2-tie |

Regression rule: keep all 69 existing tests green; the persona-TLM is additive
behind the same `contracts`/`tlm` surface.

---

## 5. Failure modes (ruthless — full table in design §4)

| # | Risk | Silent? | Mitigation |
|---|---|---|---|
| R1 | **A1 wrong** (LLM feeds ≠ real, esp. timing/recovery) | no — G2 fails | mix-in psyche (`α_mix`); report ε_teacher_vs_psyche; Loop B refit |
| R2 | mode collapse (one canonical journey) | yes (means look fine) | nucleus p=0.9, temp ≥0.8, label-smooth, EOS reg |
| R4 | **eval circularity** (calibrate + evaluate on same anchors) | yes | held-out cohort calibrator never sees; report uncalibrated stats too |
| R5 | persona tag shortcut (no real behavioural diff) | yes | 10% tag dropout in training; G3 must hold tag-masked |
| R6 | spurious atom effect | yes → bad coach later | counterfactual atom-removed pairs in data-gen |
| R7 | vocab churn forces retrain | no | lock vocab v0; reserve 32 ids |

**Critical-gap flags (silent + no test + no handling):** R2, R4, R5, R6 are all
silent — each is explicitly covered by a test/diagnostic above. None left unguarded.

---

## 6. NOT in scope (deferred, with reason)

- **Multimodal UI-patch TLM (v1)** — only if v0 fails G3 or the demo needs visual
  grounding. Text tokens carry UI state in v0.
- **Coach-TLM (v2)** — separate head, after v0 backbone exists.
- **Loop B online refit / IPS off-policy eval (v3)** — needs real logs; none yet.
- **Raw mouse/ms-timing modelling** — where A1 breaks hardest; stay at
  decision-event granularity.
- **Real PNG UI thumbnails for the teacher** — start with ASCII/json-render; add
  bitmaps only if the LLM teacher needs them to behave.

---

## 7. CRITICAL NEXT STEPS (what to de-risk first — most rests on assumptions)

Ordered by how much they collapse uncertainty per hour spent.

1. **Measure ε_teacher_vs_psyche on 300 feeds (½ day, no training).** ✅ HARNESS BUILT
   `src/uniqa/persona_datagen.py` (`python -m uniqa.persona_datagen -n 300`): step-prompt
   assembler (persona.md + persona.json + json-render + ASCII UI + atoms + reasoning),
   schema gate (`parse_events`), batch + `epsilon_teacher_vs_psyche`, with an
   OpenAI-compatible teacher backend and an offline stub (8 tests). Offline run:
   ε=0.061 over 12 cells (pipeline-validation only). **Remaining: set `OPENAI_API_KEY`
   (+ `OPENAI_BASE_URL`) and re-run for the real A1 number; gate ε ≤ ~0.05.**
2. **Lock the vocab v0 spec** (§1.6 deltas) and land it in `tlm.py` + tests.
   Cheap, unblocks everything, prevents R7 retrains.
3. **Build the data-gen harness** (`persona_datagen.py`): step prompt assembler
   (persona.md + json-render + atoms + ascii screen), LLM call, schema gate,
   counterfactual pairs, writer to token shards. Unit-test the schema gate.
4. **Run the v0 proof job on Leonardo** (§2.5): train + Stage-2 calibrate, emit
   `eval_report.json` with G1/G2/G3 + ε_anchor. This is the go/no-go.
5. **Report both ε numbers** and wire ε_anchor into the Z3 `b`/`τ` check so the
   safety proof uses a *measured* budget, not an assumed one.
6. **Only then** decide v1 multimodal / v2 coach-TLM, gated on v0 results.

### Open assumptions register (track these explicitly)

| ID | Assumption | Currently | De-risked by |
|----|-----------|-----------|--------------|
| A1 | LLM-teacher feeds ≈ real user samples | **harness ready, awaiting real-LLM run** | step 1 (ε_teacher_vs_psyche), later Loop B vs real logs |
| A2 | persona.md + persona.json sys-prompt is enough for good feeds | assumed | step 1 (real-LLM run) |
| A3 | known marginals (5.6/66/24/78) are reachable by 40-scalar calibration | assumed | step 4 (Stage-2 G2) |
| A4 | decision-event granularity is sufficient (no ms timing) | design choice | step 4 G1/G2; revisit in v1 |
| A5 | persona differentiation is learnable, not tag-memorised | assumed | step 4 G3 under tag-dropout |
| A6 | atom effects are identifiable from feeds | assumed | counterfactual pairs (step 3) + diagnostic |
| A7 | addon-step (S5/24%) scope (see HARDENING_PLAN F1) | flagged | resolve before treating 24% as a calibration anchor |

**Headline:** the entire plan is sound *conditional on A1*. Step 1 tests A1 for
half a day of effort and zero GPU. Do it first.
