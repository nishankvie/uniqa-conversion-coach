// SearchableSelect — CDK-overlay-style searchable select (mirrors UR-SELECT).
import React, { useRef } from "react";
import type { BaseComponentProps } from "@json-render/react";
import { useStateStore } from "@json-render/react";
import { useRecorder } from "../recorderContext.js";
import { updateDerived } from "../transitions.js";
import HelperTextError from "./HelperTextError.js";

interface SearchableSelectProps {
  label: string; value?: string;
  error?: string; touched?: boolean;
  placeholder?: string; options: string[];
}

const SearchableSelect = ({ props }: BaseComponentProps<SearchableSelectProps>) => {
  const { get, set } = useStateStore();
  const recorder = useRecorder();
  const storeSlice = { get: (p: string) => get(p), set: (p: string, v: unknown) => set(p, v) };

  const value   = (get("/formData/sv") as string) ?? "";
  const open    = (get("/svSelect/open") as boolean) ?? false;
  const filter  = (get("/formData/svFilter") as string) ?? "";
  const error   = (get("/errors/sv") as string) ?? "";
  const touched = (get("/touched/sv") as boolean) ?? false;
  const hasError = touched && !!error;

  const filtered = props.options.filter((o) =>
    filter ? o.toLowerCase().includes(filter.toLowerCase()) : true
  );

  function openOverlay() {
    set("/svSelect/open", true);
    recorder.emit("dropdown_open", "sv_number");
    updateDerived(storeSlice);
  }

  function closeOverlay() {
    set("/svSelect/open", false);
    set("/touched/sv", true);
    updateDerived(storeSlice);
  }

  function pick(option: string) {
    set("/formData/sv", option);
    set("/formData/svFilter", "");
    set("/svSelect/open", false);
    set("/touched/sv", true);
    recorder.emit("select", "sv_number", option);
    updateDerived(storeSlice);
  }

  return (
    <div style={{ marginBottom: 12, position: "relative" }}>
      <label style={{ display: "block", fontWeight: 600, marginBottom: 4, fontSize: ".9rem" }}>
        {props.label}
      </label>
      <button type="button"
        className={hasError ? "is-invalid is-touched" : ""}
        onClick={open ? closeOverlay : openOverlay}
        style={{
          width: 260, padding: "8px 10px", textAlign: "left",
          border: `1px solid ${hasError ? "var(--red)" : "var(--bd)"}`,
          borderRadius: 8, background: "#fff", cursor: "pointer",
          display: "flex", justifyContent: "space-between", alignItems: "center",
        }}
        aria-haspopup="listbox" aria-expanded={open}
      >
        <span style={{ color: value ? "var(--ink)" : "var(--muted)" }}>
          {value || (props.placeholder ?? "Bitte treffen Sie eine Auswahl")}
        </span>
        <span>{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div role="listbox" style={{
          position: "absolute", zIndex: 100, top: "100%", left: 0, width: 260,
          background: "#fff", border: "1px solid var(--bd)", borderRadius: 8,
          boxShadow: "0 4px 16px rgba(0,0,0,.12)", maxHeight: 220, overflowY: "auto",
        }}>
          <div style={{ padding: "6px 8px", borderBottom: "1px solid var(--bd)" }}>
            <input type="text" placeholder="Filtern…"
              autoFocus value={filter}
              style={{ width: "100%", padding: "5px 8px", border: "1px solid var(--bd)", borderRadius: 6 }}
              onChange={(e) => {
                set("/formData/svFilter", e.target.value);
                recorder.emit("keystroke", "sv_number", e.target.value.length);
              }}
            />
          </div>
          {filtered.map((opt) => (
            <div key={opt} role="option" aria-selected={opt === value}
              onClick={() => pick(opt)}
              style={{
                padding: "9px 12px", cursor: "pointer", fontSize: ".9rem",
                background: opt === value ? "#EAF0FB" : "transparent",
              }}>
              {opt}
            </div>
          ))}
        </div>
      )}
      {hasError && <HelperTextError props={{ text: error }} emit={() => {}} on={() => ({ emit: () => {}, shouldPreventDefault: false, bound: false })} />}
    </div>
  );
};

export default SearchableSelect;
