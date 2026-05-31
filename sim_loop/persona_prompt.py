"""Assemble the persona system prompt (segment markdown + behavioural dials).

Reads the project's persona assets at prompts/personas/<name>.md and
prompts/personas/<name>.params.json. Self-contained; no other module deps.
"""
from __future__ import annotations
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
PERSONA_DIR = ROOT / "prompts" / "personas"
NAMES = ("judith", "franz", "peter")

DIAL_ORDER = [
    ("budget_pressure", "Budget pressure"),
    ("value_orientation", "Value scrutiny"),
    ("complexity_overwhelm", "Complexity overwhelm"),
    ("advisor_lean", "Advisor lean"),
    ("patience", "Patience"),
    ("ux_willingness", "Willingness to push through heavy UI/UX"),
    ("comprehension", "Comprehension under load"),
    ("distractibility", "Distractibility"),
    ("commitment_anxiety", "Commitment anxiety"),
    ("uncertainty_aversion", "Uncertainty aversion"),
]


def dials(seg: str) -> dict:
    return json.loads((PERSONA_DIR / f"{seg}.params.json").read_text(encoding="utf-8"))


def _band(v: float) -> str:
    if v < 0.2: return "VERY LOW"
    if v < 0.4: return "SOMEWHAT LOW"
    if v < 0.6: return "MODERATE"
    if v < 0.8: return "FAIRLY HIGH"
    return "VERY HIGH"


def _dials_block(seg: str) -> str:
    d = dials(seg)
    lines = ["BEHAVIOURAL DIALS — how strongly each pressure acts on you; let them "
             "govern your stay-or-leave choices at each step:"]
    for key, label in DIAL_ORDER:
        if key in d:
            lines.append(f"- {label}: {_band(d[key])} ({d[key]:.2f})")
    lines.append(
        "\nYOU ARE THE CONSCIOUSNESS OF THIS PERSON. Simulate a real mind, not a "
        "form-filler.\n• Your BEHAVIOURAL DIALS above are FIXED dispositions — do not "
        "second-guess them.\n• You also carry a MENTAL STATE (attention, satisfaction, "
        "effort_left, grasp, effort_vs_reward) that CHANGES as you move through the "
        "funnel.\n• At each step: perceive the screen, UPDATE your mental state, then "
        "make a FELT decision — you leave when a state variable crosses your tolerance.")
    return "\n".join(lines)


def build_system_prompt(seg: str, session_instance: dict) -> str:
    md = (PERSONA_DIR / f"{seg}.md").read_text(encoding="utf-8")
    si = json.dumps(session_instance, ensure_ascii=False)
    today = ("\n\nTODAY'S SESSION INSTANCE (who this individual is RIGHT NOW — this "
             "OVERRIDES the segment profile whenever they conflict):\n" + si)
    return md + "\n\n" + _dials_block(seg) + today
