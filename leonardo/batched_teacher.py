"""
BatchedLocalTeacher — run MANY persona sessions through the SAME stepwise loop, but batch
every step's generations into ONE GPU call. This is the "blazing fast" local path: instead
of N_sessions × N_steps sequential generate() calls, we walk S1→S6 in LOCKSTEP over a cohort
and batch all active sessions' prompts per step (≈ N_steps batched calls total).

Faithful to LLMTeacher._session_stepwise: identical prompt builder, state updates, tariff
tracking, brief, leave/convert logic — only the model call is batched. So eval stays
comparable to the frontier dataset and to the sequential LocalTeacher.

    from leonardo.batched_teacher import BatchedLocalTeacher
    t = BatchedLocalTeacher(base, adapter, batch_size=48)
    logs = t.generate_cohort("franz", n=100, seed=500)   # list[ActivityLog]
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field

from uniqa.contracts import ActivityLog, Event, EventType, new_session_id
from uniqa.funnel import Step
from uniqa.persona_datagen import (
    _INSCOPE_FLOW, _sample_disposition, _sample_session_context, _strip_fences,
    build_step_decision_prompt, parse_session,
)
from leonardo.local_teacher import LocalTeacher


@dataclass
class _Run:
    rng: random.Random
    state: dict
    ctx: dict | None
    disp: dict | None
    intent: str | None = None
    selected_tariff: str | None = None
    events: list = field(default_factory=list)
    brief: list = field(default_factory=list)
    t: float = 0.0
    active: bool = True


class BatchedLocalTeacher(LocalTeacher):
    name = "local-batched"

    def __init__(self, base: str, adapter: str | None = None,
                 max_new_tokens: int = 768, batch_size: int = 48):
        super().__init__(base, adapter, max_new_tokens=max_new_tokens)
        self.batch_size = batch_size
        if self.tok.padding_side != "left":
            self.tok.padding_side = "left"   # decoder-only batched generation needs left pad

    # ── batched model call: list[messages] → list[str] ───────────────────────
    def _call_batch(self, msgs_list: list[list[dict]]) -> list[str]:
        out: list[str] = []
        for i in range(0, len(msgs_list), self.batch_size):
            out.extend(self._gen_chunk(msgs_list[i:i + self.batch_size]))
        return out

    def _gen_chunk(self, chunk: list[list[dict]]) -> list[str]:
        torch = self._torch
        # tokenize each via the chat template (identical to single-session path), then left-pad
        id_lists = [self.tok.apply_chat_template(m, add_generation_prompt=True, tokenize=True)
                    for m in chunk]
        maxlen = max(len(x) for x in id_lists)
        pad = self.tok.pad_token_id
        input_ids, attn = [], []
        for ids in id_lists:
            padn = maxlen - len(ids)
            input_ids.append([pad] * padn + ids)
            attn.append([0] * padn + [1] * len(ids))
        input_ids = torch.tensor(input_ids, device=self.model.device)
        attn = torch.tensor(attn, device=self.model.device)
        with torch.no_grad():
            gen = self.model.generate(input_ids=input_ids, attention_mask=attn,
                                      max_new_tokens=self.max_new_tokens, do_sample=True,
                                      temperature=0.9, top_p=0.95, pad_token_id=pad)
        gen = gen[:, input_ids.shape[1]:]
        return [self.tok.decode(g, skip_special_tokens=True) for g in gen]

    # ── cohort lockstep walk (mirrors _session_stepwise, batched per step) ────
    def generate_cohort(self, persona: str, n: int, seed: int = 0) -> list[ActivityLog]:
        runs: list[_Run] = []
        for i in range(n):
            rng = random.Random(seed + i)
            runs.append(_Run(
                rng=rng,
                state={"attention": 1.0, "satisfaction": 0.7, "effort_left": 1.0,
                       "grasp": 1.0, "effort_vs_reward": 0.7},
                ctx=_sample_session_context(persona, rng) if self.include_state else None,
                disp=_sample_disposition(persona, rng) if self.include_state else None,
            ))

        for step in _INSCOPE_FLOW:
            active = [r for r in runs if r.active]
            if not active:
                break
            msgs_list = []
            for r in active:
                r.events.append({"step": step.value, "type": "step_enter", "t": round(r.t, 2)})
                msgs_list.append(build_step_decision_prompt(
                    persona, step, r.brief[-6:], r.state,
                    include_quant=self.include_quant, include_params=self.include_params,
                    include_state=self.include_state, session_context=r.ctx,
                    intent=r.intent, disposition=r.disp, selected_tariff=r.selected_tariff))
            raws = self._call_batch(msgs_list)
            for r, raw in zip(active, raws):
                self._apply_step(r, step, raw)

        # survivors convert
        logs: list[ActivityLog] = []
        for r in runs:
            if r.active:
                r.events.append({"step": Step.PURCHASE.value, "type": "step_enter", "t": r.t + 0.5})
                r.events.append({"step": Step.PURCHASE.value, "type": "convert",
                                 "value": "online_purchase", "t": r.t + 1.0,
                                 "thought": "done — finished it online"})
            logs.append(self._finalize(r))
        return logs

    def _apply_step(self, r: _Run, step: Step, raw: str) -> None:
        try:
            out = json.loads(_strip_fences(raw))
        except Exception:
            out = {}
        r.t += r.rng.uniform(0.5, 2.0)
        step_evs = out.get("events") if isinstance(out, dict) else None
        done_here = []
        for ev in (step_evs or []):
            if not isinstance(ev, dict) or "type" not in ev:
                continue
            ev["step"] = step.value
            try:
                ev["t"] = r.t + float(ev.get("t", 0.0))
            except (TypeError, ValueError):
                ev["t"] = r.t
            done_here.append(ev)
        if done_here:
            r.t = max(e["t"] for e in done_here)
            r.events.extend(done_here)
            tgt = [str(e.get("target")) for e in done_here if e.get("target")]
            r.brief.append(f"{step.value}: " + ", ".join(tgt[:4]) if tgt else f"{step.value}: (viewed)")
            if step is Step.TARIFF_SELECT:
                for e in done_here:
                    if str(e.get("target") or "") in ("start", "optimal", "opt_plus", "premium"):
                        r.selected_tariff = str(e["target"]); break
        if isinstance(out.get("intent"), str) and not r.intent:
            r.intent = out["intent"]
        if self.include_state and isinstance(out.get("state"), dict):
            for k in ("attention", "satisfaction", "effort_left", "grasp", "effort_vs_reward"):
                if isinstance(out["state"].get(k), (int, float)):
                    r.state[k] = float(out["state"][k])
        if str(out.get("decision", "")).lower() == "leave":
            reason = out.get("reason") or out.get("feeling") or "left"
            feeling = out.get("feeling")
            val = f"{feeling}:{reason}" if feeling and feeling != "engaged" else reason
            r.events.append({"step": step.value, "type": "abandon", "target": None,
                             "value": val, "t": r.t + 0.4, "thought": reason})
            r.active = False

    @staticmethod
    def _finalize(r: _Run) -> ActivityLog:
        log = ActivityLog(new_session_id())
        evs = parse_session(r.events)
        if not evs:
            evs = [Event(EventType.STEP_ENTER, Step.COVERAGE_TYPE.value, 0.0)]
        cut = len(evs)
        for i, e in enumerate(evs):
            if e.type in (EventType.CONVERT, EventType.ABANDON):
                cut = i + 1; break
        log.events = evs[:cut]
        return log
