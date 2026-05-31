import React from "react";
import type { BaseComponentProps } from "@json-render/react";

interface CallbackCTAProps { channel?: string; phone?: string; }

const CallbackCTA = ({ props, emit }: BaseComponentProps<CallbackCTAProps>) => (
  <div style={{ textAlign: "center", padding: "4px 0" }}>
    <div style={{ fontSize: 14, color: "#444", marginBottom: 12 }}>
      {props.channel === "phone"
        ? "Persönliche Beratung am Telefon"
        : "Kostenloser Rückruf von unserem Team"}
    </div>
    {props.phone && (
      <div style={{ fontWeight: 700, fontSize: 18, color: "var(--blue, #005eb8)", marginBottom: 10 }}>
        📞 {props.phone}
      </div>
    )}
    <button
      onClick={() => emit("accept")}
      style={{
        background: "var(--blue, #005eb8)", color: "#fff",
        border: "none", borderRadius: 8, padding: "10px 20px",
        fontSize: 14, fontWeight: 600, cursor: "pointer",
      }}
    >
      Jetzt Termin vereinbaren
    </button>
  </div>
);

export default CallbackCTA;
