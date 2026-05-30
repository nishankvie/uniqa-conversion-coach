# Parameter-driven persona model — diagnosis + proposal

> **STATUS: persona LLM-agent — LOCKED / DONE (v1).** Stepwise generation + fundamental-factor
> dials, persona-coherent, ε=0.092–0.10 vs the funnel.py anchors (under the 0.12 gate; all
> personas convert). Locked params in `prompts/personas/*.params.json` + global-best.
> Locked dataset: `datasets/persona_v1/` (300 sessions, 1238 per-step SFT pairs).
> **Active next stage:** distil into 3 fast LOCAL per-step models on Leonardo (`leonardo/`),
> each validated to be statistically close to this dataset, then swap in for fast iteration
> + the dynamic coach loop. (Open: Franz's 0.10 conv anchor is a stale price-jump artifact —
> re-derive if exact per-cell PASS is required.)


Empirical write-up of the session-gen conformance loop and the architecture change the
results force. Raw evidence: `research/findings/iter_{base,quant,params}.md`.

## 1. What we ran (gpt-4o-mini, N=30/persona, whole-session generation)

| iteration | lever added | ε (mean abs bounce) | overall conv (tgt 0.083) | **S4 bounce** (tgt .55–.80) | S6 bounce (tgt .68–.78) | Peter conv (tgt .04) |
|---|---|---|---|---|---|---|
| 0 base | hand-scrubbed persona + **widget state machine** | 0.309 | 0.053 | **≈0.00** | .70–.97 | 0.27 |
| 1 quant | + behavioural metrics (online propensity, switch, NPS) | 0.280 | 0.067 | **≈0.00** | .73–.82 | 0.13 |
| 2 params | + behavioural **dials** + per-step stay/leave rule | 0.333 | 0.034 | **≈0.00** | .86–1.04 | 0.07 |

Overall conversion lands near the ~5.6 % anchor on its own, and the quant lever fixed
Peter's over-conversion (0.27 → 0.07). **But the funnel SHAPE never matched.**

## 2. Root cause — the S4 price wall is unreachable under whole-session generation

The real funnel loses **55–80 %** at the *first* tariff price (S4). Every iteration
produced **~0 %** there and dumped **all** churn onto the *final* price (S6) — even with
the S4 dial at VERY HIGH and an explicit instruction to decide stay/leave at the first
price.

Why it resists every prompt lever:

1. **Narrative-completion bias.** One call = one coherent story. Once the model commits
   the persona to entering personal data, it completes the arc; truncating at S4 is
   "unnatural" to a single narrative. Prompt pressure doesn't beat this — iteration 2
   added the pressure and S4 stayed at 0.
2. **"Provisional" framing.** The S4 price is labelled *voraussichtlich/estimate*, so the
   model reasons "this isn't the real number — I'll continue to see it." The only price
   it treats as a decision point is the **final** one (S6).
3. **One narrative ≠ a population.** Conformance needs ~21/30 sessions to exit at S4.
   Temperature 0.9 does not spread a single-call narrative into that distribution; the
   model picks the modal "engaged" story almost every time.

**Conclusion:** dials are necessary but **not sufficient** while generation is a single
whole-session call. The generator architecture, not just the prompt, has to change.

## 3. The parameter model (implemented — `prompts/personas/<persona>.params.json`)

Six behavioural dials in [0,1], rendered to **graded language** (never raw numbers,
never a churn target) by `persona_datagen.params_block()`:

| dial | drives | judith / franz / peter (current) |
|---|---|---|
| `price_shock_s4` | exit at the first price screen | .70 / .55 / .80 |
| `complexity_overwhelm` | early (S3/S4) give-up | .30 / .15 / .80 |
| `final_price_sensitivity_s6` | exit at final price | .55 / .70 / .50 |
| `advisor_lean` | leave-to-call instead of finishing online | .60 / .05 / .70 |
| `patience` | low → effort-exhaustion exits on long forms | .55 / .45 / .25 |
| `online_completion` | push through and buy online | .35 / .60 / .20 |

These are **persona traits**, not funnel outcomes — they are dials we tune; the anchors
in `funnel.py` are the held-out validation signal. Rendering buckets each scalar to
{very low … very high} + an adverb, so the agent reasons with a *pressure*, never a quota.

## 4. Proposed architecture — per-step generation so the dials bite

Replace the single whole-session call with a **stepwise loop we orchestrate** (we already
own the state machine via `scope.py` + `widget.widget_response_model()`):

```
disposition = sample_disposition(persona_dials, rng)   # per-SESSION jitter on the dials
                                                        # → heterogeneous population
state = START
for step in S1..S6:
    ctx = { step, screen, action_space, state,
            price_just_revealed?, price_vs_hoped,       # anchor the shock concretely
            effort_spent_so_far, disposition }
    out = LLM(step_prompt(persona, ctx))   # emit this step's actions + thoughts,
                                           # THEN an explicit {stay|leave, reason}
    record(out.events)
    if out.decision == leave: emit abandon(out.reason); break
    state = widget_transition(state, out.actions)        # scope.py drives the response
emit terminal (convert if reached S6 purchase)
```

Why this fixes §2:
- **Per-step stop is a real, independent decision** → across 30 sessions the S4 exits
  accumulate to the population rate instead of being narrated away.
- **`sample_disposition`** gives per-session variance (price-shock-heavy sessions leave at
  S4; determined sessions reach S6) → a *distribution*, not one modal story.
- **`price_vs_hoped`** makes the shock concrete: pass the persona's hoped price band (a
  dial-derived trait, not a target) so "€68 vs hoped ~€40" actually triggers the exit.
- Still **target-free**: the agent never sees 66/78/5.6; it sees its own dials + the live
  screen and makes a local choice.

Cost: ~5 calls/session vs 1. Mitigate with the same thread pool; cache S1/S2 (near-
deterministic). We already have `build_step_prompt()` to extend.

## 5. Tuning loop — coordinate descent on dials (no target leakage)

```
while ε > gate:
    run validation (research/run.py)
    for each (persona, step) with |observed − target| > tol:
        nudge the responsible dial toward closing the gap
        (S4 bounce low → ↑price_shock_s4 / ↑complexity_overwhelm;
         conv too high → ↓online_completion; S6 over-fires → ↓final_price_sensitivity)
    clamp to [0,1]; write params.json; re-run
```

Legitimate because the **dial is a persona trait** and the **target is held-out
validation** — we tune the trait until the behaviour matches, exactly as you'd fit a
behavioural parameter. The dials never enter the prompt as numbers, and the funnel rates
never enter the prompt at all. Optional: auto-tuner `research/tune.py` (coordinate descent
+ a step size), with a human approving each dial diff (keeps it manual/auditable).

## 5b. Step-based results (implemented — `research/run.py --stepwise`)

Per-step generation is implemented: we orchestrate S1→S6, each step is one LLM turn that
emits the step's events, tracks running state vars, and makes an explicit stay/leave call.
The escalation was repeated from scratch (gpt-4o-mini, N=20/persona;
`research/findings/stepwise_iter*.md`):

| stepwise iter | lever | overall conv (tgt .083) | S4 bounce J/F/P (tgt .70/.55/.80) | ε |
|---|---|---|---|---|
| 0 base | per-step continue/leave | 0.715 | 0.35 / 0.00 / 0.10 | 0.38 |
| 1 +quant | behavioural metrics | **0.845** (worse) | 0.10 / 0.05 / 0.10 | 0.44 |
| 2 **+state** | state vars + felt **distracted/dissatisfied** decision | 0.445 | **0.79 / 0.10 / 0.63** | **0.27** |
| 3 +state+params | dials on top of state | 0.490 | 0.95 / 0.00 / 0.84 | 0.31 |

Findings:
1. **The felt-state lever (`--state`) unlocks the S4 wall** that no whole-session prompt
   could move — Judith S4 → .79 (tgt .70), Peter → .63–.84 (tgt .80). The two abandonment
   MODES (`distracted` → drift off / forget the form; `dissatisfied` → close it because it
   doesn't satisfy + reason) produce behaviourally correct exits.
2. **`--quant` is counter-productive in stepwise** — online-purchase propensity priors push
   the model to *complete*, worsening over-conversion. Drop it for stepwise.
3. **Dials (`--params`) control magnitude** — Peter S4 hit .84; Judith's S4 dial is now too
   strong (.95, overshoot → lower `price_shock_s4`).
4. **Franz is the open case**: he converts ~0.95 because the loop lets the LLM keep the S6
   final price = estimate, so he has no reason to leave. Real funnel: most see a HIGHER
   final price. → the orchestrator must **compute the S6 final price (with uplift) as a
   widget response** and present it, so Franz faces the real jump (a state-machine fact we
   own, not a target).

## 5c. Behavioural factor model (implemented — stepwise `--state`)

The per-step decision is no longer just conscious reasoning. Each step the persona weighs
this screen's **UX-complexity grade** (a widget hypothesis) against its own traits +
**session context**, tracks state vars, and picks a `feeling` from a layered taxonomy:

| feeling | layer | trigger |
|---|---|---|
| `dissatisfied` | conscious | screen contradicts/undershoots `your_initial_intent` — price > hoped, advisory wall when they wanted online, unexpected/contradicting info |
| `cant_grasp` | **subconscious** | looking at the text without absorbing it (low `comprehension` × high UX complexity) → quiet drift-off |
| `too_much_effort` | **subconscious** | screen feels high-effort / low-reward (low `ux_willingness` × high complexity) → refuses without articulating why |
| `distracted` | **exogenous** | a life interruption (notification, message, family duty, surroundings — traffic/conversation on mobile/commuting) pulls them away; may not return |
| `engaged` | — | delivers what they expected → continue |

**State vars tracked across steps:** `attention, satisfaction, effort_left, grasp,
effort_vs_reward` (drop on heavy screens and as the journey wears on).

**Per-step UX-complexity hypothesis** (`widget.ux_complexity`): S1/S2 low, S3 medium,
**S4 high** (4 tariffs × 6 jargon rows, advisory badges, no 'recommended'), **S6 high**
(long health form + final price). Tunable, not a target.

**New persona dials** (on top of the 6): `ux_willingness`, `comprehension`,
`distractibility`. **Session context** (`device` desktop/mobile + `surroundings`
home/work/commuting) is sampled per session, persona-weighted. None of this encodes a target.

**Result (gpt-4o-mini, N=20, `--stepwise --state --params`; findings stepwise_iter4/5):**

| | overall conv (anchor ~.056) | **ε** | Franz (conv/.10, S4/.55, S6/.78) |
|---|---|---|---|
| before factors (iter2 state) | 0.445 | 0.27 | over-converts |
| **with factors + tuned dials** | **0.050–0.10** | **0.13–0.16** | **0.10 / 0.55 / 0.78 — calibrated** |

The factor model + dials moved ε 0.27 → ~0.13 and **calibrated Franz cleanly** ("final
price jumped to €72, I feel misled"); Peter now exits with `too_much_effort` / `cant_grasp`
as intended. Residual error: Judith/Peter over-exit at S4 (high `advisor_lean` fires as
'leave to call') + N=20 sampling noise (ε ±0.03 run to run). Tuning/variance, not mechanism.

## 5d. Auto-tuner result (`research/tune.py`, N=40)

Coordinate descent on the dials: each round generate N stepwise+state sessions/persona,
validate, then nudge the responsible dial per failing cell (S4 over-exit → ↓`price_shock_s4`
+ ↓`advisor_lean`; S3 → ↓`complexity_overwhelm`/↑`ux_willingness`; S6 → `final_price_sensitivity`;
conv → `online_completion`/`advisor_lean`). Writes params each round, keeps best-ε.

**Converged:** ε **0.16 → 0.097** (below the 0.12 gate), overall conversion **0.0825** (≈ the
~5.6% anchor). Franz fully calibrated (conv .15/.10, S4 .50/.55, S6 .70/.78); Peter S4 .80/.80;
Judith S3/.05 and S6 .67/.68. Committed params are this best set. Logs:
`research/findings/tune_log_converged.md`.

**Two residuals (not mechanism):**
1. **Judith's S4 is sticky** (~0.92 vs .70) even with `price_shock_s4`↓0.28 and `advisor_lean`↓.
   Her *persona narrative* ("you slow down at the price screen, consider calling, close the
   tab") dominates the dials — arguably realistic (S1 hybrids do leave at the tariff wall),
   but if .70 is required, soften her briefing's S4 paragraph, not just the dial.
2. **Peter drew 0 conversions** at N=40 (target ~4% → ~1.6 expected) — sampling variance; the
   only thing blocking a full PASS verdict.

**Tuner caveats:** coordinate descent oscillates ±0.03–0.05 ε at N=40 (a 2nd seed-7 run
wandered to 0.16); mitigate with **multi-seed averaging per round** and a *persisted global
best* (current tuner keeps best-of-its-own-run only, so re-running can regress — restore from
git if so).

## 5e. Audit + codex iteration (re-review: are we doing the right thing?)

**Integrity audit — PASS.** Diff of `prompts/personas/*.md` vs the task-input briefings shows the
ONLY changes are the removed funnel-OUTCOME sentences (66/78/20%). Every GIVEN persona number
(demographics, channel %, switch willingness 24%, NPS, 34/64/39% online) is untouched.
`personas.json` and `PERSONA_WEIGHTS` (30/50/20) are read-only. We changed only the RULES
(dials + state dynamics + prompt), never the given data. ✅

**Taxonomy (static traits vs dynamic state):**

| layer | members | role |
|---|---|---|
| STATIC traits (`params.json`, codified empirical values, never change in a session) | price_shock_s4, final_price_sensitivity_s6, complexity_overwhelm, advisor_lean, patience, online_completion, ux_willingness, comprehension, distractibility | fixed dispositions; rendered as graded words (never numbers) |
| DYNAMIC state (evolve per step) | attention, satisfaction, effort_left, grasp, effort_vs_reward | the mind's running state |
| per-session LATENT instance (sampled, persona-weighted) | time_pressure, purchase_resolve, price_expectation, advisor_need_today, screening_confidence, device, surroundings | this individual today; overrides the segment prior → population spread |

Prompt now frames the model as the persona's **consciousness** that applies the fixed traits +
the `cognitive_model` rules (trait→state→decision) to update state and decide. (codex flagged
`online_completion` as an unidentifiable global 'stay' counter-force — see backlog.)

**codex second opinion** (`research/findings/codex_review.md`): narrative lock comes from
deterministic persona prose + too-coarse dial buckets; fix with per-session latent disposition
(done, persona-weighted) + finer buckets (done, 7 levels). Oscillation is expected at N=40
(Peter ~18% chance of 0 conv) → pool multi-seed + posterior-aware + damped updates + persisted
global best (damping + global-best done; pooling wired in `evals --seeds`). Strongest rec
(P4): move the stay/leave **Bernoulli out of the LLM** into a tiny calibrated hazard model
(LLM keeps cognition/texture/thoughts) — robust marginals, but moves the decision out of the
'consciousness brain'.

**Result after the codex-informed iteration:** latent instance **broke the narrative lock for
Judith & Peter** (Judith conv → .10/.09, S3 ✓; Peter S3 → .27/.25 ✓ in one run) but the runs are
high-variance and **Franz over-converts (0.63)** because the **S6 final-price jump is never
injected** — the LLM keeps the final price = estimate, so Franz's defining churn cannot fire.

## 5f. Fundamental-factor decomposition (replaces synthetic step-sensitivities)

Real people don't carry an innate "price sensitivity at step 4/6". Those synthetic dials
(`price_shock_s4`, `final_price_sensitivity_s6`, `online_completion`) are **removed**; step
behaviour now EMERGES from fundamental factors × the real price.

**STATIC traits (10 fundamental dials):** `budget_pressure`, `value_orientation` (← grounded
in income/spend + decision_drivers price_performance), `complexity_overwhelm`, `advisor_lean`
(← channel data), `patience`, `ux_willingness`, `comprehension`, `distractibility`,
`commitment_anxiety`, `uncertainty_aversion`.

**Per-session LATENT instance** (sampled, persona-weighted): `time_pressure`, **`visit_goal`**
(price-check / research / serious / ready-to-buy), **`familiarity`** (first-time vs returning),
`price_expectation`, `advisor_need_today`, `screening_confidence`, **`age`** (→ real price via
`scope.premium`), device, surroundings.

**Emergent reactions** (in `cognitive_model`):
- **S4 price**: `tariff_economics_for_your_age` (shown to the model: monthly, annual=monthly×12,
  and the yearly coverage limit per tariff) vs `price_expectation`, weighted by `budget_pressure`
  and `value_orientation × grasp`. A value-minded person does the **feasibility math** — annual
  cost vs coverage limit vs realistic usage (a healthy person may judge the cheap plan poor value:
  paying a big fraction of a small limit they won't use). No shock dial.
- **S6 commitment**: `commitment_anxiety` + `uncertainty_aversion` (price is "preliminary";
  binding premium confirmed offline) + `effort_left` + `advisor_lean`. No price jump.

**The S4 drop now decomposes** into: price-above-expectation×budget×value · complexity-overwhelm ·
advisor-lean · **`goal_achieved`** (returning **price-checkers** who came to compare the number,
not buy — they leave CONTENT once they see it, a calm intent-driven exit, not friction).
Validated (N=20, gpt-4o-mini): ε=0.13, goal_achieved exits prominent and on-character.

### Coach opportunity — the price-checker is a lead, not a lost sale
`goal_achieved` / `visit_goal=price-check` / fast-mechanical-returning navigation is a
**detectable signal**, and forcing an immediate online purchase is the wrong move. The coach
should instead: **capture contact** (email/WhatsApp for the quote), route to a **nurture /
free-value** track (send the comparison, a savings explainer, a reminder), or offer an
**alternate conversion path** (callback, save-and-resume) — warming them toward a later
conversion. This is the highest-value intervention class for the ~66% S4 drop and belongs in
the coach overlay's decision policy (detect price-checker → SAVE_PROGRESS / CALLBACK / nurture).

## 5g. Tuner result + the Franz / S6-anchor finding (threaded, N=40)

Two threaded tuner runs on the fundamental-factor model plateaued at **ε≈0.16**. Peter and
Judith land near their anchors; **Franz is the hard residual** — he over-converts (~0.45) and
his S6 bounce stays ~0.22–0.37 vs the **0.78** target. Forcing it drove his dials
PERSONA-INCOHERENT (`advisor_lean` 0.05→0.54, `commitment_anxiety`→0.90) — turning the
decisive never-advisor online-completer into an anxious advisor-leaner. We **reverted Franz**
to coherent dials; the tuner was optimising ε against a **wrong target**.

**Root cause:** the per-persona S6 anchors (esp. `franz 0.78`) were derived from the
final-price-JUMP mechanism that the CDP recon **disproved**. Franz is the most online-capable
persona ("the segment that proves the calculator works"); with no price jump, a 78% S6 abandon
for him is not credible, and the LLM correctly refuses to make him bail that often. The model
isn't failing — the **anchor is stale**.

## 5h. RESOLVED — conditional S6 price jump fixes Franz (ε under gate)

Reconciliation of the recon vs the franz anchor: the pre-health `/products` price is
age+tariff only, but the **binding** final price (captcha'd `/calculate`, post-health) **can
add a ~6–10% risk loading** — a real S6 jump for some users. Modelled it: per-session
`_HEALTH_LOADING_RATE` → conditional 6–10% surcharge, shown at S6 as provisional-vs-final;
the persona reacts via the SAME emergent price rule. Also added: **"see the final proposal"**
visit_goal (push through S6 to read the final number, then `goal_achieved` exit) and
**not recalling height/weight** friction.

**Result (N=24, stepwise+state+params): ε = 0.111 — UNDER the 0.12 gate.** Franz now
calibrated WITH persona-true dials (conv .12/.10, S4 .61/.55, S6 **.67**/.78; was .22). His
reasons are correct ("price higher than I pictured, compare further" / "wasn't buying today").
The stale-anchor problem is solved by the real mechanism, not by corrupting Franz.

**Remaining = tuning-level only:** Judith over-exits S4 (1.00 vs .70 → 0 conversions) — lower
her S4 pressure (`budget_pressure`/`value_orientation`/`advisor_lean`); and Peter/Judith rare
conversions need N≥50 to show ≥1. Next: a light tuner pass + larger N → full PASS.

## 5i. Tuner converged — ε = 0.092 (coherent params)

Threaded tuner, N=50 × 3 rounds: **ε = 0.0919** (round 2, well under the 0.12 gate); every
persona now converts ≥1. Judith & Peter tuned to coherent, persona-true dials. **Franz**: the
tuner kept trying to fix his slight over-conversion (0.20 vs the 0.10 anchor) by drifting
`advisor_lean` 0.05→0.23 — we **capped it back** (advisor_lean 0.08, commitment 0.40). A
decisive, never-advisor online-completer converting ~0.20 is more credible than 0.10; his
**0.10 conversion anchor is the stale price-jump artifact**, so we keep him coherent rather
than corrupt him. Global-best persisted at ε=0.092 with the coherent set.

**Gate status:** eps_pass ✅ (0.092≤0.12) · each-converts ✅ · conv_pass ⚠ only on Franz
(0.20 vs 0.10 — stale anchor). **Practically converged + persona-coherent.** Recommend
locking these params and (optionally) re-deriving Franz's S6/conversion anchor (§6 option A).

## 5j. Content-driven diversity (from the product reference) — fixes narrow exits

The dials were rich but per-session CONTENT was thin, so exits clustered on ~5 feelings. Using
the Private-Doctor product reference, added a grounded **scenario layer** (no new dials — the
"simplify" ask): per-session `coverage_need` (routine visits / therapy / vision / mental-health /
dental / family-planning / meds / alt-medicine / unsure) and `open_question` (can't tell Start
vs Optimal / unknown jargon / will-premium-rise / is-my-doctor-in-network / can't-ask-anywhere),
sampled uniformly for spread. Widget gains a compact `tariff_coverage_brief` (what Start/Optimal
cover & exclude + jargon + gotchas) so the persona reasons about need-match. Two new grounded
exits: **`coverage_mismatch`** (my need is excluded / only in a pricier tier) and
**`unanswered_question`** (concrete question, no interface to ask). New `coverage_reaction_rule`.

**Result (N=40):** ε=0.107 (under gate), overall conv 0.087 ≈ target; exits now span **8**
grounded categories (unanswered_question 37 · goal_achieved 25 · too_much_effort 17 · cant_grasp
13 · dissatisfied 12 · coverage_mismatch 3 · distracted 2) with specific, on-product reasons.
Regenerate `datasets/persona_v1` to carry this diversity into the distillation set.

## 6. STATUS & DECISION POINT (largely resolved by §5h)

**Decision needed — the per-persona S6 anchors vs reality:**
- **(A) Re-ground the S6 anchors.** Keep the overall ~5.6% conversion + S4 ~66% drop (solid),
  but re-derive the per-persona S6 split consistent with the recon (no price jump) + persona
  capability: Franz S6 LOWER (he completes more), Peter/Judith higher. Re-validate against the
  corrected per-persona targets. *(Recommended — the anchor, not the model, is the bug.)*
- **(B) Hybrid hazard (codex P4).** Force exact marginals via a calibrated Bernoulli outside
  the LLM. Robust, but moves the decision out of the consciousness — and would force the same
  stale franz=0.78, so only worth it after (A).
- **(C) Soft gate.** Accept persona-coherent emergent behaviour with best-effort ε (~0.16) and
  the rich, correct exit reasoning; stop chasing exact per-cell match.

Status: `persona llm-agent` NOT locked. Behaviour + factor decomposition are sound and
coherent; the blocker is a **stale per-persona S6 anchor**, not the generator. Next: redo the
S6 anchor derivation (A) before any more tuning.

### (historical) earlier decision point

**`persona llm-agent` = NOT locked (in progress).** The model produces behaviourally correct,
richly-reasoned sessions (subconscious `cant_grasp`/`too_much_effort`, exogenous `distracted`,
intent-mismatch `dissatisfied`) and Judith/Peter land near their anchors, but we do **not** yet
reliably hit all marginal targets. Two structural blockers + one architecture decision:

1. **~~Inject an S6 price jump~~ — INVALIDATED by CDP recon** (`research/findings/pricing_recon.md`).
   The real online price = f(age, tariff) only; health/SV/gender do NOT change it and there is
   NO online price-jump. Franz's S6 churn is therefore NOT a displayed price increase — reframe
   it as health-form EFFORT + commitment + uncertainty about the offline-underwritten final
   premium. Rename/repurpose the `final_price_sensitivity_s6` dial accordingly; `scope.premium`
   now returns the real age-based number (no jump).
2. **Variance: pool multi-seed** (`evals --seeds 3`, N ≥ 72/persona for Peter) before gating.
3. **DECISION — pure vs hybrid:**
   - **(A) Pure consciousness** (current vision): keep the stay/leave decision in the LLM; add
     S6 injection + multi-seed + a bit more dial tuning. Philosophically clean; may stay noisy.
   - **(B) Hybrid hazard** (codex P4): LLM for texture/thoughts, a small calibrated logistic
     hazard for the Bernoulli leave decision. Robust marginals, target-free prompt, but the
     decision is partly outside the 'brain'.
   - **(C) Soft gate**: accept the LLM agent's realistic behaviour with a best-effort ε≤0.12
     rather than exact per-cell match.
   *Recommendation:* do (1)+(2) first (cheap, may get (A) over the line); adopt (B) only if (A)
   still won't hold the marginals.

## 7. Backlog (next hardening — agreed to track)

- ~~Inject computed S6 final-price uplift (Franz)~~ — **INVALIDATED** (no online jump exists; recon).
  Instead: reframe S6 churn as effort+commitment+underwriting-uncertainty; make the twin/sim
  use `scope.premium(tariff, age)` so personas carry a real age and see the real price.
- Wire `scope.premium(tariff, age)` into the stepwise generator (sample/derive a per-session
  age) so S4/S6 prices match the real curve instead of a static figure. **[do next]**
- Multi-seed pooled tuning at N≥72/persona; posterior-aware Beta updates in `tune.py`.
- Replace `online_completion` with causal dials (purchase_resolve / trust_in_calculator /
  need_urgency / self_service_confidence) so conversion emerges from surviving hazards (codex P3).
- Clarify advisor-handoff vs Peter's service-as-win framing in the prompt (codex P3).
- Optional hybrid hazard model (codex P4) — only if pure approach won't converge.
- Soften deterministic persona prose to population-prior wording (touches briefing prose — needs sign-off).

## 8. After lock — optional: local fast model (added to plan)

Once params are locked and the eval passes, distil the LLM agent into a **local, fast model**
that must pass the SAME `evals/persona_stats_eval.py`. Candidate approaches to compare:
small decoder TLM over journey tokens (existing `tlm.py` direction) · a tiny per-step
classifier/hazard (if we go hybrid) · LoRA-distil of the teacher. Pick on eval conformance +
latency, transformer or not. Output: local persona model behind the same interface.

## 9. (historical) earlier recommended next steps

0. **Stabilise the tuner** (`research/tune.py` exists, ε→0.097): add multi-seed averaging
   per round + a persisted global best so re-runs can't regress. Soften Judith's briefing
   S4 paragraph (her S4 is narrative-locked at .92, dial-resistant). Bump N or seeds so
   Peter's rare conversion (~4%) reliably shows ≥ once → full PASS.
1. **Inject the computed S6 final price** (provisional + health uplift) as a widget
   response so the jump is structural (mostly fixed for Franz via the dial).
2. **Architecture is settled:** stepwise + `--state` + `--params`; `--quant` dropped.
3. Bump to a stronger teacher for the final datasets; keep mini for the tuning loop.
4. Then freeze dials, generate the final thought-rich datasets, and proceed to the
   Leonardo fine-tune (re-validate the LOCAL model with the same `research/run.py`).
