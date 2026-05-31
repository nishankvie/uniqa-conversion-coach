# Sim model audit — implemented vs intended

**Date:** 2026-05-31  
**Scope:** read-only; all evidence cited as `file:line`.  
**Intended model** (user description, verbatim summary):  
Two components — PERSONA + WIDGET. COACH lives *inside* widget (its optional reactive layer).  
Turn-based: persona acts → widget reacts → coach consulted after EVERY persona turn (default NO_ACTION).  
Coach modes: (a) always-empty, (b) prompt-driven with persona-predictor detect.  
Effector appears in widget response seen by persona on next turn, influencing running state.  
Persona takes MULTIPLE turns if no widget state change + no coach effector (how sim progresses).

---

## 1. Implemented-vs-intended table

| Intended behaviour | Status | Evidence |
|---|---|---|
| Two roles: Persona + Widget | ✅ implemented | `sim.py:51-69` — `PersonaModel`, `WidgetModel` Protocols |
| Coach lives *inside* WidgetModel (its optional reactive layer) | ❌ **missing** | Coach is a **separate** third `CoachModel` Protocol passed directly to `simulate()`. `WidgetTwin` (`sim.py:76`) has no coach slot. Orchestrator calls `coach.decide()` directly (`sim.py:217`), not via `widget`. |
| Persona only talks to the widget/surface | ⚠️ **partial** | Persona receives the `CoachDecision` via `resolve(… coach …)` (`sim.py:226-229`). But the decision was made by a standalone `CoachModel`, not mediated through `widget`. The distinction matters structurally. |
| Turn-based loop | ✅ implemented | `simulate()` `sim.py:184-250` — one funnel-step outer loop |
| Coach consulted after every persona turn | ⚠️ **partial** | Coach consulted *once per funnel step*, not after each persona micro-turn within a step. Correct today because there is only one persona action per step (see multi-turn gap below). |
| Coach returns NO_ACTION by default | ✅ implemented | `RuleCoachModel._no_action()` (`coach_io.py:148`) returns `NO_ACTION` when budget=0 or no hypotheses. `simulate()` skips `widget.apply` unless `d.is_action()` (`sim.py:222`). |
| Coach mode (a): always-empty | ✅ implemented | Pass `coach=None` → Flow A (`sim.py:198-200`) or set budget=0 |
| Coach mode (b): prompt-driven (`coach_prompt.py`) | ❌ **missing** | `build_coach_prompt()` exists and is complete (`coach_prompt.py:133`). But there is **no `PromptCoachModel` class** implementing `CoachModel` that calls an LLM with that prompt. Only `RuleCoachModel` (rule-based) satisfies the Protocol. |
| Coach collects/detects signals early, then commits persona belief via predictor | ❌ **missing** | `models/persona_predictor/` exists (trained, `meta.json` confirms). But it is never loaded or called inside `sim.py`, `coach_io.py`, or any `CoachModel`. No collect-then-detect flow exists in the live loop. |
| Effector appears in widget response seen by persona on next turn | ⚠️ **partial** | `widget.apply()` emits a `WIDGET_SHOWN` event into `log.events` (`sim.py:223`, `sim.py:83-88`). That event IS in the history visible to the next `persona.step()`. BUT: (a) `PsychePersona.step()` doesn't read history at all — it runs `step_dynamics` on a latent Mind; (b) `LLMPersona.step()` falls back to psyche (`sim.py:170`), so also doesn't see it. Neither backend reads `WIDGET_SHOWN` from history as an effector cue. |
| Effector influences persona running state | ⚠️ **psyche-only** | `PsychePersona.resolve()` calls `apply_coach_effect(mind, intent, step)` (`sim.py:137-141`, `psyche.py:259-296`) — the Mind is mutated, bounce re-rolled. This IS the honest model for psyche. For `LLMPersona.resolve()` the psyche fallback is used (`sim.py:174`), so the LLM's conceptual state is never changed via the effector. |
| State-influence rules live in persona prompt | ⚠️ **datagen-only** | `build_step_decision_prompt` supports `coach_intervention` → `coach_widget_shown` + `intervention_assessment` output schema (`persona_datagen.py:451-465`). Correct rules in the prompt. But **this is only used in datagen (`datagen_v2.py`)**, never in the Flow B sim loop (`LLMPersona` in sim falls back to psyche). |
| Multi-turn advance within a step | ❌ **missing** | `simulate()` calls `persona.step()` exactly once per funnel step (outer `for step in STEP_ORDER` loop, `sim.py:207-229`). No inner retry loop. |

---

## 2. Precise gaps

### (a) Multi-turn-within-step advance — MISSING

`simulate()` `sim.py:207-229` has a single outer `for step in STEP_ORDER` loop.  
Within each iteration: **one** `persona.step()` → **one** `coach.decide()` → **one** `persona.resolve()` → advance funnel step unconditionally (or abandon).  

There is no inner loop of the form:
```
while not (widget_state_changed or coach_acted):
    persona.step()  # take another micro-turn
```

The intended model says: if a persona turn produces no widget state transition AND the coach returns NO_ACTION, the persona retakes the turn. This is the mechanism by which the sim advances through intra-step activity (hovering, re-reading, micro-hesitations) rather than jumping step-to-step with one action each. Currently each funnel step is resolved in exactly one persona action + one coach query.

**Impact:** the sim is coarser than intended; intra-step richness (multiple hover/idle/back-nav before a decision) is generated inside `persona.step()` as a batch of events, not as individually-coached micro-turns.

---

### (b) LLMPersona.step / resolve fall back to psyche — CONFIRMED

`LLMPersona.step()` (`sim.py:170`) and `LLMPersona.resolve()` (`sim.py:173`) both call `_PSYCHE_FALLBACK` — the global `PsychePersona()` instance. Comment confirms this is intentional for now: *"A full per-step LLM react loop is a drop-in here; left as the v1 upgrade"*.

Consequence: when an LLM persona is used in Flow B, it never actually queries the LLM per turn. The whole-session LLM call is only in Flow A (`whole_session()`, `sim.py:164`). Coach interventions in Flow B affect the *psyche fallback's Mind*, not the LLM's generation.

---

### (c) Prompt-driven CoachModel class — MISSING

`coach/coach_prompt.py` contains a complete, well-designed `build_coach_prompt(obs: dict) -> list[dict]` function. It produces `[system, user]` messages ready for an LLM call.

But there is **no class** implementing the `CoachModel` Protocol that:
1. calls `build_coach_prompt(obs.to_dict())`  
2. sends to OpenRouter/OpenAI  
3. parses the JSON response into a `CoachDecision`  

Only `RuleCoachModel` in `coach/coach_io.py` implements `CoachModel`. The prompt coach is a prompt builder with no runner.

---

### (d) Persona-predictor wiring — MISSING

`models/persona_predictor/` contains `actions_model.joblib` (CV acc 0.529) and `state_model.joblib` (CV acc 0.704), trained in `research/train_persona_predictor.py`.

Grep confirms zero in-sim usage:
- `coach/coach_io.py` — no `joblib` or `persona_predictor` import
- `calculator/sim.py` — same  
- `coach/coach_prompt.py` — same  

The predictor outputs a `persona_belief` distribution (probabilities over {judith, franz, peter}). `coach_prompt.py` has a `persona_belief_prior` slot in the user message (`coach_prompt.py:149`). These two are never connected: the prompt expects a prior but the sim never computes one.

The intended flow (collect signals early → predict → pass as prior to coach) is a design without implementation.

---

### (e) Effector → persona-state influence: psyche yes, LLM no

**PsychePersona:** the coach effect is real and grounded.  
`PsychePersona.resolve()` (`sim.py:135-142`) extracts `intent` from `coach.command.payload` and calls `apply_coach_effect(mind, intent, step)` (`psyche.py:259-296`), which shifts latent vars (e.g. `price_reframe` → `mind.price_readiness += 0.30`). Bounce is then re-rolled on the mutated mind. This is the intended behaviour.

**LLMPersona:** the effector never influences LLM generation.  
`LLMPersona.resolve()` (`sim.py:173-174`) delegates to `_PSYCHE_FALLBACK.resolve()`. That mutates the *fallback* Mind but not any LLM state. The LLM would need to receive `coach_widget_shown` text in its next `step()` prompt for the effector to actually change its generation — but `LLMPersona.step()` builds no prompt at all (it calls psyche).

**Persona prompt:** the rules ARE correct in `build_step_decision_prompt` (`persona_datagen.py:459-465`). The prompt tells the persona to react to `coach_widget_shown` and fill `intervention_assessment`. This is used by `datagen_v2.py` for dataset generation, but is **not wired into `LLMPersona.step()`** in the sim.

---

## 3. Minimal ordered change list

Order: dependencies first. No code written here — function signatures and one-line descriptions only.

| # | File | Function / location | Change |
|---|---|---|---|
| 1 | `calculator/sim.py` | `WidgetTwin` class | Add optional `coach: CoachModel \| None = None` slot; move `coach.decide()` call inside `WidgetTwin.react(step, history, budget)` which returns `(state_changed: bool, effector_events: list[Event])` — makes coach genuinely inside the widget |
| 2 | `calculator/sim.py` | `WidgetModel` Protocol | Extend with `react(step, history, budget) -> tuple[bool, list[Event]]` replacing separate `observe+coach.decide+apply` calls in the orchestrator |
| 3 | `coach/coach_io.py` | new class `PromptCoachModel` | Implement `CoachModel` Protocol: call `build_coach_prompt(obs.to_dict())`, POST to OpenRouter, parse JSON → `CoachDecision`. Drop-in for `RuleCoachModel`. |
| 4 | `coach/coach_io.py` | `PromptCoachModel.__init__` | Load `models/persona_predictor/actions_model.joblib`; maintain a rolling `persona_belief` dict updated each call by running the predictor on the current activity |
| 5 | `coach/coach_io.py` | `PromptCoachModel.decide` | Before calling the prompt: run predictor on `obs.activity` → update `persona_belief`; pass as `persona_belief_prior` in the obs dict to `build_coach_prompt` |
| 6 | `calculator/sim.py` | `simulate()` outer loop | Replace single `persona.step()` → `coach.decide()` → `persona.resolve()` sequence with an **inner micro-turn loop**: `while not (state_changed or coach_acted): persona.step(); react(); coach_acted = widget.react(); if not state_changed and not coach_acted: continue`. Exit on terminal or step advance. |
| 7 | `persona/persona_datagen.py` | `LLMPersona.step()` (or new `StepLLMPersona`) | Build proper per-step prompt via `build_step_decision_prompt(persona, step, history_brief, state, coach_intervention=effector_text_if_any)`, call LLM, parse events. Replace psyche fallback. |
| 8 | `persona/persona_datagen.py` | `LLMPersona.resolve()` | Parse `decision` field from the last `step()` LLM output (already in the output schema) rather than re-rolling psyche bounce. |
| 9 | `calculator/sim.py` | `simulate()`, Flow B | After `widget.react()` returns `coach_acted=True`: extract `intervention.persona_facing` from `interventions.CATALOG` and pass as `coach_intervention` arg to the next `LLMPersona.step()` call so the effector text reaches the LLM. |

---

## 4. Test coverage

### What's covered

| Test | What it covers |
|---|---|
| `test_flow_a_one_shot_terminates` | Flow A terminates, schema-clean, no coach events |
| `test_flow_a_deterministic` | Flow A is reproducible with same seed |
| `test_flow_b_coach_can_intervene_and_persona_reacts` | Interventions appear with `source=coach`; loop terminates |
| `test_flow_b_respects_message_budget` | Budget ceiling enforced |
| `test_flow_b_coach_shifts_outcomes_vs_flow_a` | Coach actually changes outcomes vs baseline |
| `test_flow_b_all_personas_terminate_within_budget` | All 3 personas × 12 seeds terminate, schema-clean, budget ≤ 3 |
| `test_custom_persona_without_whole_session_uses_turn_loop` | Protocol pluggability / fallback to turn loop |

### Gaps (no test exists)

| Gap | What would be tested |
|---|---|
| **Multi-turn advance** | If `persona.step()` produces no widget transition + coach emits NO_ACTION, the persona is called again in the same step (not advanced). Currently would fail because the loop doesn't do this. |
| **Coach inside widget** | `WidgetTwin` wrapping the coach; `widget.react()` returns `(state_changed, effector_events)` |
| **PromptCoachModel** | Calls `build_coach_prompt`; returns valid `CoachDecision`; NO_ACTION when `decide=wait`; spends budget only when `decide=intervene` |
| **Predictor wiring** | `PromptCoachModel.decide()` accumulates events and updates `persona_belief`; by S3 has a non-uniform belief; passes it as prior to coach prompt |
| **Effector → LLM state** | After a coach widget is shown, the next `LLMPersona.step()` call includes `coach_widget_shown` in its prompt; the output contains `intervention_assessment` |
| **Coach empty default** | A `PromptCoachModel` returns `NO_ACTION` when `intervention_temperature` is low (early steps, no signals) — distinct from budget exhaustion |
| **Per-step LLMPersona** | `LLMPersona.step()` calls the LLM with per-step prompt; `LLMPersona.resolve()` reads `decision` from that output rather than re-rolling psyche |

---

## Summary

The hardest gap is **multi-turn advance** (gap a) — it requires rethinking the inner loop and is a prerequisite for anything richer than "one action per funnel step". The second-hardest is **coach-inside-widget** (structural intent vs current three-party orchestrator) — it requires refactoring the Protocol boundary but no algorithmic change. Everything else (PromptCoachModel, predictor wiring, LLM step/resolve, effector→LLM state) is additive: new classes/functions with existing pieces in place.

The tests cover the *current* psyche-based Flow A/B well. None of the intended-model gaps have test coverage.
