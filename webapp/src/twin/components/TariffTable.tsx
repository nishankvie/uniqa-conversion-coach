// TariffTable — 4-column tariff selection matrix with tooltip rows (S4).
import React from "react";
import type { BaseComponentProps } from "@json-render/react";
import { useStateStore } from "@json-render/react";
import { useRecorder } from "../recorderContext.js";
import { updateDerived } from "../transitions.js";
import TariffColumn from "./TariffColumn.js";
import CoverageRowTooltip from "./CoverageRowTooltip.js";
import coverageRows from "../data/coverage_rows.json";

interface Tariff { id: string; name: string; price: number; online: boolean; maxYear?: number; }
interface TariffTableProps { tariffs: Tariff[]; selected?: string | null; }

const TariffTable = ({ props }: BaseComponentProps<TariffTableProps>) => {
  const { get, set } = useStateStore();
  const recorder = useRecorder();
  const storeSlice = { get: (p: string) => get(p), set: (p: string, v: unknown) => set(p, v) };
  const selected = (get("/formData/tariff") as string | null) ?? null;

  function pickTariff(tariff: Tariff) {
    set("/formData/tariff", tariff.id);
    set("/provisionalPrice", tariff.price);
    recorder.emit("price_reveal", tariff.id, tariff.price);
    recorder.emit("select", tariff.id);
    updateDerived(storeSlice);
  }

  function premiumClick(tariff: Tariff) {
    recorder.emit("premium_click", tariff.id);
  }

  return (
    <div>
      {/* Tariff columns */}
      <div className="row" style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
        {props.tariffs.map((tariff) => (
          <TariffColumn
            key={tariff.id}
            props={{ ...tariff, selected: selected === tariff.id }}
            emit={(ev) => {
              if (ev === "pick") {
                tariff.online ? pickTariff(tariff) : premiumClick(tariff);
              }
            }}
            on={(_ev) => ({ emit: () => {}, shouldPreventDefault: false, bound: false })}
          />
        ))}
      </div>

      {/* Coverage row tooltips */}
      <div className="row" style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 10 }}>
        {(coverageRows as { id: string; label: string; body: string }[]).map((row) => (
          <CoverageRowTooltip
            key={row.id}
            props={{ row: row.id, body: row.body }}
            emit={() => {}}
            on={() => ({ emit: () => {}, shouldPreventDefault: false, bound: false })}
          />
        ))}
      </div>
    </div>
  );
};

export default TariffTable;
