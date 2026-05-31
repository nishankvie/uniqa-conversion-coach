import React from "react";
import type { BaseComponentProps } from "@json-render/react";

interface BannerProps { tone?: string; text: string; }

const TONE_COLORS: Record<string, string> = {
  info: "#e8f4fb", warn: "#fff8e1", success: "#e8f5e9",
};

const Banner = ({ props, emit }: BaseComponentProps<BannerProps>) => (
  <div style={{
    background: TONE_COLORS[props.tone ?? "info"] ?? TONE_COLORS.info,
    border: "1px solid #ccc", borderRadius: 8,
    padding: "10px 36px 10px 14px", fontSize: 14,
    position: "relative", color: "#333",
  }}>
    {props.text}
    <button
      aria-label="Schließen" onClick={() => emit("dismiss")}
      style={{ position: "absolute", top: 8, right: 10, background: "none", border: "none", cursor: "pointer", fontSize: 16, color: "#666" }}
    >✕</button>
  </div>
);

export default Banner;
