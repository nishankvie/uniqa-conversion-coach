// transitions.test.ts — Pure state-machine tests (no React, no DOM).
// Validates all routing, validation messages, and derived-state logic.
import { describe, it, expect, vi } from "vitest";
import { validate, advance, updateDerived, STEP_ORDER } from "../transitions.js";

/** Minimal in-memory store for testing. */
function makeStore(initial: Record<string, unknown> = {}) {
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
    "/provisionalPrice": null,
    "/finalPrice": null,
    "/currentStepIndex": 0,
    "/derived/s1NextDisabled": true,
    "/derived/s2NextDisabled": true,
    "/derived/s4NextDisabled": true,
    "/derived/s6NextDisabled": true,
    "/derived/priceDelta": null,
    "/terminal": null,
    ...initial,
  };
  return {
    get: (path: string) => state[path],
    set: (path: string, value: unknown) => { state[path] = value; },
    _state: state,
  };
}

function makeRec() {
  const events: { type: string; target: string | null; value: unknown }[] = [];
  return {
    emit: vi.fn((type, target = null, value = null) => { events.push({ type, target, value }); }),
    stepEnter: vi.fn(),
    emitted: events,
    curStep: null as string | null,
  };
}

// ─── STEP_ORDER ─────────────────────────────────────────────────────────────
it("STEP_ORDER has 5 entries", () => {
  expect(STEP_ORDER).toHaveLength(5);
  expect(STEP_ORDER[0]).toBe("S1_COVERAGE_TYPE");
  expect(STEP_ORDER[4]).toBe("S6_PERSONAL_DATA");
});

// ─── S1 validation ──────────────────────────────────────────────────────────
describe("S1 validation", () => {
  it("fails when no coverage selected", () => {
    const store = makeStore();
    const { errors, ok } = validate("S1_COVERAGE_TYPE", store);
    expect(ok).toBe(false);
    expect(errors.coverage).toContain("Bitte wählen Sie");
  });

  it("passes with at least one coverage", () => {
    const store = makeStore({ "/formData/coverage/selected": ["bei_arztbesuchen"] });
    const { errors, ok } = validate("S1_COVERAGE_TYPE", store);
    expect(ok).toBe(true);
    expect(Object.keys(errors)).toHaveLength(0);
  });
});

// ─── S2 validation ──────────────────────────────────────────────────────────
describe("S2 validation", () => {
  it("fails when no insured selected", () => {
    const { errors, ok } = validate("S2_INSURED_PERSONS", makeStore());
    expect(ok).toBe(false);
    expect(errors.insured).toBeTruthy();
  });

  it("passes with ich_selbst", () => {
    const { ok } = validate("S2_INSURED_PERSONS", makeStore({ "/formData/insured": "ich_selbst" }));
    expect(ok).toBe(true);
  });
});

// ─── S3 validation ──────────────────────────────────────────────────────────
describe("S3 validation", () => {
  it("rejects bad DOB format", () => {
    const store = makeStore({ "/formData/dob": "99.99.9999", "/formData/sv": "ÖGK" });
    const { errors, ok } = validate("S3_PERSONAL_INFO", store);
    expect(ok).toBe(false);
    expect(errors.dob).toBe("Bitte geben Sie das Datum im Format TT.MM.JJJJ ein.");
  });

  it("rejects missing SV", () => {
    const store = makeStore({ "/formData/dob": "01.01.1980", "/formData/sv": "" });
    const { errors, ok } = validate("S3_PERSONAL_INFO", store);
    expect(ok).toBe(false);
    expect(errors.sv).toBe("Bitte wählen Sie Ihre Sozialversicherung.");
  });

  it("passes with valid DOB + SV", () => {
    const store = makeStore({ "/formData/dob": "15.06.1985", "/formData/sv": "ÖGK" });
    const { ok } = validate("S3_PERSONAL_INFO", store);
    expect(ok).toBe(true);
  });

  it("rejects year 1800 (outside 19xx/20xx range)", () => {
    const store = makeStore({ "/formData/dob": "01.01.1800", "/formData/sv": "ÖGK" });
    const { errors, ok } = validate("S3_PERSONAL_INFO", store);
    expect(ok).toBe(false);
    expect(errors.dob).toBeTruthy();
  });
});

// ─── S4 validation ──────────────────────────────────────────────────────────
describe("S4 validation", () => {
  it("fails without tariff", () => {
    const { ok } = validate("S4_TARIFF_SELECT", makeStore());
    expect(ok).toBe(false);
  });

  it("passes with start tariff", () => {
    const { ok } = validate("S4_TARIFF_SELECT", makeStore({ "/formData/tariff": "start" }));
    expect(ok).toBe(true);
  });
});

// ─── S6 validation ──────────────────────────────────────────────────────────
describe("S6 validation", () => {
  it("fails without email + consents", () => {
    const { errors, ok } = validate("S6_PERSONAL_DATA", makeStore());
    expect(ok).toBe(false);
    expect(errors.email).toBeTruthy();
    expect(errors.consentTos).toBeTruthy();
    expect(errors.consentPrivacy).toBeTruthy();
  });

  it("passes with all required fields", () => {
    const store = makeStore({
      "/formData/email": "test@example.com",
      "/formData/consentTos": true,
      "/formData/consentPrivacy": true,
    });
    const { ok } = validate("S6_PERSONAL_DATA", store);
    expect(ok).toBe(true);
  });
});

// ─── advance transitions ────────────────────────────────────────────────────
describe("advance S1", () => {
  it("bei_arztbesuchen only → advances to S2", () => {
    const store = makeStore({ "/formData/coverage/selected": ["bei_arztbesuchen"] });
    const rec = makeRec();
    advance("S1_COVERAGE_TYPE", store, rec);
    expect(store.get("/currentStepIndex")).toBe(1);
    expect(rec.stepEnter).toHaveBeenCalledWith("S2_INSURED_PERSONS");
  });

  it("im_krankenhaus → advisor route (abandon)", () => {
    const store = makeStore({ "/formData/coverage/selected": ["im_krankenhaus"] });
    const rec = makeRec();
    advance("S1_COVERAGE_TYPE", store, rec);
    expect(store.get("/terminal")).toBe("advisor");
    expect(rec.emit).toHaveBeenCalledWith("abandon", null, "advisor_route(hospital)");
  });
});

describe("advance S2", () => {
  it("ich_selbst → S3", () => {
    const store = makeStore({ "/formData/insured": "ich_selbst" });
    const rec = makeRec();
    advance("S2_INSURED_PERSONS", store, rec);
    expect(store.get("/currentStepIndex")).toBe(2);
  });

  it("andere_personen → advisor route", () => {
    const store = makeStore({ "/formData/insured": "andere_personen" });
    const rec = makeRec();
    advance("S2_INSURED_PERSONS", store, rec);
    expect(store.get("/terminal")).toBe("advisor");
    expect(rec.emit).toHaveBeenCalledWith("abandon", null, "advisor_route(others)");
  });
});

describe("advance S3", () => {
  it("always advances to S4", () => {
    const store = makeStore();
    const rec = makeRec();
    advance("S3_PERSONAL_INFO", store, rec);
    expect(store.get("/currentStepIndex")).toBe(3);
  });
});

describe("advance S4", () => {
  it("online tariff (start) → S6", () => {
    const store = makeStore({ "/formData/tariff": "start" });
    const rec = makeRec();
    advance("S4_TARIFF_SELECT", store, rec);
    expect(store.get("/currentStepIndex")).toBe(4);
  });

  it("start tariff → S6", () => {
    const store = makeStore({ "/formData/tariff": "optimal" });
    const rec = makeRec();
    advance("S4_TARIFF_SELECT", store, rec);
    expect(store.get("/currentStepIndex")).toBe(4);
  });

  it("opt_plus → advisor route", () => {
    const store = makeStore({ "/formData/tariff": "opt_plus" });
    const rec = makeRec();
    advance("S4_TARIFF_SELECT", store, rec);
    expect(store.get("/terminal")).toBe("advisor");
  });

  it("premium → advisor route", () => {
    const store = makeStore({ "/formData/tariff": "premium" });
    const rec = makeRec();
    advance("S4_TARIFF_SELECT", store, rec);
    expect(store.get("/terminal")).toBe("advisor");
  });
});

describe("advance S6 — final price computation", () => {
  it("health=no → finalPrice equals provisionalPrice", () => {
    const store = makeStore({ "/provisionalPrice": 68.14, "/formData/health": "no" });
    const rec = makeRec();
    advance("S6_PERSONAL_DATA", store, rec);
    expect(store.get("/finalPrice")).toBe(68.14);
    expect(rec.emit).toHaveBeenCalledWith("price_reveal", "optimal_final", 68.14);
  });

  it("health=yes → finalPrice = provisional + 3.0", () => {
    const store = makeStore({ "/provisionalPrice": 68.14, "/formData/health": "yes" });
    const rec = makeRec();
    advance("S6_PERSONAL_DATA", store, rec);
    expect(store.get("/finalPrice")).toBeCloseTo(71.14);
  });
});

// ─── updateDerived ───────────────────────────────────────────────────────────
describe("updateDerived", () => {
  it("s1NextDisabled=true when no coverage selected", () => {
    const store = makeStore();
    updateDerived(store);
    expect(store.get("/derived/s1NextDisabled")).toBe(true);
  });

  it("s1NextDisabled=false after selecting a coverage", () => {
    const store = makeStore({ "/formData/coverage/selected": ["bei_arztbesuchen"] });
    updateDerived(store);
    expect(store.get("/derived/s1NextDisabled")).toBe(false);
  });

  it("priceDelta is null when no prices set", () => {
    const store = makeStore();
    updateDerived(store);
    expect(store.get("/derived/priceDelta")).toBeNull();
  });

  it("priceDelta computed correctly", () => {
    const store = makeStore({ "/provisionalPrice": 68.14, "/finalPrice": 71.14 });
    updateDerived(store);
    expect(store.get("/derived/priceDelta")).toBeCloseTo(3.0);
  });
});
