# Component: <NAME>

> One-line purpose. What it does and why it exists.
> Module: `src/uniqa/<file>.py` · Status: <draft|built|tested> · Tests: `tests/<file>.py`

---

## 1. Responsibility (one paragraph)
What this component owns, and — just as important — what it does **not** own.
Name the single reason it would change.

## 2. Mutability
- [ ] IMMUTABLE (part of the fixed App surface — never trained/edited by research)
- [ ] MUTABLE  (trained / optimised — e.g. the coach policy)
- [ ] DERIVED  (pure function of other components; no own state)

## 3. Inputs / Outputs (the contract)

| Direction | Type | Schema / shape | Source / sink |
|-----------|------|----------------|---------------|
| in  | | | |
| out | | | |

Every type here must be JSON-serialisable (`to_dict()` round-trips). Link the
dataclass/enum in `contracts.py` it conforms to.

## 4. Public API
```python
# signatures only — the stable surface other components depend on
def fn(...) -> ...: ...
```

## 5. Data flow (ASCII)
```
INPUT ─▶ [ step ] ─▶ [ step ] ─▶ OUTPUT
                 │
                 ▼ shadow paths: nil? empty? error? stale?
```

## 6. Invariants & guardrails
- Hard constraints this component enforces no matter what callers ask (e.g.
  `EffectorCommand.validate()`, Franz-never-advisor, scope routing).
- What must always be true after each public call.

## 7. Failure modes

| Codepath | What goes wrong | Handled? | User/Coach sees |
|----------|-----------------|----------|------------------|
| | | | |

## 8. Tests (what proves it works)
- Happy path:
- Edge / shadow paths:
- Property / determinism:

## 9. Telemetry / observability
What it logs or emits that lets us debug it in production (events, metrics).

## 10. Open questions / TODO
- [ ] …
