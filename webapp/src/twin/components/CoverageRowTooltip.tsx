// CoverageRowTooltip — (i) tooltip for a tariff coverage row.
import React from "react";
import type { BaseComponentProps } from "@json-render/react";
import { useStateStore } from "@json-render/react";
import { useRecorder } from "../recorderContext.js";

interface CoverageRowTooltipProps { row: string; body: string; open?: boolean; }

const CoverageRowTooltip = ({ props }: BaseComponentProps<CoverageRowTooltipProps>) => {
  const { get, set } = useStateStore();
  const recorder = useRecorder();
  const open = (get(`/tooltipsOpen/${props.row}`) as boolean) ?? false;

  function toggle() {
    const next = !open;
    set(`/tooltipsOpen/${props.row}`, next);
    if (next) recorder.emit("tooltip_open", props.row);
  }

  return (
    <div style={{ display: "inline-block", position: "relative", margin: 3 }}>
      <button type="button"
        className="tip"
        onClick={toggle}
        aria-expanded={open}
        aria-label={`Info: ${props.row}`}
        style={{
          border: "1px solid var(--bd)", borderRadius: 999, padding: "3px 10px",
          fontSize: ".8rem", cursor: "help", color: "var(--muted)", background: "#fff",
        }}
      >
        ⓘ {props.row}
      </button>
      {open && (
        <div role="tooltip" style={{
          position: "absolute", bottom: "120%", left: "50%", transform: "translateX(-50%)",
          background: "var(--ink)", color: "#fff", padding: "6px 10px", borderRadius: 6,
          fontSize: ".78rem", whiteSpace: "nowrap", zIndex: 50,
          boxShadow: "0 2px 8px rgba(0,0,0,.25)",
        }}>
          {props.body}
        </div>
      )}
    </div>
  );
};

export default CoverageRowTooltip;
