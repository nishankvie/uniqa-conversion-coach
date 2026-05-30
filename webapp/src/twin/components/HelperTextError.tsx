import React from "react";
import type { BaseComponentProps } from "@json-render/react";

interface HelperTextErrorProps { text: string; }

const HelperTextError = ({ props }: BaseComponentProps<HelperTextErrorProps>) => (
  <div className="helper-text error" style={{ color: "var(--red)", fontSize: ".78rem", marginTop: 3, display: "flex", gap: 4, alignItems: "center" }}>
    <span aria-hidden="true">⚠</span>
    <span>{props.text}</span>
  </div>
);

export default HelperTextError;
