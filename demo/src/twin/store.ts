// store.ts — External state store for the UNIQA funnel twin.
// Uses createStateStore from @json-render/core (re-exported by @json-render/react).
import { createStateStore } from "@json-render/react";

export const initialState = {
  // navigation
  currentStepIndex: 0,
  phase: "Angaben",
  terminal: null as string | null,

  // collected form data
  formData: {
    coverage:  { selected: [] as string[] },
    insured:   null as string | null,
    dob:       "",
    sv:        "",
    svFilter:  "",
    tariff:    null as string | null,
    health:    "no",
    email:     "",
    firstName: "",
    lastName:  "",
    sport:     "no",
    doctor:    "",
    height:    "",
    weight:    "",
    consentTos:     false as boolean,
    consentPrivacy: false as boolean,
  },

  // validation
  errors:  {} as Record<string, string>,
  touched: {} as Record<string, boolean>,

  // SV CDK overlay
  svSelect: { open: false },

  // tariff table
  tooltipsOpen: {} as Record<string, boolean>,
  provisionalPrice: null as number | null,

  // final price (S7 inline)
  finalPrice: null as number | null,

  // derived flags (pre-computed by transitions.updateDerived)
  derived: {
    s1NextDisabled: true,
    s2NextDisabled: true,
    s4NextDisabled: true,
    s6NextDisabled: true,
    priceDelta:     null as number | null,
  },

  // live-region heading (used by StepLiveRegion)
  headingForCurrentStep: "Wo möchten Sie abgesichert sein?",
};

/** Create a fresh funnel store. */
export function createFunnelStore() {
  return createStateStore(initialState as unknown as Record<string, unknown>);
}

export type FunnelStore = ReturnType<typeof createFunnelStore>;
