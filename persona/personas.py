"""
UNIQA Persona Bots

Two implementations:
  RuleBasedPersona  — fast, deterministic, seeded. Used for 1k-run stats simulation.
  LLMPersona        — GPT-4 powered, uses full persona .md as system prompt.
                      Used for 3 scripted demo scenarios in Streamlit.

Annoyance tracking: persona has an internal annoyance scalar [0,1].
High annoyance → persona LESS likely to respond positively to Coach interventions.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from calculator.funnel import (
    Step, FunnelState, HesitationSignals,
    STEP_ORDER, ABANDON_PROBS, PERSONA_WEIGHTS,
    generate_signals, is_hesitating, next_step,
)
from coach.coach import (
    CoachAction, decide_action, get_modifier, get_widget_copy,
    validate_output,
)

# Paths to persona briefing files (used as LLM system prompts)
_TRACK_DIR = Path("/tmp/zero_one_hack_01/tracks/insurance-uniqa")
PERSONA_BRIEFINGS: dict[str, Path] = {
    "judith": _TRACK_DIR / "persona_judith_segment_1.md",
    "franz":  _TRACK_DIR / "persona_franz_segment_2.md",
    "peter":  _TRACK_DIR / "persona_peter_segment_3.md",
}


# ─── Session Result ───────────────────────────────────────────────────────────

@dataclass
class SessionResult:
    persona:         str
    converted:       bool
    abandoned_at:    Optional[Step]
    steps_reached:   list[Step]
    coach_actions:   list[tuple[Step, CoachAction]]
    message_count:   int
    annoyance_peak:  float         # max annoyance observed
    whatsapp_sent:   bool = False  # Peter WA re-engagement


# ─── Rule-Based Persona (stats path) ─────────────────────────────────────────

class RuleBasedPersona:
    """
    Deterministic persona for high-speed simulation.
    Uses per-step abandon probability tables from personas.json survey data.
    No LLM calls — runs 10k sessions in seconds.
    """

    def __init__(self, persona: str, rng: random.Random):
        self.persona  = persona
        self.rng      = rng
        self.annoyance = 0.0

    def will_abandon(self, step: Step, coach_action: CoachAction) -> bool:
        """Roll against (base_prob × coach_modifier). True = abandons."""
        base = ABANDON_PROBS[self.persona].get(step, 0.0)
        mod  = get_modifier(coach_action, self.persona, step)
        effective = base * mod
        abandoned = self.rng.random() < effective

        # Track annoyance (redundant Coach interventions raise annoyance)
        if coach_action != CoachAction.NONE:
            self.annoyance = min(1.0, self.annoyance + 0.05)
        return abandoned

    def generate_signals(self, step: Step) -> HesitationSignals:
        return generate_signals(step, self.persona, self.rng)


# ─── LLM Persona (demo path) ─────────────────────────────────────────────────

class LLMPersona:
    """
    GPT-4-powered persona bot.
    Uses full persona .md as system prompt.
    Used only for the 3 scripted demo scenarios — not in stats simulation.
    """

    REACT_PROMPT = """You are acting as the persona described above.
You are currently in step: {step}
You just received this Coach intervention: {widget}

Respond with a JSON object:
{{
  "reaction": "positive" | "neutral" | "negative",
  "annoyance_delta": 0.0 to 0.3,
  "next_action": "continue" | "abandon" | "ask_question",
  "internal_thought": "one sentence from persona's perspective"
}}
Only output the JSON. No extra text."""

    def __init__(self, persona: str, openai_client=None):
        self.persona   = persona
        self.client    = openai_client
        self.history:  list[dict] = []
        self.annoyance = 0.0

        brief_path = PERSONA_BRIEFINGS.get(persona)
        self.system_prompt = (
            brief_path.read_text(encoding="utf-8")
            if brief_path and brief_path.exists()
            else f"You are {persona}, a health insurance customer."
        )

    def react(self, step: Step, action: CoachAction) -> dict:
        """React to a Coach action. Returns reaction dict."""
        if self.client is None:
            # Offline fallback — rule-based approximation
            return self._offline_react(step, action)

        widget = get_widget_copy(action, self.persona)
        widget_str = json.dumps(widget, ensure_ascii=False)

        messages = [
            {"role": "system", "content": self.system_prompt},
            *self.history,
            {"role": "user", "content": self.REACT_PROMPT.format(
                step=step.value, widget=widget_str
            )},
        ]

        try:
            resp = self.client.chat.completions.create(
                model="gpt-4o-mini",   # cost-efficient for demo
                messages=messages,
                temperature=0.7,
                max_tokens=200,
                response_format={"type": "json_object"},
            )
            result = json.loads(resp.choices[0].message.content)
            self.history.append({"role": "assistant", "content": resp.choices[0].message.content})

            # Update annoyance
            self.annoyance = min(1.0, self.annoyance + result.get("annoyance_delta", 0.0))
            return result

        except Exception as e:
            return self._offline_react(step, action)

    def _offline_react(self, step: Step, action: CoachAction) -> dict:
        """Rule-based approximation when OpenAI is unavailable."""
        modifier = get_modifier(action, self.persona, step)
        # modifier < 1 = good intervention = positive reaction
        reaction = (
            "positive" if modifier < 0.80 else
            "neutral"  if modifier < 0.95 else
            "negative"
        )
        return {
            "reaction":        reaction,
            "annoyance_delta": 0.0 if reaction == "positive" else 0.1,
            "next_action":     "continue" if reaction in ("positive", "neutral") else "abandon",
            "internal_thought": f"[{self.persona}] reacts {reaction} to {action.value}",
        }


# ─── Session Runner ───────────────────────────────────────────────────────────

def run_session(
    persona: str,
    rng: random.Random,
    coach_on: bool,
    persona_impl: Optional[RuleBasedPersona] = None,
) -> SessionResult:
    """
    Run one full funnel session for a persona.
    Returns SessionResult with conversion outcome.
    """
    pb = persona_impl or RuleBasedPersona(persona, rng)
    message_count = 0
    coach_actions: list[tuple[Step, CoachAction]] = []
    steps_reached: list[Step] = [Step.START]

    for step in STEP_ORDER[1:]:   # skip START
        steps_reached.append(step)

        if step == Step.PURCHASE:
            return SessionResult(
                persona=persona,
                converted=True,
                abandoned_at=None,
                steps_reached=steps_reached,
                coach_actions=coach_actions,
                message_count=message_count,
                annoyance_peak=pb.annoyance,
            )

        # Generate behavioral signals for this step
        signals = pb.generate_signals(step)
        state   = FunnelState(step=step, persona=persona, signals=signals)

        # Coach decision
        action = CoachAction.NONE
        if coach_on and is_hesitating(signals, persona):
            action = decide_action(state, message_count=message_count)
            if action != CoachAction.NONE:
                message_count += 1
                pb.annoyance = min(1.0, pb.annoyance + 0.03)  # slight annoyance per intervention

        coach_actions.append((step, action))

        # Abandon roll
        if pb.will_abandon(step, action):
            # Peter special: WA re-engagement if abandoned after callback offer
            whatsapp = (
                persona == "peter" and
                any(a == CoachAction.CALLBACK_OFFER for _, a in coach_actions)
            )
            return SessionResult(
                persona=persona,
                converted=False,
                abandoned_at=step,
                steps_reached=steps_reached,
                coach_actions=coach_actions,
                message_count=message_count,
                annoyance_peak=pb.annoyance,
                whatsapp_sent=whatsapp,
            )

    # Should not reach here (PURCHASE step handles terminal state)
    return SessionResult(
        persona=persona, converted=False, abandoned_at=Step.PURCHASE,
        steps_reached=steps_reached, coach_actions=coach_actions,
        message_count=message_count, annoyance_peak=pb.annoyance,
    )
