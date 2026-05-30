// registry.tsx — defineRegistry(funnelCatalog, { components })
// Action handlers are in FunnelTwin.tsx (ActionProvider) so they can close over
// the external store + recorder.
import { defineRegistry } from "@json-render/react";
import { funnelCatalog } from "./catalog.js";

// Component implementations
import Stack from "./components/Stack.js";
import Heading from "./components/Heading.js";
import Instruction from "./components/Instruction.js";
import ProgressStepper from "./components/ProgressStepper.js";
import StepLiveRegion from "./components/StepLiveRegion.js";
import StickyOfferBar from "./components/StickyOfferBar.js";
import Wizard from "./components/Wizard.js";
import Step from "./components/Step.js";
import ChoiceCardGroup from "./components/ChoiceCardGroup.js";
import ChoiceCard from "./components/ChoiceCard.js";
import DatePicker from "./components/DatePicker.js";
import SearchableSelect from "./components/SearchableSelect.js";
import TextField from "./components/TextField.js";
import HelperTextError from "./components/HelperTextError.js";
import TariffTable from "./components/TariffTable.js";
import TariffColumn from "./components/TariffColumn.js";
import CoverageRowTooltip from "./components/CoverageRowTooltip.js";
import HealthForm from "./components/HealthForm.js";
import FinalPrice from "./components/FinalPrice.js";
import ClosingForm from "./components/ClosingForm.js";
import Button from "./components/Button.js";
import NavRow from "./components/NavRow.js";

export const { registry } = defineRegistry(funnelCatalog, {
  components: {
    Stack:              Stack as any,
    Heading:            Heading as any,
    Instruction:        Instruction as any,
    ProgressStepper:    ProgressStepper as any,
    StepLiveRegion:     StepLiveRegion as any,
    StickyOfferBar:     StickyOfferBar as any,
    Wizard:             Wizard as any,
    Step:               Step as any,
    ChoiceCardGroup:    ChoiceCardGroup as any,
    ChoiceCard:         ChoiceCard as any,
    DatePicker:         DatePicker as any,
    SearchableSelect:   SearchableSelect as any,
    TextField:          TextField as any,
    HelperTextError:    HelperTextError as any,
    TariffTable:        TariffTable as any,
    TariffColumn:       TariffColumn as any,
    CoverageRowTooltip: CoverageRowTooltip as any,
    HealthForm:         HealthForm as any,
    FinalPrice:         FinalPrice as any,
    ClosingForm:        ClosingForm as any,
    Button:             Button as any,
    NavRow:             NavRow as any,
  },
});
