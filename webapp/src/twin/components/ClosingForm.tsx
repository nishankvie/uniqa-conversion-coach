// ClosingForm — S12 closing / consent step (placeholder; step E may extend).
import React from "react";
import type { BaseComponentProps } from "@json-render/react";

interface ClosingFormProps {
  values: Record<string, unknown>;
  errors: Record<string, unknown>;
}

const ClosingForm = ({ props }: BaseComponentProps<ClosingFormProps>) => (
  <div style={{ padding: "12px 0" }}>
    <p style={{ color: "var(--muted)", fontSize: ".9rem" }}>
      Abschluss-Formular (Schritt 5 / S12). Konsent + Zahlung.
    </p>
  </div>
);

export default ClosingForm;
