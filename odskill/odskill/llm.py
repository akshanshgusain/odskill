"""Minimal OpenRouter chat client (stdlib only) with tool calls and usage/cost tracking."""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

API_URL = "https://openrouter.ai/api/v1/chat/completions"


def load_env(path: str | os.PathLike | None = None) -> None:
    """Load KEY=VALUE lines from paper/.env into os.environ (no overwrite)."""
    p = Path(path) if path else Path(__file__).resolve().parents[2] / ".env"
    if not p.is_file():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)
        # paper/.env stores the OpenRouter secret as OPEN_ROUTER_KEY.
        if k == "OPEN_ROUTER_KEY":
            os.environ.setdefault("OPENROUTER_API_KEY", v)


@dataclass
class Usage:
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    cost: float = 0.0
    models: set = field(default_factory=set)
    prompt_tokens_per_call: list = field(default_factory=list)

    def add(self, u: dict, model: str | None) -> None:
        self.calls += 1
        prompt = int(u.get("prompt_tokens", 0) or 0)
        self.prompt_tokens += prompt
        self.prompt_tokens_per_call.append(prompt)
        self.completion_tokens += u.get("completion_tokens", 0) or 0
        self.cached_tokens += (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0) or 0
        self.cost += float(u.get("cost", 0) or 0)
        if model:
            self.models.add(model)

    def as_dict(self) -> dict:
        return {"calls": self.calls, "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens, "cached_tokens": self.cached_tokens,
                "cost_usd": round(self.cost, 6), "reported_models": sorted(self.models),
                "prompt_tokens_per_call": list(self.prompt_tokens_per_call),
                "max_prompt_tokens": max(self.prompt_tokens_per_call, default=0)}


class LLMError(RuntimeError):
    pass


class BudgetExceeded(LLMError):
    """ODSKILL_BUDGET_USD has been reached. No further requests are sent."""


_spend_lock = threading.Lock()
_spent = 0.0
sent_tool_names: list[str] | None = None


def spent() -> float:
    return _spent


def budget_limit() -> float | None:
    raw = os.environ.get("ODSKILL_BUDGET_USD", "").strip()
    if not raw:
        return None
    return float(raw)


def ensure_budget() -> None:
    """Abort before a request once cumulative process spend reaches the cap."""
    limit = budget_limit()
    if limit is None:
        return
    with _spend_lock:
        if _spent >= limit:
            raise BudgetExceeded(
                f"ODSKILL_BUDGET_USD {limit:.4f} reached (spent ${_spent:.4f}); "
                "aborting before the next request")


def note_cost(amount: float) -> None:
    global _spent
    with _spend_lock:
        _spent += float(amount or 0)


def as_text(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(str(block.get("text") or block.get("content") or ""))
        return "\n".join(p for p in parts if p)
    return str(content)


def chat(model: str, messages: list, tools: list | None = None, *, max_tokens: int = 4096,
         temperature: float = 0.0, usage: Usage | None = None, retries: int = 4,
         timeout: int = 180, reasoning_effort: str | None = None) -> dict:
    """One chat completion. Returns the assistant message dict."""
    ensure_budget()
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise LLMError("OPENROUTER_API_KEY not set (put it in paper/.env)")
    body = {"model": model, "messages": messages, "max_tokens": max_tokens,
            "temperature": temperature, "usage": {"include": True}}
    if reasoning_effort:
        body["reasoning"] = {"effort": reasoning_effort}
    if tools:
        body["tools"] = tools
        global sent_tool_names
        with _spend_lock:
            if sent_tool_names is None:
                sent_tool_names = [t.get("function", {}).get("name", "?") for t in tools]
                print("request_tools:", " ".join(sent_tool_names), flush=True)
    data = json.dumps(body).encode()
    last = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(API_URL, data=data, headers={
            "Authorization": f"Bearer {key}", "Content-Type": "application/json",
            "X-Title": "odskill-research"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                resp = json.loads(r.read())
            if "error" in resp:
                raise LLMError(json.dumps(resp["error"])[:500])
            used = resp.get("usage") or {}
            if usage is not None:
                usage.add(used, resp.get("model"))
            note_cost(float(used.get("cost") or 0))
            return resp["choices"][0]["message"]
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read()[:300]!r}"
            if e.code == 429:
                print(f"openrouter_429 attempt={attempt + 1}", flush=True)
            if e.code not in (408, 429, 500, 502, 503, 504):
                raise LLMError(last) from e
        except (urllib.error.URLError, TimeoutError, LLMError, KeyError) as e:
            last = f"{type(e).__name__}: {e}"
        time.sleep(min(60, 2 ** attempt * 3))
    raise LLMError(f"gave up after {retries + 1} attempts: {last}")
