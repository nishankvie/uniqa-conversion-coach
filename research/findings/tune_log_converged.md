# Dial tuning — N=40, rounds=3, teacher=openrouter:openai/gpt-4o-mini, 20260530_194000


## round 0 — ε=0.1613 · conv=0.1575 · PASS=False
  judith  conv 0.03/0.09  S3 0.09/0.05  S4 0.94/0.70  S6 0.50/0.68
  franz   conv 0.30/0.10  S3 0.00/0.04  S4 0.33/0.55  S6 0.56/0.78
  peter   conv 0.00/0.04  S3 0.47/0.25  S4 0.81/0.80  S6 1.00/0.72
    tune judith: {'price_shock_s4': '-0.119', 'final_price_sensitivity_s6': '+0.09', 'online_completion': '+0.053', 'advisor_lean': '-0.033'}
    tune franz: {'price_shock_s4': '+0.113', 'final_price_sensitivity_s6': '+0.112', 'online_completion': '-0.164', 'advisor_lean': '+0.102'}
    tune peter: {'complexity_overwhelm': '-0.109', 'final_price_sensitivity_s6': '-0.14', 'ux_willingness': '+0.054', 'online_completion': '+0.034', 'advisor_lean': '-0.021'}

## round 1 — ε=0.0974 · conv=0.0825 · PASS=False
  judith  conv 0.03/0.09  S3 0.05/0.05  S4 0.92/0.70  S6 0.67/0.68
  franz   conv 0.15/0.10  S3 0.00/0.04  S4 0.50/0.55  S6 0.70/0.78
  peter   conv 0.00/0.04  S3 0.44/0.25  S4 0.80/0.80  S6 1.00/0.72
    tune judith: {'price_shock_s4': '-0.109', 'online_completion': '+0.053', 'advisor_lean': '-0.033'}
    tune franz: {'final_price_sensitivity_s6': '+0.04', 'online_completion': '-0.044', 'advisor_lean': '+0.027'}
    tune peter: {'complexity_overwhelm': '-0.097', 'final_price_sensitivity_s6': '-0.14', 'ux_willingness': '+0.049', 'online_completion': '+0.034', 'advisor_lean': '-0.021'}

## round 2 — ε=0.1333 · conv=0.1825 · PASS=False
  judith  conv 0.03/0.09  S3 0.03/0.05  S4 0.86/0.70  S6 0.80/0.68
  franz   conv 0.35/0.10  S3 0.00/0.04  S4 0.45/0.55  S6 0.36/0.78
  peter   conv 0.00/0.04  S3 0.27/0.25  S4 0.84/0.80  S6 1.00/0.72

→ kept best params from round 1 (ε=0.0974).