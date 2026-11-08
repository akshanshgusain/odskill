"""Five TRAIN rollouts of the full-injection arm with an empty evolved set.

Used to project the cost of one locked campaign before launching it.
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

from wikiskill.benchmarks.spreadsheet import load_cases

from .llm import BudgetExceeded, load_env, spent
from .spreadsheet import rollout_case

PAPER = Path(__file__).resolve().parents[2]
DATA = PAPER / "data/spreadsheet/spreadsheetbench_verified_400"
SPLITS = PAPER / "wikiskill/src/wikiskill/resources/spreadsheet/id_split"
MODEL = "anthropic/claude-haiku-5.5"
# baseline val 40 + 6 iterations * (train 80 + val 40) = 760. The stop rule also
# quotes about 1,040 executor rollouts.
EXACT_ROLLOUTS = 40 + 6 * (80 + 40)
STATED_ROLLOUTS = 1040


def _train(n: int = 5):
    cases = {case.uid: case for case in load_cases(DATA)}
    ids = [item["uid"] if isinstance(item, dict) else item
           for item in json.loads((SPLITS / "train.json").read_text(encoding="utf-8"))]
    return [cases[uid] for uid in ids[:n]]


def _model_info() -> dict:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/models", headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode())
    found = next((item for item in payload.get("data", []) if item.get("id") == MODEL), {})
    return {"context_length": found.get("context_length"),
            "prompt_price": (found.get("pricing") or {}).get("prompt"),
            "completion_price": (found.get("pricing") or {}).get("completion")}


def main() -> None:
    load_env(PAPER / ".env")
    os.environ["ODSKILL_BUDGET_USD"] = "1.50"
    info = _model_info()
    print("model_info", json.dumps(info), flush=True)
    root = Path.home() / "odskill-runs" / "measure-all"
    rows = []
    for case in _train(5):
        try:
            rows.append(rollout_case(
                case, workdir=root, model=MODEL, skill_text="", mode="all", split="train",
                noise_k=100, seed=0, reasoning_effort="low"))
        except BudgetExceeded as exc:
            print("budget_stop", exc, flush=True)
            break
        usage = rows[-1].get("usage") or {}
        print(f"{rows[-1]['uid']} calls={usage.get('calls')} "
              f"max_prompt={usage.get('max_prompt_tokens')} "
              f"prompt_per_call={usage.get('prompt_tokens_per_call')} "
              f"cost={usage.get('cost_usd')} fail={rows[-1].get('fail_reason')}", flush=True)
    calls = [n for row in rows for n in (row.get("usage") or {}).get("prompt_tokens_per_call") or []]
    costs = [float((row.get("usage") or {}).get("cost_usd") or 0) for row in rows]
    avg = round(sum(calls) / len(calls), 1) if calls else None
    per = round(sum(costs) / len(rows), 4) if rows else None
    context = info.get("context_length") or 0
    peak = max(calls, default=0)
    summary = {
        "n": len(rows), "calls": len(calls), "avg_prompt_tokens_per_call": avg,
        "max_prompt_tokens": peak, "over_100k": sum(n > 100_000 for n in calls),
        "context_length": context,
        "headroom_tokens": None if not context else context - peak,
        "cost_per_rollout": per, "spent_usd": round(spent(), 4),
        "project_760": None if per is None else round(per * EXACT_ROLLOUTS, 2),
        "project_1040": None if per is None else round(per * STATED_ROLLOUTS, 2),
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("summary", json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
