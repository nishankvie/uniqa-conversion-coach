# `@json-render/react` — Implementation Cheatsheet

> Sourced from json-render.dev/docs (schemas, components/registry, api/react) via
> parent-session search-result excerpts. Where the exact serialisation isn't given
> verbatim by the docs, the pattern is annotated `[inferred from documented structure]`.

---

## 1. Packages

```bash
npm install @json-render/react        # core + React renderer
# also available (not used for this project):
# @json-render/react-native  @json-render/react-email  @json-render/remotion
```

`@json-render/react` ships: `JsonRenderer`, `defineRegistry`, `useStateStore`,
`StateProvider`, `RegistryProvider`, TypeScript types.

---

## 2. Concepts in 30 seconds

```
CATALOG  — TypeScript/JSON declaration: which component types exist + their prop
           types; which action names exist + their param types.
           Think of it as an interface spec.

REGISTRY — A CATALOG bound to RUNTIME implementations (React components +
           action handler functions). Created with defineRegistry(catalog, impls).

SCHEMA   — JSON that describes a SPECIFIC UI: an elements map (component tree
           keyed by id) + the root element key + initial state.
           References component type names from the catalog.

STATE    — A flat Record<string, unknown> (JSON-Pointer addressable). Bound to
           component props via $state expressions. Mutated by action handlers.
```

---

## 3. Schema structure

```jsonc
// A schema is pure JSON — no code, just data.
{
  "root": "stepContainer",        // which element is the entry point
  "elements": {
    // each key is a unique element id
    "stepContainer": {
      "type": "Stack",            // must match a type name in the catalog
      "props": {
        "direction": "column"     // static prop value
      },
      "children": ["heading", "form", "navButtons"]
    },

    "heading": {
      "type": "Heading",
      "props": {
        // $state: JSON Pointer path into the state model
        "text": { "$state": "/steps/0/title" }
      }
    },

    "form": {
      "type": "TextField",
      "props": {
        "label": "Geburtsdatum",
        "value":   { "$state": "/formData/dob" },
        "error":   { "$state": "/errors/dob" },
        // action reference: name + params object
        "onChange": { "action": "setField", "params": { "path": "/formData/dob" } }
      }
    },

    "submitBtn": {
      "type": "Button",
      "props": {
        "label": "Weiter",
        "onClick": { "action": "nextStep", "params": {} },
        // conditional: disable when loading (boolean $state)
        "disabled": { "$state": "/isLoading" }
      }
    }
  }
}
```

### $state data-binding (JSON Pointer)

- Any prop value can be replaced with `{ "$state": "/json/pointer/path" }`.
- The JSON Pointer path addresses into the **state model** (the `initialState` object).
- Deeply nested: `/formData/address/postcode`, `/steps/2/visible`, etc.
- Arrays: `/items/0/label`.
- The renderer re-renders elements when their bound state paths change.

### Conditional rendering [inferred from documented structure]

```jsonc
{
  "type": "ConditionalWrapper",
  "props": {
    "show": { "$state": "/currentStep" },
    "value": 2
  },
  "children": ["step2Content"]
}
```
Or more idiomatically, keep `currentStep` in state and have the Step component
evaluate visibility: the catalog component receives the bound value and returns
`null` when not active. See §6 multi-step pattern for the complete approach.

---

## 4. Catalog

The catalog is a TypeScript/JS object declaring the **types** (not implementations):

```ts
// catalog.ts  — type declarations only, no React code
export const catalog = {
  components: {
    Stack:     { props: { direction: "string", gap: "number" } },
    Heading:   { props: { text: "string", level: "number" } },
    TextField: { props: { label: "string", value: "string", error: "string",
                           onChange: "action" } },
    Button:    { props: { label: "string", onClick: "action",
                           disabled: "boolean", variant: "string" } },
    ChoiceCard:{ props: { id: "string", title: "string", checked: "boolean",
                           onChange: "action" } },
    Step:      { props: { index: "number", current: "number" } },
  },
  actions: {
    setField:   { params: { path: "string", value: "unknown" } },
    nextStep:   { params: {} },
    prevStep:   { params: {} },
    selectCard: { params: { group: "string", id: "string" } },
    validate:   { params: { fields: "string[]" } },
  },
} as const;
```

The `@json-render/react` schema supports an **`actions` key** in the catalog where
you define "what operations AI (or the schema) can trigger".

---

## 5. Registry — `defineRegistry`

Binds the catalog to real React components and action handler functions.

```tsx
// registry.tsx
import { defineRegistry } from "@json-render/react";
import { catalog } from "./catalog";

export const registry = defineRegistry(catalog, {

  // ─── React component implementations ───────────────────────────────────
  components: {
    Stack: ({ direction = "column", gap = 8, children }) => (
      <div style={{ display: "flex", flexDirection: direction, gap }}>{children}</div>
    ),

    TextField: ({ label, value, error, onChange }) => (
      <div>
        <label>{label}</label>
        <input value={value ?? ""} onChange={(e) => onChange?.(e.target.value)} />
        {error && <span className="helper-text error">{error}</span>}
      </div>
    ),

    Button: ({ label, onClick, disabled, variant = "primary" }) => (
      <button className={`btn btn-${variant}`} onClick={onClick} disabled={disabled}>
        {label}
      </button>
    ),

    ChoiceCard: ({ id, title, checked, onChange }) => (
      <label className={`choice-card ${checked ? "selected" : ""}`}>
        <input type="checkbox" checked={!!checked} onChange={() => onChange?.(id)} />
        {title}
      </label>
    ),

    // Step: renders children only when `index === current`
    Step: ({ index, current, children }) =>
      index === current ? <>{children}</> : null,
  },

  // ─── Action handler implementations ────────────────────────────────────
  // Signature (from docs): (params, setState, state) => void | Promise<void>
  actions: {
    setField: ({ path, value }, setState) => {
      setState(path, value);
    },

    nextStep: (_params, setState, state) => {
      const cur = (state["/currentStep"] as number) ?? 0;
      setState("/currentStep", cur + 1);
    },

    prevStep: (_params, setState, state) => {
      const cur = (state["/currentStep"] as number) ?? 0;
      setState("/currentStep", Math.max(0, cur - 1));
    },

    selectCard: ({ group, id }, setState, state) => {
      // for multi-select checkboxes
      const prev = (state[`/${group}/selected`] as string[]) ?? [];
      const next = prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id];
      setState(`/${group}/selected`, next);
    },

    validate: ({ fields }, setState, state) => {
      const errors: Record<string, string> = {};
      for (const f of fields) {
        const val = state[`/formData/${f}`];
        if (!val) errors[f] = `${f} ist erforderlich.`;
      }
      setState("/errors", errors);
      setState("/isValid", Object.keys(errors).length === 0);
    },
  },
});
```

---

## 6. Rendering + state API

### Uncontrolled (simple — state owned by `JsonRenderer`)

```tsx
import { JsonRenderer } from "@json-render/react";
import { registry } from "./registry";
import { mySchema } from "./schema";

export function MyForm() {
  return (
    <JsonRenderer
      schema={mySchema}
      registry={registry}
      initialState={{
        currentStep: 0,
        formData: { dob: "", sv: "" },
        errors: {},
        isLoading: false,
        coverage: { selected: [] },
      }}
      onStateChange={(changes) => {
        // changes: Array<{ path: string; value: unknown }>
        // called once per set/update with all changed entries
        console.log("state changed", changes);
      }}
    />
  );
}
```

### Controlled (state owned externally — e.g. for capture/logging)

```tsx
import { useStateStore, JsonRenderer } from "@json-render/react";

function ControlledForm() {
  // create an external store
  const store = useStateStore({ initialState: { currentStep: 0, formData: {} } });
  //   store.state  : Record<string, unknown>
  //   store.get(path) : unknown
  //   store.set(path, value) : void
  //   store.update(updates: Record<string, unknown>) : void

  // log every event to the capture recorder
  store.onStateChange = (changes) => {
    changes.forEach(({ path, value }) => logToCapture(path, value));
  };

  return <JsonRenderer schema={mySchema} registry={registry} store={store} />;
  // When `store` is provided, `initialState` and `onStateChange` props are IGNORED
}
```

### `useStateStore` hook (inside a registry component)

```tsx
import { useStateStore } from "@json-render/react";

function MyDeepComponent() {
  const { state, get, set, update } = useStateStore();

  return (
    <button onClick={() => set("/currentStep", (get("/currentStep") as number) + 1)}>
      Next (step {get("/currentStep") as number})
    </button>
  );
}
```

---

## 7. Multi-step form pattern

### Schema (excerpt)

```jsonc
{
  "root": "wizard",
  "elements": {
    "wizard": {
      "type": "Stack",
      "children": ["step1", "step2", "step3", "navRow"]
    },
    "step1": {
      "type": "Step",
      "props": { "index": 0, "current": { "$state": "/currentStep" } },
      "children": ["step1Content"]
    },
    "step2": {
      "type": "Step",
      "props": { "index": 1, "current": { "$state": "/currentStep" } },
      "children": ["step2Content"]
    },
    "navRow": {
      "type": "NavRow",
      "props": {
        "step": { "$state": "/currentStep" },
        "onNext": { "action": "nextStep", "params": {} },
        "onBack": { "action": "prevStep", "params": {} }
      }
    }
  }
}
```

### State shape for multi-step

```js
{
  currentStep: 0,           // which Step component is visible
  formData: {               // collected across steps
    coverage: [],
    insured: null,
    dob: "",
    sv: "",
    tariff: null,
  },
  errors: {},               // field-level error messages
  isValid: false,
}
```

### Back/Weiter action (from §5)

```js
nextStep: (_p, setState, state) => setState("/currentStep", state["/currentStep"] + 1),
prevStep: (_p, setState, state) => setState("/currentStep", Math.max(0, state["/currentStep"] - 1)),
```

---

## 8. Key facts / gotchas

| Fact | Detail |
|---|---|
| `$state` paths | Must be **JSON Pointer** strings starting with `/`. `/a/b` ≠ `a.b`. |
| Action reference in props | `{ "action": "handlerName", "params": { ... } }` — params are passed as first arg to handler. |
| `setState` in handlers | First arg is JSON Pointer path; second is value. Not a React `setState` — it calls `store.set`. |
| Children | Array of element id strings referencing other keys in the `elements` map. |
| Provider hierarchy | `JsonRenderer` wraps `StateProvider` + `RegistryProvider`. Don't nest two `JsonRenderer`s. |
| Transitions | Supported in `@json-render/remotion` (Remotion schema: `transitions`, `effects` in catalog). `@json-render/react` does not ship built-in CSS transitions — handle in component implementations. |
| TypeScript | `defineRegistry(catalog, impls)` infers from the catalog for type-safe component + action props. |
| AI/coach actions | The `actions` key in catalog explicitly exists for "operations AI can trigger" — exact hook for coach interventions. |
