import React from "react";
import type { BaseComponentProps } from "@json-render/react";

interface BottomSheetProps { title: string; }

const BottomSheet = ({ props, emit, children }: BaseComponentProps<BottomSheetProps>) => (
  <div style={{
    background: "#fff", borderRadius: "16px 16px 0 0",
    boxShadow: "0 -4px 24px rgba(0,0,0,0.18)",
    padding: "20px 24px 32px",
    minWidth: 300, maxWidth: 480,
  }}>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
      <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>{props.title}</h3>
      <button
        aria-label="Schließen" onClick={() => emit("dismiss")}
        style={{ background: "none", border: "none", cursor: "pointer", fontSize: 20, color: "#666" }}
      >✕</button>
    </div>
    {children}
  </div>
);

export default BottomSheet;
