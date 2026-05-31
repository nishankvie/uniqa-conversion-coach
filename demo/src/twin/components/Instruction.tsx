import React from "react";
import type { BaseComponentProps } from "@json-render/react";

interface InstructionProps { text: string; }

const Instruction = ({ props }: BaseComponentProps<InstructionProps>) => (
  <p style={{ color: "var(--muted)", fontSize: ".9rem", margin: "0 0 12px" }}>{props.text}</p>
);

export default Instruction;
