import React from "react";
import type { BaseComponentProps } from "@json-render/react";

interface StepProps { id: string; index: number; current: number; phase: string; heading: string; }

// Renders children only when index === current.
// Visibility is also handled at schema level via visible:{$state...eq}
// but we keep this guard as belt-and-suspenders.
const Step = ({ props, children }: BaseComponentProps<StepProps>) => {
  if (props.index !== props.current) return null;
  return (
    <section aria-labelledby={`step-heading-${props.id}`} data-step={props.id}>
      {children}
    </section>
  );
};

export default Step;
