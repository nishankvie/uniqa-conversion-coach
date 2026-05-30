"""
UNIQA Conversion Coach — Live Demo (Streamlit)

Two views:
  1. LIVE JOURNEY — play a single token stream. Funnel step screens (JSON twin),
     user signals, Coach widgets, and a live Mind HUD. Walk it token-by-token.
  2. A/B UPLIFT  — Monte Carlo batch, coach OFF vs ON. Honest framing:
     overall uplift + purchase-intent conversion (the coachable cohort).

Run:  .venv/bin/streamlit run uniqa/app.py
"""

from __future__ import annotations

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import random
import pandas as pd
import streamlit as st

from uniqa.journey import run_journey, run_batch, TokenType, BatchResult
from uniqa.funnel import PERSONAS, PERSONA_WEIGHTS

# ─── Brand ────────────────────────────────────────────────────────────────────
PRIMARY = "#0046A0"
ACCENT  = "#E2001A"
SUCCESS = "#1FA971"
INK     = "#1B1F24"
MUTED   = "#6B7280"

PERSONA_META = {
    "judith": {"emoji": "🧑\u200d💼", "label": "Judith — Rising Hybrid",
               "blurb": "30% of traffic. Trusts advisors, moderate price comfort. Wants reassurance."},
    "franz":  {"emoji": "🧑\u200d💻", "label": "Franz — Online Affine",
               "blurb": "50% of traffic. High comprehension, low patience. ONLINE ONLY — never hand to advisor."},
    "peter":  {"emoji": "🧑\u200d🔧", "label": "Peter — Service Affine",
               "blurb": "20% of traffic. Wants human contact. Best recovered via WhatsApp / callback."},
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
     font-weight:600; }}
  .outcome-bad {{ background:#FBEAEA; color:{ACCENT}; border-radius:12px; padding:14px 18px;
     font-weight:600; border:1px solid #F2C7C7; }}
  .wa-card {{ background:#E7F8EE; border-left:4px solid {SUCCESS}; border-radius:12px;
     padding:12px 16px; margin:6px 0; }}
  .tariff {{ display:inline-block; background:#fff; border:1px solid #E5EAF1; border-radius:10px;
     padding:8px 12px; margin:3px; text-align:center; min-width:96px; }}
</style>
""", unsafe_allow_html=True)

st.markdown(f"<h1 style='color:{PRIMARY};margin-bottom:0'>🧭 UNIQA Conversion Coach</h1>"
            f"<p style='color:{MUTED};margin-top:4px'>A detection + decision layer on top of the existing "
            f"UNIQA chatbot. It reads the customer's mind, and intervenes only when it helps.</p>",
            unsafe_allow_html=True)

# ─── HUD ──────────────────────────────────────────────────────────────────────
HUD_AXES = [
    ("attention", "Attention"),
    ("price_readiness", "Price readiness"),
    ("comprehension", "Comprehension"),
    ("trust", "Trust"),
    ("effort_budget", "Effort budget"),
    ("valence", "Mood"),
]

def render_hud(hud: dict, where):
    where.markdown("**🧠 Customer mind**")
    intent = hud.get("intent", "?")
    where.markdown(f"<span style='color:{PRIMARY};font-weight:600'>Intent: {intent}</span>",
                   unsafe_allow_html=True)
    for key, label in HUD_AXES:
        v = float(hud.get(key, 0.0))
        v = max(0.0, min(1.0, v))
        where.markdown(f"<span style='font-size:0.8rem;color:{MUTED}'>{label}</span>",
                       unsafe_allow_html=True)
        where.progress(v)


def render_token(tok, main):
    r = tok.render or {}
    kind = r.get("kind", tok.type.value)

    if tok.type == TokenType.STEP_ENTER:
        title = r.get("title", tok.step)
        prog  = r.get("progress", "")
        comp  = r.get("component", "")
        body = ""
        if r.get("tariffs"):
            body = "".join(
                f"<div class='tariff'><b>{t['name']}</b><br>€{t['price']}<br>"
                f"<span style='font-size:0.7rem;color:{'#1FA971' if t.get('online') else '#E2001A'}'>"
                f"{'online' if t.get('online') else 'Beratung'}</span></div>"
                for t in r["tariffs"])
        elif r.get("options"):
            body = " ".join(f"<span class='signal-pill' style='background:#EEF3FB;color:{PRIMARY}'>{o}</span>"
                            for o in r["options"])
        elif r.get("fields"):
            body = " ".join(f"<span class='signal-pill' style='background:#EEF3FB;color:{PRIMARY}'>{f}</span>"
                            for f in r["fields"])
        elif r.get("addons"):
            body = " ".join(f"<span class='signal-pill' style='background:#EEF3FB;color:{PRIMARY}'>{a}</span>"
                            for a in r["addons"])
        main.markdown(
            f"<div class='step-card'><span style='color:{MUTED};font-size:0.75rem'>{prog} · {comp}</span>"
            f"<div style='font-weight:600;font-size:1.05rem;color:{INK};margin:4px 0'>📄 {title}</div>{body}</div>",
            unsafe_allow_html=True)

    elif tok.type == TokenType.USER_SIGNAL:
        active = [k.replace('_',' ') for k, v in tok.payload.items()
                  if (isinstance(v, bool) and v) or (isinstance(v, (int, float)) and not isinstance(v, bool) and v)]
        pills = " ".join(f"<span class='signal-pill'>{k}: {tok.payload.get(k_orig)}</span>"
                         for k, k_orig in [(k.replace('_',' '), k) for k in tok.payload])
        main.markdown(f"<div style='margin:2px 0 8px 0'>👁️ signals &nbsp; {pills}</div>",
                      unsafe_allow_html=True)

    elif tok.type == TokenType.COACH_WIDGET:
        p = tok.payload
        main.markdown(
            f"<div class='coach-card'><span style='color:{PRIMARY};font-weight:700'>🧭 Coach → {p['action']}</span>"
            f"<div style='font-weight:600;margin:6px 0 2px 0'>{r.get('headline','')}</div>"
            f"<div style='color:{INK}'>{r.get('body','')}</div>"
            f"<div style='margin-top:6px'><span class='signal-pill' style='background:{PRIMARY};color:#fff'>"
            f"{r.get('cta','')}</span></div>"
            f"<div style='color:{MUTED};font-size:0.72rem;margin-top:6px'>"
            f"confidence {p.get('confidence')} · targets <b>{p.get('targets')}</b></div></div>",
            unsafe_allow_html=True)

    elif tok.type == TokenType.WHATSAPP:
        main.markdown(f"<div class='wa-card'>📲 <b>WhatsApp follow-up sent</b><br>"
                      f"<span style='color:{INK}'>{r.get('message','')}</span></div>",
                      unsafe_allow_html=True)

    elif tok.type == TokenType.CONVERT:
        main.markdown("<div class='outcome-good'>✅ CONVERTED — online purchase completed</div>",
                      unsafe_allow_html=True)

    elif tok.type == TokenType.BOUNCE:
        main.markdown(f"<div class='outcome-bad'>✗ BOUNCED at {tok.step} — reason: "
                      f"<b>{tok.payload.get('reason')}</b></div>", unsafe_allow_html=True)


def render_capture_view():
    """Real-mouse capture lives in the React app (webapp/). This view links to it and
    helps compare a captured session against the persona bot."""
    import glob, os, json
    CAP_URL = os.environ.get("UNIQA_CAPTURE_URL", "http://localhost:5173")
    st.markdown("### 🎯 Play & capture (real mouse)")
    st.markdown(
        "Capturing **real physical mouse behaviour** (hover dwell, movement tone, tab "
        "switches) needs the browser, so it lives in a small **React app**. It emits the "
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
        return
    pick = st.selectbox("Session", files, format_func=os.path.basename)
    persona = st.selectbox("Compare against persona", list(PERSONAS), index=1)
    st.code(f"python -m uniqa.compare {pick} --persona {persona}", language="bash")
    try:
        data = json.load(open(pick))
        st.caption(f"{len(data.get('events', []))} events · hint={data.get('persona_hint','?')} "
                   f"· {data.get('source','')}")
        st.dataframe(data.get("events", []), height=320, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not read {pick}: {e}")


# ─── Sidebar controls ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"### Controls")
    view = st.radio("View", ["Play & capture", "Live journey", "A/B uplift"], index=0)
    st.divider()

view = view  # noqa

# ════════════════════════════════════════════════════════════════════════════════
if view == "Play & capture":
    render_capture_view()

elif view == "Live journey":
    with st.sidebar:
        persona = st.selectbox("Persona", list(PERSONAS),
                               format_func=lambda p: PERSONA_META[p]["label"])
        coach_on = st.toggle("Coach ON", value=True)
        seed = st.number_input("Seed", value=7, step=1)
        st.caption(PERSONA_META[persona]["blurb"])
        if st.button("🎲 New journey", use_container_width=True):
            st.session_state.pop("trace_key", None)
            st.session_state["seed_bump"] = st.session_state.get("seed_bump", 0) + 1

    eff_seed = int(seed) + st.session_state.get("seed_bump", 0)
    key = f"{persona}-{coach_on}-{eff_seed}"

    if st.session_state.get("trace_key") != key:
        rng = random.Random(eff_seed)
        st.session_state["trace"] = run_journey(persona, rng, coach_on=bool(coach_on))
        st.session_state["trace_key"] = key
        st.session_state["cursor"] = len(st.session_state["trace"].tokens)  # show all by default

    trace = st.session_state["trace"]
    n_tok = len(trace.tokens)

    left, right = st.columns([3, 1])

    with right:
        st.markdown(f"### {PERSONA_META[persona]['emoji']} {persona.title()}")
        play_all = st.toggle("Show full journey", value=True)
        if play_all:
            cursor = n_tok
        else:
            cursor = st.slider("Token", 1, n_tok, st.session_state.get("cursor", n_tok))
        st.session_state["cursor"] = cursor
        # HUD reflects the mind at the latest STEP_ENTER up to cursor
        latest_hud = None
        for tok in trace.tokens[:cursor]:
            if tok.type == TokenType.STEP_ENTER:
                latest_hud = tok.payload
        if latest_hud:
            render_hud(latest_hud, st)

    with left:
        for tok in trace.tokens[:cursor]:
            render_token(tok, st)

    # Outcome banner
    if trace.converted:
        st.success(f"Outcome: CONVERTED · messages used: {trace.message_count}/3")
    else:
        extra = " · 📲 WhatsApp lead captured" if trace.whatsapp_sent else ""
        st.error(f"Outcome: bounced at {trace.bounced_at} ({trace.bounce_reason}) · "
                 f"messages used: {trace.message_count}/3{extra}")

# ════════════════════════════════════════════════════════════════════════════════
elif view == "A/B uplift":
    with st.sidebar:
        n = st.select_slider("Population (N)", options=[500, 1000, 2000, 5000, 10000], value=2000)
        seed = st.number_input("Seed", value=42, step=1)

    base  = run_batch(n=int(n), seed=int(seed), coach_on=False)
    coach = run_batch(n=int(n), seed=int(seed), coach_on=True)

    delta = coach.conversion_rate - base.conversion_rate
    rel = delta / base.conversion_rate * 100 if base.conversion_rate else 0

    # purchase-intent (coachable) cohort
    pi_base  = base.conv_by_intent.get("purchase", 0.0)
    pi_coach = coach.conv_by_intent.get("purchase", 0.0)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Conversion (overall)", f"{coach.conversion_rate*100:.1f}%",
              f"+{delta*100:.1f}pp")
    c2.metric("Relative uplift", f"+{rel:.0f}%")
    c3.metric("Purchase-intent conv.", f"{pi_coach*100:.0f}%",
              f"+{(pi_coach-pi_base)*100:.0f}pp")
    c4.metric("WhatsApp leads", f"{coach.whatsapp_leads}",
              help="Peter recovered via callback → WhatsApp follow-up")

    st.caption(f"Honest framing: overall conversion {base.conversion_rate*100:.1f}% → "
               f"{coach.conversion_rate*100:.1f}%. The coachable cohort (purchase intent) moves "
               f"{pi_base*100:.0f}% → {pi_coach*100:.0f}%. `not_ready` / `distraction` bounces are "
               f"intentionally left alone (no annoyance).")

    st.divider()
    a, b = st.columns(2)

    with a:
        st.markdown("#### Conversion by persona")
        df = pd.DataFrame({
            "persona": list(coach.per_persona_conv.keys()),
            "coach ON":  [coach.per_persona_conv[p]*100 for p in coach.per_persona_conv],
            "coach OFF": [base.per_persona_conv.get(p,0)*100 for p in coach.per_persona_conv],
        }).set_index("persona")
        st.bar_chart(df, color=["#B9C6DC", PRIMARY], stack=False)

    with b:
        st.markdown("#### Per-step bounce rate (coach ON)")
        steps = ["S4_TARIFF_SELECT", "S5_ADDON_SELECT", "S6_PERSONAL_DATA"]
        df2 = pd.DataFrame({
            "step": [s.split('_',1)[1] for s in steps],
            "coach OFF": [base.per_step_bounce.get(s,0)*100 for s in steps],
            "coach ON":  [coach.per_step_bounce.get(s,0)*100 for s in steps],
        }).set_index("step")
        st.bar_chart(df2, color=["#E7B6BB", ACCENT], stack=False)

    st.markdown("#### Bounce reasons (coach OFF → ON)")
    reasons = sorted(set(base.bounce_reasons) | set(coach.bounce_reasons))
    df3 = pd.DataFrame({
        "reason": reasons,
        "coach OFF": [base.bounce_reasons.get(r,0) for r in reasons],
        "coach ON":  [coach.bounce_reasons.get(r,0) for r in reasons],
    }).set_index("reason")
    st.bar_chart(df3, color=["#C9CDD3", PRIMARY], stack=False)
    st.caption("Coach shrinks the *coachable* reasons (price_shock, comparison_leave) while "
               "leaving not_ready/distraction untouched — that's the intervention-quality story.")
