# UNIQA Funnel — Component & Action Recon (CDP, live)

> Captured live from `uniqa.at/rechner/krankenversicherung/` via chrome-cdp, plus the
> official funnel doc for the later steps. This is the source of truth for the twin:
> our React funnel must be **1-1** with these components, actions, transitions, and
> error states.

## Tech stack of the real funnel

- **Angular** SPA. Validation classes `ng-pristine / ng-invalid / ng-touched`.
- **UNIQA "Reef" design system** — custom elements prefixed `ur-*` / `uq-ui-*`:
  `UR-DATEPICKER`, `UR-SELECT` + `UR-SELECT-FIELD`, `UQ-UI-ICON` (`reef-icon`),
  helper text `helper-text ur-body-75 error`, error icon `unext-shared-error`.
- Accessibility: a live region announces each step — `"Ein neuer Schritt wurde
  geladen: <heading>"`. Honour this in the twin (aria-live announcement on step change).

## Global chrome

- **Progress stepper** (4 phases): `Angaben › Produkt › Empfehlung › Abschluss`.
  Filled bar shows current phase.
- **Primary button** `Weiter`; **secondary/outline** `Abbrechen` (step 1 only) and
  `Zurück` (steps 2+). Back navigation appears from step 2 onward.

## Steps (in-scope online path)

### S1 — COVERAGE_TYPE (phase: Angaben)
- Heading: "Wo möchten Sie abgesichert sein?"  ·  Instruction: **"Bitte wählen Sie eine oder mehrere Optionen."**
- Control: **multi-select** — two `checkbox` **choice-cards** (icon + title + 3 checkmark feature bullets, checkbox top-right):
  - `Bei Arztbesuchen` (Kassen-/Wahl-/Privatärzt:in · Schul- & Alternativmedizin · Telemedizin) ✅ in-scope
  - `Im Krankenhaus` (Spital/Privatklinik · Zweibettzimmer · OP-Termin flexibel) ❌ out-of-scope
- Buttons: `Weiter` · `Abbrechen`. Selection does **not** auto-advance (checkbox + Weiter).
- Transition: ≥1 required. Hospital (or both) selected → out-of-scope → advisor route. Else → S2.

### S2 — INSURED_PERSONS (phase: Angaben)
- Heading: "Wer soll versichert werden?"  ·  Instruction: **"Bitte wählen Sie eine Option."**
- Control: **single-select** — two `radio` options: `Ich selbst` ✅ / `Andere Personen` ❌ (advisor route).
- Buttons: `Weiter` · `Zurück`. Transition: self → S3; others → advisor route.

### S3 — PERSONAL_INFO (phase: Angaben)
- Heading: "Um eine voraussichtliche individuelle Prämie für Sie zu berechnen, benötigen wir:"
- Instruction: **"Bitte füllen Sie alle Felder aus."**
- Controls:
  - **DatePicker** (`ur-datepicker`): text input format `TT.MM.JJJJ` + "Datum im Kalender auswählen" calendar button.
  - **SearchableSelect** (`ur-select`): `readonly` trigger ("Bitte treffen Sie eine Auswahl") opens a **CDK overlay listbox**. Options: `ÖGK`, `BVAEB-OEB`, `SVS …`, `BVAEB-EB`, `KFA …`.
- Buttons: `Weiter` · `Zurück`.
- **Error states (verbatim, captured live):**
  - DOB empty/invalid (`99.99.9999`) → `helper-text … error`: **"Bitte geben Sie das Datum im Format TT.MM.JJJJ ein."** + error icon.
  - SV empty → **"Bitte wählen Sie Ihre Sozialversicherung."** + error icon.
  - Field gets `ng-invalid ng-touched`, container gets `.error`. Weiter is blocked until valid.

### S4 — TARIFF_SELECT (phase: Produkt) — ⚠️ 66% drop (first price)
- Heading: "Welche Leistungen soll Ihre Privatarzt-Versicherung abdecken?"
- Info box: "...nach 3 Jahren ohne neue Gesundheitsprüfung wechseln..."
- Control: **TariffTable** — 4 columns side by side, each a selectable card:
  | id | name | provisional € /mo | status |
  |---|---|---|---|
  | start | Start | 38.74 | online ✅ |
  | optimal | Optimal | 68.14 | online ✅ |
  | opt_plus | Opt. Plus | 96.66 | Beratung (advisory) ❌ |
  | premium | Premium | 140.15 | Beratung (advisory) ❌ |
  - Coverage rows with **(i) tooltips**: `arztleistungen, medikamente, therapien, hilfsmittel, augen_op` (+ Höchstbetrag).
  - Selecting a column **reveals** its provisional premium; sticky "Unser Angebot €.../Monat" bar.
- Transition: Start/Optimal → online path → S6. Opt.Plus/Premium → advisory route (consultation).

### S6 — PERSONAL_DATA + HEALTH (phase: Abschluss/Angaben)
- Personal data form (name, contact, height/weight/sport/doctor) + **health questions** → used for the FINAL premium. (Coach must never receive health answers as features.)

### S7 — FINAL_PRICE (phase: Empfehlung) — ⚠️ 78% drop
- Final individualised premium after health assessment; usually higher than the S4 provisional → trust-collapse moment.

### S12+ — CLOSING (phase: Abschluss) — ✅ conversion
- Personal/address · start date · payment · consents (T&C, privacy) · confirmation → **online purchase = conversion**.

## Component set (catalog for the json-render registry)

`ProgressStepper` · `ChoiceCardGroup{mode: checkbox|radio}` · `ChoiceCard` · `TextField` ·
`DatePicker` · `SearchableSelect` · `TariffTable` / `TariffColumn` · `CoverageRowTooltip` ·
`HealthForm` · `FinalPrice` · `ClosingForm` · `Button{primary|secondary}` · `HelperTextError` ·
`StickyOfferBar`.

## Action space (must be 1-1 with `calculator/widget.py` + `contracts.EventType`)

| funnel action | event(s) emitted | legal on |
|---|---|---|
| enter a step | `step_enter` | all |
| toggle coverage checkbox | `select` (target=coverage id) | S1 |
| pick insured radio | `select` (target=insured id) | S2 |
| type DOB | `keystroke` (target=date_of_birth) | S3 |
| open SV overlay | `dropdown_open` (target=sv_number) | S3 |
| pick SV option | `select` (target=sv_number, value=option) | S3 |
| invalid field | `validation_error` (target, value=message) | S3, S6 |
| select tariff | `select` + `price_reveal`(provisional) | S4 |
| click advisory tariff | `premium_click` | S4 |
| open coverage tooltip | `tooltip_open` (target=row) | S4 |
| hover element (dwell) | `hover` / `price_hover` | all / S4 |
| final price shown | `price_reveal` (value=final) | S7/S6 |
| Weiter / Zurück / Abbrechen | `submit`+advance / `nav_back` / `abandon` | per step |
| close / external link | `abandon` (reason) | all |
| switch/return tab | `tab_blur` / `tab_focus` | all |
| no movement | `idle` | all |
| finish purchase | `convert` | S12 |

## Transitions (state machine)

```
S1 (≥1 coverage) ──hospital/both──▶ advisor_route (out of scope)
   └─doctor only─▶ S2 (one insured) ──others──▶ advisor_route
                      └─self─▶ S3 (DOB valid + SV chosen) ─▶ S4 (provisional price)
                                  ↑ errors block Weiter        ├─opt_plus/premium─▶ advisory_route
                                                               └─start/optimal─▶ S6 (health) ─▶ S7 (final price) ─▶ S12 closing ─▶ convert
back: Zurück steps to previous; Abbrechen (S1) cancels.
```
