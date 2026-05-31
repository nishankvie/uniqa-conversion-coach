// Capture REAL physical mouse events; emit ONLY high-level entries.
//
// raw (never emitted):  mousemove samples, per-element enter/leave, scroll
// high-level (emitted):  step_enter · hover / price_hover / tooltip_open (dwell >= HOVER_MS)
//                        select / tariff_click / premium_click · keystroke · dropdown_open · submit
//                        idle (no movement >= IDLE_MS) · tab_blur / tab_focus · convert / abandon
// plus a per-step MOUSE TONE (rushed | hesitant | deliberate | steady) back-filled
// onto that step's step_enter.thought.
//
// Output schema == contracts.ActivityLog, so `python -m uniqa.compare` consumes it
// and every event stays within the bot's legal vocabulary (format parity).

export const HOVER_MS = 450; // dwell over an element to count as a deliberate hover
export const IDLE_MS = 2500; // no movement -> an idle "attention gap"

function newMetric(t) {
  return { t, dist: 0, moves: 0, dirX: 0, dirY: 0, flips: 0, idle: 0,
           lastX: null, lastY: null, lastMove: t, rehover: {} };
}

export class Recorder {
  constructor(persona) {
    this.persona = persona;
    this.t0 = performance.now();
    this.events = [];
    this.curStep = null;
    this.stepEnterEv = null;
    this.metric = null;
    this.blurT = null;
    this.onChange = () => {};
  }

  now() { return +((performance.now() - this.t0) / 1000).toFixed(2); }

  emit(type, target = null, value = null, thought = null) {
    const e = { type, step: this.curStep, t: this.now(), target, value, source: "human" };
    if (thought) e.thought = thought;
    this.events.push(e);
    this.onChange();
    return e;
  }

  stepEnter(step) {
    this.closeTone();
    this.curStep = step;
    this.metric = newMetric(this.now());
    this.stepEnterEv = { type: "step_enter", step, t: this.now(), target: null, source: "human" };
    this.events.push(this.stepEnterEv);
    this.onChange();
  }

  // a deliberate hover extracted from real dwell-over-element
  hover(type, elem, dwellSec) {
    if (this.metric) this.metric.rehover[elem] = (this.metric.rehover[elem] || 0) + 1;
    this.emit(type, elem, +dwellSec.toFixed(1));
  }

  onMouseMove(x, y) {
    const m = this.metric;
    if (!m) return;
    const t = this.now();
    if ((t - m.lastMove) * 1000 > IDLE_MS) {
      m.idle += t - m.lastMove;
      this.emit("idle", null, +(t - m.lastMove).toFixed(1)); // high-level attention gap
    }
    m.lastMove = t;
    if (m.lastX != null) {
      const dx = x - m.lastX, dy = y - m.lastY;
      m.dist += Math.hypot(dx, dy);
      m.moves++;
      const sx = Math.sign(dx), sy = Math.sign(dy);
      if (sx !== 0 && sx !== m.dirX) { m.flips++; m.dirX = sx; }
      if (sy !== 0 && sy !== m.dirY) { m.flips++; m.dirY = sy; }
    }
    m.lastX = x; m.lastY = y;
  }

  // general "tone" of mouse usage for the step, from raw movement aggregates
  tone() {
    const m = this.metric;
    if (!m) return "steady";
    const dur = this.now() - m.t;
    if (dur < 2.5 && m.moves < 12) return "rushed";
    const reh = Object.values(m.rehover).filter((c) => c > 1).length;
    if (m.flips > 14 || reh >= 2) return "hesitant";
    if (m.idle / Math.max(dur, 0.1) > 0.45) return "deliberate";
    return "steady";
  }

  closeTone() {
    if (this.metric && this.stepEnterEv) {
      this.stepEnterEv.thought = "mouse:" + this.tone();
      this.onChange();
    }
  }

  tabBlur() { this.blurT = this.now(); this.emit("tab_blur", null, "tab_switch"); }
  tabFocus() {
    if (this.blurT != null) {
      this.emit("tab_focus", null, +(this.now() - this.blurT).toFixed(1)); // real seconds away
      this.blurT = null;
    }
  }

  payload() {
    return {
      schema: "1.0",
      session_id: "cap_" + Date.now(),
      persona_hint: this.persona,
      source: "human (mouse-capture, react)",
      events: this.events,
    };
  }

  lastTone() {
    const e = [...this.events].reverse().find((x) => x.thought);
    return e ? e.thought : "";
  }
}
