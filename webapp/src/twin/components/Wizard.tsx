import React from "react";
import type { BaseComponentProps } from "@json-render/react";

interface WizardProps { current: number; }

const Wizard = ({ children }: BaseComponentProps<WizardProps>) => (
  <div className="wizard" role="main" style={{ position: "relative" }}>
    {children}
  </div>
);

export default Wizard;
