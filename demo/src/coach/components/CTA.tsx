import React from "react";
import type { BaseComponentProps } from "@json-render/react";

interface CTAProps { label: string; variant?: string; }

const CTA = ({ props, emit }: BaseComponentProps<CTAProps>) => (
  <button
    onClick={() => emit("press")}
    style={{
      background: props.variant === "secondary" ? "#fff" : "var(--blue, #005eb8)",
      color: props.variant === "secondary" ? "var(--ink, #1a1a1a)" : "#fff",
      border: props.variant === "secondary" ? "1px solid #ccc" : "none",
      borderRadius: 8, padding: "10px 18px",
      fontSize: 14, fontWeight: 600, cursor: "pointer",
    }}
  >
    {props.label}
  </button>
);

export default CTA;
