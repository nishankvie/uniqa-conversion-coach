// FunnelTwin.tsx — Top-level component: creates the json-render runtime stack
// and wires the Recorder through RecorderProvider.
// The funnel schema is read-only at runtime (never patched).
import React, { useEffect, useMemo } from "react";
import {
  StateProvider, ActionProvider, Renderer, VisibilityProvider,
} from "@json-render/react";
import type { Recorder } from "../capture.js";
import { registry } from "./registry.js";
import { createFunnelStore } from "./store.js";
import { attachCaptureBridge } from "./captureBridge.js";
import { validate, advance, updateDerived, gotoStep } from "./transitions.js";
import { RecorderProvider } from "./recorderContext.js";
import funnelSpec from "./schema/funnel.json";

export interface FunnelTwinProps {
  recorder: Recorder;
  /** Called when wizard reaches a terminal state. */
  onTerminal?: (term: string) => void;
}

/** Singleton store created once per mount. */
let _store: ReturnType<typeof createFunnelStore> | null = null;

export function getFunnelStore() {
  if (!_store) _store = createFunnelStore();
  return _store;
}

export default function FunnelTwin({ recorder, onTerminal }: FunnelTwinProps) {
  // Create store once
  const store = useMemo(() => {
    _store = createFunnelStore();
    return _store;
  }, []);

  const storeSlice = useMemo(() => ({
    get: (p: string) => store.get(p),
    set: (p: string, v: unknown) => store.set(p, v),
  }), [store]);

  // Attach capture bridge (field_blur derivation from touched state)
  useEffect(() => {
    const unsub = attachCaptureBridge(store, recorder);
    return unsub;
  }, [store, recorder]);

  // Emit step_enter for S1 on first mount
  useEffect(() => {
    recorder.stepEnter("S1_COVERAGE_TYPE");
    updateDerived(storeSlice);
  }, []);

  // Watch terminal state → notify parent
  useEffect(() => {
    return store.subscribe(() => {
      const snap = store.getSnapshot() as Record<string, unknown>;
      const term = snap["terminal"] as string | null;
      if (term && onTerminal) onTerminal(term);
    });
  }, [store, onTerminal]);

  // Action handlers (closed over store + recorder)
  const handlers = useMemo(() => ({
    validateStep: (params: { step?: string }) => {
      const step = params?.step ?? "";
      const { errors, ok } = validate(step, storeSlice);
      store.set("/errors", errors);
      if (!ok) {
        Object.entries(errors).forEach(([field, msg]) =>
          recorder.emit("validation_error", field, msg));
      } else {
        recorder.emit("submit", null, step);
        advance(step, storeSlice, recorder);
      }
    },

    prevStep: () => {
      const cur = (store.get("/currentStepIndex") as number) ?? 0;
      const nextIdx = Math.max(0, cur - 1);
      const stepIds = ["S1_COVERAGE_TYPE", "S2_INSURED_PERSONS", "S3_PERSONAL_INFO", "S4_TARIFF_SELECT", "S6_PERSONAL_DATA"];
      gotoStep(nextIdx, stepIds[nextIdx], storeSlice, recorder);
      recorder.emit("nav_back");
    },

    cancelWizard: (params: { reason?: string }) => {
      store.set("/terminal", `abandon:${params?.reason ?? "cancel"}`);
      recorder.emit("abandon", null, params?.reason ?? "cancel");
    },

    finishConvert: () => {
      store.set("/terminal", "convert");
      recorder.emit("convert", null, "online_purchase");
    },
  }), [store, recorder, storeSlice]);

  return (
    <RecorderProvider value={recorder}>
      <StateProvider store={store}>
        <VisibilityProvider>
          <ActionProvider handlers={handlers}>
            <Renderer spec={funnelSpec as any} registry={registry} />
          </ActionProvider>
        </VisibilityProvider>
      </StateProvider>
    </RecorderProvider>
  );
}
