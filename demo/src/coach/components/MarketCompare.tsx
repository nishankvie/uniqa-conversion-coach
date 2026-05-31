import React from "react";
import type { BaseComponentProps } from "@json-render/react";

interface MarketCompareProps { ours: number; market: number; note?: string; }

const MarketCompare = ({ props }: BaseComponentProps<MarketCompareProps>) => (
  <div style={{ fontSize: 14 }}>
    <div style={{ display: "flex", gap: 16, justifyContent: "center", marginBottom: 6 }}>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontWeight: 800, fontSize: 22, color: "var(--blue, #005eb8)" }}>
          €{props.ours.toFixed(2)}
        </div>
        <div style={{ fontSize: 11, color: "#555" }}>UNIQA</div>
      </div>
      <div style={{ alignSelf: "center", color: "#999", fontSize: 18 }}>vs</div>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontWeight: 700, fontSize: 22, color: "#888", textDecoration: "line-through" }}>
          €{props.market.toFixed(2)}
        </div>
        <div style={{ fontSize: 11, color: "#555" }}>Marktdurchschnitt</div>
      </div>
    </div>
    {props.note && <div style={{ color: "#555", textAlign: "center", fontSize: 12 }}>{props.note}</div>}
  </div>
);

export default MarketCompare;
