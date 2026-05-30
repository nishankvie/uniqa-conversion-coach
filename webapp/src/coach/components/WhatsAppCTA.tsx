import React from "react";
import type { BaseComponentProps } from "@json-render/react";

interface WhatsAppCTAProps { number?: string; message?: string; }

const WhatsAppCTA = ({ props, emit }: BaseComponentProps<WhatsAppCTAProps>) => {
  const href = props.number
    ? `https://wa.me/${props.number.replace(/\D/g, "")}?text=${encodeURIComponent(props.message ?? "")}`
    : "#";

  return (
    <div style={{ textAlign: "center", padding: "4px 0" }}>
      <div style={{ fontSize: 14, color: "#444", marginBottom: 10 }}>
        Chat mit uns auf WhatsApp
      </div>
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        onClick={() => emit("accept")}
        style={{
          display: "inline-block",
          background: "#25D366", color: "#fff",
          borderRadius: 8, padding: "10px 20px",
          fontSize: 14, fontWeight: 600, textDecoration: "none",
        }}
      >
        💬 WhatsApp öffnen
      </a>
    </div>
  );
};

export default WhatsAppCTA;
