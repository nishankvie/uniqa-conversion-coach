# Dial tuning — N=40, rounds=3, teacher=openrouter:openai/gpt-4o-mini, 20260530_194654


## round 0 — ε=0.1856 · conv=0.1375 · PASS=False
  judith  conv 0.00/0.09  S3 0.03/0.05  S4 0.92/0.70  S6 1.00/0.68
  franz   conv 0.28/0.10  S3 0.00/0.04  S4 0.40/0.55  S6 0.54/0.78
  peter   conv 0.00/0.04  S3 0.62/0.25  S4 0.77/0.80  S6 1.00/0.72
    tune judith: {'price_shock_s4': '-0.11', 'advisor_lean': '-0.1', 'final_price_sensitivity_s6': '-0.16', 'online_completion': '+0.073'}
    tune franz: {'price_shock_s4': '+0.075', 'advisor_lean': '+0.128', 'final_price_sensitivity_s6': '+0.119', 'online_completion': '-0.144'}
    tune peter: {'complexity_overwhelm': '-0.184', 'ux_willingness': '+0.092', 'final_price_sensitivity_s6': '-0.14', 'online_completion': '+0.034', 'advisor_lean': '-0.021'}

## round 1 — ε=0.1613 · conv=0.1075 · PASS=False
  judith  conv 0.03/0.09  S3 0.00/0.05  S4 0.95/0.70  S6 0.50/0.68
  franz   conv 0.20/0.10  S3 0.00/0.04  S4 0.20/0.55  S6 0.75/0.78
  peter   conv 0.00/0.04  S3 0.38/0.25  S4 0.95/0.80  S6 1.00/0.72
    tune judith: {'price_shock_s4': '-0.123', 'advisor_lean': '-0.095', 'final_price_sensitivity_s6': '+0.09', 'online_completion': '+0.053'}
    tune franz: {'price_shock_s4': '+0.175', 'advisor_lean': '+0.14', 'online_completion': '-0.084'}
    tune peter: {'complexity_overwhelm': '-0.062', 'ux_willingness': '+0.031', 'price_shock_s4': '-0.075', 'advisor_lean': '-0.058', 'final_price_sensitivity_s6': '-0.14', 'online_completion': '+0.034'}

## round 2 — ε=0.2124 · conv=0.19 · PASS=False
  judith  conv 0.05/0.09  S3 0.00/0.05  S4 0.95/0.70  S6 0.00/0.68
  franz   conv 0.35/0.10  S3 0.00/0.04  S4 0.38/0.55  S6 0.44/0.78
  peter   conv 0.00/0.04  S3 0.27/0.25  S4 0.88/0.80  S6 1.00/0.72

→ kept best params from round 1 (ε=0.1613).