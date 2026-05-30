import React from "react";
import type { BaseComponentProps } from "@json-render/react";

interface TariffColumnProps {
  id: string; name: string; price: number;
  online: boolean; selected?: boolean;
}

const TariffColumn = ({ props, emit }: BaseComponentProps<TariffColumnProps>) => (
  <div
    className={`card tariff${props.selected ? " card-selected" : ""}`}
    onClick={() => emit("pick")}
    style={{
      width: 150, textAlign: "center", cursor: "pointer",
      border: `2px solid ${props.selected ? "var(--blue)" : "var(--bd)"}`,
      borderRadius: 10, padding: "14px 10px",
      background: props.selected ? "#EAF0FB" : "#fff", transition: ".12s",
    }}
  >
    <div style={{ fontWeight: 600, marginBottom: 6 }}>{props.name}</div>
    <div className="p" style={{ fontSize: "1.3rem", fontWeight: 700, color: "var(--ink)" }}>
      {new Intl.NumberFormat("de-AT", { style: "currency", currency: "EUR" }).format(props.price)}<small>/Mo</small>
    </div>
    <div className={`b ${props.online ? "online" : "adv"}`}
      style={{ fontSize: ".72rem", color: props.online ? "var(--green)" : "var(--red)", marginTop: 4 }}>
      {props.online ? "online ✅" : "Beratung ☎"}
    </div>
  </div>
);

export default TariffColumn;
