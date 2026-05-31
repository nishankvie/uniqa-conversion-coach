"""
Coach-in-the-loop for the stepwise persona simulator (Mode B = persona+widget+coach).

Each step, AFTER the persona acts, the coach observes the new events/feeling/state and decides
whether to intervene; the chosen intervention's `persona_facing` text is injected into the
persona's NEXT step so the persona reacts to it and assesses it (helpful vs noisy).

`ReactiveCoach` is the v0 policy: a feeling/state-driven rule mapper over the intervention
catalog, with persona priorities, hard gates (Franz never advisor), and the ≤3 annoyance
budget. It implements the same `decide(...)` interface a trained coach-model will later expose,
so the cohort loop is policy-agnostic.
"""
from __future__ import annotations

from calculator.funnel import Step
from coach.interventions import CATALOG, NONE_ID, is_apt


# feeling (persona's self-reported state) → ordered candidate interventions
_FEELING_PLAYBOOK: dict[str, list[str]] = {
    "cant_grasp":          ["package_nuance", "coverage_explain", "quick_quiz"],
    "too_much_effort":     ["form_simplify", "form_helper", "quick_quiz", "preselect_optimal"],
    "dissatisfied":        ["value_justification", "price_reframe", "pricing_explain", "upgrade_explain"],
    "unanswered_question": ["coverage_checker", "whatsapp_bot", "package_nuance"],
    "coverage_mismatch":   ["coverage_explain", "package_nuance", "coverage_checker"],
    "distracted":          ["save_progress", "email_capture"],
}

# per-persona overrides applied BEFORE the generic playbook (strategy / hard gates)
_PERSONA_PRIORITY = {
    # Peter: route to a human channel early, before the price wall
    "peter": {Step.COVERAGE_TYPE: ["callback_offer", "whatsapp_bot"],
              # form-averse → "leave email/phone, we take it from here" (skips the forms = his conversion)
              Step.PERSONAL_INFO: ["contact_handoff", "callback_offer", "whatsapp_bot"],
              Step.PERSONAL_DATA: ["contact_handoff", "callback_offer"]},
    # Judith: graceful advisor option / lower stakes at the final price
    "judith": {Step.PERSONAL_DATA: ["advisor_handoff", "social_proof"],
               Step.TARIFF_SELECT: ["upgrade_path", "social_proof"]},
    # Franz: NEVER advisor/callback — keep him online; clear the Premium confusion
    "franz": {Step.TARIFF_SELECT: ["upgrade_explain", "package_nuance", "price_reframe"]},
}

# Franz must never be handed to a human (hard constraint from the brief)
_FORBIDDEN = {"franz": {"advisor_handoff", "callback_offer", "whatsapp_bot"}}


class ReactiveCoach:
    name = "reactive-rule"

    def __init__(self, budget: int = 3):
        self.budget = budget

    def decide(self, *, persona: str, step: Step, feeling: str | None,
               state: dict, budget_used: int, last_intervention: str | None,
               hesitation: float = 0.0) -> str:
        """Return an intervention id from the catalog, or NONE_ID for no-op."""
        if budget_used >= self.budget:
            return NONE_ID

        candidates: list[str] = []
        # BIG-FORM pre-emptive nudge: the moment a long form (S3/S6) is hit with high hesitation,
        # explain WHY the form is needed BEFORE the user bails (don't let the form scare them off).
        # big form: Peter SKIPS it (contact_handoff, from his persona priority below); everyone
        # else gets a pre-emptive explainer to help them fill it.
        if step in (Step.PERSONAL_INFO, Step.PERSONAL_DATA) and persona != "peter" and (
                hesitation >= 0.5 or feeling == "too_much_effort"):
            candidates.append("form_explainer")
        # add-on step: defuse the optional-upsell cost bump
        if step is Step.ADDON_SELECT:
            candidates.append("addon_skip_ok")
        # 1) persona-specific priority for this step
        pr = _PERSONA_PRIORITY.get(persona, {}).get(step)
        if pr:
            candidates += pr
        # 2) feeling-driven playbook
        if feeling and feeling in _FEELING_PLAYBOOK:
            candidates += _FEELING_PLAYBOOK[feeling]
        # 3) mild generic nudge if the persona is fading but hasn't named a feeling
        if not candidates:
            if state.get("satisfaction", 1.0) < 0.45 or state.get("effort_vs_reward", 1.0) < 0.4:
                candidates += ["trust_signal", "price_reframe"]

        forbidden = _FORBIDDEN.get(persona, set())
        for cid in candidates:
            if cid in forbidden:
                continue
            if cid == last_intervention:          # don't repeat the same widget back-to-back
                continue
            if cid in CATALOG and is_apt(cid, step, persona):
                return cid
        return NONE_ID
