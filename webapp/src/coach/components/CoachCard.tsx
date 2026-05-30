// CoachCard.tsx — Primary coaching overlay card.
// Emits "cta" when the action button is clicked, "dismiss" on ✕.
import React from "react";
import type { BaseComponentProps } from "@json-render/react";

interface CoachCardProps {
  intent: string;
  headline: string;
  body: string;
  cta?: string;
  surface?: string;
}

const CoachCard = ({ props, emit }: BaseComponentProps<CoachCardProps>) => (
  <div
    role="dialog"
    aria-label={props.headline}
    style={{
      background: "#fff",
      border: "2px solid var(--blue, #005eb8)",
      borderRadius: 12,
      boxShadow: "0 4px 24px rgba(0,0,0,0.18)",
      padding: "20px 24px 16px",
      minWidth: 280,
      maxWidth: 360,
      position: "relative",
    }}
  >
    <button
      aria-label="Schließen"
      onClick={() => emit("dismiss")}
      style={{
        position: "absolute", top: 10, right: 12,
        background: "none", border: "none", cursor: "pointer",
        fontSize: 18, color: "#666", lineHeight: 1,
      }}
    >
      ✕
    </button>
    <div style={{ fontSize: 11, fontWeight: 700, color: "var(--blue, #005eb8)", textTransform: "uppercase", marginBottom: 6 }}>
      🎯 Coach
    </div>
    <h3 style={{ margin: "0 0 8px", fontSize: 16, fontWeight: 700, paddingRight: 24 }}>
      {props.headline}
    </h3>
    <p style={{ margin: "0 0 14px", fontSize: 14, color: "#444", lineHeight: 1.5 }}>
      {props.body}
    </p>
    {props.cta && (
      <button
        className="cta"
        onClick={() => emit("cta")}
        style={{
          background: "var(--blue, #005eb8)", color: "#fff",
          border: "none", borderRadius: 8, padding: "8px 16px",
          fontSize: 14, cursor: "pointer", fontWeight: 600,
        }}
      >
        {props.cta}
      </button>
    )}
  </div>
);

export default CoachCard;
