// CoachLayer.tsx — Portal-rendered coach overlay.
// Subscribes to a DecisionStream; executes effectors and renders overlays
// via the #coach-layer portal target (z-index 9000).
// The funnel schema is NEVER patched — coach only overlays via portal or calls effectorBridge.
import React, { createPortal, useEffect, useMemo, useRef, useState } from "react";
import {
  StateProvider, VisibilityProvider, ActionProvider, Renderer,
} from "@json-render/react";
import type { Recorder } from "../capture.js";
import type { CoachDecision, DecisionStream } from "./decisionStream.js";
import { makeEffectorBridge } from "./effectorBridge.js";
import { coachRegistry } from "./registry.js";

// ── Per-decision renderer ─────────────────────────────────────────────────────
interface DecisionRendererProps {
  decision: CoachDecision;
  recorder: Recorder;
  onDismiss: (d: CoachDecision) => void;
}

/** Renders one active CoachDecision inside its own provider stack.
 *  Exported so tests can render it directly. */
export function DecisionRenderer({ decision, recorder, onDismiss }: DecisionRendererProps) {
  const intent = decision.command.payload?.intent as string | undefined;
  const surface = (decision.command.payload?.surface as string | undefined) ?? "on_page";

  // Emit widget_shown on mount (identical to contracts.ActivityLog semantics)
  useEffect(() => {
    recorder.emit("widget_shown", intent ?? decision.command.effector, { surface } as any);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handlers = useMemo(() => ({
    cta: (_p: Record<string, unknown>) => {
      recorder.emit("widget_cta", intent ?? decision.command.effector);
      onDismiss(decision);
    },
    dismiss: (_p: Record<string, unknown>) => {
      recorder.emit("widget_dismiss", intent ?? decision.command.effector);
      onDismiss(decision);
    },
    surfacePick: (p: Record<string, unknown>) => {
      recorder.emit("widget_cta",
        (p?.surface as string | undefined) ?? surface,
        p?.option,
      );
    },
    // extra aliases used by CallbackCTA / EmailResume / WhatsAppCTA / Survey components
    accept: (_p: Record<string, unknown>) => {
      recorder.emit("widget_cta", intent ?? decision.command.effector);
      onDismiss(decision);
    },
    send: (_p: Record<string, unknown>) => {
      recorder.emit("widget_cta", "email_resume");
      onDismiss(decision);
    },
    pick: (p: Record<string, unknown>) => {
      recorder.emit("widget_cta", "survey", p?.option ?? null);
    },
    press: (_p: Record<string, unknown>) => {
      recorder.emit("widget_cta", intent ?? decision.command.effector);
      onDismiss(decision);
    },
  }), [decision, recorder, onDismiss, intent, surface]);

  const initialState = useMemo(() => ({ intent, surface }), [intent, surface]);

  if (!decision.command.render) return null;

  return (
    <StateProvider initialState={initialState}>
      <VisibilityProvider>
        <ActionProvider handlers={handlers}>
          <Renderer spec={decision.command.render as any} registry={coachRegistry} />
        </ActionProvider>
      </VisibilityProvider>
    </StateProvider>
  );
}

// ── CoachLayer ────────────────────────────────────────────────────────────────
interface CoachLayerProps {
  stream:   DecisionStream;
  recorder: Recorder;
}

function isOffPageSurface(d: CoachDecision): boolean {
  const eff = d.command.effector;
  return ["save_progress", "email", "whatsapp"].includes(eff);
}

export function CoachLayer({ stream, recorder }: CoachLayerProps) {
  const [active, setActive] = useState<CoachDecision[]>([]);
  const bridge = useMemo(() => makeEffectorBridge(recorder), [recorder]);
  const idxRef = useRef(0);

  useEffect(() => {
    return stream.subscribe((d: CoachDecision) => {
      const eff = d.command.effector;

      // 1) Side-effecting-only effectors — execute immediately, no render
      if (eff === "focus_field")  { bridge.focus(d.command.target ?? ""); return; }
      if (eff === "scroll_to")   { bridge.scrollTo(d.command.target ?? ""); return; }
      if (eff === "highlight")   { bridge.highlight(d.command.target ?? ""); return; }
      if (eff === "autofill")    { bridge.autofill(d.command.target ?? "", d.command.payload?.value); return; }
      if (eff === "fill_sample") { bridge.fillSample(d.command.target ?? "", d.command.payload?.value); return; }
      if (eff === "preselect_tariff") { bridge.preselect(d.command.target ?? ""); return; }
      if (eff === "no_action")   { return; }

      // 2) Renderable overlays (show_widget + off-page surfaces with render spec)
      if (eff === "show_widget" || isOffPageSurface(d)) {
        if (eff === "save_progress") bridge.deliver("save_progress", d.command.payload);
        setActive((prev) => [...prev, d]);
      }
    });
  }, [stream, bridge]);

  const handleDismiss = (d: CoachDecision) =>
    setActive((prev) => prev.filter((x) => x !== d));

  const portalTarget = typeof document !== "undefined"
    ? document.getElementById("coach-layer")
    : null;

  const content = (
    <div style={{ position: "fixed", bottom: 80, right: 24, zIndex: 9000, display: "flex", flexDirection: "column", gap: 12, pointerEvents: "none" }}>
      {active.map((d, i) => (
        <div key={idxRef.current + i} style={{ pointerEvents: "auto" }}>
          <DecisionRenderer
            decision={d}
            recorder={recorder}
            onDismiss={handleDismiss}
          />
        </div>
      ))}
    </div>
  );

  if (!portalTarget) return content;
  return createPortal(content, portalTarget);
}
