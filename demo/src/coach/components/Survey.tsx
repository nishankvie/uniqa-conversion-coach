import React from "react";
import type { BaseComponentProps } from "@json-render/react";

interface SurveyProps { question: string; options: string[]; }

const Survey = ({ props, emit }: BaseComponentProps<SurveyProps>) => (
  <div style={{ fontSize: 14 }}>
    <div style={{ fontWeight: 700, marginBottom: 10 }}>{props.question}</div>
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {(props.options ?? []).map((opt, i) => (
        <button
          key={i}
          onClick={() => emit("pick")}
          style={{
            background: "#f5f5f5", border: "1px solid #ddd",
            borderRadius: 6, padding: "8px 12px", fontSize: 13,
            cursor: "pointer", textAlign: "left",
          }}
        >
          {opt}
        </button>
      ))}
    </div>
  </div>
);

export default Survey;
