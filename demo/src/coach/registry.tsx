// coach/registry.tsx — defineRegistry(coachCatalog, { components }).
// Action handlers (cta / dismiss / surfacePick) live in CoachLayer.tsx ActionProvider
// so they can close over the shared Recorder.
import { defineRegistry } from "@json-render/react";
import { coachCatalog } from "./catalog.js";

import CoachCard    from "./components/CoachCard.js";
import Banner       from "./components/Banner.js";
import Toast        from "./components/Toast.js";
import Tooltip      from "./components/Tooltip.js";
import BottomSheet  from "./components/BottomSheet.js";
import CTA          from "./components/CTA.js";
import InfoBlock    from "./components/InfoBlock.js";
import PriceReframe from "./components/PriceReframe.js";
import MarketCompare from "./components/MarketCompare.js";
import CallbackCTA  from "./components/CallbackCTA.js";
import EmailResume  from "./components/EmailResume.js";
import WhatsAppCTA  from "./components/WhatsAppCTA.js";
import Survey       from "./components/Survey.js";

export const { registry: coachRegistry } = defineRegistry(coachCatalog, {
  components: {
    CoachCard:    CoachCard    as any,
    Banner:       Banner       as any,
    Toast:        Toast        as any,
    Tooltip:      Tooltip      as any,
    BottomSheet:  BottomSheet  as any,
    CTA:          CTA          as any,
    InfoBlock:    InfoBlock    as any,
    PriceReframe: PriceReframe as any,
    MarketCompare: MarketCompare as any,
    CallbackCTA:  CallbackCTA  as any,
    EmailResume:  EmailResume  as any,
    WhatsAppCTA:  WhatsAppCTA  as any,
    Survey:       Survey       as any,
  },
});
