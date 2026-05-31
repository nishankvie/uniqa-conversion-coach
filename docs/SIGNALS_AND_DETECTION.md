# Behavioral signals, traffic source & early persona detection

The Coach watches one thing: the **event trace over time**. Its job is to (1) **detect the
persona group early** (S1–S2 + traffic source) and (2) fire the **right intervention** when a
**churn signal** appears. This doc lists *every* signal explicitly and grounds each in the
UNIQA materials (segment booklet, comparison matrix, funnel doc) + behavioral first-principles.

Sources: `personas_comparison_matrix.md`, `uniqa-funnel-doc_en.md`, segment booklet,
`personas.json`, `Private_Doctor_Tariff_Product_Reference_EN.md`.

---

## 0. Traffic source — a session prior AND a persona signal
UNIQA fact: **~80% of calculator traffic is Paid + Organic Search**; **70%+ between 9–20h**;
entry = `uniqa.at/rechner/krankenversicherung`. Source correlates with *intent* and *persona*
(hypothesis layer — the exact joint isn't in the data; inferred from per-persona media/channel
prefs: search-engine use Judith 89 / Franz 86 / Peter 71; Franz "compares offers" 82, "online
purchase option" 36%; Peter passive, customer-service-led, 65% mobile):

| Source | Intent | Persona prior (hypothesis) |
|---|---|---|
| **paid_search** (intent keyword "Privatarzt Versicherung Rechner") | high — actively shopping | Franz↑ (online, searches), Judith↑ (researches) |
| **organic_search** | medium-high — info gathering | Judith / Franz |
| **price-comparison referrer** (Durchblicker/Check24-style) | high, comparison-mode | **Franz** (compares 82–94%) |
| **display / social ad** | low — interrupted, wasn't actively looking | **Peter** (passive) / low-intent browser |
| **direct / portal** | warm — existing customer | Judith (portal 54%) |

Plus: **device** (Peter 65% mobile; Franz/Judith desktop-lean), **time-of-day**, **returning vs
new**. → These seed the persona prior *before any click*, sharpening early detection.

---

## 1. Atomic events (the trace vocabulary)
Existing (`contracts.EventType`): `step_enter, mouse_move, hover, pause, idle, scroll,
field_focus/blur/edit/invalid, keystroke, tap, select, dropdown_open, tooltip_open,
validation_error, price_reveal, price_hover, tariff_click, premium_click, nav_back,
session_gap, tab_blur, tab_focus(value=sec away), cancel_hover, submit, abandon, convert,
widget_shown/cta/dismiss`.

**NEW (add — the creative repertoire):**
| Event | Meaning / why it matters |
|---|---|
| `exit_intent` | cursor darts to top/edge (toward tab-close / URL bar) → **about to leave** — the strongest last-chance intervention trigger |
| `text_select` | highlighted text → reading hard, or selecting a TERM (jargon) they don't get |
| `copy` | copied text → about to **google a term / leave to compare** (funnel killer #6) |
| `external_nav` | opened a new tab / left to compare (vs `tab_blur` which may be incidental) |
| `compare_return` | came back; `value=sec away`: **short** = googled/compared (re-engage), **long** = forgot (re-orient) |
| `slow_mouse` | slow, wandering cursor over options → deliberation / uncertainty (not decisive) |
| `rage_click` / `repeat_click` | repeated clicks same target → frustration / unresponsive-feel |
| `scroll_up` / `reread` | scrolled back up to re-read → confusion / didn't absorb |
| `field_clear` | cleared a field after typing → doubt / abandoned input |

---

## 2. Cumulative / derived signals (what the Coach scores OVER TIME)
The policy reads windows + cumulative counters, not single events:

**Hesitation / friction:** `back_nav_count` (cumulative ↩), `field_reedit_count`,
`validation_error_count`, `field_clear_count`, `longest_idle_sec`, `time_to_first_action`
(landing hesitation), `hesitation` (0..1, persona-emitted).
**Info-seeking / confusion:** `tooltip_open_count`, `hover_count`, `scroll_reversals` (re-reads),
`text_select_count`, `term_copy_count`, `slow_mouse_ratio`.
**Comparison / leaving:** `tab_away_count`, `tab_away_total_sec`, `return_time` (fast↔long),
`external_nav_count`, `exit_intent_count`.
**Price reaction:** `price_hover_count`, `cancel_hover_count`, dwell-after-`price_reveal`.
**Effort / momentum:** `keystroke_total`, `taps_total`, `step_dwell_sec`, `step_revisit_count`
(back-and-forth), `momentum` (advancing fast vs stalling), `total_session_sec`.

---

## 2b. Cohort baseline & RELATIVE signals (anomaly detection, not thresholds)
"Fast" is meaningless absolutely — only relative to peers. So we measure a **cohort baseline**
(`src/uniqa/baseline.py`): per (step, metric) mean/std/p50/p90 over many sessions (cohort = e.g.
this week × device), for dwell_sec, price_hover_n, field_focus_n, back_nav_n, cancel_hover_n,
tooltip_n, keystrokes, validation_err_n, tab_away_n/sec, idle_n, exit_intent_n, etc. Then each live
session is scored as **divergence (z-score)** from that baseline; the coach acts on **OUTLIERS**
(`|z| ≥ ~2`), not fixed numbers:
- `dwell_sec` z ≈ −2.3 on early steps → **much faster than peers** → decisive (Franz, H1/H6) or skimming.
- `back_nav_n` / `cancel_hover_n` / `validation_err_n` z high → anomalously stuck → friction.
- `tab_away_sec` z high → left far longer than peers → forgot (vs short = compared).
`baseline.build_baseline(logs)` + `baseline.divergence(session, baseline)` produce the z-scores fed
to the coach as `relative_signals`. Baselines are cohort/time-window-scoped → recompute per window.

## 3. Churn signals → intervention opportunities (the trigger table)
| Signal (derived) | Reads as | Coach move |
|---|---|---|
| `exit_intent` on S4/S6 | leaving NOW | last-chance widget (price_reframe / save_progress) |
| `copy` / `text_select` of a jargon term | doesn't understand a term | term/`coverage_explain`, `coverage_checker` |
| `tab_away` on S4 then `compare_return` (short) | left to compare | `comparison_table` ("we compared for you") |
| `tab_away` long / big `longest_idle` | forgot the page is open | gentle re-orient nudge / `save_progress` |
| high `hesitation` + big form (S3/S6) | scared by the form | **`form_explainer`** (pre-emptive, before they bail) |
| repeated `nav_back` at S4 + `tooltip_open` | tariff/package confusion | `package_nuance`, `upgrade_explain` |
| `premium_click` then `nav_back` | "advisory-only" dead end | "Optimal is fully online" clarifier |
| dwell-after-`price_reveal` + `cancel_hover` | price shock | `price_reframe` / `pricing_explain` |
| early `slow_mouse` + low momentum (Peter-like) | overwhelmed early | proactive `callback_offer` / `whatsapp_bot` / `quick_quiz` |

---

## 4. Per-persona behavioral fingerprints (for generation diversity AND detection)
From the matrix (decision drivers, channel prefs, online behavior, pain points):

- **Judith** (research-then-advisor): deliberate; `hover`/`tooltip_open` (researches); price-
  performance focus; at S4 leans "I'll confirm with my advisor" → `nav_back` then graceful exit.
  **81% won't finish online** — recover via advisor handoff, don't force online. Desktop, radio+
  messenger media, portal-registered (returning).
- **Franz** (fast online comparer): mechanical/fast input, low dwell; **compares** → early
  `tab_away`/`external_nav` + `compare_return`; hates friction & advisor (Medienbruch pain);
  primary drop at **S6** when final > expected. "Online purchase option" is a top purchase
  criterion. Vienna/urban, online-news media, desktop.
- **Peter** (passive, overwhelmed, mobile): slow `slow_mouse`, high `time_to_first_action`,
  early `validation_error`/`field_reedit` on S3 form; **exits early** (S3 25% drop); low decision-
  drivers across the board (passive); needs guidance. 65% mobile, 43% had hospitalization (warm
  but passive). Service-affine — online presence itself signals an atypical/pushed session.

---

## 5. Early persona detection (the Coach's first job, S1–S2)
Combine: **traffic-source prior** (§0) × **device/time** × **S1–S2 behavior**:
- fast, decisive card selects + desktop + paid/comparison source → **Franz**
- deliberate, hover/tooltip, portal/direct, desktop → **Judith**
- slow, high landing-hesitation, mobile, display/social source, early friction → **Peter**
Output: a running `persona_belief` (distribution) refined each event → by S3/S4 the Coach commits
and **tailors the widget set** (Franz: never-advisor; Peter: early handoff; Judith: advisor-ok).
This is the central technical challenge per the matrix ("do not unify" warning).

---

## 6. Implication for the persona MODEL (richer generation)
The simulator persona must EMIT this repertoire so the trace is realistic + diverse:
back-and-forth nav, hover/slow-mouse deliberation, text-select/copy of jargon, tab-away-to-
compare (short vs long return), scroll re-reads, exit-intent (mouse-to-edge) before leaving,
landing hesitation on big forms. The persona prompt becomes a **narrative usage story** with
JSON hints (`preferred_interventions`, `likely_churn_reasons`, `traffic_source`) — see
`PERSONA_DISTILL_V2_PLAN.md`. The persona also **assesses** the coach intervention (helpful vs
noisy) so the trace teaches the coach what works per persona.
