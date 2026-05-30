import React, { useEffect, useReducer, useRef, useState } from "react";
import { Recorder, HOVER_MS } from "./capture.js";

const PERSONAS = {
  judith: "Judith — Rising Hybrid",
  franz: "Franz — Online Affine",
  peter: "Peter — Service Affine",
};

const STEP_ID = {
  S1: "S1_COVERAGE_TYPE", S2: "S2_INSURED_PERSONS", S3: "S3_PERSONAL_INFO",
  S4: "S4_TARIFF_SELECT", S6: "S6_PERSONAL_DATA",
};
const ORDER = ["S1", "S2", "S3", "S4", "S6"];

const TARIFFS = [
  ["start", "Start", 38.74, true], ["optimal", "Optimal", 68.14, true],
  ["opt_plus", "Opt. Plus", 96.66, false], ["premium", "Premium", 140.15, false],
];
const ROWS = ["arztleistungen", "medikamente", "therapien", "hilfsmittel", "augen_op"];

// dwell-over-element -> a high-level hover the moment the cursor leaves
function Hoverable({ rec, elem, ev = "hover", className, style, children, onClick }) {
  const enter = useRef(0);
  return (
    <div className={className} style={style} onClick={onClick}
      onMouseEnter={() => (enter.current = performance.now())}
      onMouseLeave={() => {
        const d = (performance.now() - enter.current) / 1000;
        if (d * 1000 >= HOVER_MS) rec.hover(ev, elem, d);
      }}>
      {children}
    </div>
  );
}

export default function App() {
  const [persona, setPersona] = useState("franz");
  const [step, setStep] = useState("S1");
  const [done, setDone] = useState(null); // {term, url, payload}
  const [final, setFinal] = useState(null);
  const [form, setForm] = useState({ dob: "", sv: "", email: "", health: "no" });
  const [, force] = useReducer((x) => x + 1, 0);
  const recRef = useRef(null);

  // (re)start whenever persona changes
  useEffect(() => {
    const rec = new Recorder(persona);
    rec.onChange = force;
    recRef.current = rec;
    setForm({ dob: "", sv: "", email: "", health: "no" });
    setFinal(null);
    setDone(null);
    setStep("S1");
    rec.stepEnter(STEP_ID.S1);
  }, [persona]);

  // global REAL mouse + tab listeners
  useEffect(() => {
    const mv = (e) => recRef.current && recRef.current.onMouseMove(e.clientX, e.clientY);
    const vis = () => {
      const rec = recRef.current; if (!rec) return;
      if (document.visibilityState === "hidden") rec.tabBlur();
      else rec.tabFocus();
    };
    window.addEventListener("mousemove", mv, { passive: true });
    document.addEventListener("visibilitychange", vis);
    const clock = setInterval(force, 250);
    return () => {
      window.removeEventListener("mousemove", mv);
      document.removeEventListener("visibilitychange", vis);
      clearInterval(clock);
    };
  }, []);

  const rec = recRef.current;
  if (!rec) return null;

  function advance() {
    const i = ORDER.indexOf(step);
    if (i + 1 < ORDER.length) { const k = ORDER[i + 1]; setStep(k); rec.stepEnter(STEP_ID[k]); }
    else finishConvert();
  }
  function finishConvert() {
    rec.closeTone();
    rec.curStep = "S7_PURCHASE";
    rec.emit("step_enter");
    rec.emit("convert", null, "online_purchase");
    finish("convert");
  }
  function leave(reason) {
    rec.closeTone();
    rec.emit("abandon", null, reason);
    finish("abandon:" + reason);
  }
  function finish(term) {
    const payload = rec.payload();
    const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }));
    setDone({ term, url, payload });
  }

  function onSelect(target, isTariff = false) {
    if (isTariff) rec.emit("price_reveal", target, TARIFFS.find((t) => t[0] === target)[2]);
    rec.emit("select", target);
    advance();
  }
  function onNext() {
    if (form.dob) rec.emit("keystroke", "date_of_birth", form.dob.length);
    if (form.sv) { rec.emit("dropdown_open", "sv_number"); rec.emit("select", "sv_number", form.sv); }
    advance();
  }
  function onCalc() {
    if (form.email) rec.emit("keystroke", "email", form.email.length);
    rec.emit("submit", "health", form.health);
    const p = form.health === "yes" ? 71.0 : 68.14;
    rec.emit("price_reveal", "optimal_final", p);
    setFinal(p);
  }

  return (
    <div className="app">
      <header>
        <b>🧭 UNIQA funnel — mouse capture</b>
        <label>Role-play:&nbsp;
          <select value={persona} onChange={(e) => setPersona(e.target.value)}>
            {Object.entries(PERSONAS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
        <span className="clock">{rec.now()}s</span>
      </header>

      <div className="wrap">
        <div className="screen">
          {done ? <Done done={done} /> : (
            <>
              <Screen step={step} rec={rec} form={form} setForm={setForm}
                      final={final} onSelect={onSelect} onNext={onNext} onCalc={onCalc}
                      onConvert={finishConvert} />
              <div className="exit">
                <button className="ghost" onClick={() => leave("external_link")}>🔗 Leave via external link</button>
                <button className="ghost" onClick={() => leave("closed_page")}>✕ Leave / close page</button>
                <span className="hint">switching browser tab is captured automatically</span>
              </div>
            </>
          )}
        </div>

        <div className="side">
          <div className="sidehead">📋 High-level log <span className="tone">{rec.lastTone()}</span></div>
          <table><tbody>
            {rec.events.slice(-40).map((e, i) => (
              <tr key={i}>
                <td className="t">{e.t}</td><td className="ty">{e.type}</td>
                <td>{(e.step || "").split("_")[0]}</td><td>{e.target || ""}</td><td>{e.value ?? ""}</td>
              </tr>
            ))}
          </tbody></table>
        </div>
      </div>
    </div>
  );
}

function Screen({ step, rec, form, setForm, final, onSelect, onNext, onCalc, onConvert }) {
  if (step === "S1") return (
    <>
      <div className="crumbs">Angaben · 1/5</div>
      <h2>Wo möchten Sie abgesichert sein?</h2>
      <div className="row">
        <Hoverable rec={rec} elem="bei_arztbesuchen" className="card" onClick={() => onSelect("bei_arztbesuchen")}>Bei Arztbesuchen ✅</Hoverable>
        <Hoverable rec={rec} elem="im_krankenhaus" className="card" onClick={() => { rec.emit("select", "im_krankenhaus"); rec.closeTone(); rec.emit("abandon", null, "advisor_route(hospital)"); }}>Im Krankenhaus</Hoverable>
      </div>
    </>
  );
  if (step === "S2") return (
    <>
      <div className="crumbs">Angaben · 2/5</div>
      <h2>Wer soll versichert werden?</h2>
      <div className="row">
        <Hoverable rec={rec} elem="ich_selbst" className="card" onClick={() => onSelect("ich_selbst")}>Ich selbst ✅</Hoverable>
        <Hoverable rec={rec} elem="andere_personen" className="card" onClick={() => { rec.emit("select", "andere_personen"); rec.closeTone(); rec.emit("abandon", null, "advisor_route(others)"); }}>Andere Personen</Hoverable>
      </div>
    </>
  );
  if (step === "S3") return (
    <>
      <div className="crumbs">Angaben · 3/5</div>
      <h2>Für Ihre Prämie benötigen wir:</h2>
      <Hoverable rec={rec} elem="date_of_birth">
        <input placeholder="Geburtsdatum TT.MM.JJJJ" value={form.dob}
               onChange={(e) => setForm({ ...form, dob: e.target.value })} />
      </Hoverable>
      <Hoverable rec={rec} elem="sv_number">
        <select value={form.sv} onChange={(e) => setForm({ ...form, sv: e.target.value })}>
          <option value="">Sozialversicherung…</option>
          <option>ÖGK</option><option>BVAEB-OEB</option><option>SVS</option><option>BVAEB-EB</option>
        </select>
      </Hoverable>
      <div><button className="cta" onClick={onNext}>Weiter →</button></div>
    </>
  );
  if (step === "S4") return (
    <>
      <div className="crumbs">Produkt · 4/5 — Tarifauswahl</div>
      <h2>Welche Leistungen soll Ihre Privatarzt-Versicherung abdecken?</h2>
      <div className="row">
        {TARIFFS.map(([id, n, p, on]) => (
          <Hoverable key={id} rec={rec} elem={id} ev="price_hover" className="card tariff"
            onClick={() => on ? onSelect(id, true) : rec.emit("premium_click", id)}>
            <div>{n}</div><div className="p">€{p}</div>
            <div className={"b " + (on ? "online" : "adv")}>{on ? "online ✅" : "Beratung ☎"}</div>
          </Hoverable>
        ))}
      </div>
      <div className="row" style={{ marginTop: 10 }}>
        {ROWS.map((r) => (
          <Hoverable key={r} rec={rec} elem={r} ev="tooltip_open" className="tip">ⓘ {r}</Hoverable>
        ))}
      </div>
      <p className="hint">Pick Start or Optimal to finish online.</p>
    </>
  );
  if (step === "S6") return (
    <>
      <div className="crumbs">Abschluss · 5/5 — Daten + Gesundheit</div>
      <h2>Angaben zu Ihrer Person</h2>
      <Hoverable rec={rec} elem="email">
        <input placeholder="E-Mail" value={form.email}
               onChange={(e) => setForm({ ...form, email: e.target.value })} />
      </Hoverable>
      <Hoverable rec={rec} elem="health_answers">
        <div>Gesundheitsfragen:&nbsp;
          {["no", "yes"].map((h) => (
            <label key={h} style={{ marginRight: 10 }}>
              <input type="radio" name="h" checked={form.health === h}
                     onChange={() => setForm({ ...form, health: h })} /> {h}
            </label>
          ))}
        </div>
      </Hoverable>
      {final == null
        ? <div><button className="cta" onClick={onCalc}>Endpreis berechnen</button></div>
        : (<div>
            <p><b>Endpreis: €{final}/Monat</b></p>
            <button className="cta" onClick={onConvert}>Abschließen ✅</button>
          </div>)}
    </>
  );
  return null;
}

function Done({ done }) {
  const ok = done.term === "convert";
  const id = done.payload.session_id;
  return (
    <div>
      <div className={"done " + (ok ? "ok" : "bad")}>
        {ok ? "✅ Converted" : "✗ " + done.term} — session captured ({done.payload.events.length} high-level events).
      </div>
      <p><a href={done.url} download={id + ".json"}><button className="cta">⬇ Download log JSON</button></a></p>
      <p className="hint">Save into <code>_local/captures/</code>, then compare:</p>
      <pre>python -m uniqa.compare _local/captures/{id}.json --persona {done.payload.persona_hint}</pre>
      <textarea readOnly value={JSON.stringify(done.payload, null, 2)} />
    </div>
  );
}
