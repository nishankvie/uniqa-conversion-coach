import React from "react";
import type { BaseComponentProps } from "@json-render/react";

interface FinalPriceProps { price?: number | null; deltaFromProvisional?: number | null; }

const FinalPrice = ({ props }: BaseComponentProps<FinalPriceProps>) => {
  if (props.price == null) return null;
  const fmt = (n: number) => new Intl.NumberFormat("de-AT", { style: "currency", currency: "EUR" }).format(n);
  const delta = props.deltaFromProvisional;
  return (
    <div style={{ background: "#E7F8EE", borderRadius: 10, padding: "14px 18px", marginTop: 16 }}>
      <div style={{ fontSize: ".85rem", color: "var(--muted)", marginBottom: 4 }}>Ihr individueller Beitrag</div>
      <div style={{ fontSize: "1.6rem", fontWeight: 700, color: "var(--blue)" }}>
        {fmt(props.price)}<small style={{ fontSize: ".85rem", fontWeight: 400 }}>/Monat</small>
      </div>
      {delta != null && delta !== 0 && (
        <div style={{ fontSize: ".8rem", color: delta > 0 ? "var(--red)" : "var(--green)", marginTop: 4 }}>
          {delta > 0 ? "+" : ""}{fmt(delta)} gegenüber vorläufiger Prämie
        </div>
      )}
    </div>
  );
};

export default FinalPrice;
