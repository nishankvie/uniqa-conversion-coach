// funnelRefs.ts — DOM ref registry for coach overlay (focus, scroll, highlight).
// Components call registerRef(id, el) on mount; effectorBridge calls getRef(id).

const refs = new Map<string, HTMLElement>();

/** Register a DOM element under an id. Call on mount. */
export function registerRef(id: string, el: HTMLElement | null): void {
  if (el) refs.set(id, el);
  else refs.delete(id);
}

/** Retrieve a registered element. Returns undefined if not yet mounted. */
export function getRef(id: string): HTMLElement | undefined {
  return refs.get(id);
}

/** The full map (read-only view for step E effectorBridge). */
export const funnelRefsMap: ReadonlyMap<string, HTMLElement> = refs;
