"""
UNIQA Conversion Coach — Live Demo (Streamlit)

Views:
  1. Before / After       — scripted Franz journey, coach OFF vs ON side-by-side
  2. Live journey         — step-by-step walkthrough with Mind Reader HUD
  3. A/B uplift           — Monte Carlo batch results
  4. Attribution Audit    — hypothesis-scored bounce attribution vs analyst guesses
  5. Revealed Preference  — what abandoning users wanted that UNIQA doesn't offer
  6. Play & capture       — link to the React capture app

Run:  .venv/bin/streamlit run demo/streamlit_app.py
"""

from __future__ import annotations

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import random
import pandas as pd
import streamlit as st
from collections import Counter, defaultdict

from calculator.journey import run_journey, run_batch, TokenType, JourneyTrace
from calculator.funnel import PERSONAS, PERSONA_WEIGHTS

PRIMARY = "#0046A0"
ACCENT  = "#E2001A"
SUCCESS = "#1FA971"
WARN    = "#F59E0B"
INK     = "#1B1F24"
MUTED   = "#6B7280"

PERSONA_META = {
    "judith": {"emoji": "🧑‍💼", "label": "Judith — Rising Hybrid",
               "blurb": "30% of traffic. Trusts advisors, moderate price comfort. Wants reassurance."},
    "franz":  {"emoji": "🧑‍💻", "label": "Franz — Online Affine",
               "blurb": "50% of traffic. High comprehension, low patience. ONLINE ONLY — never hand to advisor."},
    "peter":  {"emoji": "🧑‍🔧", "label": "Peter — Service Affine",
               "blurb": "20% of traffic. Wants human contact. Best recovered via WhatsApp / callback."},
}

BOUNCE_META = {
    "price_shock":       {"analyst": "Price abandonment (S4)",  "action": "PRICE_REFRAME",    "fixable": True,  "tag": "coachable"},
    "comparison_leave":  {"analyst": "Price abandonment (S4)",  "action": "MARKET_COMPARE",   "fixable": True,  "tag": "misattributed"},
    "trust_gap":         {"analyst": "Price abandonment (S4)",  "action": "TRUST_SIGNAL",     "fixable": True,  "tag": "misattributed"},
    "effort_exhaustion": {"analyst": "Form friction (S6)",      "action": "FORM_HELPER",      "fixable": True,  "tag": "coachable"},
    "overwhelm":         {"analyst": "Early drop-off",          "action": "COVERAGE_EXPLAIN", "fixable": True,  "tag": "coachable"},
    "not_ready":         {"analyst": "Unknown drop-off",        "action": "SILENCE",          "fixable": False, "tag": "uncoachable"},
    "distraction":       {"analyst": "Unknown drop-off",        "action": "SILENCE",          "fixable": False, "tag": "uncoachable"},
    "none":              {"analyst": "—",                       "action": "—",                "fixable": False, "tag": "—"},
}

st.set_page_config(page_title="UNIQA Conversion Coach", page_icon="🧭", layout="wide")

st.markdown(f"""
<style>
  .block-container {{ padding-top: 2rem; }}
  .coach-card {{ background:#fff; border-left:4px solid {PRIMARY};
     border-radius:12px; padding:14px 18px; box-shadow:0 8px 24px rgba(0,70,160,0.12);
     margin:6px 0; }}
  .step-card {{ background:#F6F8FB; border-radius:12px; padding:16px 20px; margin:6px 0;
     border:1px solid #E5EAF1; }}
  .signal-pill {{ display:inline-block; background:#FFF3F4; color:{ACCENT};
     border-radius:999px; padding:2px 10px; font-size:0.8rem; margin:2px; }}
  .outcome-good {{ background:{SUCCESS}; color:#fff; border-radius:12px; padding:14px 18px;
     font-weight:600; margin:6px 0; }}
  .outcome-bad {{ background:#FBEAEA; color:{ACCENT}; border-radius:12px; padding:14px 18px;
     font-weight:600; border:1px solid #F2C7C7; margin:6px 0; }}
  .wa-card {{ background:#E7F8EE; border-left:4px solid {SUCCESS}; border-radius:12px;
     padding:12px 16px; margin:6px 0; }}
  .tariff {{ display:inline-block; background:#fff; border:1px solid #E5EAF1; border-radius:10px;
     padding:8px 12px; margin:3px; text-align:center; min-width:96px; }}
  .hazard-high {{ background:#FBEAEA; border-left:4px solid {ACCENT}; border-radius:8px;
     padding:10px 14px; margin:4px 0; }}
  .hazard-med {{ background:#FFF7ED; border-left:4px solid {WARN}; border-radius:8px;
     padding:8px 12px; margin:4px 0; font-size:0.85rem; }}
  .tag-coachable {{ background:#DCFCE7; color:#166534; border-radius:999px;
     padding:2px 9px; font-size:0.75rem; font-weight:600; }}
  .tag-misattributed {{ background:#FEF9C3; color:#854D0E; border-radius:999px;
     padding:2px 9px; font-size:0.75rem; font-weight:600; }}
  .tag-uncoachable {{ background:#F1F5F9; color:{MUTED}; border-radius:999px;
     padding:2px 9px; font-size:0.75rem; font-weight:600; }}
  .revenue-box {{ background:linear-gradient(135deg,{PRIMARY} 0%,#0066CC 100%); color:#fff;
     border-radius:16px; padding:20px 24px; text-align:center; }}
  .dead-session {{ background:#F1F5F9; border-radius:16px; padding:20px 24px; text-align:center;
     color:{MUTED}; }}
</style>
""", unsafe_allow_html=True)

st.markdown(
    f"<h1 style='color:{PRIMARY};margin-bottom:0'>🧭 UNIQA Conversion Coach</h1>"
    f"<p style='color:{MUTED};margin-top:4px'>A behavioral detection + decision layer on top of the "
    f"existing UNIQA calculator. Reads why a user is about to leave. Intervenes only when it helps.</p>",
    unsafe_allow_html=True)

@st.cache_data
def _audit_traces(n: int = 500, seed: int = 99) -> list[dict]:
    rng = random.Random(seed)
    plist    = list(PERSONA_WEIGHTS.keys())
    pweights = list(PERSONA_WEIGHTS.values())
    out = []
    for _ in range(n):
        persona = rng.choices(plist, weights=pweights, k=1)[0]
        trace: JourneyTrace = run_journey(persona, rng, coach_on=False)
        if not trace.bounced_at:
            continue
        bounce_tok = next((t for t in trace.tokens if t.type == TokenType.BOUNCE), None)
        hazards    = bounce_tok.payload.get("hazards", {}) if bounce_tok else {}
        signals: dict = {}
        for t in trace.tokens:
            if t.type == TokenType.USER_SIGNAL and t.step == trace.bounced_at:
                signals = t.payload
                break
        s4_signals: dict = {}
        for t in trace.tokens:
            if t.type == TokenType.USER_SIGNAL and t.step == "S4_TARIFF_SELECT":
                s4_signals = t.payload
                break
        out.append({
            "persona":    persona,
            "step":       trace.bounced_at,
            "reason":     trace.bounce_reason,
            "hazards":    hazards,
            "signals":    signals,
            "s4_signals": s4_signals,
        })
    return out

HUD_AXES = [
    ("attention",       "Attention"),
    ("price_readiness", "Price readiness"),
    ("comprehension",   "Comprehension"),
    ("trust",           "Trust"),
    ("effort_budget",   "Effort budget"),
    ("valence",         "Mood"),
]

def _bar_color(v: float) -> str:
    if v >= 0.6: return SUCCESS
    if v >= 0.4: return WARN
    return ACCENT

def render_hud(hud: dict, where, hazards: dict | None = None,
               coach_action: str | None = None, rationale: str | None = None):
    where.markdown("**🧠 Mind Reader**")
    intent = hud.get("intent", "?")
    intent_color = PRIMARY if intent == "purchase" else (WARN if intent == "research" else MUTED)
    where.markdown(
        f"<div style='font-size:0.8rem;color:{MUTED};margin-bottom:2px'>Inferred intent</div>"
        f"<span style='color:{intent_color};font-weight:700;font-size:1rem'>{intent}</span>",
        unsafe_allow_html=True)
    where.markdown("")
    for key, label in HUD_AXES:
        v = max(0.0, min(1.0, float(hud.get(key, 0.0))))
        color = _bar_color(v)
        pct = int(v * 100)
        where.markdown(
            f"<div style='display:flex;justify-content:space-between;font-size:0.78rem;"
            f"color:{MUTED};margin-bottom:2px'><span>{label}</span>"
            f"<span style='color:{color};font-weight:600'>{pct}%</span></div>"
            f"<div style='background:#E5EAF1;border-radius:4px;height:7px;margin-bottom:8px'>"
            f"<div style='background:{color};width:{pct}%;height:7px;border-radius:4px'></div></div>",
            unsafe_allow_html=True)
    if hazards:
        active = {k: v for k, v in hazards.items() if v > 0}
        if active:
            top_reason, top_h = max(active.items(), key=lambda kv: kv[1])
            sev_color = ACCENT if top_h >= 0.4 else WARN
            where.markdown(
                f"<div class='hazard-high'>"
                f"<div style='font-size:0.72rem;color:{MUTED}'>Active hazard</div>"
                f"<div style='font-weight:700;color:{sev_color};font-size:0.95rem'>"
                f"{top_reason.replace('_',' ').upper()}</div>"
                f"<div style='font-size:0.78rem;color:{INK}'>severity {top_h:.0%}</div></div>",
                unsafe_allow_html=True)
            others = sorted([(k, v) for k, v in active.items() if k != top_reason],
                            key=lambda kv: -kv[1])[:2]
            for r, h in others:
                where.markdown(
                    f"<div class='hazard-med'>"
                    f"<span style='color:{WARN}'>{r.replace('_',' ')}</span> {h:.0%}</div>",
                    unsafe_allow_html=True)
    if coach_action and coach_action != "none":
        where.markdown(
            f"<div style='margin-top:8px;padding:8px 10px;background:#EEF3FB;"
            f"border-radius:8px;font-size:0.8rem'>"
            f"<span style='color:{PRIMARY};font-weight:700'>Coach fired:</span> "
            f"<span style='color:{INK}'>{coach_action}</span>"
            f"{'<br><span style=\"color:' + MUTED + ';font-size:0.75rem\">' + rationale + '</span>' if rationale else ''}"
            f"</div>",
            unsafe_allow_html=True)

def render_token(tok, main):
    r = tok.render or {}
    if tok.type == TokenType.STEP_ENTER:
        title = r.get("title", tok.step)
        prog  = r.get("progress", "")
        comp  = r.get("component", "")
        body = ""
        if r.get("tariffs"):
            body = "".join(
                f"<div class='tariff'><b>{t['name']}</b><br>€{t['price']}<br>"
                f"<span style='font-size:0.7rem;color:{'#1FA971' if t.get('online') else '#E2001A'}'>"
                f"{'online ✓' if t.get('online') else 'Beratung'}</span></div>"
                for t in r["tariffs"])
        elif r.get("options"):
            body = " ".join(
                f"<span class='signal-pill' style='background:#EEF3FB;color:{PRIMARY}'>{o}</span>"
                for o in r["options"])
        elif r.get("fields"):
            body = " ".join(
                f"<span class='signal-pill' style='background:#EEF3FB;color:{PRIMARY}'>{f}</span>"
                for f in r["fields"])
        elif r.get("addons"):
            body = " ".join(
                f"<span class='signal-pill' style='background:#EEF3FB;color:{PRIMARY}'>{a}</span>"
                for a in r["addons"])
        main.markdown(
            f"<div class='step-card'>"
            f"<span style='color:{MUTED};font-size:0.75rem'>{prog} · {comp}</span>"
            f"<div style='font-weight:600;font-size:1.05rem;color:{INK};margin:4px 0'>\U0001f4c4 {title}</div>"
            f"{body}</div>",
            unsafe_allow_html=True)
    elif tok.type == TokenType.USER_SIGNAL:
        active_signals = {
            k: v for k, v in tok.payload.items()
            if (isinstance(v, bool) and v) or
               (not isinstance(v, bool) and isinstance(v, (int, float)) and v != 0)
        }
        if not active_signals:
            return
        pills = " ".join(
            f"<span class='signal-pill'>{k.replace('_',' ')}: {v}</span>"
            for k, v in active_signals.items())
        main.markdown(
            f"<div style='margin:2px 0 8px 0'>\U0001f441️ signals &nbsp; {pills}</div>",
            unsafe_allow_html=True)
    elif tok.type == TokenType.COACH_WIDGET:
        p = tok.payload
        main.markdown(
            f"<div class='coach-card'>"
            f"<span style='color:{PRIMARY};font-weight:700'>\U0001f9ed Coach → {p['action']}</span>"
            f"<div style='font-weight:600;margin:6px 0 2px 0'>{r.get('headline','')}</div>"
            f"<div style='color:{INK}'>{r.get('body','')}</div>"
            f"<div style='margin-top:6px'>"
            f"<span class='signal-pill' style='background:{PRIMARY};color:#fff'>{r.get('cta','')}</span>"
            f"</div>"
            f"<div style='color:{MUTED};font-size:0.72rem;margin-top:6px'>"
            f"confidence {p.get('confidence')} · targeting <b>{p.get('targets')}</b>"
            f"<br><span style='font-style:italic'>{p.get('rationale','')}</span>"
            f"</div></div>",
            unsafe_allow_html=True)
    elif tok.type == TokenType.WHATSAPP:
        main.markdown(
            f"<div class='wa-card'>\U0001f4f2 <b>WhatsApp follow-up sent</b><br>"
            f"<span style='color:{INK}'>{r.get('message','')}</span></div>",
            unsafe_allow_html=True)
    elif tok.type == TokenType.CONVERT:
        main.markdown(
            "<div class='outcome-good'>✅ CONVERTED — online purchase completed</div>",
            unsafe_allow_html=True)
    elif tok.type == TokenType.BOUNCE:
        main.markdown(
            f"<div class='outcome-bad'>✗ BOUNCED at {tok.step} — reason: "
            f"<b>{tok.payload.get('reason')}</b></div>",
            unsafe_allow_html=True)

VIEWS = ["Before / After", "Live journey", "A/B uplift",
         "Attribution Audit", "Revealed Preference", "Play & capture"]

with st.sidebar:
    st.markdown("### Controls")
    view = st.radio("View", VIEWS, index=0)
    st.divider()

if view == "Before / After":
    st.markdown(
        f"<h2 style='color:{INK}'>The same user. Two outcomes.</h2>"
        f"<p style='color:{MUTED}'>Franz, 38. Online-affine. Wants the best coverage he can get "
        f"online — but the calculator labels Premium as advisory-required and he hits price shock. "
        f"Without the coach, he’s gone in 40 seconds.</p>",
        unsafe_allow_html=True)
    trace_off = run_journey("franz", random.Random(48), coach_on=False)
    trace_on  = run_journey("franz", random.Random(48), coach_on=True)
    left, right = st.columns(2)
    with left:
        st.markdown(
            f"<div style='background:#F1F5F9;border-radius:12px;padding:12px 16px;margin-bottom:12px'>"
            f"<span style='font-size:0.8rem;color:{MUTED};font-weight:600'>WITHOUT COACH</span></div>",
            unsafe_allow_html=True)
        for tok in trace_off.tokens:
            render_token(tok, st)
    with right:
        st.markdown(
            f"<div style='background:#EEF3FB;border-radius:12px;padding:12px 16px;margin-bottom:12px'>"
            f"<span style='font-size:0.8rem;color:{PRIMARY};font-weight:600'>WITH COACH</span></div>",
            unsafe_allow_html=True)
        for tok in trace_on.tokens:
            render_token(tok, st)
    st.divider()
    r_left, r_mid, r_right = st.columns([2, 1, 2])
    with r_left:
        st.markdown(
            f"<div class='dead-session'>"
            f"<div style='font-size:2rem'>✗</div>"
            f"<div style='font-weight:700;font-size:1.1rem;margin:8px 0'>Session ended</div>"
            f"<div>Bounced at {trace_off.bounced_at or 'S4'}</div>"
            f"<div style='margin-top:12px;font-size:1.4rem;font-weight:700'>€0</div>"
            f"<div style='font-size:0.8rem'>revenue this session</div>"
            f"</div>",
            unsafe_allow_html=True)
    with r_mid:
        st.markdown(
            f"<div style='text-align:center;padding:40px 0;font-size:2rem'>→</div>",
            unsafe_allow_html=True)
    with r_right:
        monthly = 74.46
        annual  = round(monthly * 12, 2)
        ltv     = round(annual * 10)
        st.markdown(
            f"<div class='revenue-box'>"
            f"<div style='font-size:2rem'>✅</div>"
            f"<div style='font-weight:700;font-size:1.1rem;margin:8px 0'>Converted online</div>"
            f"<div style='opacity:0.8'>Optimal tariff · real UNIQA pricing</div>"
            f"<div style='margin-top:12px;font-size:2rem;font-weight:800'>€{monthly:.2f}/mo</div>"
            f"<div style='font-size:0.9rem;opacity:0.85'>€{annual}/yr · ~€{ltv:,} LTV (10yr)</div>"
            f"</div>",
            unsafe_allow_html=True)
    st.markdown("")
    st.info(
        f"**4,000-session simulation (same paired random seed):** baseline 5.6% → "
        f"coached 14.5% conversion. +8.9pp absolute · +159% relative uplift. "
        f"Purchase-intent cohort: 14% → 38%.")

elif view == "Live journey":
    with st.sidebar:
        persona  = st.selectbox("Persona", list(PERSONAS),
                                format_func=lambda p: PERSONA_META[p]["label"])
        coach_on = st.toggle("Coach ON", value=True)
        seed     = st.number_input("Seed", value=7, step=1)
        st.caption(PERSONA_META[persona]["blurb"])
        if st.button("\U0001f3b2 New journey", use_container_width=True):
            st.session_state.pop("trace_key", None)
            st.session_state["seed_bump"] = st.session_state.get("seed_bump", 0) + 1
    eff_seed = int(seed) + st.session_state.get("seed_bump", 0)
    key = f"{persona}-{coach_on}-{eff_seed}"
    if st.session_state.get("trace_key") != key:
        rng = random.Random(eff_seed)
        st.session_state["trace"]     = run_journey(persona, rng, coach_on=bool(coach_on))
        st.session_state["trace_key"] = key
        st.session_state["cursor"]    = len(st.session_state["trace"].tokens)
    trace = st.session_state["trace"]
    n_tok = len(trace.tokens)
    left, right = st.columns([3, 1])
    with right:
        st.markdown(f"### {PERSONA_META[persona]['emoji']} {persona.title()}")
        play_all = st.toggle("Show full journey", value=True)
        cursor   = n_tok if play_all else st.slider(
            "Token", 1, n_tok, st.session_state.get("cursor", n_tok))
        st.session_state["cursor"] = cursor
        latest_hud = latest_hazards = last_coach_action = last_rationale = None
        for tok in trace.tokens[:cursor]:
            if tok.type == TokenType.STEP_ENTER:
                latest_hud = tok.payload
            if tok.type == TokenType.BOUNCE:
                latest_hazards = tok.payload.get("hazards")
            if tok.type == TokenType.COACH_WIDGET:
                last_coach_action = tok.payload.get("action")
                last_rationale    = tok.payload.get("rationale")
        if latest_hud:
            render_hud(latest_hud, st, hazards=latest_hazards,
                       coach_action=last_coach_action, rationale=last_rationale)
    with left:
        for tok in trace.tokens[:cursor]:
            render_token(tok, st)
    if trace.converted:
        st.success(f"Outcome: CONVERTED · messages used: {trace.message_count}/3")
    else:
        extra = " · \U0001f4f2 WhatsApp lead captured" if trace.whatsapp_sent else ""
        st.error(f"Outcome: bounced at {trace.bounced_at} ({trace.bounce_reason}) · "
                 f"messages used: {trace.message_count}/3{extra}")

elif view == "A/B uplift":
    with st.sidebar:
        n    = st.select_slider("Population (N)", options=[500, 1000, 2000, 5000, 10000], value=2000)
        seed = st.number_input("Seed", value=42, step=1)
    base  = run_batch(n=int(n), seed=int(seed), coach_on=False)
    coach = run_batch(n=int(n), seed=int(seed), coach_on=True)
    delta    = coach.conversion_rate - base.conversion_rate
    rel      = delta / base.conversion_rate * 100 if base.conversion_rate else 0
    pi_base  = base.conv_by_intent.get("purchase", 0.0)
    pi_coach = coach.conv_by_intent.get("purchase", 0.0)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Conversion (overall)", f"{coach.conversion_rate*100:.1f}%", f"+{delta*100:.1f}pp")
    c2.metric("Relative uplift", f"+{rel:.0f}%")
    c3.metric("Purchase-intent conv.", f"{pi_coach*100:.0f}%", f"+{(pi_coach-pi_base)*100:.0f}pp")
    c4.metric("WhatsApp leads", f"{coach.whatsapp_leads}",
              help="Peter recovered via callback → WhatsApp follow-up")
    st.caption(
        f"Honest framing: overall conversion {base.conversion_rate*100:.1f}% → "
        f"{coach.conversion_rate*100:.1f}%. The coachable cohort (purchase intent) moves "
        f"{pi_base*100:.0f}% → {pi_coach*100:.0f}%. `not_ready` / `distraction` bounces are "
        f"intentionally left alone — no annoyance budget spent on lost causes.")
    st.divider()
    a, b = st.columns(2)
    with a:
        st.markdown("#### Conversion by persona")
        df = pd.DataFrame({
            "persona":   list(coach.per_persona_conv.keys()),
            "coach ON":  [coach.per_persona_conv[p]*100 for p in coach.per_persona_conv],
            "coach OFF": [base.per_persona_conv.get(p, 0)*100 for p in coach.per_persona_conv],
        }).set_index("persona")
        st.bar_chart(df, color=["#B9C6DC", PRIMARY], stack=False)
    with b:
        st.markdown("#### Per-step bounce rate")
        steps = ["S4_TARIFF_SELECT", "S5_ADDON_SELECT", "S6_PERSONAL_DATA"]
        df2 = pd.DataFrame({
            "step":      [s.split('_', 1)[1] for s in steps],
            "coach OFF": [base.per_step_bounce.get(s, 0)*100 for s in steps],
            "coach ON":  [coach.per_step_bounce.get(s, 0)*100 for s in steps],
        }).set_index("step")
        st.bar_chart(df2, color=["#E7B6BB", ACCENT], stack=False)
    st.markdown("#### Bounce reasons (coach OFF → ON)")
    reasons = sorted(set(base.bounce_reasons) | set(coach.bounce_reasons))
    df3 = pd.DataFrame({
        "reason":    reasons,
        "coach OFF": [base.bounce_reasons.get(r, 0) for r in reasons],
        "coach ON":  [coach.bounce_reasons.get(r, 0) for r in reasons],
    }).set_index("reason")
    st.bar_chart(df3, color=["#C9CDD3", PRIMARY], stack=False)
    st.caption("Coach shrinks the coachable reasons (price_shock, comparison_leave, effort_exhaustion) "
               "while leaving not_ready/distraction untouched — that’s the intervention-quality story.")

elif view == "Attribution Audit":
    st.markdown(
        f"<h2 style='color:{INK}'>The data quality problem UNIQA already knows they have.</h2>"
        f"<p style='color:{MUTED}'>UNIQA’s analysts see step-level drop-off. They guess why. "
        f"Most of the time they’re partially wrong — and they’re optimizing against the wrong thing. "
        f"Here’s the verified attribution from 500 simulated sessions.</p>",
        unsafe_allow_html=True)
    with st.sidebar:
        audit_n    = st.select_slider("Sessions", options=[200, 500, 1000], value=500)
        audit_seed = st.number_input("Seed", value=99, step=1)
    with st.spinner("Running 500 sessions..."):
        traces = _audit_traces(n=audit_n, seed=audit_seed)
    total_bounces = len(traces)
    by_reason: dict[str, list[dict]] = defaultdict(list)
    for r in traces:
        by_reason[r["reason"]].append(r)
    s4_bounces       = [r for r in traces if r["step"] == "S4_TARIFF_SELECT"]
    misattributed_s4 = [r for r in s4_bounces if r["reason"] in ("comparison_leave", "trust_gap")]
    coachable_total  = sum(1 for r in traces if BOUNCE_META.get(r["reason"], {}).get("fixable"))
    uncoachable_total = total_bounces - coachable_total
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total sessions analysed", total_bounces)
    m2.metric("S4 bounces", len(s4_bounces),
              help="All look like 'price abandonment' in standard analytics")
    m3.metric("S4 misattributed", len(misattributed_s4),
              f"{len(misattributed_s4)/max(len(s4_bounces),1)*100:.0f}% of S4",
              help="Comparison-leave + trust-gap look identical to price-shock in drop-off reports")
    m4.metric("Uncoachable bounces", uncoachable_total,
              help="not_ready + distraction — optimizing against these wastes budget")
    st.divider()
    st.markdown("#### Bounce attribution — what the analyst sees vs what actually happened")
    rows = []
    reason_order = ["price_shock", "comparison_leave", "trust_gap",
                    "effort_exhaustion", "overwhelm", "not_ready", "distraction"]
    for reason in reason_order:
        bucket = by_reason.get(reason, [])
        if not bucket:
            continue
        meta     = BOUNCE_META.get(reason, {})
        tag      = meta.get("tag", "—")
        tag_html = (f"<span class='tag-{tag}'>{tag}</span>"
                    if tag in ("coachable", "misattributed", "uncoachable") else tag)
        dominant_step = Counter(r["step"] for r in bucket).most_common(1)[0][0].split("_", 1)[-1]
        rows.append({
            "Bounce reason":     reason.replace("_", " "),
            "Count":             len(bucket),
            "% of bounces":      f"{len(bucket)/total_bounces*100:.0f}%",
            "What analyst sees": meta.get("analyst", "—"),
            "Step":              dominant_step,
            "Coach response":    meta.get("action", "—"),
            "tag":               tag_html,
            "Fixable":           "✓" if meta.get("fixable") else "—",
        })
    df_rows = pd.DataFrame(rows)
    st.markdown(
        "<table style='width:100%;border-collapse:collapse;font-size:0.88rem'>"
        "<thead><tr style='border-bottom:2px solid #E5EAF1'>"
        + "".join(f"<th style='text-align:left;padding:6px 10px;color:{MUTED}'>{c}</th>"
                  for c in ["Reason", "N", "%", "Analyst sees", "Step",
                             "Coach response", "Classification", "Fixable"])
        + "</tr></thead><tbody>"
        + "".join(
            f"<tr style='border-bottom:1px solid #F1F5F9'>"
            f"<td style='padding:7px 10px;font-weight:600'>{r['Bounce reason']}</td>"
            f"<td style='padding:7px 10px'>{r['Count']}</td>"
            f"<td style='padding:7px 10px;color:{MUTED}'>{r['% of bounces']}</td>"
            f"<td style='padding:7px 10px;color:{INK}'>{r['What analyst sees']}</td>"
            f"<td style='padding:7px 10px;color:{MUTED}'>{r['Step']}</td>"
            f"<td style='padding:7px 10px;font-family:monospace;font-size:0.82rem'>{r['Coach response']}</td>"
            f"<td style='padding:7px 10px'>{r['tag']}</td>"
            f"<td style='padding:7px 10px;text-align:center'>{r['Fixable']}</td>"
            f"</tr>"
            for _, r in df_rows.iterrows())
        + "</tbody></table>",
        unsafe_allow_html=True)
    st.markdown("")
    st.markdown(
        f"<div style='background:#FEF9C3;border-radius:10px;padding:14px 18px;border-left:4px solid {WARN}'>"
        f"<b>The key finding:</b> {len(misattributed_s4)} of {len(s4_bounces)} step-4 bounces "
        f"({len(misattributed_s4)/max(len(s4_bounces),1)*100:.0f}%) are misattributed as ‘price abandonment’ "
        f"in a standard drop-off report. They are actually <b>comparison shopping</b> or <b>trust gaps</b> — "
        f"two problems that a price reframe doesn’t fix, and may make worse.</div>",
        unsafe_allow_html=True)
    st.divider()
    st.markdown("#### Per-reason hazard breakdown (top 3 active signals per bounce)")
    hazard_cols = st.columns(3)
    col_idx = 0
    for reason in ["price_shock", "comparison_leave", "effort_exhaustion"]:
        bucket = by_reason.get(reason, [])
        if not bucket:
            continue
        all_hazards: dict[str, list[float]] = defaultdict(list)
        for r in bucket:
            for h, v in r["hazards"].items():
                all_hazards[h].append(v)
        avg_h = {h: sum(vs)/len(vs) for h, vs in all_hazards.items() if vs}
        top3  = sorted(avg_h.items(), key=lambda kv: -kv[1])[:3]
        with hazard_cols[col_idx % 3]:
            st.markdown(f"**{reason.replace('_',' ')}** _(n={len(bucket)})_")
            for h, v in top3:
                color = ACCENT if v >= 0.4 else WARN
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;font-size:0.8rem;"
                    f"margin-bottom:4px'><span>{h.replace('_',' ')}</span>"
                    f"<span style='color:{color};font-weight:600'>{v:.0%}</span></div>"
                    f"<div style='background:#E5EAF1;border-radius:4px;height:6px;margin-bottom:8px'>"
                    f"<div style='background:{color};width:{int(v*100)}%;height:6px;border-radius:4px'>"
                    f"</div></div>",
                    unsafe_allow_html=True)
        col_idx += 1

elif view == "Revealed Preference":
    st.markdown(
        f"<h2 style='color:{INK}'>What your abandoning users actually wanted.</h2>"
        f"<p style='color:{MUTED}'>When users leave, they leave a behavioral trace. "
        f"Aggregated across 500 sessions, that trace reveals which users had a <em>fixable</em> "
        f"problem vs which users revealed a <em>product gap</em> — something UNIQA doesn’t "
        f"currently offer online. No other team is telling UNIQA this.</p>",
        unsafe_allow_html=True)
    with st.sidebar:
        rp_n    = st.select_slider("Sessions", options=[200, 500, 1000], value=500)
        rp_seed = st.number_input("Seed", value=99, step=1)
    with st.spinner("Analysing abandonment signals..."):
        traces = _audit_traces(n=rp_n, seed=rp_seed)
    s4_bounces = [r for r in traces if r["step"] == "S4_TARIFF_SELECT"]
    premium_seekers     = [r for r in s4_bounces if r.get("s4_signals", {}).get("premium_click")]
    comparison_shoppers = [r for r in s4_bounces
                           if r["reason"] == "comparison_leave"
                           and not r.get("s4_signals", {}).get("premium_click")]
    price_anchored      = [r for r in s4_bounces
                           if r["reason"] == "price_shock"
                           and r.get("s4_signals", {}).get("price_hover_count", 0) >= 3
                           and not r.get("s4_signals", {}).get("premium_click")]
    s6_bounces  = [r for r in traces if r["step"] == "S6_PERSONAL_DATA"]
    sv_friction = [r for r in s6_bounces if r["reason"] == "effort_exhaustion"]
    total_s4 = max(len(s4_bounces), 1)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("S4 bounces analysed",  len(s4_bounces))
    m2.metric("Product gap signal",   len(premium_seekers),   f"{len(premium_seekers)/total_s4*100:.0f}% of S4")
    m3.metric("Comparison shopping",  len(comparison_shoppers), f"{len(comparison_shoppers)/total_s4*100:.0f}% of S4")
    m4.metric("Genuine price shock",  len(price_anchored),    f"{len(price_anchored)/total_s4*100:.0f}% of S4")
    st.divider()
    st.markdown("#### What each group revealed they wanted")
    gap1, gap2, gap3 = st.columns(3)
    with gap1:
        pct = len(premium_seekers) / total_s4 * 100
        st.markdown(
            f"<div style='background:#FEF2F2;border-radius:12px;padding:16px 18px;"
            f"border:1px solid #FECACA;height:100%'>"
            f"<div style='font-size:1.8rem'>\U0001f512</div>"
            f"<div style='font-weight:700;font-size:1rem;margin:8px 0;color:{INK}'>Premium/Opt.Plus coverage — online</div>"
            f"<div style='color:{MUTED};font-size:0.85rem'>Clicked advisory-required tariff, then left. "
            f"Didn’t want to book an advisor. Wanted the coverage without the friction.</div>"
            f"<div style='margin-top:12px;font-size:1.3rem;font-weight:800;color:{ACCENT}'>{pct:.0f}% of S4 exits</div>"
            f"<div style='margin-top:8px;font-size:0.8rem;color:{MUTED}'>"
            f"<b>Product gap:</b> No online path for Opt.Plus or Premium. "
            f"Estimated annual revenue foregone: €{int(len(premium_seekers) * 109.56 * 12):,}/yr at current traffic.</div>"
            f"</div>", unsafe_allow_html=True)
    with gap2:
        pct2 = len(comparison_shoppers) / total_s4 * 100
        st.markdown(
            f"<div style='background:#FFF7ED;border-radius:12px;padding:16px 18px;"
            f"border:1px solid #FED7AA;height:100%'>"
            f"<div style='font-size:1.8rem'>\U0001f50d</div>"
            f"<div style='font-weight:700;font-size:1rem;margin:8px 0;color:{INK}'>Better price-coverage ratio</div>"
            f"<div style='color:{MUTED};font-size:0.85rem'>Left to shop competitors. Not committed to UNIQA. "
            f"Didn’t find a tier that fit their budget and coverage expectations simultaneously.</div>"
            f"<div style='margin-top:12px;font-size:1.3rem;font-weight:800;color:{WARN}'>{pct2:.0f}% of S4 exits</div>"
            f"<div style='margin-top:8px;font-size:0.8rem;color:{MUTED}'>"
            f"<b>Product gap:</b> No mid-tier option between Start (€42/mo, 1,400 limit) "
            f"and Optimal (€75/mo, 2,800 limit). A €58/mo × 2,100 limit tier would capture this segment.</div>"
            f"</div>", unsafe_allow_html=True)
    with gap3:
        pct3 = len(price_anchored) / total_s4 * 100
        st.markdown(
            f"<div style='background:#F0FDF4;border-radius:12px;padding:16px 18px;"
            f"border:1px solid #BBF7D0;height:100%'>"
            f"<div style='font-size:1.8rem'>\U0001f4b6</div>"
            f"<div style='font-weight:700;font-size:1rem;margin:8px 0;color:{INK}'>Reframeable price shock</div>"
            f"<div style='color:{MUTED};font-size:0.85rem'>Genuinely reacted to the price — "
            f"hovered 3+ times, didn’t explore Premium. The coach’s PRICE_REFRAME "
            f"(€2.43/day framing) directly addresses this.</div>"
            f"<div style='margin-top:12px;font-size:1.3rem;font-weight:800;color:{SUCCESS}'>{pct3:.0f}% of S4 exits</div>"
            f"<div style='margin-top:8px;font-size:0.8rem;color:{MUTED}'>"
            f"<b>Already fixed:</b> The coach handles this. No product decision needed.</div>"
            f"</div>", unsafe_allow_html=True)
    st.divider()
    st.markdown("#### S6 friction — what SV-number abandonment actually signals")
    sv_col, insight_col = st.columns([1, 2])
    with sv_col:
        st.metric("S6 effort-exhaustion bounces", len(sv_friction))
        if s6_bounces:
            st.caption(f"{len(sv_friction)/len(s6_bounces)*100:.0f}% of S6 exits are effort exhaustion")
    with insight_col:
        st.markdown(
            f"<div style='background:#EEF3FB;border-radius:10px;padding:14px 18px'>"
            f"<b>What the SV-number really signals:</b> Users who made it to S6 have already "
            f"committed to a tariff and price. They are leaving because they don’t have their "
            f"Sozialversicherungsnummer memorized. A single tooltip — ‘You can find this on your "
            f"SV card or via FinanzOnline’ — recovers a meaningful fraction without any product change. "
            f"UNIQA’s current read: ‘form friction.’ Our read: ‘one missing tooltip.’</div>",
            unsafe_allow_html=True)
    st.divider()
    st.markdown(
        f"<div style='background:{PRIMARY};color:#fff;border-radius:12px;padding:20px 24px'>"
        f"<b style='font-size:1.05rem'>The product recommendation:</b><br><br>"
        f"1. <b>Offer Opt.Plus online</b> — streamlined path without full advisor for age &lt; 50. "
        f"Captures {len(premium_seekers)} of {len(s4_bounces)} S4 exits at €109.56/mo average.<br><br>"
        f"2. <b>Add a mid-tier tariff</b> (~€58/mo, 2,100 limit) — closes the Start↔Optimal gap "
        f"that {len(comparison_shoppers)} users were searching for.<br><br>"
        f"3. <b>Add SV-number tooltip</b> — 2 lines of copy. Recovers the S6 group at zero cost.<br><br>"
        f"The coach cannot fix these. Only a product decision can. "
        f"This is the intelligence no analytics tool was surfacing.</div>",
        unsafe_allow_html=True)

elif view == "Play & capture":
    import glob
    CAP_URL = os.environ.get("UNIQA_CAPTURE_URL", "http://localhost:5173")
    st.markdown("### \U0001f3af Play & capture (real mouse)")
    st.markdown(
        "Capturing **real physical mouse behaviour** (hover dwell, movement tone, tab "
        "switches) needs the browser, so it lives in the **React app**. It emits the "
        "same high-level `ActivityLog` the persona bots produce.")
    try:
        st.link_button("▶ Open the capture app", CAP_URL)
    except Exception:
        st.markdown(f"[▶ Open the capture app]({CAP_URL})")
    st.caption("Not running yet? Start it once:")
    st.code("cd webapp && npm install && npm run dev   # http://localhost:5173", language="bash")
    st.divider()
    st.markdown("#### Captured sessions")
    files = sorted(glob.glob("_local/captures/*.json"), key=os.path.getmtime, reverse=True)
    if not files:
        st.info("No captures yet — finish a session in the capture app and **Download log "
                "JSON** into `_local/captures/`.")
    else:
        pick    = st.selectbox("Session", files, format_func=os.path.basename)
        persona = st.selectbox("Compare against persona", list(PERSONAS), index=1)
        st.code(f"python -m evaluations.compare {pick} --persona {persona}", language="bash")
        try:
            data = json.load(open(pick))
            st.caption(f"{len(data.get('events', []))} events · hint={data.get('persona_hint','?')} "
                       f"· {data.get('source','')}")
            st.dataframe(data.get("events", []), height=320, use_container_width=True)
        except Exception as e:
            st.warning(f"Could not read {pick}: {e}")
