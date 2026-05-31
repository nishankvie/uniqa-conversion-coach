// overlay_render.test.tsx — Each decision schema renders without crash and
// emits widget_shown on mount.
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render } from "@testing-library/react";

// Mock FunnelTwin / funnelRefs (not needed for render tests)
vi.mock("../../twin/FunnelTwin.js", () => ({
  getFunnelStore: () => ({ set: vi.fn(), get: vi.fn(), subscribe: vi.fn(() => () => {}), getSnapshot: vi.fn(() => ({})) }),
}));
vi.mock("../../twin/funnelRefs.js", () => ({ getRef: () => undefined }));

import { DecisionRenderer } from "../CoachLayer.js";

// Load all 5 demo decisions
import s4PriceReframe   from "../decisions/s4_price_reframe.json";
import s4PremiumClicked from "../decisions/s4_premium_clicked.json";
import s4PeterCallback  from "../decisions/s4_peter_callback.json";
import s6FormHelper     from "../decisions/s6_form_helper.json";
import s7SaveProgress   from "../decisions/s7_save_progress.json";

const DEMO_DECISIONS = [
  { name: "s4_price_reframe",   d: s4PriceReframe },
  { name: "s4_premium_clicked", d: s4PremiumClicked },
  { name: "s4_peter_callback",  d: s4PeterCallback },
  { name: "s6_form_helper",     d: s6FormHelper },
  { name: "s7_save_progress",   d: s7SaveProgress },
] as const;

// ── Decision JSON structure ───────────────────────────────────────────────────
describe("decision JSON structure", () => {
  for (const { name, d } of DEMO_DECISIONS) {
    it(`${name} has required command fields`, () => {
      expect(d.command).toBeDefined();
      expect(typeof d.command.effector).toBe("string");
      expect(typeof d.command.step).toBe("string");
    });

    it(`${name} has a renderable spec (root + elements)`, () => {
      const spec = d.command.render as any;
      expect(spec).toBeDefined();
      expect(typeof spec.root).toBe("string");
      expect(typeof spec.elements).toBe("object");
      // root element must exist in elements map
      expect(spec.elements[spec.root]).toBeDefined();
    });

    it(`${name} root element type is a known coach component`, () => {
      const spec = d.command.render as any;
      const rootEl = spec.elements[spec.root];
      const COACH_TYPES = [
        "CoachCard", "Banner", "Toast", "Tooltip", "BottomSheet",
        "CTA", "InfoBlock", "PriceReframe", "MarketCompare",
        "CallbackCTA", "EmailResume", "WhatsAppCTA", "Survey",
      ];
      expect(COACH_TYPES).toContain(rootEl.type);
    });
  }
});

// ── Rendering tests ───────────────────────────────────────────────────────────
describe("DecisionRenderer", () => {
  const mockEmit = vi.fn();
  const mockRecorder = { emit: mockEmit, events: [] as any[], curStep: null };

  beforeEach(() => mockEmit.mockClear());

  for (const { name, d } of DEMO_DECISIONS) {
    it(`${name} renders without crash`, () => {
      const { container } = render(
        <DecisionRenderer
          decision={d as any}
          recorder={mockRecorder as any}
          onDismiss={() => {}}
        />,
      );
      expect(container.firstChild).toBeTruthy();
    });
  }

  it("emits widget_shown on mount for s4_price_reframe", () => {
    render(
      <DecisionRenderer
        decision={s4PriceReframe as any}
        recorder={mockRecorder as any}
        onDismiss={() => {}}
      />,
    );
    expect(mockEmit).toHaveBeenCalledWith(
      "widget_shown",
      expect.any(String),
      expect.anything(),
    );
  });

  it("calls onDismiss + emits widget_dismiss when dismiss fired", async () => {
    const onDismiss = vi.fn();
    const { getByLabelText } = render(
      <DecisionRenderer
        decision={s4PriceReframe as any}
        recorder={mockRecorder as any}
        onDismiss={onDismiss}
      />,
    );
    const closeBtn = getByLabelText("Schließen");
    closeBtn.click();
    expect(mockEmit).toHaveBeenCalledWith("widget_dismiss", expect.any(String));
    expect(onDismiss).toHaveBeenCalled();
  });
});
