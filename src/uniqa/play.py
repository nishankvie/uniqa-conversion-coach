"""
Play the journey as a HUMAN and emit the SAME event schema the simulator emits.

This proves the contract is real: whether the user is a psyche persona model or a
person at a keyboard, the APP produces one `ActivityLog` of `contracts.Event`s.
The same log feeds eventproc (collapse/features/detections), the TLM tokenizer,
and the coach.

  python -m uniqa.play              # interactive
  python -m uniqa.play --demo       # scripted walk (no input), prints everything

Schematic UI ("UI images") are ASCII wireframes per step — same render contract,
text renderer.
"""

from __future__ import annotations

import random
import sys

from uniqa.funnel import Step
from uniqa.scope import IN_SCOPE_STEPS, Coverage, Insured, Tariff, route
from uniqa.contracts import Event, EventType, ActivityLog, new_session_id


# ─── Schematic UI (ASCII wireframe) ───────────────────────────────────────────

SCHEMATIC: dict[Step, str] = {
    Step.COVERAGE_TYPE: """
 ┌─ Angaben ───────────────────────────────────┐
 │  Wo möchten Sie abgesichert sein?            │
 │   [ Bei Arztbesuchen ]   [ Im Krankenhaus ]  │
 └──────────────────────────────────────────────┘""",
    Step.INSURED: """
 ┌─ Angaben ───────────────────────────────────┐
 │  Wer soll versichert werden?                 │
 │   [ Ich selbst ]   [ Andere Personen ]       │
 └──────────────────────────────────────────────┘""",
    Step.PERSONAL_INFO: """
 ┌─ Angaben ───────────────────────────────────┐
 │  Für Ihre Prämie benötigen wir:              │
 │   Geburtsdatum [____.__.____]                │
 │   SV-Nummer    [__________]                  │
 └──────────────────────────────────────────────┘""",
    Step.TARIFF_SELECT: """
 ┌─ Produkt ─ Tarifauswahl ─────────────────────┐
 │  Start  €38,74 ✅   Optimal €68,14 ✅          │
 │  Opt.Plus €96,66 ☎   Premium €140,15 ☎        │
 └──────────────────────────────────────────────┘""",
    Step.PERSONAL_DATA: """
 ┌─ Abschluss ─ Daten + Gesundheitsfragen ──────┐
 │  Vorname[____] Name[____] E-Mail[________]    │
 │  SV-Nr[______]  Gesundheitsfragen [ ... ]     │
 │  Endpreis: €68,14/Monat        [ Abschließen ]│
 └──────────────────────────────────────────────┘""",
    Step.PURCHASE: """
 ┌─ Abschluss ──────────────────────────────────┐
 │   ✅ Online abgeschlossen. Willkommen!         │
 └──────────────────────────────────────────────┘""",
}


def ascii_screen(step: Step) -> str:
    return SCHEMATIC.get(step, f"[{step.value}]")


# ─── micro-event synthesis (mouse moves, pauses, hover, edits) ────────────────

def _mouse_to(log: ActivityLog, step: Step, t: float, target: str, n: int = 3) -> float:
    for _ in range(n):
        log.append(Event(EventType.MOUSE_MOVE, step.value, t, target=target)); t += 0.08
    return t


def _emit_choice(log: ActivityLog, step: Step, t: float, target: str,
                 dwell: float, hovers: int, edits: int) -> float:
    """Synthesize the micro-events a human produces around a single decision."""
    log.append(Event(EventType.STEP_ENTER, step.value, t)); t += 0.1
    t = _mouse_to(log, step, t, target)
    if dwell:
        log.append(Event(EventType.PAUSE, step.value, t, value=round(dwell, 1))); t += dwell
    for _ in range(hovers):
        log.append(Event(EventType.HOVER, step.value, t, target=target)); t += 0.3
    for _ in range(edits):
        log.append(Event(EventType.FIELD_EDIT, step.value, t, target="sv_number")); t += 0.6
    return t


# ─── trace builder (scripted; used by --demo and tests) ───────────────────────

def human_trace(choices: dict | None = None, seed: int = 0) -> ActivityLog:
    """
    Build a human-style ActivityLog deterministically.
    `choices` overrides defaults: coverage/insured/tariff + per-step dwell/hovers/edits.
    """
    rng = random.Random(seed)
    c = {
        "coverage": Coverage.DOCTOR_VISITS, "insured": Insured.SELF, "tariff": Tariff.OPTIMAL,
        "tariff_dwell": 9.0, "tariff_hovers": 2, "info_edits": 1, "convert": True,
    }
    if choices:
        c.update(choices)

    log = ActivityLog(new_session_id())
    t = 0.0
    t = _emit_choice(log, Step.COVERAGE_TYPE, t, "start_tariff", dwell=1.5, hovers=0, edits=0)
    log.append(Event(EventType.TARIFF_CLICK, Step.COVERAGE_TYPE.value, t, target=c["coverage"].value)); t += 0.3

    t = _emit_choice(log, Step.INSURED, t, "field", dwell=1.0, hovers=0, edits=0)
    log.append(Event(EventType.SUBMIT, Step.INSURED.value, t, value=c["insured"].value)); t += 0.3

    # out-of-scope short-circuit → advisor handoff (no further coaching)
    decision = route(c["coverage"], c["insured"], c["tariff"])
    if not decision.in_scope:
        log.append(Event(EventType.ABANDON, Step.INSURED.value, t, value="advisor_handoff"))
        return log

    t = _emit_choice(log, Step.PERSONAL_INFO, t, "sv_number", dwell=2.0, hovers=0, edits=c["info_edits"])
    log.append(Event(EventType.SUBMIT, Step.PERSONAL_INFO.value, t, value="dob+sv")); t += 0.3

    t = _emit_choice(log, Step.TARIFF_SELECT, t, "price",
                     dwell=c["tariff_dwell"], hovers=c["tariff_hovers"], edits=0)
    log.append(Event(EventType.PRICE_HOVER, Step.TARIFF_SELECT.value, t, target="price")); t += 0.3
    log.append(Event(EventType.TARIFF_CLICK, Step.TARIFF_SELECT.value, t, target=c["tariff"].value)); t += 0.3

    t = _emit_choice(log, Step.PERSONAL_DATA, t, "email", dwell=3.0, hovers=0, edits=1)
    if c["convert"]:
        log.append(Event(EventType.SUBMIT, Step.PERSONAL_DATA.value, t, value="final")); t += 0.3
        log.append(Event(EventType.STEP_ENTER, Step.PURCHASE.value, t))
        log.append(Event(EventType.CONVERT, Step.PURCHASE.value, t + 0.2, value="online_purchase"))
    else:
        log.append(Event(EventType.CANCEL_HOVER, Step.PERSONAL_DATA.value, t, target="cancel")); t += 0.3
        log.append(Event(EventType.ABANDON, Step.PERSONAL_DATA.value, t, value="price_delta"))
    return log


# ─── CLI ──────────────────────────────────────────────────────────────────────

def _print_report(log: ActivityLog) -> None:
    from uniqa.eventproc import collapse, detections, features
    from uniqa.tlm import encode
    print("\n── RAW EVENTS ──", len(log.events))
    print("── COLLAPSED MOMENTS ──")
    for m in collapse(log):
        print(f"   {m.t0:6.1f}s  {m.label:14s} {m.step:18s} {m.detail}")
    print("── DETECTIONS ──")
    for d in detections(log):
        print(f"   {d.t:6.1f}s  {d.name:18s} score={d.score}  {d.note}")
    print("── TLM TOKENS ──", len(encode(log, persona="unknown")), "ids "
          f"(vocab={__import__('uniqa.tlm', fromlist=['VOCAB']).VOCAB.__len__()})")


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if "--demo" in argv:
        log = human_trace()
        for s in IN_SCOPE_STEPS:
            print(ascii_screen(s))
        _print_report(log)
        return 0

    # interactive
    log = ActivityLog(new_session_id()); t = 0.0
    print("UNIQA journey — type the bracketed option. (Ctrl-C to quit)")
    cov = _ask(Step.COVERAGE_TYPE, {"a": Coverage.DOCTOR_VISITS, "h": Coverage.HOSPITAL},
               "a=Arztbesuche  h=Krankenhaus")
    log.append(Event(EventType.STEP_ENTER, Step.COVERAGE_TYPE.value, t)); t += 1
    log.append(Event(EventType.TARIFF_CLICK, Step.COVERAGE_TYPE.value, t, target=cov.value)); t += 1
    ins = _ask(Step.INSURED, {"s": Insured.SELF, "o": Insured.OTHERS}, "s=Ich selbst  o=Andere")
    log.append(Event(EventType.SUBMIT, Step.INSURED.value, t, value=ins.value)); t += 1
    if not route(cov, ins).in_scope:
        print("→ advisor handoff (out of scope). No coaching.")
        log.append(Event(EventType.ABANDON, Step.INSURED.value, t, value="advisor_handoff"))
        _print_report(log); return 0
    tar = _ask(Step.TARIFF_SELECT, {"s": Tariff.START, "o": Tariff.OPTIMAL,
               "p": Tariff.PREMIUM}, "s=Start  o=Optimal  p=Premium")
    log.append(Event(EventType.STEP_ENTER, Step.TARIFF_SELECT.value, t)); t += 1
    log.append(Event(EventType.TARIFF_CLICK, Step.TARIFF_SELECT.value, t, target=tar.value)); t += 1
    if tar in (Tariff.OPT_PLUS, Tariff.PREMIUM):
        print("→ advisory tariff: consultation required. Try Start/Optimal online.")
    done = input("Abschließen? [y/n] ").strip().lower().startswith("y")
    log.append(Event(EventType.CONVERT if done else EventType.ABANDON,
                     Step.PURCHASE.value if done else Step.PERSONAL_DATA.value, t,
                     value="online_purchase" if done else "abandon"))
    _print_report(log)
    return 0


def _ask(step: Step, opts: dict, hint: str):
    print(ascii_screen(step)); 
    while True:
        k = input(f"  choose ({hint}): ").strip().lower()[:1]
        if k in opts:
            return opts[k]


if __name__ == "__main__":
    raise SystemExit(main())
