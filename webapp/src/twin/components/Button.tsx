import React from "react";
import type { BaseComponentProps } from "@json-render/react";

interface ButtonProps { label: string; variant?: string; disabled?: boolean; }

const Button = ({ props, emit }: BaseComponentProps<ButtonProps>) => (
  <button
    type="button"
    className={props.variant === "secondary" ? "ghost" : "cta"}
    disabled={!!props.disabled}
    onClick={() => !props.disabled && emit("press")}
    style={{
      background: props.variant === "secondary" ? "#fff" : "var(--blue)",
      color: props.variant === "secondary" ? "var(--ink)" : "#fff",
      border: props.variant === "secondary" ? "1px solid var(--bd)" : "none",
      borderRadius: 8, padding: "10px 16px", cursor: props.disabled ? "not-allowed" : "pointer",
      opacity: props.disabled ? 0.5 : 1, marginRight: 6,
    }}
  >
    {props.label}
  </button>
);

export default Button;
