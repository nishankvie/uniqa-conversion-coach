"""
LoRA SFT of a small instruct model into a local per-step PERSONA model (one per persona).

Distills the frontier teacher's per-step behaviour (events + state + stay/leave decision)
into a fast local model. Completion-only loss on the assistant turn. Runs on 1x A100.

    python leonardo/train_persona_lora.py --persona franz \
        --base Qwen/Qwen2.5-1.5B-Instruct --data leonardo/data --out leonardo/out/franz

Deps (Leonardo pixi/conda env): torch, transformers, peft, trl, datasets, accelerate, bitsandbytes.
"""
from __future__ import annotations

import argparse
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", required=True, choices=["judith", "franz", "peter"])
    ap.add_argument("--base", default="Qwen/Qwen2.5-1.5B-Instruct")
    ap.add_argument("--data", default="leonardo/data")
    ap.add_argument("--out", default=None)
    ap.add_argument("--epochs", type=float, default=3.0)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--bsz", type=int, default=4)
    ap.add_argument("--grad_accum", type=int, default=4)
    ap.add_argument("--max_len", type=int, default=4096)
    args = ap.parse_args(argv)

    import torch
    from datasets import load_dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import SFTConfig, SFTTrainer

    out = args.out or f"leonardo/out/{args.persona}"
    data = Path(args.data)
    ds = load_dataset("json", data_files={
        "train": str(data / f"{args.persona}.train.jsonl"),
        "validation": str(data / f"{args.persona}.val.jsonl")})

    tok = AutoTokenizer.from_pretrained(args.base)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.base, torch_dtype=torch.bfloat16,
                                                 device_map="auto")
    lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
                      task_type="CAUSAL_LM",
                      target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                                      "gate_proj", "up_proj", "down_proj"])
    cfg = SFTConfig(
        output_dir=out, num_train_epochs=args.epochs, learning_rate=args.lr,
        per_device_train_batch_size=args.bsz, gradient_accumulation_steps=args.grad_accum,
        per_device_eval_batch_size=args.bsz, eval_strategy="epoch", logging_steps=10,
        bf16=True, max_length=args.max_len, gradient_checkpointing=True,
        warmup_ratio=0.03, lr_scheduler_type="cosine", save_strategy="epoch",
        assistant_only_loss=True,          # completion-only: learn the assistant JSON turn
        packing=False, report_to=[])
    trainer = SFTTrainer(model=model, args=cfg, peft_config=lora,
                         train_dataset=ds["train"], eval_dataset=ds["validation"],
                         processing_class=tok)
    trainer.train()
    trainer.save_model(out)
    tok.save_pretrained(out)
    print(f"saved LoRA adapter -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
