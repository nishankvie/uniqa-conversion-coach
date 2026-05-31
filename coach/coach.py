"""
UNIQA Conversion Coach — Detection + Decision Layer

Architecture (two layers):
  Detection:  is_hesitating() in funnel.py → bool
  Decision:   decide_action() here → CoachAction

Hard constraints:
  - Franz NEVER receives AdvisorHandoff (he hates advisors → kills conversion)
  - Message budget: max 3 interventions per session (annoyance ceiling)
  - Peter is routed to callback/WA BEFORE price display (early routing)
  - Out-of-scope paths (hospital, other persons, Opt.Plus/Premium) → clean advisor exit

Coach effect on abandon probability:
  - Intervention applied → abandon_prob × modifier (< 1.0 = reduces abandon risk)
  - No-op → modifier = 1.0 (no change)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from calculator.funnel import Step, FunnelState, HesitationSignals, is_hesitating


# ─── Action Space ─────────────────────────────────────────────────────────────

class CoachAction(Enum):
    NONE              = "none"
    PRICE_REFRAME     = "price_reframe"       # "€1.37/day" framing
    UPGRADE_EXPLAIN   = "upgrade_explain"     # Premium/OptPlus → explain advisory + Optimal online
    TRUST_SIGNAL      = "trust_signal"        # brand trust, since 1811, AAA-rated
    COVERAGE_EXPLAIN  = "coverage_explain"    # translate EUR limits to real-world visits
    HEALTH_EXPLAIN    = "health_explain"      # explain why final price changed
    ADVISOR_HANDOFF   = "advisor_handoff"     # smooth handoff to advisor (Judith only)
    CALLBACK_OFFER    = "callback_offer"      # offer phone callback (Peter priority)
    UPGRADE_PATH      = "upgrade_path"        # "upgrade after 3y no new health check"
    FEATURE_HIGHLIGHT = "feature_highlight"   # eye surgery doubled Sep 2025
    FORM_HELPER       = "form_helper"         # "Your SV-nr is on your e-card top-right"
    PROGRESS_SAVER    = "progress_saver"      # "May I save your email? Continue later."


# ─── Hard Constraints ─────────────────────────────────────────────────────────

# Actions that are FORBIDDEN for specific personas (enforced before any LLM call)
FORBIDDEN_ACTIONS: dict[str, set[CoachAction]] = {
    "franz":  {CoachAction.ADVISOR_HANDOFF},   # Franz: online-only, advisor = conversion kill
    "judith": set(),
    "peter":  set(),
}

MESSAGE_BUDGET = 3   # max interventions per session before annoyance ceiling


def validate_output(action: CoachAction, persona: str) -> None:
    """
    Hard constraint gate. Raises ValueError if action is forbidden for this persona.
    Called in BOTH sim path and demo path — cannot be bypassed.

    Defense-in-depth: also called in emit_widget() and simulation step.
    """
    forbidden = FORBIDDEN_ACTIONS.get(persona, set())
    if action in forbidden:
        raise ValueError(
            f"CONSTRAINT VIOLATION: {action.value!r} is forbidden for persona={persona!r}. "
            "Franz must never receive AdvisorHandoff — it destroys his conversion probability."
        )


# ─── Coach Effect on Abandon Probability ──────────────────────────────────────

# Abandon probability multiplier after intervention.
# 0.70 = intervention reduces abandon prob by 30%.
# 1.0  = no effect (NONE action).
COACH_MODIFIERS: dict[CoachAction, dict[str, dict[Step, float]]] = {
    CoachAction.PRICE_REFRAME: {
        "judith": {Step.TARIFF_SELECT: 0.78, Step.PERSONAL_DATA: 0.85},
        "franz":  {Step.TARIFF_SELECT: 0.82, Step.PERSONAL_DATA: 0.75},
        "peter":  {Step.TARIFF_SELECT: 0.85},
    },
    CoachAction.UPGRADE_EXPLAIN: {
        # Franz clicks Premium → Coach explains Premium needs advisory, Optimal fully online
        "franz":  {Step.TARIFF_SELECT: 0.60},   # big effect — removes the confusion
        "judith": {Step.TARIFF_SELECT: 0.72},
        "peter":  {Step.TARIFF_SELECT: 0.80},
    },
    CoachAction.HEALTH_EXPLAIN: {
        # Judith/Franz see final price > estimate → Coach explains why
        "judith": {Step.PERSONAL_DATA: 0.65},
        "franz":  {Step.PERSONAL_DATA: 0.68},
        "peter":  {Step.PERSONAL_DATA: 0.75},
    },
    CoachAction.ADVISOR_HANDOFF: {
        "judith": {Step.TARIFF_SELECT: 0.62, Step.PERSONAL_DATA: 0.60},
        # Franz: NOT in this table (forbidden — validate_output catches it)
        "peter":  {Step.PERSONAL_DATA: 0.70},
    },
    CoachAction.CALLBACK_OFFER: {
        # Peter primary — offer callback BEFORE price shock
        "peter":  {Step.PERSONAL_INFO: 0.48, Step.TARIFF_SELECT: 0.55},
        "judith": {Step.PERSONAL_DATA: 0.72},
    },
    CoachAction.TRUST_SIGNAL: {
        "judith": {Step.TARIFF_SELECT: 0.85, Step.PERSONAL_DATA: 0.88},
        "franz":  {Step.TARIFF_SELECT: 0.90},
        "peter":  {Step.PERSONAL_INFO: 0.80, Step.TARIFF_SELECT: 0.88},
    },
    CoachAction.UPGRADE_PATH: {
        "judith": {Step.TARIFF_SELECT: 0.82},
        "franz":  {Step.TARIFF_SELECT: 0.88},
        "peter":  {Step.TARIFF_SELECT: 0.90},
    },
    CoachAction.FORM_HELPER: {
        # Helps with SV-number anxiety
        "peter":  {Step.PERSONAL_INFO: 0.65, Step.PERSONAL_DATA: 0.72},
        "judith": {Step.PERSONAL_DATA: 0.82},
        "franz":  {Step.PERSONAL_DATA: 0.85},
    },
    CoachAction.COVERAGE_EXPLAIN: {
        "judith": {Step.TARIFF_SELECT: 0.80},
        "peter":  {Step.TARIFF_SELECT: 0.82},
        "franz":  {Step.TARIFF_SELECT: 0.88},
    },
    CoachAction.FEATURE_HIGHLIGHT: {
        "judith": {Step.TARIFF_SELECT: 0.83, Step.ADDON_SELECT: 0.80},
        "franz":  {Step.TARIFF_SELECT: 0.87},
    },
    CoachAction.PROGRESS_SAVER: {
        "peter":  {Step.PERSONAL_DATA: 0.60},
        "judith": {Step.PERSONAL_DATA: 0.75},
        "franz":  {Step.PERSONAL_DATA: 0.82},
    },
    CoachAction.NONE: {},  # no effect
}


def get_modifier(action: CoachAction, persona: str, step: Step) -> float:
    """Returns abandon_prob multiplier. 1.0 = no change."""
    return COACH_MODIFIERS.get(action, {}).get(persona, {}).get(step, 1.0)


# ─── Decision Logic ───────────────────────────────────────────────────────────

def decide_action(
    state: FunnelState,
    message_count: int = 0,
) -> CoachAction:
    """
    Rule-based Coach policy.
    Maps (step, persona, signals) → CoachAction.

    Decision tree (priority order):
      1. Message budget exceeded → NONE
      2. Peter + early step → CALLBACK_OFFER (before price shock)
      3. Franz + premium_click → UPGRADE_EXPLAIN (removes confusion)
      4. Final price step + cancel hovering → HEALTH_EXPLAIN or ADVISOR_HANDOFF
      5. Tariff step + price hovering → PRICE_REFRAME or COVERAGE_EXPLAIN
      6. Personal info overwhelm → FORM_HELPER
      7. Generic fallback → TRUST_SIGNAL or NONE

    All outputs validated through validate_output().
    """
    step    = state.step
    persona = state.persona
    sig     = state.signals

    # Annoyance budget ceiling
    if message_count >= MESSAGE_BUDGET:
        return CoachAction.NONE

    action = _select_action(step, persona, sig)
    validate_output(action, persona)   # hard gate — always
    return action


def _select_action(step: Step, persona: str, sig: HesitationSignals) -> CoachAction:
    """Inner logic — pure decision, no validation."""

    # ── Peter: route early before price shock ────────────────────────────────
    if persona == "peter" and step in (Step.PERSONAL_INFO, Step.COVERAGE_TYPE):
        if sig.form_reedits >= 2 or sig.backward_nav_count >= 1 or sig.dwell_time_sec >= 6.0:
            return CoachAction.CALLBACK_OFFER

    # ── Franz: Premium confusion → explain Optimal online path ───────────────
    if persona == "franz" and step == Step.TARIFF_SELECT and sig.premium_click:
        return CoachAction.UPGRADE_EXPLAIN

    # ── Final price step: explain why price changed ───────────────────────────
    if step == Step.PERSONAL_DATA:
        if sig.cancel_hover_count >= 2:
            # Judith: offer advisor handoff gracefully
            if persona == "judith":
                return CoachAction.ADVISOR_HANDOFF
            # Franz: never advisor — health explanation instead
            if persona == "franz":
                return CoachAction.HEALTH_EXPLAIN
            # Peter: progress saver (async completion)
            if persona == "peter":
                return CoachAction.PROGRESS_SAVER
        if sig.dwell_time_sec >= 15.0:
            return CoachAction.HEALTH_EXPLAIN
        if sig.form_reedits >= 2:
            return CoachAction.FORM_HELPER

    # ── Tariff selection: price shock interventions ───────────────────────────
    if step == Step.TARIFF_SELECT:
        if sig.backward_nav_count >= 1 and not sig.premium_click:
            # Judith: back-nav without Premium = uncertain → upgrade path
            if persona == "judith":
                return CoachAction.UPGRADE_PATH
            # Franz: back-nav = price anxiety → reframe
            if persona == "franz":
                return CoachAction.PRICE_REFRAME
        if sig.price_hover_count >= 3:
            return CoachAction.PRICE_REFRAME
        if sig.dwell_time_sec >= 10.0:
            return CoachAction.COVERAGE_EXPLAIN

    # ── Personal info form: SV-number helper ─────────────────────────────────
    if step == Step.PERSONAL_INFO:
        if sig.form_reedits >= 2 or sig.dwell_time_sec >= 8.0:
            return CoachAction.FORM_HELPER

    # ── Add-on selection: feature highlight ──────────────────────────────────
    if step == Step.ADDON_SELECT and sig.dwell_time_sec >= 10.0:
        return CoachAction.FEATURE_HIGHLIGHT

    # ── Generic trust signal for lingering users ──────────────────────────────
    if sig.dwell_time_sec >= 20.0:
        return CoachAction.TRUST_SIGNAL

    return CoachAction.NONE


# ─── Widget Content (for demo / Streamlit rendering) ─────────────────────────

WIDGET_COPY: dict[CoachAction, dict[str, dict]] = {
    CoachAction.PRICE_REFRAME: {
        "judith": {
            "headline": "Start ab €1,27 täglich",
            "body":     "Optimal: €2,25/Tag — weniger als ein Kaffee. Für €68/Monat bekommen Sie €2.800/Jahr Schutz.",
            "cta":      "Mit Optimal weiter",
        },
        "franz": {
            "headline": "Optimal: €2,43/Tag",
            "body":     "€68/Monat, vollständig online abschließbar. Keine Beratung erforderlich.",
            "cta":      "Optimal wählen",
        },
        "peter": {
            "headline": "Start ab €1,27 täglich",
            "body":     "Der einfachste Einstieg. Jederzeit erweiterbar.",
            "cta":      "Mit Start beginnen",
        },
    },
    CoachAction.UPGRADE_EXPLAIN: {
        "franz": {
            "headline": "Premium & Opt. Plus erfordern eine kurze Beratung",
            "body":     "Optimal hingegen schließen Sie jetzt vollständig online ab — direkt und ohne Termin.",
            "cta":      "Optimal online abschließen",
        },
        "judith": {
            "headline": "Höhere Tarife per Beratung",
            "body":     "Optimal deckt Arztbesuche, Medikamente und Therapien — vollständig online, ohne Wartezeit.",
            "cta":      "Optimal wählen",
        },
        "peter": {
            "headline": "Einen höheren Tarif braucht eine Beratung",
            "body":     "Soll ich Ihnen jemanden empfehlen, der Sie anruft?",
            "cta":      "Rückruf anfordern",
        },
    },
    CoachAction.HEALTH_EXPLAIN: {
        "judith": {
            "headline": "Warum hat sich der Preis geändert?",
            "body":     "Ihre Angaben wurden individuell bewertet. Das ist transparent und fair — Ihr finaler Schutz ist jetzt genau auf Sie abgestimmt.",
            "cta":      "Jetzt online abschließen",
        },
        "franz": {
            "headline": "Preis geändert — das steckt dahinter",
            "body":     "Die Differenz basiert auf Ihren Gesundheitsangaben. Sie können trotzdem sofort online abschließen.",
            "cta":      "Trotzdem abschließen",
        },
        "peter": {
            "headline": "Fragen zur Preisänderung?",
            "body":     "Wir erklären alles gerne persönlich.",
            "cta":      "Rückruf anfordern",
        },
    },
    CoachAction.ADVISOR_HANDOFF: {
        "judith": {
            "headline": "Lieber persönlich beraten lassen?",
            "body":     "Kein Problem — buchen Sie jetzt einen Termin. Ihr bisheriger Fortschritt bleibt gespeichert.",
            "cta":      "Beratungsgespräch buchen",
        },
        "peter": {
            "headline": "Jemanden sprechen?",
            "body":     "Wir rufen Sie gerne zurück.",
            "cta":      "Rückruf anfordern",
        },
    },
    CoachAction.CALLBACK_OFFER: {
        "peter": {
            "headline": "Rückruf gewünscht?",
            "body":     "Unser Team hilft Ihnen in wenigen Minuten — kostenlos und unverbindlich.",
            "cta":      "Jetzt zurückrufen lassen",
        },
        "judith": {
            "headline": "Lieber persönlich?",
            "body":     "Wir rufen Sie gerne zurück und begleiten Sie durch die letzten Schritte.",
            "cta":      "Rückruf buchen",
        },
    },
    CoachAction.UPGRADE_PATH: {
        "judith": {
            "headline": "Nach 3 Jahren flexibel wechseln",
            "body":     "Sie können jederzeit in einen höheren Tarif wechseln — ohne erneute Gesundheitsprüfung.",
            "cta":      "Jetzt mit Start oder Optimal beginnen",
        },
        "franz": {
            "headline": "Jetzt Start, später upgraden",
            "body":     "Nach 3 Jahren Wechsel ohne neue Gesundheitsprüfung — vollständig online.",
            "cta":      "Start wählen",
        },
        "peter": {
            "headline": "Starten Sie einfach",
            "body":     "Start deckt Ihre Grundbedürfnisse. Ein Upgrade ist später jederzeit möglich.",
            "cta":      "Mit Start beginnen",
        },
    },
    CoachAction.FORM_HELPER: {
        "peter": {
            "headline": "SV-Nummer finden",
            "body":     "Ihre Sozialversicherungsnummer steht auf Ihrer e-Card oben rechts (10 Ziffern).",
            "cta":      "Verstanden, weiter",
        },
        "judith": {
            "headline": "Wo finde ich meine SV-Nummer?",
            "body":     "Sie steht auf Ihrer e-Card oben rechts.",
            "cta":      "Weiter",
        },
        "franz": {
            "headline": "SV-Nummer: e-Card oben rechts",
            "body":     "10 Ziffern — die ersten 4 sind eine laufende Nummer, die letzten 6 Ihr Geburtsdatum.",
            "cta":      "Weiter",
        },
    },
    CoachAction.COVERAGE_EXPLAIN: {
        "judith": {
            "headline": "Was bedeutet €2.800/Jahr?",
            "body":     "Optimal deckt ~35 Facharztbesuche, Physiotherapie, Medikamente und mehr — ohne Kassenwartezeit.",
            "cta":      "Optimal wählen",
        },
        "franz": {
            "headline": "€2.800/Jahr Erstattung",
            "body":     "Arztleistungen, Therapien, Medikamente, Sehhilfen — alles inklusive. Start deckt €1.400/Jahr.",
            "cta":      "Optimal wählen",
        },
        "peter": {
            "headline": "Was bin ich versichert?",
            "body":     "Start: Arztbesuche & Medikamente. Optimal: zusätzlich Therapien & Sehhilfen.",
            "cta":      "Start wählen",
        },
    },
    CoachAction.TRUST_SIGNAL: {
        "judith": {
            "headline": "UNIQA — seit 1811",
            "body":     "Über 3 Millionen Kunden in Österreich. AAA-bewertet. Ihre Daten sind sicher.",
            "cta":      "Weiter",
        },
        "franz": {
            "headline": "4,8/5 Kundenbewertung (eKomi)",
            "body":     "Vollständig online abschließbar. Sofort versichert.",
            "cta":      "Weiter",
        },
        "peter": {
            "headline": "Sie sind in guten Händen",
            "body":     "UNIQA ist Österreichs führender Versicherer. Jederzeit erreichbar.",
            "cta":      "Weiter",
        },
    },
    CoachAction.PROGRESS_SAVER: {
        "peter": {
            "headline": "Jetzt speichern, später fertig machen",
            "body":     "Darf ich Ihre E-Mail notieren? Wir sichern Ihren Fortschritt für 30 Tage.",
            "cta":      "Fortschritt speichern",
        },
        "judith": {
            "headline": "Fortschritt gespeichert",
            "body":     "Sie können später weitermachen — Ihre Angaben bleiben für 30 Tage gesichert.",
            "cta":      "Link per E-Mail senden",
        },
        "franz": {
            "headline": "Fortschritt speichern",
            "body":     "Weitermachen wann Sie wollen — direkter Link per E-Mail.",
            "cta":      "Link senden",
        },
    },
    CoachAction.FEATURE_HIGHLIGHT: {
        "judith": {
            "headline": "Neu: Refraktive Augen-OP doppelt abgedeckt",
            "body":     "Seit September 2025: €280/Jahr für Laserbehandlungen — in Optimal enthalten.",
            "cta":      "Optimal wählen",
        },
        "franz": {
            "headline": "Neu in Optimal: €280 für Augen-OP",
            "body":     "Refraktive Chirurgie (Laser) jetzt mit doppelter Deckung — seit Sep 2025.",
            "cta":      "Optimal wählen",
        },
        "peter": {
            "headline": "Was ist neu?",
            "body":     "Augen-Laserbehandlungen jetzt besser abgedeckt. Fragen? Wir rufen an.",
            "cta":      "Rückruf anfordern",
        },
    },
    CoachAction.NONE: {
        "judith": {"headline": "", "body": "", "cta": ""},
        "franz":  {"headline": "", "body": "", "cta": ""},
        "peter":  {"headline": "", "body": "", "cta": ""},
    },
}


def get_widget_copy(action: CoachAction, persona: str) -> dict:
    """Returns headline/body/cta for a given action + persona."""
    return WIDGET_COPY.get(action, {}).get(persona, {"headline": "", "body": "", "cta": ""})
