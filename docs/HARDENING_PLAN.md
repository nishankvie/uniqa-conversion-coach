# Hardening Plan — UNIQA Conversion Coach

State assessment + component-by-component hardening, scope/form-logic registry,
open findings, and Leonardo HPC usage plan. Day 2, deadline Sun 10:00.

---

## 1. Current state (assessment)

| Component | File | State | Tests |
|---|---|---|---|
| Funnel state machine | `funnel.py` | ✅ solid, calibrated | covered |
| Coach policy | `coach.py` | ✅ 12 actions, hard gates | covered |
| Psyche persona model | `psyche.py` | ✅ 6 latents, hazard bounce, tunable gains | covered |
| Journey harness + JSON twin | `journey.py` | ✅ demo + batch | covered |
| Simulation A/B | `simulation.py` | ✅ uplift report | covered |
| Autoresearch loop | `autoresearch.py` | ✅ gated hill-climb | covered |
| Z3 certificate | `specs/z3/` | ✅ 5 theorems | in CI |
| Streamlit demo | `app.py` | ✅ live + A/B views | manual |
| **Scope + form logic** | `scope.py` | ✅ **new — encoded this pass** | 14 tests |
| Leonardo access | skill `leonardo-connect` | ✅ **smoke test PASSES live** | n/a |

**52 tests pass.** Calibration anchors hold (baseline ≈5.6%, S4 66%, S6 78%).

---

## 2. Scope registry (encoded in `scope.py`)

| Dimension | IN SCOPE ✅ | OUT OF SCOPE ❌ → advisor handoff |
|---|---|---|
| Coverage (S1) | `Bei Arztbesuchen` (Privatarzt) | `Im Krankenhaus` (hospital) |
| Insured (S2) | `Ich selbst` | `Andere Personen` |
| Tariff (S4) | `Start`, `Optimal` (online) | `Opt. Plus`, `Premium` (advisory) |
| Outcome | **online purchase** of Start/Optimal | advisor handoff is **NOT** a conversion |

Encoded as `route(coverage, insured, tariff) → IN_SCOPE | ADVISOR_HANDOFF` and
`is_conversion(...)`. Franz hard constraint (never advisor) still enforced in
`coach.validate_output`.

---

## 3. Form logic (encoded in `scope.py`, `FORM_FIELDS`)

Track rule: **no step may be removed**; the Coach may only assist, never skip
collection. Required fields + validators per in-scope step:

| Step | Required fields | Validators |
|---|---|---|
| S1 Coverage | coverage | enum |
| S2 Insured | insured | enum |
| S3 Personal info | date_of_birth, **sv_number** | DOB format, **AT SV checksum** |
| S4 Tariff | tariff | enum (online vs advisory) |
| S6 Personal+health | first/last name, email, sv_number, health_answers | email, SV checksum, nonempty |

`validate_step(step, data)` returns `missing` + `invalid` lists. Austrian SV
number gets the real weighted checksum (`weights = 3 7 9 0 5 8 4 2 1 6`, mod 11).

---

## 4. Open findings

### F1 — add-on step is out of scope (correctness) — ⚠️ DECISION NEEDED
The official funnel doc marks **Step 5 "Add-on coverage selection (24% drop)"**
as the **hospital path → OUT OF SCOPE**. The in-scope Privatarzt flow is:
`coverage → insured → personal(DOB+SV) → tariff(66%) → health Qs → final price(78%)`
— with **no add-on screen**. Our `Step.ADDON_SELECT` (+24% anchor + FEATURE_HIGHLIGHT
coaching there) conflates the hospital add-on into the in-scope path.

- **Flagged** now: `scope.ADDON_IS_INSCOPE = False`.
- **Options:** (A) keep S5 for calibration continuity, relabel as provisional and
  drop coach intervention there; (B) remove S5 from the in-scope chain and
  re-calibrate the 2-drop survival math (S4 66% → health → S7 78%). 
- **Recommendation:** A for the demo (calibration is locked, deadline), document
  the caveat. Do B post-hackathon. Either way, do **not** claim coach uplift on S5.

### F2 — tariff price fidelity (demo credibility) — easy fix
Demo PriceTable shows Start `41,30` / Optimal `73,02`; official reference (age 27,
ÖGK) is `38.74` / `68.14`. Align `journey.STEP_SCREENS` + widget copy to official
numbers (now in `scope.TARIFF_PRICE_EUR`) so jury sees real numbers.

### F3 — global `COACH_GAIN` mutation (autoresearch hygiene) — covered, watch
`autoresearch.evaluate_policy` mutates module-global `COACH_GAIN` then resets.
Tests assert cleanup. Risk: parallel eval would race. Keep autoresearch
single-threaded (it is) or thread a policy arg through `apply_coach_effect` later.

### F4 — LLMPersona offline path (demo safety)
`personas.LLMPersona` falls back offline if no API key. Confirm the stage demo
uses RuleBasedPersona / psyche only (no network) — already the default in
`run_batch`. No live API on stage.

---

## 5. Hardening actions (priority order)

1. **[done]** Encode scope + form logic + tests (`scope.py`, 14 tests).
2. **[done]** Leonardo connect skill + live smoke test.
3. **F2** align demo tariff prices to official (5 min).
4. **F1** add caveat to README/app: coach uplift claimed on S4/S6 only; relabel S5.
5. Wire `scope.route()` into `journey.run_journey` start so out-of-scope draws
   emit an `ADVISOR_HANDOFF` token instead of a coachable journey (realism).
6. Add `validate_step` assertions in the journey at S3/S6 (defensive: never
   advance on invalid/missing required data).
7. Demo dry-run script + fixed seeds for the 3 hero journeys (Judith/Franz/Peter).

---

## 6. Leonardo HPC — usage plan

Access verified: user `a08trd13`, `$SCRATCH=/leonardo_scratch/large/usertrain/a08trd13`,
SLURM 23.11.10, reservation **`s_tra_ncc`** (account `euhpc_d30_031`, partition
`boost_usr_prod`) **active until 2026-05-31 12:00** — 25 nodes, 1/team.
Skill: `leonardo-connect` (`leo.sh smoke|run|put|get|shell`).

**Honest take:** the UNIQA coach simulation is CPU-only and runs in seconds
locally — it does **not** need Leonardo to ship. Leonardo earns its keep on three
things, in priority:

| Option | What | Why it matters | Effort |
|---|---|---|---|
| **L1 — Validate A1 at scale** ⭐ | Run `LLMPersona` via a **vLLM Singularity container** on 1–4 A100s to generate a large synthetic cohort; compare its funnel statistics to the real anchors. | Directly strengthens the autoresearch thesis (assumption A1 = model fidelity). Turns "we assume the model is faithful" into measured ε. | M |
| **L2 — Autoresearch at scale** | Run `autoresearch --rounds 200 -n 50000` on a compute node for a deeper policy search + tighter τ. | More credible self-improvement curve for the demo. | S (CPU job) |
| **L3 — Infineon nanoGPT (secondary track)** | Real GPU training run for the karpathy-experiment track. | Shows real A100 training if we present the secondary track. | M |

**Mechanics (all via the skill):**
- Big downloads + `singularity pull` on a **login node** (compute nodes = no
  internet). `srun --partition=lrd_all_serial --time 04:00:00 --gres=tmpfs:100G --mem=16G --pty singularity pull vllm-openai.sif docker://vllm/vllm-openai:0.21.0-cu129`
- Datasets/checkpoints in `$SCRATCH` (50 GB `$HOME` cap).
- GPU jobs: `scripts/job_gpu.sh` (reservation + account pre-filled; set GPUS 1/2/4).
- Proxy env vars only for low-bandwidth fetches inside jobs (restarts ~10 min).

**Recommendation:** do **L2** tonight (cheap, CPU, strengthens the demo curve).
Attempt **L1** if time allows (highest narrative payoff — it's the empirical leg
the Z3 proof rests on). Skip **L3** unless we decide to present Infineon.

---

## 7. Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Jury challenges S5 add-on scope (F1) | Med | Flagged + documented; claim uplift on S4/S6 only |
| "Numbers look made up" (F2) | Low | Align to official tariff reference |
| Live demo network failure | Med | Streamlit local, no API, fixed seeds |
| Leonardo reservation ends Sun 12:00 | Low | Past our 10:00 deadline; run jobs Sat night |
| Overclaiming uplift | Med | Honest framing: overall + coachable cohort already in README |
