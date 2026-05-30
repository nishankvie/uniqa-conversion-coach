"""
Coach intervention catalog — the COMPLETE set of moves the Coach can make on top of the
(immutable) UNIQA funnel. One source of truth, consumed by:
  • the Coach policy (rule or model) → picks an intervention id given the session,
  • the renderer / widget twin → draws it,
  • the persona simulator → the `persona_facing` text is injected into the persona's next
    step so it can REACT and ASSESS it (helpful/engaging vs distracting/noisy).

Design notes
------------
- The Coach is detection + decision only; it never edits the funnel. Every intervention is a
  widget/overlay the user can ignore.
- Each intervention has a CATEGORY (what kind of help), the STEPS where it's apt, the personas
  it tends to fit, whether it spends the annoyance BUDGET, and a PERSONA_FACING line (what the
  user actually sees — this is what we feed the persona to react to).
- The persona, given its intent+state, decides if it was helpful/engaging or distracting/noisy.
  We do NOT hard-code that; the simulator persona judges it. This catalog only describes the move.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from uniqa.funnel import Step


class Category(str, Enum):
    INFORM      = "inform"        # explain something (reduce confusion / uncertainty)
    REASSURE    = "reassure"      # trust / social proof / lower commitment anxiety
    PRICE       = "price"         # reframe / explain price
    ENGAGE      = "engage"        # lower effort, pull them forward (quiz, helper)
    CONVERT_AID = "convert_aid"   # nudge the online completion (preselect, upgrade path)
    CAPTURE     = "capture"       # not-ready-today → keep the lead (email, save progress)
    HANDOFF     = "handoff"       # move to a human/channel (advisor, callback, whatsapp)


@dataclass(frozen=True)
class Intervention:
    id: str
    category: Category
    title: str                 # short label (renderer)
    persona_facing: str        # what the user SEES — injected into the persona prompt
    steps: tuple[Step, ...]    # where it's apt ( () = any )
    personas: tuple[str, ...]  # who it tends to fit ( () = any )
    spends_budget: bool = True # counts against the ≤3 annoyance budget (passive aids don't)


_S4 = Step.TARIFF_SELECT
_S6 = Step.PERSONAL_DATA
_S3 = Step.PERSONAL_INFO
_S1 = Step.COVERAGE_TYPE


# ─── THE CATALOG ──────────────────────────────────────────────────────────────
CATALOG: dict[str, Intervention] = {i.id: i for i in [
    # ── price ────────────────────────────────────────────────────────────────
    Intervention("price_reframe", Category.PRICE, "Price reframe",
        "A small card reframing the monthly premium as a daily cost — “≈ €1.37/day, less than a coffee” — next to what it covers.",
        (_S4, _S6), ()),
    Intervention("pricing_explain", Category.PRICE, "How the price is built",
        "A plain-language breakdown of how the premium is calculated (age + tariff; health questions can adjust the final price) so the number feels predictable, not arbitrary.",
        (_S4, _S6), ()),
    Intervention("health_explain", Category.INFORM, "Why the final price changed",
        "A short note explaining the final price moved after the health questions, why that happened, and that it's still fully online.",
        (_S6,), ()),

    # ── inform / package nuance ───────────────────────────────────────────────
    Intervention("upgrade_explain", Category.INFORM, "Premium vs Optimal (online)",
        "A clarifier: Premium / Opt.Plus need an advisor, but **Optimal is fully completable online right now** — removing the “do I have to call someone?” confusion.",
        (_S4,), ("franz", "judith")),
    Intervention("package_nuance", Category.INFORM, "Start vs Optimal — what really differs",
        "A compact, neutral comparison of Start vs Optimal: the 3–4 differences that actually matter (limits, refund %, what's included) — no upsell pressure.",
        (_S4,), ()),
    Intervention("coverage_explain", Category.INFORM, "What the limits mean in real life",
        "Translates the € coverage limits into real-world terms (“covers ~X specialist visits / a physio series a year”).",
        (_S4, _S1), ()),
    Intervention("coverage_checker", Category.INFORM, "Is YOUR treatment covered?",
        "A tiny lookup answering the user's open question — “is dental / physio / my doctor covered?” — the question the funnel gives them no way to ask.",
        (_S4, _S1), ()),
    Intervention("feature_highlight", Category.INFORM, "Recently improved",
        "Highlights a concrete recent improvement relevant to them (e.g. laser-eye-surgery limit doubled in 2025).",
        (_S4,), ()),

    # ── reassure ───────────────────────────────────────────────────────────────
    Intervention("trust_signal", Category.REASSURE, "Why UNIQA",
        "A quiet trust cue — “UNIQA, insuring Austria since 1811, AAA-rated” — no exclamation, just reassurance.",
        (), ()),
    Intervention("social_proof", Category.REASSURE, "What others chose",
        "Light social proof — “most people with your needs picked Optimal this month” — to lower commitment anxiety.",
        (_S4, _S6), ("judith", "peter")),

    # ── engage (lower effort, pull forward) ───────────────────────────────────
    Intervention("quick_quiz", Category.ENGAGE, "60-second fit quiz",
        "An offer to take a short 3-question quiz that recommends the right tariff for them — turns an overwhelming choice into a guided one.",
        (_S1, _S4), ("peter", "judith")),
    Intervention("form_helper", Category.ENGAGE, "Inline form help",
        "A contextual hint that de-frictions the current field (e.g. “your insurance number is top-right on your e-card”).",
        (_S3, _S6), ()),
    Intervention("preselect_optimal", Category.CONVERT_AID, "Sensible default selected",
        "Pre-selects the online-completable Optimal tariff (still changeable) so the user can proceed without deciding from scratch.",
        (_S4,), ("franz",), spends_budget=False),
    Intervention("upgrade_path", Category.CONVERT_AID, "Start now, upgrade later",
        "Reassurance that they can start on a lower tariff today and upgrade within 3 years without a new health check — lowers the stakes of choosing now.",
        (_S4,), ("judith",)),

    # ── capture (not ready today → keep the lead) ─────────────────────────────
    Intervention("save_progress", Category.CAPTURE, "Save & continue later",
        "Offers to save their progress to an email link so they can finish later — for someone clearly not converting in this session.",
        (_S4, _S6), (), spends_budget=False),
    Intervention("email_capture", Category.CAPTURE, "Send me the details",
        "Offers to email a summary of this quote + a short explainer — a low-commitment way to keep a not-ready-today visitor.",
        (_S4, _S6), ()),

    # ── handoff (human / channel) ──────────────────────────────────────────────
    Intervention("callback_offer", Category.HANDOFF, "Free callback",
        "Offers a quick scheduled phone callback from an advisor — surfaced EARLY for service-preferring users, before the price wall.",
        (_S1, _S3), ("peter",)),
    Intervention("whatsapp_bot", Category.HANDOFF, "Ask on WhatsApp",
        "Offers a WhatsApp assistant that can answer their open questions and send the quote — a familiar low-effort channel with something valuable attached.",
        (_S1, _S3, _S4), ("peter",)),
    Intervention("advisor_handoff", Category.HANDOFF, "Talk to an advisor",
        "A graceful, optional handoff to a human advisor to finish — offered (never forced) to users who want reassurance before committing.",
        (_S6,), ("judith",)),
]}

NONE_ID = "none"


def persona_facing(intervention_id: str) -> str:
    """The line shown to the user — fed to the persona simulator so it can react/assess."""
    iv = CATALOG.get(intervention_id)
    return iv.persona_facing if iv else ""


def is_apt(intervention_id: str, step: Step, persona: str | None = None) -> bool:
    iv = CATALOG.get(intervention_id)
    if not iv:
        return False
    if iv.steps and step not in iv.steps:
        return False
    if persona and iv.personas and persona not in iv.personas:
        return False
    return True


def by_category(cat: Category) -> list[Intervention]:
    return [iv for iv in CATALOG.values() if iv.category == cat]


# Map the rule coach's CoachAction → catalog id (so the existing policy plugs in unchanged).
# CoachAction names that already match an id resolve directly; the rest are aliased here.
RULE_ACTION_TO_ID = {
    "none": NONE_ID,
    "price_reframe": "price_reframe",
    "upgrade_explain": "upgrade_explain",
    "trust_signal": "trust_signal",
    "coverage_explain": "coverage_explain",
    "health_explain": "health_explain",
    "advisor_handoff": "advisor_handoff",
    "callback_offer": "callback_offer",
    "upgrade_path": "upgrade_path",
    "feature_highlight": "feature_highlight",
    "form_helper": "form_helper",
    "progress_saver": "save_progress",
}
