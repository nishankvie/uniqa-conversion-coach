// captureBridge.ts — Wires the funnel store to the Recorder.
// Subscribes to store changes and derives field_focus / field_blur events
// from /touched/* path flips (most events are already emitted by action
// handlers in FunnelTwin; this catches passive state transitions).
import type { FunnelStore } from "./store.js";
import type { Recorder } from "../capture.js";

/** Attach a bridge that watches /touched/* for focus/blur derivation. */
export function attachCaptureBridge(store: FunnelStore, recorder: Recorder): () => void {
  let prevTouched: Record<string, boolean> = {};

  return store.subscribe(() => {
    const snap = store.getSnapshot() as Record<string, unknown>;
    const touched = (snap["touched"] as Record<string, boolean>) ?? {};

    // Detect newly-touched fields → emit field_blur (Angular-style: touched on blur)
    for (const [field, nowTouched] of Object.entries(touched)) {
      if (nowTouched && !prevTouched[field]) {
        recorder.emit("field_blur", field, null);
      }
    }
    prevTouched = { ...touched };
  });
}
