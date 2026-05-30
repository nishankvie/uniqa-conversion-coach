// effector_guards.test.ts — NEVER_AUTOFILL / SAMPLE_FILLABLE / online-only guardrails.
// No DOM or React required — pure function tests.
import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock FunnelTwin to avoid DOM/React setup in this pure test file.
const mockSet = vi.fn();
vi.mock("../../twin/FunnelTwin.js", () => ({
  getFunnelStore: () => ({
    set: mockSet,
    get: vi.fn(),
    subscribe: vi.fn(() => () => {}),
    getSnapshot: vi.fn(() => ({})),
  }),
}));
vi.mock("../../twin/funnelRefs.js", () => ({
  getRef: () => undefined,
}));

// Dynamic import after mocks are registered
const { makeEffectorBridge, NEVER_AUTOFILL, SAMPLE_FILLABLE, ONLINE_TARIFFS } =
  await import("../effectorBridge.js");

const mockEmit = vi.fn();
const mockRecorder = { emit: mockEmit, events: [] as any[], curStep: null };

describe("effectorBridge — NEVER_AUTOFILL guardrail", () => {
  const bridge = makeEffectorBridge(mockRecorder as any);

  beforeEach(() => { mockSet.mockClear(); mockEmit.mockClear(); });

  it("throws on every NEVER_AUTOFILL field", () => {
    for (const field of NEVER_AUTOFILL) {
      expect(() => bridge.autofill(field, "x")).toThrow("AUTOFILL forbidden");
    }
  });

  it("error message includes the field name", () => {
    expect(() => bridge.autofill("email", "x@y.com"))
      .toThrow(/email/);
  });

  it("does NOT throw on a non-protected field", () => {
    expect(() => bridge.autofill("someOtherField", "ok")).not.toThrow();
  });

  it("writes to store when allowed", () => {
    bridge.autofill("someField", "value");
    expect(mockSet).toHaveBeenCalledWith("/formData/someField", "value");
  });

  it("emits widget_shown on successful autofill", () => {
    bridge.autofill("someField", "value");
    expect(mockEmit).toHaveBeenCalledWith("widget_shown", "autofill", expect.anything());
  });
});

describe("effectorBridge — SAMPLE_FILLABLE guardrail", () => {
  const bridge = makeEffectorBridge(mockRecorder as any);

  beforeEach(() => { mockSet.mockClear(); mockEmit.mockClear(); });

  it("allows all SAMPLE_FILLABLE fields", () => {
    for (const field of SAMPLE_FILLABLE) {
      expect(() => bridge.fillSample(field, "test")).not.toThrow();
    }
  });

  it("throws on non-SAMPLE_FILLABLE fields", () => {
    const notFillable = ["email", "sv_number", "first_name", "date_of_birth"];
    for (const field of notFillable) {
      expect(() => bridge.fillSample(field, "x")).toThrow("FILL_SAMPLE only allowed");
    }
  });

  it("error message lists the allowed fields", () => {
    expect(() => bridge.fillSample("email", "x@y.com"))
      .toThrow(/coverage|insured|tariff/);
  });

  it("writes to store on fillSample", () => {
    bridge.fillSample("coverage", "bei_arztbesuchen");
    expect(mockSet).toHaveBeenCalledWith("/formData/coverage", "bei_arztbesuchen");
  });

  it("emits widget_shown on fillSample", () => {
    bridge.fillSample("tariff", "optimal");
    expect(mockEmit).toHaveBeenCalledWith("widget_shown", "fill_sample", expect.anything());
  });
});

describe("effectorBridge — PRESELECT_TARIFF guardrail (online-only)", () => {
  const bridge = makeEffectorBridge(mockRecorder as any);

  beforeEach(() => { mockSet.mockClear(); mockEmit.mockClear(); });

  it("allows online tariffs", () => {
    for (const t of ONLINE_TARIFFS) {
      expect(() => bridge.preselect(t)).not.toThrow();
    }
  });

  it("throws on non-online tariffs", () => {
    expect(() => bridge.preselect("opt_plus")).toThrow("online tariffs only");
    expect(() => bridge.preselect("premium")).toThrow("online tariffs only");
  });

  it("error message includes the forbidden tariff id", () => {
    expect(() => bridge.preselect("premium")).toThrow(/premium/);
  });

  it("writes tariff to store on preselect", () => {
    bridge.preselect("optimal");
    expect(mockSet).toHaveBeenCalledWith("/formData/tariff", "optimal");
  });

  it("emits widget_shown on preselect", () => {
    bridge.preselect("start");
    expect(mockEmit).toHaveBeenCalledWith("widget_shown", "preselect_tariff", expect.anything());
  });
});
