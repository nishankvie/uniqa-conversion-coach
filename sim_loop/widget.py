"""Widget = deterministic funnel state machine + screen renderer.

It is NOT an LLM. It renders the per-step screen the persona perceives (reusing the
canonical screen templates extracted from datasets/persona_v2), injects any coach
intervention, and advances the funnel.
"""
from __future__ import annotations
import json, pathlib

HERE = pathlib.Path(__file__).resolve().parent
TEMPLATES = json.loads((HERE / "step_templates.json").read_text(encoding="utf-8"))
STEP_ORDER = ["S1_COVERAGE_TYPE", "S2_INSURED_PERSONS", "S3_PERSONAL_INFO",
              "S4_TARIFF_SELECT", "S5_ADDON_SELECT", "S6_PERSONAL_DATA",
              "S7_HEALTH_QUESTIONS", "S8_REVIEW_PURCHASE"]


def first_step() -> str:
    return STEP_ORDER[0]


def next_step(step: str):
    i = STEP_ORDER.index(step)
    return STEP_ORDER[i + 1] if i + 1 < len(STEP_ORDER) else None


def render(step: str, running_state: dict, history_brief: list,
           session_instance: dict, initial_intent: str,
           coach_injection: dict | None = None) -> dict:
    """Build the user-turn screen JSON the persona model receives."""
    tpl = TEMPLATES[step]
    screen = json.loads(json.dumps(tpl))  # deep copy
    screen["your_running_state"] = running_state
    screen["history_brief"] = history_brief
    screen["session_instance"] = session_instance
    screen["your_initial_intent"] = initial_intent
    if coach_injection:
        # a coach surface is shown on this screen; persona may engage or dismiss it
        screen["coach_intervention_shown"] = {
            "surface": coach_injection.get("surface", "on_page"),
            "title": coach_injection.get("title", ""),
            "message": coach_injection.get("message", ""),
            "cta": coach_injection.get("cta", ""),
            "intent": coach_injection.get("effector", ""),
            "category": coach_injection.get("category"),
        }
        asp = screen.get("action_space", {})
        legal = asp.get("legal_event_types", [])
        for ev in ("widget_cta", "widget_dismiss"):
            if ev not in legal:
                legal.append(ev)
        asp["legal_event_types"] = legal
        osch = screen.get("output_schema")
        if isinstance(osch, dict):
            osch["intervention_assessment"] = {
                "engaged": "<true if you USE the helper (also emit a widget_cta event) / false if you "
                           "ignore it (emit widget_dismiss)>",
                "reaction": "helpful | engaging | neutral | distracting | annoying",
                "effect": "<short: did it change your state / decision, and how>",
            }
        screen.setdefault("rules", []).append(
            "A COACH HELPER is on this screen now (`coach_intervention_shown`: intent + title + "
            "message). It does NOT change the funnel — but judge it HONESTLY against the pain you "
            "feel on THIS screen and decide its effect on YOU:\n"
            "• If it directly addresses what is making you hesitate RIGHT NOW — a price you find too "
            "high → a price reframe / breakdown; a long scary form → a 'why + it's short' explainer or "
            "a simplify/skip option; a confusing term → a plain explanation; an unanswered worry → a "
            "checker/FAQ — then it GENUINELY HELPS: emit `widget_cta`, RAISE the relevant state "
            "var(s) (satisfaction / effort_vs_reward / grasp / effort_left) by ~0.15–0.35, and it can "
            "turn a would-be 'leave' into 'continue'. Don't pretend help you didn't need.\n"
            "• If you are SERVICE-AFFINE / overwhelmed and it offers a human path (callback, WhatsApp, "
            "'leave your number and we take it from here', advisor) and you wanted that — TAKE IT: "
            "emit `widget_cta` and set decision 'leave' with a reason that NAMES the callback / "
            "advisor / WhatsApp. That is your PREFERRED outcome (a service contact), NOT a frustrated abandon.\n"
            "• If it is irrelevant, mistimed, pushy, or you didn't need it: emit `widget_dismiss`, "
            "optionally lower attention/satisfaction slightly, and decide as you would have anyway.\n"
            "Fill `intervention_assessment` {reaction, engaged, effect} and let a GOOD, well-timed "
            "match move your decision — a mismatch must NOT save you.")
    return screen
