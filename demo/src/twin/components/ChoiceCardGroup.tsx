// ChoiceCardGroup — multi-checkbox (S1) or radio (S2) group.
// Directly accesses funnelStore via useStateStore + useRecorder for event emission.
import React from "react";
import type { BaseComponentProps } from "@json-render/react";
import { useStateStore } from "@json-render/react";
import { useRecorder } from "../recorderContext.js";
import { updateDerived } from "../transitions.js";
import ChoiceCard from "./ChoiceCard.js";

interface Item { id: string; title: string; icon?: string; features?: string[]; }
interface ChoiceCardGroupProps { mode: string; group: string; items: Item[]; }

const ChoiceCardGroup = ({ props }: BaseComponentProps<ChoiceCardGroupProps>) => {
  const { get, set, getSnapshot } = useStateStore();
  const recorder = useRecorder();

  function handleToggle(id: string) {
    const storeSlice = {
      get: (p: string) => get(p),
      set: (p: string, v: unknown) => set(p, v),
    };

    if (props.mode === "checkbox") {
      const prev = (get("/formData/coverage/selected") as string[]) ?? [];
      const next = prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id];
      set("/formData/coverage/selected", next);
      recorder.emit("select", id, next.includes(id));
      updateDerived(storeSlice);

    } else {
      // radio — single select
      set("/formData/insured", id);
      recorder.emit("select", id);
      updateDerived(storeSlice);
    }
  }

  const selected = props.mode === "checkbox"
    ? ((get("/formData/coverage/selected") as string[]) ?? [])
    : [(get("/formData/insured") as string | null) ?? ""];

  return (
    <div className="row" style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 16 }}
      role={props.mode === "radio" ? "radiogroup" : "group"}>
      {props.items.map((item) => (
        <ChoiceCard
          key={item.id}
          props={{ ...item, checked: selected.includes(item.id), mode: props.mode }}
          emit={(ev) => ev === "toggle" && handleToggle(item.id)}
          on={(_ev) => ({ emit: () => handleToggle(item.id), shouldPreventDefault: false, bound: true })}
        />
      ))}
    </div>
  );
};

export default ChoiceCardGroup;
