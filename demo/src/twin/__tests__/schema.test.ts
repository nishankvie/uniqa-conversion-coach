// schema.test.ts — Validates funnel.json structure:
// • Every element id referenced in children exists in elements map
// • Every type is in the expected catalog type set
// • Root element exists
// • All 5 steps are present with correct ids and indices
import { describe, it, expect } from "vitest";
import funnelSpec from "../schema/funnel.json";

const CATALOG_TYPES = new Set([
  "Stack", "Heading", "Instruction", "ProgressStepper", "StepLiveRegion",
  "StickyOfferBar", "Wizard", "Step", "ChoiceCardGroup", "ChoiceCard",
  "DatePicker", "SearchableSelect", "TextField", "HelperTextError",
  "TariffTable", "TariffColumn", "CoverageRowTooltip",
  "HealthForm", "FinalPrice", "ClosingForm",
  "Button", "NavRow",
]);

const EXPECTED_STEP_IDS = [
  "S1_COVERAGE_TYPE",
  "S2_INSURED_PERSONS",
  "S3_PERSONAL_INFO",
  "S4_TARIFF_SELECT",
  "S6_PERSONAL_DATA",
];

describe("funnel.json structural validity", () => {
  const spec = funnelSpec as {
    root: string;
    elements: Record<string, { type: string; props?: Record<string, unknown>; children?: string[] }>;
  };

  it("has a root key", () => {
    expect(spec.root).toBeTruthy();
  });

  it("root element exists in elements", () => {
    expect(spec.elements[spec.root]).toBeDefined();
  });

  it("every child reference resolves to a defined element", () => {
    const missing: string[] = [];
    for (const [id, el] of Object.entries(spec.elements)) {
      const children = (el as any).children ?? [];
      for (const childId of children) {
        if (!spec.elements[childId]) {
          missing.push(`${id} → ${childId}`);
        }
      }
    }
    expect(missing, `Missing element ids: ${missing.join(", ")}`).toHaveLength(0);
  });

  it("every element type is in the catalog", () => {
    const unknown: string[] = [];
    for (const [id, el] of Object.entries(spec.elements)) {
      if (!CATALOG_TYPES.has(el.type)) {
        unknown.push(`${id}:${el.type}`);
      }
    }
    expect(unknown, `Unknown types: ${unknown.join(", ")}`).toHaveLength(0);
  });

  it("all 5 expected step ids are present", () => {
    const stepElements = Object.values(spec.elements).filter((el) => el.type === "Step");
    const stepIds = stepElements.map((el: any) => el.props?.id);
    for (const expectedId of EXPECTED_STEP_IDS) {
      expect(stepIds, `Missing step: ${expectedId}`).toContain(expectedId);
    }
  });

  it("step indices are 0..4 (no gaps)", () => {
    const stepElements = Object.values(spec.elements)
      .filter((el) => el.type === "Step")
      .map((el: any) => el.props?.index as number)
      .sort((a, b) => a - b);
    expect(stepElements).toEqual([0, 1, 2, 3, 4]);
  });

  it("wizard is the root type", () => {
    expect(spec.elements[spec.root].type).toBe("Wizard");
  });

  it("wizard children include all 5 step element keys", () => {
    const wizardEl = spec.elements[spec.root] as any;
    const children: string[] = wizardEl.children ?? [];
    const stepChildKeys = children.filter((c) => spec.elements[c]?.type === "Step");
    expect(stepChildKeys).toHaveLength(5);
  });

  it("NavRow elements have showBack props", () => {
    const navRows = Object.entries(spec.elements)
      .filter(([_, el]) => el.type === "NavRow")
      .map(([id, el]) => ({ id, props: (el as any).props }));
    expect(navRows.length).toBeGreaterThan(0);
    // S1 NavRow: showBack=false; others showBack=true
    const s1Nav = navRows.find(({ id }) => id === "s1Nav");
    expect(s1Nav?.props?.showBack).toBe(false);
  });

  it("S4 TariffTable has 4 tariffs inlined", () => {
    const s4Table = spec.elements["s4Table"] as any;
    expect(s4Table).toBeDefined();
    expect(s4Table.props.tariffs).toHaveLength(4);
    const ids = s4Table.props.tariffs.map((t: any) => t.id);
    expect(ids).toContain("start");
    expect(ids).toContain("optimal");
    expect(ids).toContain("opt_plus");
    expect(ids).toContain("premium");
  });

  it("tariff prices match widget.py constants", () => {
    const s4Table = spec.elements["s4Table"] as any;
    const tariffs = s4Table.props.tariffs;
    const byId = Object.fromEntries(tariffs.map((t: any) => [t.id, t]));
    expect((byId as any).start.price).toBe(38.74);
    expect((byId as any).optimal.price).toBe(68.14);
    expect((byId as any).opt_plus.price).toBe(96.66);
    expect((byId as any).premium.price).toBe(140.15);
  });
});
