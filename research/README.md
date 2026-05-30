# Research — persona session generation + statistical conformance

Iterative loop to make the **LLM persona agents** produce sessions whose *emergent*
statistics match the calibration anchors — **without** ever telling the agent the
targets. Targets (per-(persona,step) `ABANDON_PROBS`, implied conversion) live only in
`funnel.py` and are used here for **validation**, never injected into the prompt.

## What the generator now knows

- **Persona** — hand-scrubbed prompt (`prompts/personas/<persona>.md`), funnel-outcome
  numbers removed by hand.
- **Widget response state machine** — `widget.widget_response_model()`: how the static
  widget reacts to each action (what advances, what blocks, what reveals a price, what
  hands off to an advisor). So the LLM reasons against real widget behaviour.
- **Action space + low-res UI** per step (existing).

## The escalation protocol

```
ITER 0  base prompt  ──► python -m research.run --n 30
          conforms? ── PASS → done
                    └─ FAIL ↓
ITER 1  + behavioural quantitative metrics (curated, NO funnel-outcome stats)
                       ──► python -m research.run --n 30 --quant
          conforms? ── PASS → done
                    └─ FAIL ↓
ITER 2  persona model becomes PARAMETER-DRIVEN (see PERSONA_PARAM_MODEL.md):
          expose a small set of behavioural params, tune them to hit the anchors.
```

**Pass gate** (loose, small-N loop): mean abs per-cell bounce diff `ε ≤ 0.12`,
per-persona `|conv − implied_target| ≤ 0.06`, and every persona converts ≥ once.

## Iteration 1 lever — quantitative metrics

`--quant` appends an allowlisted, behaviour-only block from `personas.json`
(`persona_datagen.quant_metrics_block`): online-purchase propensity, switch
willingness, NPS, attitude, online/in-person purchase split. **Excludes** every
funnel-outcome statistic (no per-step bounce, no conversion rate, no 30/50/20 mix) —
these shape behaviour, they do not dictate the session outcome.

## Outputs

`research/runs/<ts>_<mode>/` (git-ignored): `logs.jsonl` (raw sessions), `report.md`,
`report.json`. The committed artifacts are the code + protocol + any promoted report.
