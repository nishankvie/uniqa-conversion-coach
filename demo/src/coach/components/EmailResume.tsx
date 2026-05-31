import React from "react";
import type { BaseComponentProps } from "@json-render/react";

interface EmailResumeProps { subject?: string; to?: string; body?: string; }

const EmailResume = ({ props, emit }: BaseComponentProps<EmailResumeProps>) => (
  <div style={{ textAlign: "center", padding: "4px 0" }}>
    <div style={{ fontSize: 28, marginBottom: 8 }}>✉️</div>
    <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 6 }}>
      Fortsetzen per E-Mail
    </div>
    {props.to && (
      <div style={{ fontSize: 13, color: "#555", marginBottom: 12 }}>
        Link wird gesendet an: <strong>{props.to}</strong>
      </div>
    )}
    <button
      onClick={() => emit("send")}
      style={{
        background: "var(--blue, #005eb8)", color: "#fff",
        border: "none", borderRadius: 8, padding: "8px 18px",
        fontSize: 14, cursor: "pointer", fontWeight: 600,
      }}
    >
      E-Mail senden
    </button>
  </div>
);

export default EmailResume;
