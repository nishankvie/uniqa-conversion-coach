import React from "react";
import type { BaseComponentProps } from "@json-render/react";

interface ProgressStepperProps { phases: string[]; current: number; }

const STEP_TO_PHASE = [0, 0, 0, 1, 3]; // currentStepIndex → phase index

const ProgressStepper = ({ props }: BaseComponentProps<ProgressStepperProps>) => {
  const phaseIdx = STEP_TO_PHASE[props.current] ?? 0;
  return (
    <div style={{ display: "flex", gap: 0, marginBottom: 20 }} role="navigation" aria-label="Fortschritt">
      {props.phases.map((phase, i) => (
        <div key={phase} style={{
          flex: 1, padding: "6px 12px", fontSize: ".8rem", fontWeight: i <= phaseIdx ? 700 : 400,
          color: i <= phaseIdx ? "var(--blue)" : "var(--muted)",
          borderBottom: i <= phaseIdx ? "3px solid var(--blue)" : "3px solid var(--bd)",
        }}>
          {phase}
        </div>
      ))}
    </div>
  );
};

export default ProgressStepper;
