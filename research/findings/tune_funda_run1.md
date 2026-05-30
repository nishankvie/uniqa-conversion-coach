# Dial tuning — N=40, rounds=3, teacher=openrouter:openai/gpt-4o-mini, 20260530_211920


## round 0 — ε=0.2004 · conv=0.235 · PASS=False
  judith  conv 0.07/0.09  S3 0.05/0.05  S4 0.90/0.70  S6 0.25/0.68
  franz   conv 0.42/0.10  S3 0.00/0.04  S4 0.36/0.55  S6 0.32/0.78
  peter   conv 0.00/0.04  S3 0.20/0.25  S4 0.96/0.80  S6 1.00/0.72
    tune judith: {'budget_pressure': '-0.03', 'value_orientation': '-0.021', 'advisor_lean': '-0.021', 'commitment_anxiety': '+0.095', 'uncertainty_aversion': '+0.047'}
    tune franz: {'budget_pressure': '+0.029', 'value_orientation': '+0.021', 'advisor_lean': '+0.186', 'commitment_anxiety': '+0.233', 'uncertainty_aversion': '+0.051'}
    tune peter: {'budget_pressure': '-0.024', 'value_orientation': '-0.017', 'advisor_lean': '-0.038', 'commitment_anxiety': '-0.078', 'uncertainty_aversion': '-0.031'}

## round 1 — ε=0.1677 · conv=0.28 · PASS=False
  judith  conv 0.10/0.09  S3 0.00/0.05  S4 0.80/0.70  S6 0.50/0.68
  franz   conv 0.50/0.10  S3 0.00/0.04  S4 0.33/0.55  S6 0.26/0.78
  peter   conv 0.00/0.04  S3 0.19/0.25  S4 0.86/0.80  S6 1.00/0.72
    tune judith: {'budget_pressure': '-0.015', 'value_orientation': '-0.01', 'advisor_lean': '-0.01', 'commitment_anxiety': '+0.04', 'uncertainty_aversion': '+0.02'}
    tune franz: {'budget_pressure': '+0.035', 'value_orientation': '+0.025', 'advisor_lean': '+0.227', 'commitment_anxiety': '+0.277', 'uncertainty_aversion': '+0.057'}
    tune peter: {'commitment_anxiety': '-0.078', 'uncertainty_aversion': '-0.031', 'advisor_lean': '-0.021'}

## round 2 — ε=0.2033 · conv=0.31 · PASS=False
  judith  conv 0.03/0.09  S3 0.03/0.05  S4 0.95/0.70  S6 0.50/0.68
  franz   conv 0.57/0.10  S3 0.00/0.04  S4 0.30/0.55  S6 0.18/0.78
  peter   conv 0.07/0.04  S3 0.12/0.25  S4 0.83/0.80  S6 0.40/0.72

→ kept this run (round 1, ε=0.1677).