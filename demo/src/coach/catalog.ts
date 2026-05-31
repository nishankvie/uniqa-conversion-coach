// coach/catalog.ts — Typed UI contract for the coach overlay layer.
// Components-only catalog (no actions) so defineRegistry stays simple.
// Action handlers (cta / dismiss / surfacePick) are provided directly
// to ActionProvider in CoachLayer.tsx, closed over the shared Recorder.
import { defineCatalog } from "@json-render/core";
import { schema } from "@json-render/react/schema";
import { z } from "zod";

export const coachCatalog = defineCatalog(schema, {
  components: {
    // ── On-page overlay widgets ───────────────────────────────────────────
    CoachCard: {
      props: z.object({
        intent:   z.string(),
        headline: z.string(),
        body:     z.string(),
        cta:      z.string().optional(),
        surface:  z.string().optional(),
      }),
      description: "Primary coaching card (headline + body + CTA + dismiss)",
    },
    Banner: {
      props: z.object({ tone: z.string().optional(), text: z.string() }),
      description: "Informational banner strip (info | warn | success)",
    },
    Toast: {
      props: z.object({ text: z.string(), duration: z.number().optional() }),
      description: "Auto-dismissing toast notification",
    },
    Tooltip: {
      props: z.object({ anchor: z.string().optional(), body: z.string() }),
      description: "Anchored tooltip callout",
    },
    BottomSheet: {
      props: z.object({ title: z.string() }),
      description: "Modal sheet sliding up from bottom",
    },
    CTA: {
      props: z.object({ label: z.string(), variant: z.string().optional() }),
      description: "Stand-alone CTA button",
    },
    InfoBlock: {
      props: z.object({ title: z.string(), bullets: z.array(z.string()) }),
      description: "Title + bullet-point list",
    },
    PriceReframe: {
      props: z.object({ monthly: z.number(), daily: z.number() }),
      description: "€X/month = €Y/day reframe card",
    },
    MarketCompare: {
      props: z.object({ ours: z.number(), market: z.number(), note: z.string().optional() }),
      description: "Our price vs market average comparison",
    },
    CallbackCTA: {
      props: z.object({ channel: z.string().optional(), phone: z.string().optional() }),
      description: "Phone / callback request card",
    },

    // ── Off-page surface confirmations ───────────────────────────────────
    EmailResume: {
      props: z.object({
        subject: z.string().optional(),
        to:      z.string().optional(),
        body:    z.string().optional(),
      }),
      description: "'Email sent' confirmation shown in-page",
    },
    WhatsAppCTA: {
      props: z.object({ number: z.string().optional(), message: z.string().optional() }),
      description: "WhatsApp contact card with QR / tel link",
    },
    Survey: {
      props: z.object({ question: z.string(), options: z.array(z.string()) }),
      description: "Inline survey with option buttons",
    },
  },
});

export type CoachCatalog = typeof coachCatalog;
