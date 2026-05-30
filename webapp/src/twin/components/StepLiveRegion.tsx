import React from "react";
import type { BaseComponentProps } from "@json-render/react";

interface StepLiveRegionProps { heading: string; }

const StepLiveRegion = ({ props }: BaseComponentProps<StepLiveRegionProps>) => (
  <div role="status" aria-live="polite" style={{ position: "absolute", left: "-9999px" }}>
    {props.heading ? `Ein neuer Schritt wurde geladen: ${props.heading}` : ""}
  </div>
);

export default StepLiveRegion;
