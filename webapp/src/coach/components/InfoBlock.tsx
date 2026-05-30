import React from "react";
import type { BaseComponentProps } from "@json-render/react";

interface InfoBlockProps { title: string; bullets: string[]; }

const InfoBlock = ({ props }: BaseComponentProps<InfoBlockProps>) => (
  <div style={{ fontSize: 14, color: "#333" }}>
    <div style={{ fontWeight: 700, marginBottom: 8 }}>{props.title}</div>
    <ul style={{ margin: 0, paddingLeft: 18 }}>
      {(props.bullets ?? []).map((b, i) => (
        <li key={i} style={{ marginBottom: 4 }}>{b}</li>
      ))}
    </ul>
  </div>
);

export default InfoBlock;
