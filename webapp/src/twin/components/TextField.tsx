import React from "react";
import type { BaseComponentProps } from "@json-render/react";
import { useStateStore } from "@json-render/react";
import { useRecorder } from "../recorderContext.js";
import { updateDerived } from "../transitions.js";
import HelperTextError from "./HelperTextError.js";

interface TextFieldProps {
  label: string; value?: string;
  error?: string; touched?: boolean; type?: string;
  fieldPath?: string; // e.g. "/formData/email"
}

const TextField = ({ props }: BaseComponentProps<TextFieldProps>) => {
  const { get, set } = useStateStore();
  const recorder = useRecorder();
  const storeSlice = { get: (p: string) => get(p), set: (p: string, v: unknown) => set(p, v) };

  const fieldPath = props.fieldPath ?? "";
  const value   = fieldPath ? ((get(fieldPath) as string) ?? "") : (props.value ?? "");
  const error   = props.error ?? "";
  const touched = props.touched ?? false;
  const hasError = touched && !!error;

  return (
    <div style={{ marginBottom: 10 }}>
      <label style={{ display: "block", fontWeight: 600, marginBottom: 4, fontSize: ".9rem" }}>
        {props.label}
      </label>
      <input
        type={props.type ?? "text"}
        value={value}
        className={hasError ? "is-invalid is-touched" : ""}
        style={{ padding: "8px 10px", border: `1px solid ${hasError ? "var(--red)" : "var(--bd)"}`, borderRadius: 8, width: 260 }}
        onChange={(e) => {
          if (fieldPath) {
            set(fieldPath, e.target.value);
            recorder.emit("keystroke", fieldPath.split("/").pop() ?? "field", e.target.value.length);
            updateDerived(storeSlice);
          }
        }}
        onFocus={() => recorder.emit("field_focus", fieldPath.split("/").pop() ?? "field")}
        onBlur={() => recorder.emit("field_blur", fieldPath.split("/").pop() ?? "field")}
      />
      {hasError && <HelperTextError props={{ text: error }} emit={() => {}} on={() => ({ emit: () => {}, shouldPreventDefault: false, bound: false })} />}
    </div>
  );
};

export default TextField;
