// recorderContext.tsx — React context that provides the Recorder to all twin components.
import React, { createContext, useContext } from "react";
import type { Recorder } from "../capture.js";

const RecorderCtx = createContext<Recorder | null>(null);

export const RecorderProvider = RecorderCtx.Provider;

export function useRecorder(): Recorder {
  const rec = useContext(RecorderCtx);
  if (!rec) throw new Error("useRecorder: missing <RecorderProvider>");
  return rec;
}
