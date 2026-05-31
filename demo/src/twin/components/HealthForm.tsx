// HealthForm — S6 personal data + health questions form.
import React from "react";
import type { BaseComponentProps } from "@json-render/react";
import { useStateStore } from "@json-render/react";
import { useRecorder } from "../recorderContext.js";
import { updateDerived, advance } from "../transitions.js";
import HelperTextError from "./HelperTextError.js";

interface HealthFormProps {
  values: Record<string, unknown>;
  errors: Record<string, unknown>;
}

const FIELDS: { key: string; label: string; type?: string }[] = [
  { key: "firstName", label: "Vorname" },
  { key: "lastName",  label: "Nachname" },
  { key: "email",     label: "E-Mail", type: "email" },
  { key: "height",    label: "Größe (cm)", type: "number" },
  { key: "weight",    label: "Gewicht (kg)", type: "number" },
];

const HealthForm = ({ props }: BaseComponentProps<HealthFormProps>) => {
  const { get, set } = useStateStore();
  const recorder = useRecorder();
  const storeSlice = { get: (p: string) => get(p), set: (p: string, v: unknown) => set(p, v) };

  const errors = (get("/errors") as Record<string, string>) ?? {};
  const formData = (get("/formData") as Record<string, unknown>) ?? {};
  const health = (formData.health as string) ?? "no";

  function setField(key: string, value: unknown) {
    set(`/formData/${key}`, value);
    recorder.emit("keystroke", key, typeof value === "string" ? value.length : 0);
    updateDerived(storeSlice);
  }

  function submitHealth() {
    advance("S6_PERSONAL_DATA", storeSlice, recorder);
  }

  return (
    <div style={{ maxWidth: 480 }}>
      {FIELDS.map(({ key, label, type }) => {
        const val = (formData[key] as string) ?? "";
        const err = errors[key] as string | undefined;
        return (
          <div key={key} style={{ marginBottom: 10 }}>
            <label style={{ display: "block", fontWeight: 600, marginBottom: 4, fontSize: ".9rem" }}>{label}</label>
            <input
              type={type ?? "text"} value={val}
              style={{ padding: "8px 10px", border: `1px solid ${err ? "var(--red)" : "var(--bd)"}`, borderRadius: 8, width: 260 }}
              onChange={(e) => setField(key, e.target.value)}
              onFocus={() => recorder.emit("field_focus", key)}
              onBlur={() => { set(`/touched/${key}`, true); recorder.emit("field_blur", key); }}
            />
            {err && <HelperTextError props={{ text: err }} emit={() => {}} on={() => ({ emit: () => {}, shouldPreventDefault: false, bound: false })} />}
          </div>
        );
      })}

      {/* Health question */}
      <div style={{ marginBottom: 12 }}>
        <label style={{ display: "block", fontWeight: 600, marginBottom: 4, fontSize: ".9rem" }}>
          Gesundheitsfragen
        </label>
        {["no", "yes"].map((h) => (
          <label key={h} style={{ marginRight: 16, cursor: "pointer" }}>
            <input type="radio" name="health" checked={health === h}
              onChange={() => setField("health", h)} style={{ marginRight: 4 }} />
            {h === "no" ? "Keine Vorerkrankungen" : "Mit Vorerkrankungen"}
          </label>
        ))}
      </div>

      {/* Consents */}
      {["consentTos", "consentPrivacy"].map((key) => {
        const checked = !!(formData[key] as boolean);
        const err = errors[key] as string | undefined;
        return (
          <div key={key} style={{ marginBottom: 8, display: "flex", gap: 8, alignItems: "flex-start" }}>
            <input type="checkbox" id={key} checked={checked}
              onChange={(e) => {
                set(`/formData/${key}`, e.target.checked);
                updateDerived(storeSlice);
              }} />
            <label htmlFor={key} style={{ fontSize: ".85rem" }}>
              {key === "consentTos" ? "Ich stimme den Allgemeinen Geschäftsbedingungen zu." : "Ich stimme der Datenschutzerklärung zu."}
            </label>
            {err && <HelperTextError props={{ text: err }} emit={() => {}} on={() => ({ emit: () => {}, shouldPreventDefault: false, bound: false })} />}
          </div>
        );
      })}

      <button type="button" className="cta"
        style={{ background: "var(--blue)", color: "#fff", border: 0, borderRadius: 8, padding: "10px 16px", cursor: "pointer", marginTop: 8 }}
        onClick={submitHealth}>
        Endpreis berechnen
      </button>
    </div>
  );
};

export default HealthForm;
