// decisionStream.ts — Pluggable decision source.
// localMockStream: hand-fired via stream.fire(decision) (for demo button in App.jsx).
// wsStream / httpPollStream: wiring for a real Python coach backend.

/** Serialised CoachDecision shape (subset — only what the frontend uses). */
export interface CoachDecision {
  command: {
    effector: string;
    step:     string;
    target?:  string | null;
    payload?: Record<string, unknown>;
    /** json-render Spec: { root, elements } */
    render?:  Record<string, unknown>;
  };
  reasoning:       string;
  confidence?:     number;
  value_estimate?: number;
}

export interface DecisionStream {
  subscribe(cb: (d: CoachDecision) => void): () => void;
}

/** A stream you can fire decisions into manually (for the hackathon demo button). */
export interface MutableDecisionStream extends DecisionStream {
  fire(d: CoachDecision): void;
}

/** Create a mutable local mock stream. */
export function createLocalMockStream(): MutableDecisionStream {
  const listeners: Array<(d: CoachDecision) => void> = [];
  return {
    subscribe(cb) {
      listeners.push(cb);
      return () => {
        const i = listeners.indexOf(cb);
        if (i >= 0) listeners.splice(i, 1);
      };
    },
    fire(d) {
      listeners.forEach((cb) => cb(d));
    },
  };
}

/** WebSocket-backed stream (for future Python coach bridge). */
export function wsStream(url: string): DecisionStream {
  return {
    subscribe(cb) {
      let ws: WebSocket | null = null;
      try {
        ws = new WebSocket(url);
        ws.onmessage = (ev) => {
          try { cb(JSON.parse(ev.data) as CoachDecision); } catch { /* malformed */ }
        };
      } catch { /* no WS available in test env */ }
      return () => { ws?.close(); };
    },
  };
}

/** HTTP-polling stream (for future Python coach bridge). */
export function httpPollStream(url: string, ms = 1000): DecisionStream {
  return {
    subscribe(cb) {
      let active = true;
      const poll = async () => {
        while (active) {
          try {
            const res = await fetch(url);
            if (res.ok) {
              const decisions: CoachDecision[] = await res.json();
              decisions.forEach(cb);
            }
          } catch { /* network error */ }
          await new Promise((r) => setTimeout(r, ms));
        }
      };
      poll();
      return () => { active = false; };
    },
  };
}
