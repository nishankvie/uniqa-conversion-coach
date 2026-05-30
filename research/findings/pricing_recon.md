# Real UNIQA pricing — reverse-engineered via Chrome CDP (2026)

Captured live from `uniqa.at/rechner/krankenversicherung/` by intercepting the calculator's
own API calls + replaying the (non-captcha) pricing endpoints with varied inputs.

## API contract (api.ovtapp.com — health-insurance-calculator-ms)

| endpoint | method | request | returns | captcha? |
|---|---|---|---|---|
| `/v1/statics` | GET | — | insuranceProviders (SV→id: ÖGK=1, BVAEB-OEB=2, SVS-Landw=3, SVS-gew=4, BVAEB-EB=6, KFA=11) | no |
| `/v1/products` | POST | `{productCategory:"PRIVATE_DOCTOR", birthDate:"YYYY-MM-DD", insuranceProviderId}` | 4 tariffs w/ `premium`, `maxCoverageValue`, `coverageLimits` | **no** |
| `/v1/premiums` | POST | `+ maxCoverageId, selectedAddons[], gender?` | `totalMonthlyPremium`, baseProduct, addons | **no** |
| `/v1/calculate` | POST | — | (the binding offer) | **YES (captcha header)** |

The on-screen S4/S6 prices come from `/products` + `/premiums` (no captcha). Only the final
binding `/calculate` is captcha-gated.

## Codified + multi-experiment (not a single pass)

The experiment is codified in `research/price_probe.js` (re-runnable against the live
session) and the canonical dataset is `research/findings/pricing_dataset.json` (age curve
18–75 × 4 tariffs + factor-isolation block). Findings below are from sweeping many inputs,
not one form fill.

## What drives the price (experiments)

- **Age (birthDate): YES** — smooth & monotonic, with a **youth band** (age 18 ≈ half: Optimal
  €35.40; jumps to €62.34 at 21, then gradual). ÖGK, gender-neutral, 2026:

  | age | Start | Optimal | Opt. Plus | Premium |
  |----|------|---------|-----------|---------|
  | 25 | 37.75 | 66.40 | 94.06 | 136.39 |
  | 35 | 41.10 | 72.62 | 104.29 | 151.23 |
  | 41 | 42.53 | 75.36 | 109.56 | 158.87 |
  | 45 | 43.90 | 77.74 | 113.98 | 165.27 |
  | 55 | 48.26 | 84.74 | 124.57 | 180.63 |
  | 65 | 53.12 | 92.90 | 137.83 | 199.86 |

  (Our old static 38.74 / 68.14 / 96.66 / 140.15 ≈ the age-25 column — they were age-~27 figures.)

- **Tariff (maxCoverageId): YES** — Start=11/1400, Optimal=12/2800, Opt.Plus=13/4200, Premium=14/8400.
- **SV (insuranceProviderId): NO** — ids 1/4/6/11 all give the same premium (72.62 @ age35 Optimal).
- **Gender: NO** — female = male = 72.62 (EU unisex pricing).
- **Health answers: NO** — not even an input to `/products` or `/premiums`. The displayed
  online premium does **not** change after the health questionnaire.

## The big correction: there is NO online price-jump

The S4 "voraussichtliche Prämie" and the S6/final price are the **same** age+tariff number.
Health questions gate **offline underwriting** (the binding premium is confirmed later), but
the user never sees an online recalculation. So:

- The twin's `health="yes" → +3` jump (App.jsx / transitions) is **fabricated** → remove it.
- Last turn's "inject computed S6 final-price jump to fix Franz" is **wrong** — there is no jump.
- **Franz's real S6 friction** is therefore NOT a displayed price increase. It is: the long
  health questionnaire (effort), the commitment moment, and the *uncertainty* that the
  binding post-underwriting premium "could" differ from the estimate (anticipated, not shown).
  Persona S6 churn should be modelled as effort + commitment-anxiety + underwriting-uncertainty,
  not a price delta.

## Twin updates

- `scope.premium(tariff, age)` — age-interpolated real curve (this file's table).
- `widget.widget_response_model()` S6 — corrected: final online price == provisional
  (age+tariff); health is for underwriting, not an online surcharge.
