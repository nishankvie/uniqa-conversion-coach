// effectorBridge.ts — The ONLY path that writes the funnelStore from outside.
// Mirrors contracts.EffectorCommand.validate() guardrails 1-1.
// Must be called AFTER FunnelTwin has mounted (getFunnelStore() returns the live store).
import { getFunnelStore } from "../twin/FunnelTwin.js";
import { getRef } from "../twin/funnelRefs.js";
import type { Recorder } from "../capture.js";

// ── Guardrails (mirrors contracts.py) ────────────────────────────────────────
export const NEVER_AUTOFILL = new Set([
  "sv_number", "first_name", "last_name", "email",
  "health_answers", "date_of_birth", "consent",
]);

export const SAMPLE_FILLABLE = new Set(["coverage", "insured", "tariff"]);

export const ONLINE_TARIFFS = new Set(["start", "optimal"]);

// ── Bridge factory ────────────────────────────────────────────────────────────
export function makeEffectorBridge(recorder: Recorder) {
  const store = () => getFunnelStore();

  return {
    /** Fill a field with a known/derived user value. Forbidden on identity fields. */
    autofill(field: string, value: unknown): void {
      if (NEVER_AUTOFILL.has(field))
        throw new Error(`AUTOFILL forbidden on protected field '${field}'`);
      store().set(`/formData/${field}`, value);
      recorder.emit("widget_shown", "autofill", { field, value } as any);
    },

    /** Fill placeholder data so user can explore the flow. Only SAMPLE_FILLABLE fields. */
    fillSample(field: string, value: unknown): void {
      if (!SAMPLE_FILLABLE.has(field))
        throw new Error(
          `FILL_SAMPLE only allowed on [${[...SAMPLE_FILLABLE].join(", ")}], not '${field}'`,
        );
      store().set(`/formData/${field}`, value);
      recorder.emit("widget_shown", "fill_sample", { field, value } as any);
    },

    /** Pre-select a tariff. Online tariffs only (start | optimal). */
    preselect(tariffId: string): void {
      if (!ONLINE_TARIFFS.has(tariffId))
        throw new Error(`PRESELECT_TARIFF: online tariffs only, got '${tariffId}'`);
      store().set("/formData/tariff", tariffId);
      recorder.emit("widget_shown", "preselect_tariff", { tariff: tariffId } as any);
    },

    /** Visually highlight a registered DOM element for `ms` ms. */
    highlight(elementId: string, ms = 1500): void {
      const el = getRef(elementId);
      if (!el) return;
      el.classList.add("coach-highlight");
      setTimeout(() => el.classList.remove("coach-highlight"), ms);
      recorder.emit("widget_shown", "highlight", { target: elementId } as any);
    },

    /** Move keyboard focus to a registered element. */
    focus(elementId: string): void {
      getRef(elementId)?.focus();
    },

    /** Smooth-scroll a registered element into view. */
    scrollTo(id: string): void {
      getRef(id)?.scrollIntoView({ behavior: "smooth" });
    },

    /** Mocked off-page delivery (email / whatsapp / survey / advisor_booking).
     *  Emits widget_shown so the capture log records the intervention. */
    deliver(surface: string, payload: unknown): void {
      recorder.emit("widget_shown", surface, payload as any);
    },
  };
}

export type EffectorBridge = ReturnType<typeof makeEffectorBridge>;
