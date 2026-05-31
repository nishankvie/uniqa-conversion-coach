You are a 200-IQ ML/simulation engineer giving a focused second opinion. READ these files in this repo (read-only):
- research/PERSONA_PARAM_MODEL.md  (full diagnosis + results so far)
- persona/persona_datagen.py     (the stepwise generator: build_step_decision_prompt, _session_stepwise, params_block, _COGNITIVE_MODEL)
- prompts/personas/judith.md, judith.params.json (and franz/peter)
- calculator/funnel.py (ABANDON_PROBS = eval targets; PERSONA_WEIGHTS 30/50/20)
- research/run.py (validate(): per-(persona,step) conditional bounce vs ABANDON_PROBS; ε = mean abs diff)

GOAL: generate synthetic persona sessions (LLM, gpt-4o-mini) whose EMERGENT funnel stats match anchors
WITHOUT encoding targets in the prompt. Anchors (eval-only): per-persona conditional bounce at S3/S4/S6
(e.g. judith .05/.70/.68, franz .04/.55/.78, peter .25/.80/.72) and overall conversion ~5.6% over a
30/50/20 persona mix. We tune persona "dials" (static traits, rendered as graded words, never numbers)
and the model tracks dynamic mental state per step, choosing engaged/distracted/cant_grasp/too_much_effort/
dissatisfied + stay/leave.

WHERE WE'RE STUCK (after many runs):
1. Judith S4 bounce is "narrative-locked" at ~0.90-1.00 vs target 0.70 — lowering her price_shock_s4 to 0.28
   and advisor_lean does NOT move it. Her persona .md says she slows at the price screen and often leaves.
   The model treats S4 as a near-certain exit for her regardless of dials.
2. Peter S3 over-exits (~0.5-0.7 vs target 0.25) — too overwhelmed too early.
3. Coordinate-descent tuner OSCILLATES ±0.05-0.10 ε at N=40 (seeds give 0.097, 0.16, 0.17, 0.20). Best
   we hit is ε=0.097 once (gate 0.12) but can't hold it; full PASS also needs each persona to convert >=1
   (Peter ~4% target → often draws 0 at N=40).

QUESTIONS (be concrete, prioritized, implementable):
a) How do we break the per-persona "narrative lock" so a step's bounce probability matches a target rate
   ACROSS a population, when each LLM session is a single near-deterministic narrative? Is per-session
   latent "disposition sampling" (jitter dials per session) the right fix, or something better?
b) How to kill the tuner oscillation — multi-seed averaging? larger N? a smoothed/again Bayesian update
   instead of error-proportional coordinate descent? a different objective than per-cell ε?
c) Is the static-trait vs dynamic-state taxonomy sound, or is online_completion (a "stay" dial that fights
   the leave dials) causing the oscillation? Should conversion emerge purely from leave-pressures?
d) Anything fundamentally wrong with using an LLM per-step stay/leave decision to hit a target marginal
   bounce distribution? Would a hybrid (LLM for event/thought texture, a tiny per-step Bernoulli whose
   logit is a tuned linear fn of state, for the leave decision) be more correct AND still target-free?
Keep it tight and actionable.

═══════════════════════════════════════════════════════════════════════════
CODEX RESPONSE (read-only consult, gpt high reasoning):
═══════════════════════════════════════════════════════════════════════════
P1 BREAK NARRATIVE LOCK: persona prose is deterministic ("you close the tab") and dials
are appended as coarse 5-level graded text → model treats archetype > dials; moving a dial
within a bucket is invisible. Fix: (a) soften persona .md from deterministic path to
POPULATION PRIOR ("some sessions end here; others continue if price feels explainable");
(b) add a per-session SESSION INSTANCE sampled above/after the prose (time_pressure,
purchase_resolve, price_expectation, advisor_need_today, screening_confidence) with
precedence "instance wins over segment prior when they conflict". Gives spread, no leakage.

P2 KILL OSCILLATION: N=40 too small (Peter 4.2% conv → ~18% chance of 0). Tune on POOLED
multi-seed counts (sum reach/bounce/convert across ≥3 seeds, then compute rates — never
average rounded rates). Posterior-aware Beta(1+bounce,1+reach-bounce); update only if target
outside credible interval, scale by reach. Damping k=0.15–0.25; require same-sign error two
rounds; persist GLOBAL best across runs. Final gate N≥120/persona (Peter needs ~72 for ≥95%
chance of ≥1 conversion).

P3 DIAL IDENTIFIABILITY: online_completion is a bad global "stay" dial fighting every leave
dial → unidentifiable (many param sets explain same data). Replace with causal dials
(purchase_resolve, trust_in_calculator, need_urgency, self_service_confidence); conversion
emerges from surviving hazards. advisor_lean should bias reason/channel, not mean "leave";
Peter conflict: prompt says advisor handoff=online abandon while his briefing frames service
as his win — clarify.

P4 HYBRID DECISION MODEL (most robust): keep LLM for cognition/texture/thoughts, but compute
p_leave OUTSIDE the LLM via a small logistic hazard: logit = step_base + trait·pressures +
state_weights·state + context; sample Bernoulli; LLM narrates the reason. Targets fit only
the tiny hazard model, never the prompt. NOTE: this moves the decision out of the
"consciousness brain" — a tradeoff vs the stated vision; user decision.
