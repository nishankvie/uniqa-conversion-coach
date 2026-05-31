"""LLM persona — system prompt set once at session start, mental state threaded
turn to turn. Emits events + decision + new state + feeling each step; terminates
by emitting decision == "leave" (or by converting at the end of the funnel)."""
from __future__ import annotations
import json
from llm import chat, extract_json
from persona_prompt import build_system_prompt

STATE_KEYS = ["attention", "satisfaction", "effort_left", "grasp", "effort_vs_reward"]


class LLMPersona:
    def __init__(self, seg: str, session_instance: dict, start_state: dict,
                 model: str | None = None, temperature: float = 0.8):
        self.seg = seg
        self.session_instance = session_instance
        self.system = build_system_prompt(seg, session_instance)
        self.state = dict(start_state)
        self.history_brief: list[str] = []
        self.model = model
        self.temperature = temperature
        self.initial_intent = session_instance.get("visit_goal", "researching")

    def step(self, screen: dict) -> dict:
        """screen = widget.render(...) user content. Returns parsed persona output."""
        user = json.dumps(screen, ensure_ascii=False)
        default = {"events": [], "decision": "leave", "state": dict(self.state),
                   "feeling": "distracted", "reason": "unparseable",
                   "intent": self.initial_intent}
        try:
            raw = chat([{"role": "system", "content": self.system},
                        {"role": "user", "content": user}],
                       model=self.model, temperature=self.temperature, max_tokens=900)
            out = extract_json(raw)
            if not isinstance(out, dict):
                out = dict(default)
        except Exception:
            out = dict(default)
        # normalize fields defensively
        if not isinstance(out.get("events"), list):
            out["events"] = []
        if out.get("decision") not in ("continue", "leave"):
            out["decision"] = "leave"
        if not isinstance(out.get("state"), dict):
            out["state"] = dict(self.state)
        # thread state forward
        st = out.get("state", {}) or {}
        new = {}
        for k in STATE_KEYS:
            try: new[k] = float(st.get(k, self.state.get(k)))
            except Exception: new[k] = self.state.get(k)
        self.state = new
        out["state"] = new
        # compact history line for next turn
        step = screen.get("you_are_on", "?")
        feel = out.get("feeling", "")
        dec = out.get("decision", "")
        self.history_brief.append(f"{step}: {dec}/{feel}")
        return out
