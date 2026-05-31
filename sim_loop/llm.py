"""Minimal OpenRouter chat client (self-contained; reads .env-style env)."""
from __future__ import annotations
import json, os, sys, time, urllib.request, urllib.error, pathlib

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _load_dotenv():
    """Populate os.environ from repo-root .env if keys are missing."""
    root = pathlib.Path(__file__).resolve().parents[1]
    env = root / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()  # .env takes precedence over stale env


_load_dotenv()
DEFAULT_MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")


def chat(messages, *, model=None, temperature=0.8, max_tokens=900,
         timeout=60, retries=4) -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set (.env)")
    payload = {"model": model or DEFAULT_MODEL, "messages": messages,
               "temperature": temperature, "max_tokens": max_tokens}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    data = json.dumps(payload).encode()
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(OPENROUTER_URL, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                obj = json.loads(resp.read().decode())
                return obj["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            last = e
            body = ""
            try: body = e.read().decode()[:300]
            except Exception: pass
            sys.stderr.write(f"[chat] HTTP {e.code} {attempt+1}/{retries}: {body}\n")
            time.sleep(1.5 ** attempt)
        except Exception as e:
            last = e
            sys.stderr.write(f"[chat] {type(e).__name__} {attempt+1}/{retries}: {e}\n")
            time.sleep(1.5 ** attempt)
    raise RuntimeError(f"chat failed after {retries}: {last}")


def extract_json(text: str):
    """Pull the first {...} JSON object out of an LLM reply."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object in reply")
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == "{": depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError("unbalanced JSON in reply")
