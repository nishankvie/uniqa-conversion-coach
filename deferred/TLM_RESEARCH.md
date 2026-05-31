# TLM — Trajectory Language Model: research + feasibility

A **TLM** is a small autoregressive transformer over **journey tokens** (events,
not words). Goal: replace prompt-driven LLM personas with **learned persona-TLMs**
that emit realistic event feeds, and (same vocab) a **coach-TLM** policy.

Token space is implemented in `calculator/tlm.py`; this doc is the literature
grounding + a go/no-go feasibility test you can run in an afternoon.

---

## 1. Prior art (this is a known-good shape)

| Work | Relevance |
|------|-----------|
| **Decision Transformer** (Chen et al. 2021, arXiv 2106.01345) | RL as next-token prediction over `(return, state, action)` tokens. Our coach-TLM = same idea: predict the next *coach action* token. |
| **Trajectory Transformer** (Janner et al. 2021, arXiv 2106.02039) | Discretise continuous state/action into tokens, model with a GPT decoder. We discretise dwell/hover/Δt into buckets — identical move. |
| **Behavior Sequence Transformer / BST** (Alibaba 2019, arXiv 1905.06874) | Transformers over user behaviour sequences, **deployed in Taobao prod**. Evidence the architecture works on real clickstreams. |
| **TRACE** (2024, arXiv 2409.12972) | Lightweight transformer encoder over *attributed clickstream events* → user embeddings. Confirms small models suffice. |
| **BERT4ClickPath** (2021) | Configurable transformer for click-path data; reference for tokenisation choices. |
| **LLM human-behavior simulation** (arXiv 2503.20749; Kuaishou benchmark 2604.08362) | LLMs predict next action **+ rationale** from observation+history; reasoning-synthesis pipeline. Justifies using persona-prompted LLMs as the *teacher* that labels traces (incl. reasoning). |
| **PersonaTrace** (EACL industry) | Persona profile → plausible event sequence → concrete artifacts. Exactly our "persona sys-prompt → event feed" data-generation recipe. |
| **Chinchilla** (Hoffmann 2022) / **SLM bottlenecks** (Ashkboos 2024) | Compute-optimal token/param ratios; small-model training economics → our sizing below. |

Takeaway: "tokenise the trajectory, train a tiny GPT, condition on a tag" is a
**well-trodden, production-proven** pattern. The novelty here is narrow (insurance
funnel, persona-conditioned generation + a coach head sharing the vocab), not the
method — low research risk.

---

## 2. The token space (implemented)

Vocab ≈ **83 tokens** (`tlm.VOCAB`):
`special (PAD/BOS/EOS/SEP)` · `persona tags` · `step markers S0–S7` ·
`event types <ev:…>` · `targets <tgt:…>` · bucketised `<dwell:b> <count:b> <dt:b>` ·
`coach actions <coach:…>`.

A session encodes to **~50–300 tokens** (`encode()`), e.g. the demo human journey
= 125 ids. Two training objectives over one vocab:

```
Persona-TLM:  <bos><persona:franz><step:S4><ev:price_hover><tgt:price><dt:2> … <eos>
              loss on USER tokens   → next-behaviour prediction
Coach-TLM:    … <ev:idle><dwell:5><sep><coach:price_reframe> …
              loss on COACH tokens  → next-action policy
```

---

## 3. Feasibility math (it's tiny)

Reference config `tlm.TLMConfig` = 4 layers, 4 heads, d=128, block=512.

```
params  ≈ 12·n_layer·d²  + vocab·d  ≈ 12·4·128² + 83·128 ≈ 0.8 M
Chinchilla-optimal tokens ≈ 20 × params ≈ 16 M tokens
at ~150 tokens/session    ≈ 110 K sessions
```

110K persona-labelled sessions is **cheap** to synthesise (psyche model generates
them in seconds; an LLM teacher can label a subset with reasoning). Training a
0.8M-param GPT on 16M tokens is **minutes on one A100** (Leonardo `boost_usr_prod`,
reservation `s_tra_ncc`). This is squarely in nanoGPT territory — no distributed
training, no exotic infra.

---

## 4. Go/no-go test (one afternoon on Leonardo)

**Assumption under test:** *persona sys-prompts are enough to generate good event
feeds, and a TLM can learn to reproduce them.*

1. **Generate.** For each persona, prompt an LLM (sys-prompt = persona `.md`) to
   emit N event feeds in our JSON event schema. Validate every feed parses into
   `contracts.Event` (schema gate). Fallback teacher = the psyche model (already
   calibrated) for volume.
2. **Tokenise** with `tlm.encode(log, persona=…)`. Hold out 10%.
3. **Train** the tiny GPT (nanoGPT adapter) on next-token; mask loss to USER
   tokens for the persona-TLM.
4. **Score (3 gates):**
   - **Next-event accuracy / perplexity** vs an n-gram baseline (must beat it).
   - **Distribution match:** sample sessions from the TLM, compute funnel stats
     (per-step bounce, intent mix) and compare to the teacher + real anchors
     (baseline ≈5.6%, S4 ≈66%, S6 ≈78%) via TV/KL. Pass if within tolerance (say
     TV < 0.1) — this is the same ε that assumption **A1** (see AUTORESEARCH.md)
     depends on.
   - **Persona separability:** condition on each persona tag; generated stats must
     differ in the right direction (Franz price-sensitive, Peter overwhelmed early).
5. **Verdict.** All three pass → persona-TLMs are feasible and can replace the
   prompt-driven personas in Loop A (cheaper, faster, differentiable). Any gate
   fails → keep prompt-driven personas; the contract is unchanged either way.

**Risk register:** vocab too coarse (raise bucket resolution); LLM teacher feeds
unrealistic timing (calibrate Δt buckets to real logs in Loop B); mode collapse
on short sessions (mix temperatures, add EOS regularisation). All cheap to retry.

---

## 5. Why this matters

A persona-TLM is a **differentiable, fast, conditionable** user simulator. It
sharpens Loop A (synthetic autoresearch) and, because it shares the vocab with the
coach-TLM, lets us train both in one stack. The whole bet is low-risk: proven
architecture, tiny compute, synthetic data we already know how to generate, and a
clean schema gate (`contracts.Event`) between data and model.
