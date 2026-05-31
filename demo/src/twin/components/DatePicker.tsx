// DatePicker — mirrors UR-DATEPICKER (TT.MM.JJJJ text input + calendar button).
// Direct state + recorder access for event emission.
import React from "react";
import type { BaseComponentProps } from "@json-render/react";
import { useStateStore } from "@json-render/react";
import { useRecorder } from "../recorderContext.js";
import { updateDerived } from "../transitions.js";
import HelperTextError from "./HelperTextError.js";

interface DatePickerProps {
  label: string; value?: string;
  error?: string; touched?: boolean;
}

const DatePicker = ({ props }: BaseComponentProps<DatePickerProps>) => {
  const { get, set } = useStateStore();
  const recorder = useRecorder();
  const storeSlice = { get: (p: string) => get(p), set: (p: string, v: unknown) => set(p, v) };

  const value   = (get("/formData/dob") as string) ?? "";
  const error   = (get("/errors/dob") as string) ?? "";
  const touched = (get("/touched/dob") as boolean) ?? false;
  const hasError = touched && !!error;

  return (
    <div style={{ marginBottom: 12 }}>
      <label style={{ display: "block", fontWeight: 600, marginBottom: 4, fontSize: ".9rem" }}>
        {props.label}
      </label>
      <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
        <input
          type="text"
          placeholder="TT.MM.JJJJ"
          value={value}
          className={hasError ? "is-invalid is-touched" : ""}
          data-field="date_of_birth"
          style={{ padding: "8px 10px", border: `1px solid ${hasError ? "var(--red)" : "var(--bd)"}`, borderRadius: 8, width: 200 }}
          onChange={(e) => {
            set("/formData/dob", e.target.value);
            if (e.target.value) recorder.emit("keystroke", "date_of_birth", e.target.value.length);
            updateDerived(storeSlice);
          }}
          onFocus={() => recorder.emit("field_focus", "date_of_birth")}
          onBlur={() => {
            set("/touched/dob", true);
            recorder.emit("field_blur", "date_of_birth");
            updateDerived(storeSlice);
          }}
        />
        <button type="button" aria-label="Datum im Kalender auswählen"
          style={{ padding: "8px 10px", border: "1px solid var(--bd)", borderRadius: 8, background: "#fff", cursor: "pointer" }}>
          📅
        </button>
      </div>
      {hasError && <HelperTextError props={{ text: error }} emit={() => {}} on={() => ({ emit: () => {}, shouldPreventDefault: false, bound: false })} />}
    </div>
  );
};

export default DatePicker;
