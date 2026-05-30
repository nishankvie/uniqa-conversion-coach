import React from "react";
import type { BaseComponentProps } from "@json-render/react";

interface TooltipProps { anchor?: string; body: string; }

const Tooltip = ({ props, emit }: BaseComponentProps<TooltipProps>) => (
  <div style={{
    background: "#1a1a1a", color: "#fff", borderRadius: 6,
    padding: "8px 12px", fontSize: 13, maxWidth: 260,
    boxShadow: "0 2px 10px rgba(0,0,0,0.2)", position: "relative",
  }}>
    {props.body}
    <button
      aria-label="Schließen" onClick={() => emit("dismiss")}
      style={{ position: "absolute", top: 4, right: 6, background: "none", border: "none", cursor: "pointer", fontSize: 14, color: "#aaa" }}
    >✕</button>
  </div>
);

export default Tooltip;
