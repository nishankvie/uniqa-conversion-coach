"""
LocalTeacher — a fine-tuned per-persona model that plugs into the SAME stepwise loop as the
frontier LLMTeacher. This is the "replace the persona LLM with a fast local model" piece:
it reuses LLMTeacher._session_stepwise unchanged and only swaps _call() for local generation.

Because generation stays per-step, the dynamic coach widget slots in later by adding the
coach's action into each step's context (build_step_decision_prompt) — the local persona
model reacts, exactly as the frontier teacher did.

    from leonardo.local_teacher import LocalTeacher
    t = LocalTeacher("Qwen/Qwen2.5-1.5B-Instruct", "leonardo/out/franz")
    log = generate_feed("franz", t, random.Random(0))
"""
from __future__ import annotations

from uniqa.persona_datagen import LLMTeacher


class LocalTeacher(LLMTeacher):
    def __init__(self, base: str, adapter: str | None = None, max_new_tokens: int = 768):
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer
        # NB: do NOT call super().__init__ (it builds an OpenAI client). Set the attrs
        # _session_stepwise relies on, then load the local model.
        self.include_quant = False
        self.include_params = True
        self.stepwise = True
        self.include_state = True
        self.capture_steps = False
        self.step_log = []
        self.max_new_tokens = max_new_tokens
        self.tok = AutoTokenizer.from_pretrained(base)
        if self.tok.pad_token is None:
            self.tok.pad_token = self.tok.eos_token
        model = AutoModelForCausalLM.from_pretrained(base, torch_dtype=torch.bfloat16,
                                                     device_map="auto")
        self.model = PeftModel.from_pretrained(model, adapter) if adapter else model
        self.model.eval()
        self.name = f"local:{adapter or base}"
        self._torch = torch

    def _call(self, msgs: list[dict]) -> str:
        ids = self.tok.apply_chat_template(msgs, add_generation_prompt=True,
                                           return_tensors="pt").to(self.model.device)
        with self._torch.no_grad():
            out = self.model.generate(ids, max_new_tokens=self.max_new_tokens,
                                      do_sample=True, temperature=0.9, top_p=0.95,
                                      pad_token_id=self.tok.pad_token_id)
        return self.tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True)
