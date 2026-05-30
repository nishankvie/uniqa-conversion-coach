import React from "react";
import type { BaseComponentProps } from "@json-render/react";

interface StackProps { direction?: string; gap?: number; }

const Stack = ({ props, children }: BaseComponentProps<StackProps>) => (
  <div style={{
    display: "flex",
    flexDirection: (props.direction ?? "column") as "column" | "row",
    gap: props.gap ?? 8,
    flexWrap: "wrap",
  }}>
    {children}
  </div>
);

export default Stack;
