import React from "react";
import type { BaseComponentProps } from "@json-render/react";

interface HeadingProps { text: string; level?: number; }

const Heading = ({ props }: BaseComponentProps<HeadingProps>) => {
  const level = props.level ?? 2;
  const Tag = `h${Math.min(Math.max(level, 1), 6)}` as keyof JSX.IntrinsicElements;
  return <Tag style={{ color: "var(--blue)", margin: ".2rem 0 1rem", fontSize: "1.15rem" }}>{props.text}</Tag>;
};

export default Heading;
