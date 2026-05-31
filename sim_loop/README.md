# sim_loop — persona ↔ widget ↔ coach turn loop (temporary / standalone)

Self-contained implementation of the agreed loop. Touches no other project files
(only *reads* `src/uniqa/data/.../personas.json` + the segment markdown, and the
canonical screen templates extracted from `datasets/persona_v2`).

## Funnel (8 steps)

`S1 coverage → S2 persons → S3 personal → S4 tariff/price → S5 add-ons →
S6 personal-data → S7 health-questions → S8 review+confirm (= conversion)`.
Conversion happens only at **S8** (the `convert` action on the final review screen);
reaching S8 is not yet a sale. Screens live in `step_templates.json`.

## The loop (observe-then-act)

```
session start
  for step in funnel [S1..S8]:
    widget.render(step, running_state, history, session_instance, intent, coach_injection)
    persona.step()             -> events + decision + NEW state + feeling   (may LEAVE)
    coach.decide(FILTERED log) -> effector | NO_ACTION   (lands on the NEXT screen)
    advance / terminate
session end  -> convert | abandon | advisor_handoff
```

- **Persona** = LLM. System prompt set ONCE at session start (segment markdown +
  behavioural dials + today's session instance). Mental state (`attention,
  satisfaction, effort_left, grasp, effort_vs_reward`) is threaded turn→turn.
  Terminates by emitting `decision: "leave"` (or converts at end of funnel).
- **Widget** = deterministic state machine + screen renderer. No LLM. Injects any
  coach intervention into the next screen as `coach_intervention_shown`.
- **Coach** = LLM policy (`coach.py`). Sees the **filtered activity log only** — no
  thoughts, no state vars, no feeling, no persona label, no S6 health data. Emits an
  effector + reasoning + hypotheses under an annoyance budget. `mode="skip"` = the
  control arm (always NO_ACTION, no LLM call).

## Files
| file | role |
|---|---|
| `llm.py` | OpenRouter client (reads repo `.env`) + JSON extractor |
| `persona_prompt.py` | builds the persona system prompt (md + dials + session instance) |
| `persona.py` | `LLMPersona` — system prompt + threaded mental state |
| `widget.py` | funnel state machine + screen renderer (+ coach injection) |
| `coach.py` | `CoachModel` — skip / active, effector space, annoyance budget |
| `run.py` | orchestrator: proportions, two arms, dataset writer |
| `step_templates.json` | canonical per-step screens (extracted from persona_v2) |
| `session_pools.json` | session-instance value pools + seed mental state |

## Run
```bash
python sim_loop/run.py --sessions 16 --arms off,on --proportions real \
                       --coach-budget 2 --concurrency 6 --out sim_loop/out
```
- `--proportions real` → normalized segment shares J 0.21 / F 0.41 / P 0.39
  (`balanced` = 1/3 each). Both arms share the SAME sampled persona mix (paired A/B).
- `--sessions` is **per arm**.

## Output (the generated dataset, split in two)
- `out/sessions_coach_off.jsonl` — coach ALWAYS skips (control)
- `out/sessions_coach_on.jsonl`  — coach active
- `out/summary.json` — per-arm conversion/advisor/abandon + uplift

Each session line: `{persona, arm, session_instance, outcome, n_steps,
coach_interventions, steps:[{step, shown_coach, persona_output, coach_decision}]}`.

### Sample run (16 sessions/arm, real mix J3/F7/P6, gpt-4o-mini)
| arm | convert | advisor | abandon | interventions |
|---|---|---|---|---|
| coach off | 0.50 | 2 | 6 | 0 |
| coach on  | 0.69 | 1 | 4 | 23 |

→ **uplift +0.19 conversion-rate.** Small n — demonstrative, not significant.

## Calibration (`calibrate.py`) — match the funnel anchors

Tunes persona behavioural dials so the simulated per-step ABANDON distribution
matches the UNIQA telemetry anchors (FUNNEL_AUTOPSY.md), focus S4/S5/S6:

| step | S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8 |
|---|---|---|---|---|---|---|---|---|
| target hazard | .18 | .06 | .10 | .30 | .05 | .12 | .08 | .11 |

Method (as specified): the **immutable persona core is the system prompt** (identical
across calls → provider-cached); each run feeds it a different session instance → a
different action sequence. Run N sessions (coach OFF), measure the conditional leave
rate per step, coordinate-descent the driving dial per step. Tuned dials are written
to `tuned_dials.json` (applied by `persona_prompt.dials()` on top of `personas.json`).

```bash
python sim_loop/calibrate.py --n 100                      # measure vs anchors
python sim_loop/calibrate.py --tune --rounds 2 --n 60 --focus S4,S5,S6
```

**Result (100-run baseline → tuned):** S4 0.20→0.26 (target .30), S5 0.03→0.06,
S6 0.11→0.14 — S1–S7 all within ≤0.04 of anchors. Residual: **S8 over-abandons**
(~0.26 vs .11) — raising `value_orientation` strengthens the final-price reaction too;
down-tune `budget_pressure` on S8 next. Artifacts: `tuned_dials.json`,
`calibration_report.json`.

## Downstream
- `sessions_coach_on.jsonl` → coach SFT pairs: `coach_decision` given the filtered
  log at each step (the §5.1 distillation traces).
- both arms → Monte-Carlo A/B uplift (`simulation.py` style) and the empirical gate.
- persona steps → more `persona_v2`-style state rows (feeds the persona classifier).
