import React from "react";
import type { BaseComponentProps } from "@json-render/react";

interface ChoiceCardProps {
  id: string; title: string; icon?: string;
  features?: string[]; checked?: boolean; mode?: string;
}

const ChoiceCard = ({ props, emit }: BaseComponentProps<ChoiceCardProps>) => {
  const isChecked = !!props.checked;
  return (
    <div
      className={`card${isChecked ? " card-selected" : ""}`}
      role={props.mode === "radio" ? "radio" : "checkbox"}
      aria-checked={isChecked}
      tabIndex={0}
      onClick={() => emit("toggle")}
      onKeyDown={(e) => (e.key === " " || e.key === "Enter") && emit("toggle")}
      style={{
        border: `2px solid ${isChecked ? "var(--blue)" : "var(--bd)"}`,
        borderRadius: 10, padding: "14px 16px", cursor: "pointer",
        background: isChecked ? "#EAF0FB" : "#fff",
        minWidth: 180, position: "relative", transition: ".12s",
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 8 }}>{props.title}</div>
      {props.features && props.features.length > 0 && (
        <ul style={{ margin: 0, paddingLeft: 16, fontSize: ".8rem", color: "var(--muted)" }}>
          {props.features.map((f) => <li key={f}>{f}</li>)}
        </ul>
      )}
      {/* checkbox indicator top-right (Reef parity) */}
      <span style={{
        position: "absolute", top: 10, right: 10, width: 18, height: 18,
        borderRadius: props.mode === "radio" ? "50%" : 4,
        border: `2px solid ${isChecked ? "var(--blue)" : "var(--bd)"}`,
        background: isChecked ? "var(--blue)" : "#fff",
        display: "flex", alignItems: "center", justifyContent: "center",
        color: "#fff", fontSize: ".7rem",
      }}>
        {isChecked ? "✓" : ""}
      </span>
    </div>
  );
};

export default ChoiceCard;
