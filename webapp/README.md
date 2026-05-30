# UNIQA Capture Widget (React)

The funnel capture surface: renders the real in-scope funnel screens, captures
**real physical mouse events** (movement, dwell-over-element, tab focus), and emits
**only high-level** entries in the `contracts.ActivityLog` schema — the same format
the persona bots produce, so `python -m uniqa.compare` consumes it directly.

## Run

```bash
cd webapp
npm install
npm run dev        # http://localhost:5173
```

The Streamlit dashboard ("Play & capture" view) links here.

## What it captures

- **hover / price_hover / tooltip_open** — derived from real dwell over an element
  (>= 450 ms). Raw mousemove samples are never emitted.
- **mouse tone** per step (`rushed | hesitant | deliberate | steady`) — from movement
  distance, direction flips, idle ratio, and re-hovers; back-filled onto `step_enter.thought`.
- **idle** — no movement for >= 2.5 s (attention gap).
- **tab_blur / tab_focus** — real browser tab switches (`visibilitychange`); `tab_focus`
  carries the real seconds away.
- **select / tariff price_reveal / premium_click / keystroke / dropdown_open / submit**
  — funnel actions. **convert / abandon** (close, external link, advisor route) — terminals.

## Output

Finishing a session offers a **Download log JSON**. Save it into `_local/captures/`
and run:

```bash
python -m uniqa.compare _local/captures/<id>.json --persona franz
```
