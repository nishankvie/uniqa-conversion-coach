import React from "react";
import type { BaseComponentProps } from "@json-render/react";

interface NavRowProps {
  showBack?: boolean; nextDisabled?: boolean;
  nextLabel?: string; backLabel?: string;
}

const NavRow = ({ props, emit }: BaseComponentProps<NavRowProps>) => (
  <div className="nav-row" style={{ display: "flex", gap: 8, marginTop: 16, alignItems: "center" }}>
    {props.showBack && (
      <button type="button" className="ghost"
        onClick={() => emit("back")}
        style={{ background: "#fff", border: "1px solid var(--bd)", borderRadius: 8, padding: "10px 16px", cursor: "pointer" }}>
        {props.backLabel ?? "Zurück"}
      </button>
    )}
    {!props.showBack && (
      <button type="button" className="ghost"
        onClick={() => emit("cancel")}
        style={{ background: "#fff", border: "1px solid var(--bd)", borderRadius: 8, padding: "10px 16px", cursor: "pointer" }}>
        Abbrechen
      </button>
    )}
    <button type="button" className="cta"
      disabled={!!props.nextDisabled}
      onClick={() => !props.nextDisabled && emit("next")}
      style={{
        background: "var(--blue)", color: "#fff", border: "none", borderRadius: 8,
        padding: "10px 16px", cursor: props.nextDisabled ? "not-allowed" : "pointer",
        opacity: props.nextDisabled ? 0.5 : 1,
      }}>
      {props.nextLabel ?? "Weiter"}
    </button>
  </div>
);

export default NavRow;
