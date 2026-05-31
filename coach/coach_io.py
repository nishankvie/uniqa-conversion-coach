"""
UNIQA Coach — I/O adapter + baseline Coach model.

Proves the `contracts.py` wire format end-to-end IN SIMULATION:

  psyche signals ──▶ ActivityLog (what the APP would emit)
  ActivityLog    ──▶ CoachObservation (what the COACH sees — no latent ground truth)
  CoachModel.decide(obs) ──▶ CoachDecision (effector cmd + reasoning + hypotheses)
  CoachDecision  ──▶ CoachAction intent (feeds the existing psyche effect model)

The baseline `RuleCoachModel` is a stand-in for the trainable policy: same I/O
contract a learned model will satisfy. Swap the body for a neural policy later;
the rest of the system does not change.
"""

from __future__ import annotations

import random
from typing import Optional

from calculator.funnel import Step, HesitationSignals
from coach.coach import CoachAction, MESSAGE_BUDGET
from calculator.contracts import (
    Event, EventType, ActivityLog, Effector, EffectorCommand,
    Hypothesis, HypoStatus, CoachObservation, CoachDecision, new_session_id,
)


# ── intent → effector mapping (which mechanical capability realises the intent) ──
INTENT_EFFECTOR: dict[CoachAction, Effector] = {
    CoachAction.NONE:              Effector.NO_ACTION,
    CoachAction.FORM_HELPER:       Effector.FOCUS_FIELD,    # + widget hint
    CoachAction.PROGRESS_SAVER:    Effector.SAVE_PROGRESS,
    # everything else is delivered as an overlay widget
}
def _effector_for(intent: CoachAction) -> Effector:
    return INTENT_EFFECTOR.get(intent, Effector.SHOW_WIDGET)


# ════════════════════════════════════════════════════════════════════════════
#  APP side: synthesise an activity log from psyche signals (simulation only)
# ════════════════════════════════════════════════════════════════════════════

def activity_from_signals(log: ActivityLog, step: Step, signals: HesitationSignals,
                          t0: float = 0.0) -> float:
    """Translate a step's HesitationSignals into the events the APP would emit."""
    t = t0
    log.append(Event(EventType.STEP_ENTER, step.value, t)); t += 0.2
    if signals.dwell_time_sec:
        log.append(Event(EventType.IDLE, step.value, t, value=round(signals.dwell_time_sec, 1)))
        t += signals.dwell_time_sec
    for _ in range(signals.price_hover_count):
        log.append(Event(EventType.PRICE_HOVER, step.value, t, target="price")); t += 0.4
    for _ in range(signals.form_reedits):
        log.append(Event(EventType.FIELD_EDIT, step.value, t, target="sv_number")); t += 0.5
    for _ in range(signals.backward_nav_count):
        log.append(Event(EventType.NAV_BACK, step.value, t)); t += 0.3
    for _ in range(signals.cancel_hover_count):
        log.append(Event(EventType.CANCEL_HOVER, step.value, t, target="cancel")); t += 0.3
    if signals.premium_click:
        log.append(Event(EventType.PREMIUM_CLICK, step.value, t, target="premium_tariff")); t += 0.3
    if signals.session_gap_spike:
        log.append(Event(EventType.SESSION_GAP, step.value, t, value=True)); t += 1.0
    return t


def observation_from_log(log: ActivityLog, step: Step, budget_remaining: int,
                         form_state: Optional[dict] = None) -> CoachObservation:
    return CoachObservation(
        session_id=log.session_id,
        step=step.value,
        activity=[e.to_dict() for e in log.window(step=step.value)],
        form_state=form_state or {},
        budget_remaining=budget_remaining,
    )


# ════════════════════════════════════════════════════════════════════════════
#  COACH side: baseline model satisfying the trainable contract
# ════════════════════════════════════════════════════════════════════════════

# behavioral signal → (hypothesis claim, latent axis, predicted bounce event, counter intent)
_HYPO_RULES = [
    # (trigger_fn(summary, step), id, claim, latent, predicts, counter)
]


class RuleCoachModel:
    """
    Baseline Coach policy. Same I/O as a future learned model:
        decide(CoachObservation) -> CoachDecision
    Reads ONLY the activity log + step + budget (never latent persona/intent).
    Forms falsifiable hypotheses, then issues one effector command.
    """

    name = "rule_coach_v1"

    def decide(self, obs: CoachObservation) -> CoachDecision:
        s = self._summarise(obs.activity)
        step = obs.step

        # budget gate → NO_ACTION (the most important capability)
        if obs.budget_remaining <= 0:
            return self._no_action(step, "Annoyance budget exhausted — staying silent.")

        hypos = self._hypotheses(s, step)
        if not hypos:
            return self._no_action(step, "No hesitation signal above threshold — no intervention.")

        top = max(hypos, key=lambda h: h.p)
        intent = CoachAction(top.counters)
        eff = _effector_for(intent)

        target = None
        payload = {"intent": intent.value}
        if eff is Effector.FOCUS_FIELD:
            target = "sv_number"; payload["hint"] = "SV-Nr top-right on your e-card"
        elif eff is Effector.SHOW_WIDGET:
            payload["widget"] = intent.value

        cmd = EffectorCommand(effector=eff, step=step, target=target, payload=payload,
                              render={"kind": "coach_widget", "intent": intent.value})
        cmd.validate()
        reasoning = (f"{top.claim} (p={top.p:.2f}) at {step} → {intent.value} via {eff.value}. "
                     f"Signals: {s}.")
        return CoachDecision(command=cmd, reasoning=reasoning, hypotheses=hypos,
                             confidence=top.p, value_estimate=min(0.95, 0.3 + top.p * 0.5))

    # ── helpers ──
    def _summarise(self, activity: list[dict]) -> dict:
        kinds = [e["type"] for e in activity]
        idle = max([e.get("value") or 0 for e in activity if e["type"] == "idle"] or [0])
        return {
            "idle": float(idle),
            "price_hover": kinds.count("price_hover"),
            "reedits":     kinds.count("field_edit"),
            "nav_back":    kinds.count("nav_back"),
            "cancel_hover": kinds.count("cancel_hover"),
            "premium_click": "premium_click" in kinds,
            "session_gap":   "session_gap" in kinds,
        }

    def _hypotheses(self, s: dict, step: str) -> list[Hypothesis]:
        h: list[Hypothesis] = []
        if s["premium_click"]:
            h.append(Hypothesis("h_premium", "user wants an advisory-only tariff",
                                "comprehension", 0.8, EventType.NAV_BACK,
                                CoachAction.UPGRADE_EXPLAIN.value))
        if s["price_hover"] >= 2 or (step == Step.TARIFF_SELECT.value and s["idle"] >= 8):
            h.append(Hypothesis("h_price", "user is price-shocked",
                                "price_readiness", 0.7, EventType.ABANDON,
                                CoachAction.PRICE_REFRAME.value))
        if step == Step.PERSONAL_DATA.value and s["cancel_hover"] >= 2:
            h.append(Hypothesis("h_pricedelta", "final price exceeded the estimate",
                                "price_readiness", 0.72, EventType.ABANDON,
                                CoachAction.HEALTH_EXPLAIN.value))
        if s["reedits"] >= 2:
            h.append(Hypothesis("h_form", "user struggles with the form (SV-Nr)",
                                "effort_budget", 0.6, EventType.ABANDON,
                                CoachAction.FORM_HELPER.value))
        if s["session_gap"]:
            h.append(Hypothesis("h_gap", "attention left the session",
                                "attention", 0.55, EventType.ABANDON,
                                CoachAction.PROGRESS_SAVER.value))
        return h

    def _no_action(self, step: str, why: str) -> CoachDecision:
        return CoachDecision(
            command=EffectorCommand(Effector.NO_ACTION, step,
                                    render={"kind": "effector", "effector": "no_action"}),
            reasoning=why, hypotheses=[], confidence=1.0, value_estimate=0.0)


# ════════════════════════════════════════════════════════════════════════════
#  Hypothesis scoring  (the bridge to persona-model re-fitting, online loop)
# ════════════════════════════════════════════════════════════════════════════

def score_hypotheses(decision: CoachDecision, subsequent: list[Event]) -> dict:
    """
    After the journey continues, mark each hypothesis confirmed/refuted. The hit
    rate is the signal that (a) grades the coach's user-model and (b) feeds the
    persona-model re-fit in the online loop.
    """
    out = {"confirmed": 0, "refuted": 0, "open": 0}
    for h in decision.hypotheses:
        st = h.evaluate(subsequent)
        out[st.value] += 1
    return out
