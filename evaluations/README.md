# evaluations/ — regular statistical conformance gate

`persona_stats_eval.py` generates a population sampled to the **given** persona
distribution (30/50/20) and checks emergent funnel stats vs the `funnel.py` anchors
(per-(persona,step) bounce + per-persona + overall conversion). Same gate for the LLM
agent now and the future local/distilled model (`--generator local-model`).

```bash
python -m evals.persona_stats_eval --n 150            # LLM agent
python -m evals.persona_stats_eval --n 150 --seeds 3  # pooled, low-variance
```

Exits non-zero on FAIL → drop into CI/cron. Reports in `evaluations/reports/` (git-ignored;
promote notable ones). Pass gate: ε ≤ 0.12, per-persona |conv−target| ≤ 0.06, each
persona converts ≥ 1.
