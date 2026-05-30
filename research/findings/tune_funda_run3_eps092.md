# Dial tuning — N=50, rounds=3, teacher=openrouter:openai/gpt-4o-mini, 20260530_215207


## round 0 — ε=0.1039 · conv=0.116 · PASS=False
  judith  conv 0.04/0.09  S3 0.04/0.05  S4 0.88/0.70  S6 0.67/0.68
  franz   conv 0.20/0.10  S3 0.00/0.04  S4 0.36/0.55  S6 0.69/0.78
  peter   conv 0.02/0.04  S3 0.20/0.25  S4 0.95/0.80  S6 0.50/0.72
    tune judith: {'budget_pressure': '-0.027', 'value_orientation': '-0.019', 'advisor_lean': '-0.045', 'commitment_anxiety': '-0.02'}
    tune franz: {'budget_pressure': '+0.029', 'value_orientation': '+0.021', 'advisor_lean': '+0.073', 'commitment_anxiety': '+0.062', 'uncertainty_aversion': '+0.01'}
    tune peter: {'budget_pressure': '-0.023', 'value_orientation': '-0.016', 'advisor_lean': '-0.016', 'commitment_anxiety': '+0.048', 'uncertainty_aversion': '+0.024'}

## round 1 — ε=0.1034 · conv=0.14 · PASS=False
  judith  conv 0.02/0.09  S3 0.04/0.05  S4 0.77/0.70  S6 0.91/0.68
  franz   conv 0.26/0.10  S3 0.00/0.04  S4 0.36/0.55  S6 0.59/0.78
  peter   conv 0.02/0.04  S3 0.27/0.25  S4 0.77/0.80  S6 0.88/0.72
    tune judith: {'commitment_anxiety': '-0.079', 'uncertainty_aversion': '-0.025', 'advisor_lean': '-0.036'}
    tune franz: {'budget_pressure': '+0.029', 'value_orientation': '+0.021', 'advisor_lean': '+0.103', 'commitment_anxiety': '+0.107', 'uncertainty_aversion': '+0.02'}
    tune peter: {'commitment_anxiety': '-0.034', 'uncertainty_aversion': '-0.017'}

## round 2 — ε=0.0919 · conv=0.132 · PASS=False
  judith  conv 0.04/0.09  S3 0.10/0.05  S4 0.82/0.70  S6 0.75/0.68
  franz   conv 0.20/0.10  S3 0.02/0.04  S4 0.49/0.55  S6 0.60/0.78
  peter   conv 0.10/0.04  S3 0.21/0.25  S4 0.73/0.80  S6 0.50/0.72

→ kept this run (round 2, ε=0.0919).