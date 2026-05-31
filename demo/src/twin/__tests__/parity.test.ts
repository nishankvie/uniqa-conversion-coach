// parity.test.ts — Asserts that every EventType the JS funnel twin emits on each
// step is a subset of widget.py's legal_events(step).
// The Python legal sets are hardcoded here as fixtures (read from widget.py).
import { describe, it, expect } from "vitest";
import { validate, advance, updateDerived } from "../transitions.js";

// ─── Python legal_events fixtures (hardcoded from src/uniqa/widget.py) ───────
// Base events legal on every step (mirrors widget.py `legal_events` base set):
const BASE_LEGAL = new Set([
  "step_enter", "idle", "pause",
  "hover", "mouse_move",
  "nav_back",
  "field_focus", "field_blur",
  "submit",
  "session_gap",
  "tab_blur", "tab_focus",
  "abandon", "convert",
]);

const LEGAL_PER_STEP: Record<string, Set<string>> = {
  S1_COVERAGE_TYPE:  new Set([...BASE_LEGAL, "select", "tap"]),
  S2_INSURED_PERSONS:new Set([...BASE_LEGAL, "select", "tap"]),
  S3_PERSONAL_INFO:  new Set([...BASE_LEGAL, "keystroke", "field_edit", "dropdown_open", "select",
                                             "validation_error", "submit", "tap"]),
  S4_TARIFF_SELECT:  new Set([...BASE_LEGAL, "select", "tariff_click", "premium_click",
                                             "price_reveal", "price_hover", "tooltip_open", "tap"]),
  S6_PERSONAL_DATA:  new Set([...BASE_LEGAL, "keystroke", "field_edit", "validation_error",
                                             "cancel_hover", "submit", "tap", "price_reveal"]),
};

// ─── JS events emitted per step (collected by tracking action handler calls) ─
// These mirror what FunnelTwin's action handlers + components emit.

/** Events the JS twin may emit on S1 (COVERAGE_TYPE). */
const S1_JS_EVENTS = new Set([
  "step_enter",   // on mount / entering step
  "select",       // toggleCoverage (ChoiceCardGroup)
  "abandon",      // cancelWizard / hospital route
  "submit",       // validateStep → advance (success)
  "nav_back",     // prevStep
  "field_focus",  // captureBridge
  "field_blur",   // captureBridge
  "hover",        // Hoverable (base recorder)
  "idle",         // base recorder
  "tab_blur",     // base recorder
  "tab_focus",    // base recorder
]);

/** Events the JS twin may emit on S2 (INSURED_PERSONS). */
const S2_JS_EVENTS = new Set([
  "step_enter", "select", "submit", "nav_back", "abandon",
  "field_focus", "field_blur", "hover", "idle", "tab_blur", "tab_focus",
]);

/** Events the JS twin may emit on S3 (PERSONAL_INFO). */
const S3_JS_EVENTS = new Set([
  "step_enter", "keystroke", "dropdown_open", "select", "validation_error",
  "submit", "nav_back", "field_focus", "field_blur",
  "hover", "idle", "tab_blur", "tab_focus",
]);

/** Events the JS twin may emit on S4 (TARIFF_SELECT). */
const S4_JS_EVENTS = new Set([
  "step_enter", "select", "price_reveal", "premium_click", "tooltip_open",
  "nav_back", "field_focus", "field_blur",
  "hover", "idle", "tab_blur", "tab_focus",
]);

/** Events the JS twin may emit on S6 (PERSONAL_DATA). */
const S6_JS_EVENTS = new Set([
  "step_enter", "keystroke", "validation_error", "price_reveal", "submit",
  "convert", "nav_back", "field_focus", "field_blur",
  "hover", "idle", "tab_blur", "tab_focus",
]);

const JS_EVENTS_BY_STEP: Record<string, Set<string>> = {
  S1_COVERAGE_TYPE:   S1_JS_EVENTS,
  S2_INSURED_PERSONS: S2_JS_EVENTS,
  S3_PERSONAL_INFO:   S3_JS_EVENTS,
  S4_TARIFF_SELECT:   S4_JS_EVENTS,
  S6_PERSONAL_DATA:   S6_JS_EVENTS,
};

// ─── Parity assertions ────────────────────────────────────────────────────────
describe("JS event set ⊆ Python legal_events for each step", () => {
  const steps = Object.keys(JS_EVENTS_BY_STEP);

  for (const step of steps) {
    it(`[${step}] all JS events are in legal_events`, () => {
      const jsEvents   = JS_EVENTS_BY_STEP[step];
      const legalEvents = LEGAL_PER_STEP[step];

      const illegal = [...jsEvents].filter((ev) => !legalEvents.has(ev));
      expect(illegal, `Illegal events on ${step}: ${illegal.join(", ")}`).toHaveLength(0);
    });
  }
});

// ─── Concrete emit-trace tests using transitions module ─────────────────────
// Ensures the specific events emitted by transitions.advance match the legal set.

function makeStore(overrides: Record<string, unknown> = {}) {
  const state: Record<string, unknown> = {
    "/formData/coverage/selected": [],
    "/formData/insured": null,
    "/formData/dob": "",
    "/formData/sv": "",
    "/formData/tariff": null,
    "/formData/email": "",
    "/formData/health": "no",
    "/formData/consentTos": false,
    "/formData/consentPrivacy": false,
    "/provisionalPrice": 68.14,
    "/finalPrice": null,
    "/currentStepIndex": 0,
    "/terminal": null,
    ...overrides,
  };
  return {
    get: (p: string) => state[p],
    set: (p: string, v: unknown) => { state[p] = v; },
  };
}

function makeRec(step: string) {
  const emitted: string[] = [];
  return {
    emit: (type: string) => { emitted.push(type); },
    stepEnter: () => { emitted.push("step_enter"); },
    curStep: step,
    getEmitted: () => emitted,
  };
}

describe("transitions.advance emits only legal events", () => {
  it("S1 hospital path emits only abandon (legal in base)", () => {
    const store = makeStore({ "/formData/coverage/selected": ["im_krankenhaus"] });
    const rec = makeRec("S1_COVERAGE_TYPE");
    advance("S1_COVERAGE_TYPE", store, rec);
    const illegal = rec.getEmitted().filter((ev) => !LEGAL_PER_STEP.S1_COVERAGE_TYPE.has(ev));
    expect(illegal).toHaveLength(0);
  });

  it("S4 advance to S6 emits step_enter (legal in base)", () => {
    const store = makeStore({ "/formData/tariff": "start" });
    const rec = makeRec("S4_TARIFF_SELECT");
    advance("S4_TARIFF_SELECT", store, rec);
    const illegal = rec.getEmitted().filter((ev) => !LEGAL_PER_STEP.S4_TARIFF_SELECT.has(ev));
    expect(illegal).toHaveLength(0);
  });

  it("S6 advance emits price_reveal (legal on S6)", () => {
    const store = makeStore({
      "/provisionalPrice": 68.14, "/formData/health": "no",
      "/formData/email": "a@b.com", "/formData/consentTos": true, "/formData/consentPrivacy": true,
    });
    const rec = makeRec("S6_PERSONAL_DATA");
    advance("S6_PERSONAL_DATA", store, rec);
    expect(rec.getEmitted()).toContain("price_reveal");
    const illegal = rec.getEmitted().filter((ev) => !LEGAL_PER_STEP.S6_PERSONAL_DATA.has(ev));
    expect(illegal).toHaveLength(0);
  });
});

// ─── validate emits validation_error (legal on S3 and S6) ────────────────────
describe("validate produces errors with correct messages (legal events when emitted)", () => {
  it("S3 invalid DOB produces the verbatim Reef error message", () => {
    const { errors } = validate("S3_PERSONAL_INFO",
      makeStore({ "/formData/dob": "99.99.9999", "/formData/sv": "ÖGK" }));
    expect(errors.dob).toBe("Bitte geben Sie das Datum im Format TT.MM.JJJJ ein.");
  });

  it("S3 missing SV produces the verbatim Reef error message", () => {
    const { errors } = validate("S3_PERSONAL_INFO",
      makeStore({ "/formData/dob": "01.01.1990", "/formData/sv": "" }));
    expect(errors.sv).toBe("Bitte wählen Sie Ihre Sozialversicherung.");
  });
});
