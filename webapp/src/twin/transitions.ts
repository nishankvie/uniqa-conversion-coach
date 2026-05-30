// transitions.ts — Pure state machine, NO React imports (framework-free + unit-testable).
// Mirrors src/uniqa/widget.py legal_events and transition logic exactly.

export const STEP_ORDER = [
  "S1_COVERAGE_TYPE",
  "S2_INSURED_PERSONS",
  "S3_PERSONAL_INFO",
  "S4_TARIFF_SELECT",
  "S6_PERSONAL_DATA",
] as const;

export type StepId = typeof STEP_ORDER[number];

const DDMMYYYY = /^([0-2]\d|3[01])\.(0\d|1[0-2])\.(19|20)\d\d$/;
const ONLINE_TARIFFS = new Set(["start", "optimal"]);

// Minimal store interface (avoids importing @json-render/core in test env)
export interface StoreSlice {
  get: (path: string) => unknown;
  set: (path: string, value: unknown) => void;
}

// Minimal recorder interface (avoids importing capture.js in test env)
export interface RecorderSlice {
  emit: (type: string, target?: string | null, value?: unknown, thought?: string | null) => void;
  stepEnter?: (step: string) => void;
  curStep?: string | null;
}

export interface ValidationResult {
  errors: Record<string, string>;
  ok: boolean;
}

/** Per-step validation. Returns error map and ok flag. */
export function validate(step: string, store: StoreSlice): ValidationResult {
  const errors: Record<string, string> = {};

  switch (step) {
    case "S1_COVERAGE_TYPE": {
      const sel = (store.get("/formData/coverage/selected") as string[]) ?? [];
      if (sel.length === 0) errors.coverage = "Bitte wählen Sie eine oder mehrere Optionen.";
      return { errors, ok: sel.length > 0 };
    }
    case "S2_INSURED_PERSONS": {
      const v = store.get("/formData/insured") as string | null;
      if (!v) errors.insured = "Bitte wählen Sie eine Option.";
      return { errors, ok: !!v };
    }
    case "S3_PERSONAL_INFO": {
      const dob = (store.get("/formData/dob") as string) ?? "";
      const sv  = (store.get("/formData/sv")  as string) ?? "";
      if (!DDMMYYYY.test(dob)) errors.dob = "Bitte geben Sie das Datum im Format TT.MM.JJJJ ein.";
      if (!sv)                  errors.sv  = "Bitte wählen Sie Ihre Sozialversicherung.";
      return { errors, ok: Object.keys(errors).length === 0 };
    }
    case "S4_TARIFF_SELECT": {
      const t = store.get("/formData/tariff") as string | null;
      if (!t) errors.tariff = "Bitte wählen Sie einen Tarif.";
      return { errors, ok: !!t };
    }
    case "S6_PERSONAL_DATA": {
      const email    = store.get("/formData/email") as string;
      const tos      = store.get("/formData/consentTos") as boolean;
      const privacy  = store.get("/formData/consentPrivacy") as boolean;
      if (!email)   errors.email         = "E-Mail erforderlich.";
      if (!tos)     errors.consentTos    = "Bitte zustimmen.";
      if (!privacy) errors.consentPrivacy= "Bitte zustimmen.";
      return { errors, ok: Object.keys(errors).length === 0 };
    }
    default:
      return { errors, ok: true };
  }
}

/** Advance after successful validation — side-effectful (store writes + recorder events). */
export function advance(step: string, store: StoreSlice, rec: RecorderSlice): void {
  switch (step) {
    case "S1_COVERAGE_TYPE": {
      const sel = (store.get("/formData/coverage/selected") as string[]) ?? [];
      if (sel.includes("im_krankenhaus")) {
        store.set("/terminal", "advisor");
        rec.emit("abandon", null, "advisor_route(hospital)");
        return;
      }
      gotoStep(1, "S2_INSURED_PERSONS", store, rec);
      return;
    }
    case "S2_INSURED_PERSONS": {
      if (store.get("/formData/insured") === "andere_personen") {
        store.set("/terminal", "advisor");
        rec.emit("abandon", null, "advisor_route(others)");
        return;
      }
      gotoStep(2, "S3_PERSONAL_INFO", store, rec);
      return;
    }
    case "S3_PERSONAL_INFO":
      gotoStep(3, "S4_TARIFF_SELECT", store, rec);
      return;
    case "S4_TARIFF_SELECT": {
      const t = store.get("/formData/tariff") as string;
      if (!ONLINE_TARIFFS.has(t)) {
        store.set("/terminal", "advisor");
        rec.emit("abandon", null, `advisor_route(${t})`);
        return;
      }
      gotoStep(4, "S6_PERSONAL_DATA", store, rec);
      return;
    }
    case "S6_PERSONAL_DATA": {
      // Compute final price (health = "yes" adds €3 loading)
      const base  = (store.get("/provisionalPrice") as number) ?? 68.14;
      const final = store.get("/formData/health") === "yes" ? base + 3.0 : base;
      store.set("/finalPrice", final);
      rec.emit("price_reveal", "optimal_final", final);
      return;
    }
  }
}

/** Helper: set step index + emit step_enter. */
export function gotoStep(index: number, stepId: string, store: StoreSlice, rec: RecorderSlice): void {
  store.set("/currentStepIndex", index);
  // stepEnter is the primary event; update curStep on recorder if possible
  if (rec.stepEnter) {
    rec.stepEnter(stepId);
  } else {
    rec.emit("step_enter", null, null);
  }
  // update derived disabled flags
  updateDerived(store);
}

/** Update /derived/* flags after any state change that affects navigation. */
export function updateDerived(store: StoreSlice): void {
  const sel     = (store.get("/formData/coverage/selected") as string[]) ?? [];
  const insured = store.get("/formData/insured") as string | null;
  const tariff  = store.get("/formData/tariff")  as string | null;
  const email   = store.get("/formData/email")   as string;
  const tos     = store.get("/formData/consentTos") as boolean;
  const privacy = store.get("/formData/consentPrivacy") as boolean;
  const provisional = store.get("/provisionalPrice") as number | null;
  const final   = store.get("/finalPrice") as number | null;

  store.set("/derived/s1NextDisabled", sel.length === 0);
  store.set("/derived/s2NextDisabled", !insured);
  store.set("/derived/s4NextDisabled", !tariff);
  store.set("/derived/s6NextDisabled", !email || !tos || !privacy);
  store.set("/derived/priceDelta", provisional != null && final != null ? final - provisional : null);
}
