"""
UNIQA Journey Harness — composable token model for funnel + coach.

A journey is a sequence of JourneyTokens. The same tokens:
  - drive the simulation (bounce/convert outcome via psyche model)
  - render to frontend JSON (composable twin of the website widget flow)
  - feed the next-token suggester (the Coach predicts the next best token)

One harness, two modes:
  - run_journey(..., on_token=cb)  → demo: step-by-step, observable
  - run_batch(...)                 → automatic: fast aggregate

Token stream is stable + deterministic given a seed.

  STEP_ENTER ─▶ USER_SIGNAL ─▶ [COACH_WIDGET] ─▶ (BOUNCE | advance) ─▶ ...
                                                          │
                                                          ▼
                                                  CONVERT | WHATSAPP
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Callable, Optional

from uniqa.funnel import (
    Step, STEP_ORDER, FunnelState, HesitationSignals,
    generate_signals, is_hesitating, next_step,
)
from uniqa.coach import (
    CoachAction, decide_action, get_widget_copy, validate_output, MESSAGE_BUDGET,
)
from uniqa.psyche import (
    Mind, Intent, BounceReason, init_mind, step_dynamics,
    evaluate_bounce, apply_coach_effect,
)


# ─── Token Model ──────────────────────────────────────────────────────────────

class TokenType(Enum):
    STEP_ENTER   = "step_enter"
    USER_SIGNAL  = "user_signal"
    COACH_WIDGET = "coach_widget"
    BOUNCE       = "bounce"
    CONVERT      = "convert"
    WHATSAPP     = "whatsapp"


@dataclass
class JourneyToken:
    """One atomic event in a journey. Renders to a frontend spec."""
    type:    TokenType
    step:    str                      # Step.value
    payload: dict = field(default_factory=dict)
    render:  dict = field(default_factory=dict)   # composable frontend JSON

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "step": self.step,
            "payload": self.payload,
            "render": self.render,
        }


@dataclass
class JourneyTrace:
    persona:        str
    intent:         str
    coach_on:       bool
    tokens:         list[JourneyToken] = field(default_factory=list)
    converted:      bool = False
    bounced_at:     Optional[str] = None
    bounce_reason:  str = "none"
    whatsapp_sent:  bool = False
    message_count:  int = 0
    final_mind:     Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "persona": self.persona,
            "intent": self.intent,
            "coach_on": self.coach_on,
            "converted": self.converted,
            "bounced_at": self.bounced_at,
            "bounce_reason": self.bounce_reason,
            "whatsapp_sent": self.whatsapp_sent,
            "message_count": self.message_count,
            "final_mind": self.final_mind,
            "tokens": [t.to_dict() for t in self.tokens],
        }


# ─── JSON-render twin (composable frontend specs) ─────────────────────────────

STEP_SCREENS: dict[Step, dict] = {
    Step.COVERAGE_TYPE: {
        "screen": "coverage_type",
        "title": "Wo möchten Sie abgesichert sein?",
        "component": "ChoiceCards",
        "options": ["Bei Arztbesuchen", "Im Krankenhaus"],
        "progress": "Angaben",
    },
    Step.INSURED: {
        "screen": "insured_persons",
        "title": "Wer soll versichert werden?",
        "component": "ChoiceCards",
        "options": ["Ich selbst", "Andere Personen"],
        "progress": "Angaben",
    },
    Step.PERSONAL_INFO: {
        "screen": "personal_info",
        "title": "Für Ihre individuelle Prämie benötigen wir:",
        "component": "Form",
        "fields": ["Geburtsdatum", "Sozialversicherung"],
        "progress": "Angaben",
    },
    Step.TARIFF_SELECT: {
        "screen": "tariff_table",
        "title": "Welche Leistungen soll Ihre Privatarzt-Versicherung abdecken?",
        "component": "PriceTable",
        "tariffs": [
            {"name": "Start",   "price": "41,30", "online": True},
            {"name": "Optimal", "price": "73,02", "online": True},
            {"name": "Opt.Plus","price": "105,07","online": False},
            {"name": "Premium", "price": "152,35","online": False},
        ],
        "note": "Voraussichtliche Prämie — final nach Gesundheitsfragen",
        "progress": "Produkt",
    },
    Step.ADDON_SELECT: {
        "screen": "addons",
        "title": "Wünschen Sie Extra-Schutz?",
        "component": "AddonToggles",
        "addons": ["Fit fühlen +17,17", "Eltern werden +12,73", "Mental wachsen +25,76",
                   "Akut Versorgt +12,79", "BabyOption +4,62", "VitalPlan +16,34"],
        "progress": "Produkt",
    },
    Step.PERSONAL_DATA: {
        "screen": "personal_data",
        "title": "Angaben zu Ihrer Person",
        "component": "LongForm",
        "fields": ["Geschlecht", "Vorname", "Name", "SV-Nummer", "E-Mail",
                   "Telefon", "Größe", "Gewicht", "Sport", "Behandelnder Arzt"],
        "progress": "Abschluss",
    },
    Step.PURCHASE: {
        "screen": "purchase",
        "title": "Abschluss",
        "component": "Confirmation",
        "progress": "Abschluss",
    },
}

# UNIQA design tokens for the JSON-render (composable twin)
DESIGN = {
    "color.primary": "#0046A0",
    "color.accent":  "#E2001A",
    "color.success": "#1FA971",
    "radius.card":   "12px",
    "shadow.coach":  "0 8px 24px rgba(0,70,160,0.12)",
}


def render_step(step: Step, mind: Mind) -> dict:
    """Frontend spec for a funnel step screen + the live mind readout (HUD)."""
    screen = STEP_SCREENS.get(step, {"screen": step.value, "component": "Unknown"})
    return {
        "kind": "step_screen",
        **screen,
        "hud": _render_hud(mind),
    }


def _render_hud(mind: Mind) -> dict:
    """Live mental-state readout — drives the demo HUD."""
    return {
        "intent":          mind.intent.value,
        "attention":       round(mind.attention, 2),
        "price_readiness": round(mind.price_readiness, 2),
        "comprehension":   round(mind.comprehension, 2),
        "trust":           round(mind.trust, 2),
        "effort_budget":   round(mind.effort_budget, 2),
        "valence":         round(mind.valence, 2),
    }


def render_widget(action: CoachAction, persona: str, step: Step) -> dict:
    """Frontend spec for a Coach intervention widget (composable card)."""
    copy = get_widget_copy(action, persona)
    return {
        "kind": "coach_widget",
        "widget_type": action.value,
        "headline": copy.get("headline", ""),
        "body":     copy.get("body", ""),
        "cta":      copy.get("cta", ""),
        "style": {
            "border_radius": DESIGN["radius.card"],
            "shadow":        DESIGN["shadow.coach"],
            "accent":        DESIGN["color.primary"],
        },
        "anchor_step": step.value,
        "user_visible": action != CoachAction.NONE,
    }


# ─── Next-token suggester (the Coach as sequence predictor) ───────────────────

@dataclass
class NextTokenSuggestion:
    action:        CoachAction
    confidence:    float
    targeted_reason: str          # which bounce reason this counters
    render:        dict           # frontend JSON for the suggested widget
    rationale:     str


def suggest_next_token(
    mind: Mind,
    step: Step,
    signals: HesitationSignals,
    message_count: int,
) -> NextTokenSuggestion:
    """
    Given the journey-so-far (mind + step + signals), suggest the next COACH_WIDGET
    token and how it renders on the frontend. This is the 'next journey token
    suggester' — the Coach predicting the best next move.
    """
    state = FunnelState(step=step, persona=mind.persona, signals=signals)

    # Only suggest if hesitating and budget remains
    if message_count >= MESSAGE_BUDGET or not is_hesitating(signals, mind.persona):
        return NextTokenSuggestion(
            action=CoachAction.NONE, confidence=1.0, targeted_reason="none",
            render=render_widget(CoachAction.NONE, mind.persona, step),
            rationale="No hesitation detected or message budget exhausted.",
        )

    action = decide_action(state, message_count=message_count)

    # Which bounce reason does this action target? Dominant live hazard (no roll).
    ev = evaluate_bounce(replace_mind(mind), step, _peek_rng())
    if ev.hazards:
        targeted = max(ev.hazards, key=ev.hazards.get).value
    else:
        targeted = "preventive"
    confidence = _confidence(action, mind, step)

    return NextTokenSuggestion(
        action=action,
        confidence=confidence,
        targeted_reason=targeted,
        render=render_widget(action, mind.persona, step),
        rationale=_rationale(action, mind, step),
    )


def replace_mind(mind: Mind) -> Mind:
    """Shallow copy so the peek evaluation doesn't mutate the real mind."""
    from dataclasses import replace as _r
    return _r(mind)


_PEEK_RNG = random.Random(0)
def _peek_rng() -> random.Random:
    # deterministic peek (we only read hazards, not the roll)
    return _PEEK_RNG


def _confidence(action: CoachAction, mind: Mind, step: Step) -> float:
    """Heuristic confidence: how well does this action fit the mind's weakest axis?"""
    from uniqa.coach import get_modifier
    mod = get_modifier(action, mind.persona, step)
    # lower modifier (bigger effect) → higher confidence, capped
    return round(min(0.95, 0.5 + (1.0 - mod)), 2)


def _rationale(action: CoachAction, mind: Mind, step: Step) -> str:
    axis = min(
        [("attention", mind.attention), ("price_readiness", mind.price_readiness),
         ("comprehension", mind.comprehension), ("trust", mind.trust),
         ("effort_budget", mind.effort_budget)],
        key=lambda kv: kv[1],
    )
    return f"Weakest axis: {axis[0]}={axis[1]:.2f} at {step.value} → {action.value}"


# ─── The Harness ──────────────────────────────────────────────────────────────

def run_journey(
    persona: str,
    rng: random.Random,
    coach_on: bool = True,
    on_token: Optional[Callable[[JourneyToken], None]] = None,
) -> JourneyTrace:
    """
    Run one journey through the funnel using the psyche model.
    Emits tokens. on_token callback fires for each (demo mode).
    Deterministic given rng.
    """
    mind = init_mind(persona, rng)
    trace = JourneyTrace(persona=persona, intent=mind.intent.value, coach_on=coach_on)

    def emit(tok: JourneyToken):
        trace.tokens.append(tok)
        if on_token:
            on_token(tok)

    for step in STEP_ORDER[1:]:   # skip START
        # STEP_ENTER
        step_dynamics(mind, step, rng)
        emit(JourneyToken(
            type=TokenType.STEP_ENTER, step=step.value,
            payload=_render_hud(mind),
            render=render_step(step, mind),
        ))

        if step == Step.PURCHASE:
            trace.converted = True
            emit(JourneyToken(type=TokenType.CONVERT, step=step.value,
                              payload={"outcome": "online_purchase"},
                              render={"kind": "outcome", "status": "converted"}))
            break

        # USER_SIGNAL
        signals = generate_signals(step, persona, rng)
        emit(JourneyToken(
            type=TokenType.USER_SIGNAL, step=step.value,
            payload=_signals_dict(signals),
            render={"kind": "signal", **_signals_dict(signals)},
        ))

        # COACH_WIDGET (next-token suggestion)
        action = CoachAction.NONE
        if coach_on:
            sug = suggest_next_token(mind, step, signals, trace.message_count)
            action = sug.action
            if action != CoachAction.NONE:
                validate_output(action, persona)        # hard gate
                apply_coach_effect(mind, action.value, step)
                trace.message_count += 1
                emit(JourneyToken(
                    type=TokenType.COACH_WIDGET, step=step.value,
                    payload={"action": action.value, "confidence": sug.confidence,
                             "targets": sug.targeted_reason, "rationale": sug.rationale},
                    render=sug.render,
                ))

        # BOUNCE evaluation (psyche)
        ev = evaluate_bounce(mind, step, rng)
        if ev.bounced:
            trace.bounced_at = step.value
            trace.bounce_reason = ev.reason.value
            # Peter WhatsApp recovery if a callback was offered
            if persona == "peter" and any(
                t.type == TokenType.COACH_WIDGET and
                t.payload.get("action") == CoachAction.CALLBACK_OFFER.value
                for t in trace.tokens
            ):
                trace.whatsapp_sent = True
                emit(JourneyToken(
                    type=TokenType.WHATSAPP, step=step.value,
                    payload={"reason": ev.reason.value},
                    render={"kind": "whatsapp", "message":
                            "Hallo! Sie haben Privatarzt Start angesehen. "
                            "Hier weitermachen: [link]"},
                ))
            emit(JourneyToken(
                type=TokenType.BOUNCE, step=step.value,
                payload={"reason": ev.reason.value,
                         "hazards": {r.value: round(h, 2) for r, h in ev.hazards.items()}},
                render={"kind": "outcome", "status": "bounced", "reason": ev.reason.value},
            ))
            break

    trace.final_mind = _render_hud(mind)
    return trace


def _signals_dict(s: HesitationSignals) -> dict:
    return {
        "dwell_time_sec": round(s.dwell_time_sec, 1),
        "backward_nav_count": s.backward_nav_count,
        "price_hover_count": s.price_hover_count,
        "form_reedits": s.form_reedits,
        "session_gap_spike": s.session_gap_spike,
        "premium_click": s.premium_click,
        "cancel_hover_count": s.cancel_hover_count,
    }


# ─── Batch runner (automatic) ─────────────────────────────────────────────────

from uniqa.funnel import PERSONA_WEIGHTS
from collections import Counter, defaultdict

_PLIST = list(PERSONA_WEIGHTS.keys())
_PWEIGHTS = list(PERSONA_WEIGHTS.values())


@dataclass
class BatchResult:
    n: int
    coach_on: bool
    conversion_rate: float
    per_persona_conv: dict[str, float]
    per_step_bounce: dict[str, float]
    bounce_reasons: dict[str, int]
    whatsapp_leads: int
    avg_messages: float
    conv_by_intent: dict[str, float]


def run_batch(n: int = 1000, seed: int = 42, coach_on: bool = True) -> BatchResult:
    """Fast automatic run. No token callbacks. Aggregates outcomes."""
    rng = random.Random(seed)
    traces: list[JourneyTrace] = []
    for _ in range(n):
        persona = rng.choices(_PLIST, weights=_PWEIGHTS, k=1)[0]
        traces.append(run_journey(persona, rng, coach_on=coach_on))
    return _aggregate_batch(traces, n, coach_on)


def _aggregate_batch(traces: list[JourneyTrace], n: int, coach_on: bool) -> BatchResult:
    conv = sum(1 for t in traces if t.converted)
    per_p: dict[str, list[bool]] = defaultdict(list)
    for t in traces:
        per_p[t.persona].append(t.converted)

    arrivals = Counter()
    bounces  = Counter()
    for t in traces:
        seen = set()
        for tok in t.tokens:
            if tok.type == TokenType.STEP_ENTER and tok.step not in seen:
                arrivals[tok.step] += 1
                seen.add(tok.step)
        if t.bounced_at:
            bounces[t.bounced_at] += 1

    reasons = Counter(t.bounce_reason for t in traces if t.bounced_at)
    by_intent: dict[str, list[bool]] = defaultdict(list)
    for t in traces:
        by_intent[t.intent].append(t.converted)

    return BatchResult(
        n=n, coach_on=coach_on,
        conversion_rate=conv / n,
        per_persona_conv={p: sum(v)/len(v) for p, v in per_p.items()},
        per_step_bounce={s: bounces[s]/arrivals[s] for s in arrivals if arrivals[s]},
        bounce_reasons=dict(reasons),
        whatsapp_leads=sum(1 for t in traces if t.whatsapp_sent),
        avg_messages=sum(t.message_count for t in traces)/n,
        conv_by_intent={i: sum(v)/len(v) for i, v in by_intent.items()},
    )


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--trace", action="store_true", help="print one demo journey trace")
    args = ap.parse_args()

    if args.trace:
        rng = random.Random(args.seed)
        print("\n── DEMO JOURNEY (Franz, coach ON) ──")
        def show(tok):
            line = f"  [{tok.type.value:12s}] {tok.step:20s}"
            if tok.type == TokenType.COACH_WIDGET:
                line += f" → {tok.payload['action']} (conf {tok.payload['confidence']}, targets {tok.payload['targets']})"
            elif tok.type == TokenType.BOUNCE:
                line += f" ✗ {tok.payload['reason']}"
            elif tok.type == TokenType.CONVERT:
                line += " ✓ CONVERTED"
            elif tok.type == TokenType.WHATSAPP:
                line += " 📲 WhatsApp sent"
            print(line)
        run_journey("franz", rng, coach_on=True, on_token=show)
        raise SystemExit

    base = run_batch(args.n, args.seed, coach_on=False)
    coach = run_batch(args.n, args.seed, coach_on=True)

    def fmt(b: BatchResult, label):
        print(f"\n{'='*58}\n  {label}  N={b.n:,}\n{'='*58}")
        print(f"  Conversion: {b.conversion_rate*100:.2f}%")
        print(f"  Per persona: " + " | ".join(f"{p}:{r*100:.1f}%" for p,r in b.per_persona_conv.items()))
        print(f"  Per-step bounce:")
        for s in [Step.PERSONAL_INFO, Step.TARIFF_SELECT, Step.ADDON_SELECT, Step.PERSONAL_DATA]:
            print(f"    {s.value:22s}: {b.per_step_bounce.get(s.value,0)*100:.1f}%")
        print(f"  Bounce reasons: {b.bounce_reasons}")
        print(f"  Conv by intent: " + " | ".join(f"{i}:{r*100:.1f}%" for i,r in b.conv_by_intent.items()))
        print(f"  WhatsApp leads: {b.whatsapp_leads} | avg msgs: {b.avg_messages:.2f}")

    fmt(base, "WITHOUT COACH (baseline)")
    fmt(coach, "WITH COACH")
    delta = coach.conversion_rate - base.conversion_rate
    rel = delta / base.conversion_rate * 100 if base.conversion_rate else 0
    print(f"\n  UPLIFT: {base.conversion_rate*100:.2f}% → {coach.conversion_rate*100:.2f}%  "
          f"(+{delta*100:.2f}pp, +{rel:.0f}%)")
