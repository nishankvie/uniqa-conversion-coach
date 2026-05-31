# Leonardo jobs — distil the persona LLM into fast local per-step models

**Goal:** replace the frontier LLM persona (slow, paid, per-step API calls) with **three
local fine-tuned models** (one per persona) whose stepwise inference is **statistically
close** to the frontier-generated dataset. Then the autoresearch / coach loop iterates fast
and offline.

## Why per-step (stepwise) distillation

The dynamic **coach widget intervenes per step**, and the persona reacts per step. So the
local model must be a **per-step function**, not a whole-session generator:

```
(persona, step UI + action-space, running mental state, real prices, [COACH ACTION])
        → events (with thoughts) + state update + stay/leave decision
```

We distil exactly the per-step (prompt → JSON) pairs the frontier teacher produced. When the
coach is added, its action enters each step's context and the local persona reacts — same loop
(`LocalTeacher` reuses `LLMTeacher._session_stepwise` verbatim; only `_call` swaps to local).

## Dataset (locked)

`datasets/persona_v1/` — 500 sessions at the **30/50/20 population mix** (judith 150 /
franz 250 / peter 100), **2129 per-step SFT pairs**, ε=0.0998 vs the `funnel.py` anchors
(under the 0.12 gate; all personas convert). Built by `research.build_dataset --total 500`
with the locked, persona-coherent dials (matches `prompts/personas/*.params.json`).

## Pipeline

```bash
# 1. prepare per-persona SFT (login node — has the dataset)
python leonardo/prepare_sft.py --in datasets/persona_v1/sft_steps.jsonl --out leonardo/data
# 2. download the base model on a LOGIN node (compute nodes have no internet)
#    huggingface-cli download Qwen/Qwen2.5-1.5B-Instruct --local-dir $HOME/models/qwen2.5-1.5b
#    (slurm_finetune.sh defaults BASE to $HOME/models/qwen2.5-1.5b)
# 3. fine-tune the 3 LoRA adapters + eval (GPU job, ~A100)
$LEO put leonardo && $LEO run "sbatch zero-one/leonardo/slurm_finetune.sh"
# 4. eval locally any time
python leonardo/eval_local.py --base Qwen/Qwen2.5-1.5B-Instruct --adapters leonardo/out --n 100
```

## Files

- `prepare_sft.py` — `sft_steps.jsonl` → per-persona `{train,val}.jsonl` (chat format).
- `train_persona_lora.py` — LoRA SFT (completion-only) of a small instruct base, per persona.
- `slurm_finetune.sh` — Leonardo job (boost_usr_prod · s_tra_ncc · A100) → 3 adapters + eval.
- `local_teacher.py` — `LocalTeacher`: the fine-tuned model as a drop-in stepwise teacher.
- `eval_local.py` — runs the SAME statistical gate on the local models.

## Outcome / lock criterion

Each local model passes `evals/persona_stats_eval` (and `eval_local.py`) with **local ε ≈
frontier ε (~0.10)** and per-persona bounce/conversion within tolerance. When met, swap the
frontier teacher for `LocalTeacher` in the sim/autoresearch loop for fast iteration, and add
the coach action to the per-step context.

> Base model is a starting point (`Qwen/Qwen2.5-1.5B-Instruct`); compare a couple of small
> bases on eval conformance + latency. Transformer or not — the gate is the eval, not the arch.
