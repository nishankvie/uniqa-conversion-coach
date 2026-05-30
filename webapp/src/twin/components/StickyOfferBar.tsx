import React from "react";
import type { BaseComponentProps } from "@json-render/react";

interface StickyOfferBarProps { label: string; price?: number | null; }

const StickyOfferBar = ({ props }: BaseComponentProps<StickyOfferBarProps>) => {
  if (props.price == null) return null;
  const formatted = new Intl.NumberFormat("de-AT", { style: "currency", currency: "EUR" }).format(props.price);
  return (
    <div style={{
      position: "sticky", bottom: 0, background: "var(--blue)", color: "#fff",
      padding: "10px 16px", borderRadius: "8px 8px 0 0",
      display: "flex", justifyContent: "space-between", alignItems: "center",
      fontSize: ".9rem", fontWeight: 600, marginTop: 16,
    }}>
      <span>{props.label}</span>
      <span style={{ fontSize: "1.2rem" }}>{formatted}<small style={{ fontWeight: 400 }}>/Monat</small></span>
    </div>
  );
};

export default StickyOfferBar;
