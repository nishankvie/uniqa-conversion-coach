# Parameter-driven persona model — diagnosis + proposal

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

## 6. Recommended next steps

1. Implement the per-step generator (§4) behind `--stepwise`; keep whole-session for
   cheap smoke tests.
2. Add `sample_disposition` + `price_vs_hoped` (dial-derived).
3. Re-run iter-2; expect S4 bounce to move off 0. Then run the coordinate-descent tuner
   (§5) to convergence (ε ≤ 0.12, each persona converts ≥ once).
4. Bump to a stronger teacher for the final datasets; keep mini for the tuning loop.
5. Only then freeze dials, generate the final thought-rich datasets, and proceed to the
   Leonardo fine-tune (then re-validate the LOCAL model with the same `research/run.py`).
