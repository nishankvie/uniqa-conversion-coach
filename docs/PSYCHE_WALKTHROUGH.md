# Pure Consciousness Walkthrough — Grounding the Bounce Model
> First-person traversal of the real screenshotted UNIQA flow.
> Each step: what the mind actually does, where attention leaks, why it bounces.

The point: replace crude per-step abandon probabilities with a *latent mental state*
that evolves, plus *named bounce reasons* that fire when state crosses thresholds.
A real user doesn't "abandon at step 4 with p=0.66" — they bounce because price
arrived before they were ready, or a kid walked in, or the form felt endless.

---

## The 6 latent state variables (what's actually in the mind)

```
attention        0..1   how present I am. External events (phone, tab, life) leak it.
price_readiness  0..1   am I braced to see a number? builds slowly, shocks reset it.
comprehension    0..1   do I understand what I'm buying?
trust            0..1   do I believe this brand / this online channel?
effort_budget    0..1   patience remaining. every field, every step drains it.
valence         -1..1   felt emotion. frustration ↓, small wins ↑.
```

Plus a fixed `intent` per session: `purchase | orientation | comparison | price_check`.
Most bounces are people whose intent was never "purchase today."

---

## The 7 bounce reasons (named, grounded, each maps to a counter-move)

| Reason | Fires when | Real-world cause | Coach counter |
|--------|-----------|------------------|---------------|
| DISTRACTION | attention < 0.25 | phone rings, kid, tab switch, doorbell | (cannot fully prevent — progress_saver to recover later) |
| PRICE_SHOCK | price shown & price_readiness < 0.4 | number bigger than imagined, no framing | price_reframe (€/day), trust_signal first |
| OVERWHELM | comprehension < 0.3 & options ≥ 3 | 4 tariffs × 6 coverage rows, no guidance | coverage_explain, callback (Peter) |
| EFFORT_EXHAUSTION | effort_budget < 0.2 | 12-field form, SV-number wall | form_helper, progress_saver |
| TRUST_GAP | trust < 0.35 at commit step | "do I give these people my health data?" | trust_signal, advisor_handoff (not Franz) |
| NOT_READY | intent=orientation & proximity low | just checking, not buying today | upgrade_path (low-commitment), progress_saver |
| COMPARISON_LEAVE | intent=comparison & dwell high | opened competitor tab | coverage_explain, market framing |

---

## Step-by-step consciousness trace (in-scope path)

### S1 — "Wo möchten Sie abgesichert sein?" (Bei Arztbesuchen / Im Krankenhaus)
> *Okay, two cards. "Bei Arztbesuchen" — that's me, I want to pick my own doctor.
> "Im Krankenhaus" sounds like more. Do I need both? ... no, doctor visits, that's
> what I came for.*

State moves: comprehension +0.1 (clear choice), effort_budget −0.03.
Bounce risk: very low. Only DISTRACTION here. This is the "warm up" step.

### S2 — "Wer soll versichert werden?" (Ich selbst / Andere Personen)
> *Just me. Easy.*

State moves: effort_budget −0.03, valence +0.05 (momentum).
Bounce risk: low. DISTRACTION only.

### S3 — Geburtsdatum + Sozialversicherung
> *Birthdate, fine. Sozialversicherung... which one am I? ÖGK I think? Let me check
> the dropdown... BVAEB, SVS... yeah ÖGK. Okay.*

State moves: effort_budget −0.08 (first real input), comprehension −0.05 (the SV
dropdown introduces a flicker of doubt), price_readiness +0.1 (I sense a price is coming).
Bounce risk (Peter especially): OVERWHELM if comprehension already low, EFFORT_EXHAUSTION
if the dropdown is confusing. Peter's 25% early exit lives here.

### S4 — TARIFF TABLE (66% bounce) ← the wall
> *Oh. €41,30. And €73, and €105, and €152. Four columns. Wait — "Voraussichtliche
> Prämie", so this isn't even final? It could go UP? And what's the difference between
> Start and Optimal again — Therapeutische Behandlungen, Heilbehelfe... €1.400 vs
> €2.800 max per year, what does that even mean in real visits?*
>
> *[Franz subtype]: clicks Premium out of curiosity → "Nur nach Beratung" → ugh, I
> have to TALK to someone for that? I just want to do this online. [backs out]*
>
> *[Judith subtype]: €41 is fine but is Optimal worth double? I should probably ask
> someone... [opens thought of advisor]*
>
> *[Peter subtype]: too many numbers. I don't know which one is right for me. I'll
> just... maybe call them later. [leaves]*

State moves: **price arrives**. If price_readiness < 0.4 → PRICE_SHOCK fires.
comprehension tested against options=4 → OVERWHELM if low. valence −0.2 (the
"could go up" line). This is where attention, price_readiness, comprehension all
get stress-tested at once. 66% don't survive it.

### S5 — ADD-ON UPSELL (24% bounce) ← wrong moment
> *Now they want me to add MORE? Fit fühlen +€17, Mental wachsen +€25... I haven't
> even committed to the base and you're upselling me. I'll skip all of these. ...
> actually this makes me wonder if €41 was the real price at all.*

State moves: effort_budget −0.1, valence −0.1 (premature upsell irritation),
price_readiness −0.1 (re-anchoring doubt). Bounce: EFFORT_EXHAUSTION or NOT_READY.

### S6 — PERSONAL DATA FORM (78% bounce) ← the worst
> *Geschlecht, Vorname, Name... Sozialversicherungsnummer — ten digits — where is
> that, my e-card is in my wallet in the other room. Email, phone, height, weight,
> do I do competitive sport, who's my doctor... this is a lot. And it's asking my
> WEIGHT? Are they going to reject me or jack up the price? The final price is going
> to be different from €41 anyway... I'll do this later. [closes tab]*

State moves: effort_budget −0.25 (the wall), trust tested hard (health data),
price_readiness re-shocked (final price ≠ estimate). Bounce: EFFORT_EXHAUSTION
(SV-number + length), TRUST_GAP (health data), PRICE_SHOCK round 2 (final > estimate).
78% don't survive.

### S7 — PURCHASE (success)
> *Done. That was... actually fine once I got going.*

---

## What this means for the model

1. **Bounce is multi-causal.** Same step, different reason per person/moment.
   The Coach must read *which* reason is firing, not just "they're hesitating."

2. **Price_readiness is the master variable for S4.** It builds across S1–S3 and
   gets shocked at S4. A Coach that raises price_readiness *before* S4 (daily-cost
   framing, trust) beats one that reacts after the shock.

3. **Effort_budget is the master variable for S6.** It only drains. The Coach can
   slow the drain (form_helper, "3 fields left") or decouple it (progress_saver,
   deposit, WhatsApp resume).

4. **DISTRACTION is irreducible** (~external). Best the Coach does is enable recovery
   (progress_saver → WhatsApp resume link). This is the honest ceiling: you cannot
   coach away a ringing phone, you can only let them come back.

5. **intent gates everything.** A price_check visitor will not convert today no
   matter what. Counting them as "lost conversions" overstates the opportunity.
   Honest uplift = conversion among *purchase-intent* sessions.
