# Dial tuning — N=40, rounds=3, teacher=openrouter:openai/gpt-4o-mini, 20260530_212618


## round 0 — ε=0.2121 · conv=0.165 · PASS=False
  judith  conv 0.05/0.09  S3 0.00/0.05  S4 0.95/0.70  S6 0.00/0.68
  franz   conv 0.30/0.10  S3 0.00/0.04  S4 0.53/0.55  S6 0.37/0.78
  peter   conv 0.00/0.04  S3 0.13/0.25  S4 0.85/0.80  S6 1.00/0.72
    tune judith: {'budget_pressure': '-0.038', 'value_orientation': '-0.027', 'advisor_lean': '-0.048', 'commitment_anxiety': '+0.133', 'uncertainty_aversion': '+0.075'}
    tune franz: {'commitment_anxiety': '+0.173', 'uncertainty_aversion': '+0.045', 'advisor_lean': '+0.102'}
    tune peter: {'complexity_overwhelm': '+0.027', 'ux_willingness': '-0.013', 'commitment_anxiety': '-0.078', 'uncertainty_aversion': '-0.031', 'advisor_lean': '-0.021'}

## round 1 — ε=0.2464 · conv=0.2325 · PASS=False
  judith  conv 0.03/0.09  S3 0.00/0.05  S4 0.97/0.70  S6 0.00/0.68
  franz   conv 0.45/0.10  S3 0.00/0.04  S4 0.33/0.55  S6 0.33/0.78
  peter   conv 0.00/0.04  S3 0.11/0.25  S4 0.88/0.80  S6 1.00/0.72
    tune judith: {'budget_pressure': '-0.042', 'value_orientation': '-0.03', 'advisor_lean': '-0.063', 'commitment_anxiety': '+0.123', 'uncertainty_aversion': '+0.075'}
    tune franz: {'budget_pressure': '+0.035', 'value_orientation': '+0.025', 'advisor_lean': '+0.202', 'commitment_anxiety': '+0.24', 'uncertainty_aversion': '+0.049'}
    tune peter: {'complexity_overwhelm': '+0.031', 'ux_willingness': '-0.016', 'commitment_anxiety': '-0.078', 'uncertainty_aversion': '-0.031', 'advisor_lean': '-0.021'}

## round 2 — ε=0.1611 · conv=0.2425 · PASS=False
  judith  conv 0.03/0.09  S3 0.00/0.05  S4 0.92/0.70  S6 0.67/0.68
  franz   conv 0.45/0.10  S3 0.00/0.04  S4 0.42/0.55  S6 0.22/0.78
  peter   conv 0.05/0.04  S3 0.11/0.25  S4 0.61/0.80  S6 0.83/0.72

→ kept this run (round 2, ε=0.1611).