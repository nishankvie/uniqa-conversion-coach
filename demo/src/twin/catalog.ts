// catalog.ts — Typed UI contract for the UNIQA funnel twin.
// Uses defineCatalog + Zod (actual @json-render/react API).
import { defineCatalog } from "@json-render/core";
import { schema } from "@json-render/react/schema";
import { z } from "zod";

export const funnelCatalog = defineCatalog(schema, {
  components: {
    // ─── Layout / chrome ─────────────────────────────────────────────────
    Stack: {
      props: z.object({ direction: z.string().optional(), gap: z.number().optional() }),
      description: "Flex stack container",
    },
    Heading: {
      props: z.object({ text: z.string(), level: z.number().optional() }),
      description: "Section heading",
    },
    Instruction: {
      props: z.object({ text: z.string() }),
      description: "Muted instruction line (ur-body-75)",
    },
    ProgressStepper: {
      props: z.object({ phases: z.array(z.string()), current: z.number() }),
      description: "4-phase progress bar",
    },
    StepLiveRegion: {
      props: z.object({ heading: z.string() }),
      description: "aria-live announcer for step changes",
    },
    StickyOfferBar: {
      props: z.object({ label: z.string(), price: z.number().nullable().optional() }),
      description: "Sticky provisional price bar",
    },
    Wizard: {
      props: z.object({ current: z.number() }),
      description: "Top-level wizard wrapper",
    },
    Step: {
      props: z.object({
        id: z.string(),
        index: z.number(),
        current: z.number(),
        phase: z.string(),
        heading: z.string(),
      }),
      description: "Single wizard step (renders only when index===current)",
    },

    // ─── Choice cards ────────────────────────────────────────────────────
    ChoiceCardGroup: {
      props: z.object({
        mode: z.string(),
        group: z.string(),
        items: z.array(z.object({
          id: z.string(),
          title: z.string(),
          icon: z.string().optional(),
          features: z.array(z.string()).optional(),
        })),
      }),
      description: "Multi-checkbox or radio choice-card group",
    },
    ChoiceCard: {
      props: z.object({
        id: z.string(), title: z.string(), icon: z.string().optional(),
        features: z.array(z.string()).optional(),
        checked: z.boolean().optional(), mode: z.string().optional(),
      }),
      description: "Single choice card (checkbox or radio)",
    },

    // ─── Inputs ──────────────────────────────────────────────────────────
    DatePicker: {
      props: z.object({
        label: z.string(), value: z.string().optional(),
        error: z.string().optional(), touched: z.boolean().optional(),
      }),
      description: "Date input TT.MM.JJJJ (UR-DATEPICKER parity)",
    },
    SearchableSelect: {
      props: z.object({
        label: z.string(), value: z.string().optional(),
        error: z.string().optional(), touched: z.boolean().optional(),
        placeholder: z.string().optional(), options: z.array(z.string()),
      }),
      description: "CDK-overlay-style searchable select (UR-SELECT parity)",
    },
    TextField: {
      props: z.object({
        label: z.string(), value: z.string().optional(),
        error: z.string().optional(), touched: z.boolean().optional(),
        type: z.string().optional(),
      }),
      description: "Generic text field",
    },
    HelperTextError: {
      props: z.object({ text: z.string() }),
      description: ".helper-text.error with error icon",
    },

    // ─── Tariff table ─────────────────────────────────────────────────────
    TariffTable: {
      props: z.object({
        tariffs: z.array(z.object({
          id: z.string(), name: z.string(),
          price: z.number(), online: z.boolean(), maxYear: z.number().optional(),
        })),
        selected: z.string().nullable().optional(),
      }),
      description: "4-column tariff selection table",
    },
    TariffColumn: {
      props: z.object({
        id: z.string(), name: z.string(), price: z.number(),
        online: z.boolean(), selected: z.boolean().optional(),
      }),
      description: "Single tariff column card",
    },
    CoverageRowTooltip: {
      props: z.object({
        row: z.string(), body: z.string(), open: z.boolean().optional(),
      }),
      description: "(i) coverage row tooltip",
    },

    // ─── S6 forms ─────────────────────────────────────────────────────────
    HealthForm: {
      props: z.object({ values: z.record(z.unknown()), errors: z.record(z.unknown()) }),
      description: "Health + personal data form (S6)",
    },
    FinalPrice: {
      props: z.object({
        price: z.number().nullable().optional(),
        deltaFromProvisional: z.number().nullable().optional(),
      }),
      description: "Final individualised price (S7 inline)",
    },
    ClosingForm: {
      props: z.object({ values: z.record(z.unknown()), errors: z.record(z.unknown()) }),
      description: "Closing / consent form (S12)",
    },

    // ─── Navigation ───────────────────────────────────────────────────────
    Button: {
      props: z.object({
        label: z.string(), variant: z.string().optional(), disabled: z.boolean().optional(),
      }),
      description: "Weiter / Zurück / Abbrechen button",
    },
    NavRow: {
      props: z.object({
        showBack: z.boolean().optional(), nextDisabled: z.boolean().optional(),
        nextLabel: z.string().optional(), backLabel: z.string().optional(),
      }),
      description: "Navigation row with back + next buttons",
    },
  },

  actions: {
    // Lifecycle
    validateStep:  { description: "Validate current step and advance if valid" },
    prevStep:      { description: "Go to previous step (nav_back)" },
    cancelWizard:  { description: "Abort wizard (S1 Abbrechen)" },
    finishConvert: { description: "Complete purchase (terminal: convert)" },
  },
});

export type FunnelCatalog = typeof funnelCatalog;
