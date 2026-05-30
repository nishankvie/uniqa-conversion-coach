import React from "react";
import type { BaseComponentProps } from "@json-render/react";

interface PriceReframeProps { monthly: number; daily: number; }

const PriceReframe = ({ props }: BaseComponentProps<PriceReframeProps>) => (
  <div style={{ textAlign: "center", padding: "8px 0" }}>
    <div style={{ fontSize: 28, fontWeight: 800, color: "var(--blue, #005eb8)" }}>
      €{props.monthly.toFixed(2)}<span style={{ fontSize: 14, fontWeight: 400 }}>/Monat</span>
    </div>
    <div style={{ fontSize: 14, color: "#555", marginTop: 4 }}>
      = nur <strong>€{props.daily.toFixed(2)}</strong> pro Tag
    </div>
    <div style={{ fontSize: 12, color: "#888", marginTop: 2 }}>
      weniger als ein Kaffee ☕
    </div>
  </div>
);

export default PriceReframe;
