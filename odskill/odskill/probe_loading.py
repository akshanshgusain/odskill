"""Load-rate probe for index v2. No evolution.

120 rollouts: 2 models x 3 library sizes x 2 description styles x the first 10 TRAIN tasks.
Haiku cells run before Sonnet. A budget trip stops the matrix and keeps what finished.
"""

from __future__ import annotations

import json
import os
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from wikiskill.benchmarks.spreadsheet import load_cases

from . import llm
from .agent import executor_tools
from .llm import BudgetExceeded, load_env, spent
from .skills import index_v2_text, parse
from .spreadsheet import rollout_case

PAPER = Path(__file__).resolve().parents[2]
DATA = PAPER / "data/spreadsheet/spreadsheetbench_verified_400"
SPLITS = PAPER / "wikiskill/src/wikiskill/resources/spreadsheet/id_split"
MODELS = ("anthropic/claude-haiku-5.5", "anthropic/claude-sonnet-5.5")
SIZES = (0, 20, 100)
STYLES = ("plain", "directive")
PROBE_NAME = "spreadsheet_task_workflow"
EFFORT = "low"
WORKERS = 4
BUDGET = "4"
PLAIN = ("Workflow for spreadsheet manipulation tasks: inspect the workbook, "
         "locate the answer region, write concrete values, verify before saving.")
DIRECTIVE = ("Use this skill for any task that reads or writes an .xlsx workbook. "
             "Load it before inspecting the file: it contains the required workflow "
             "for filling answer_position ranges and verifying the output.")
BODY = """
## When to Apply
A task that reads or edits a spreadsheet workbook.

## When NOT to Apply
The task does not read or write a workbook.

## Instructions
1. Inspect the workbook: sheets, headers, and the cells named in the instruction.
2. Locate the answer region from the instruction.
3. Compute concrete values in code from the source cells.
4. Write exactly that answer range into the output workbook.
5. Verify the written cells before saving.
"""
_lock = threading.Lock()


def probe_skill(style: str) -> str:
    description = PLAIN if style == "plain" else DIRECTIVE
    if style not in STYLES:
        raise ValueError("style must be plain or directive")
    return f"---\nname: {PROBE_NAME}\ndescription: {description}\n---\n{BODY}"


def assert_index_v2() -> None:
    skills = parse(probe_skill("plain"))
    tools = executor_tools(True, skills, "v2")
    names = [tool["function"]["name"] for tool in tools]
    print("executor_tools:", " ".join(names), flush=True)
    if names != ["bash", "load_skill"]:
        raise SystemExit(f"od request tools are {names}")
    description = tools[1]["function"]["description"]
    if "you may load none" in description or "<available_skills>" not in description:
        raise SystemExit("v2 tool description is not the available_skills index")
    if f"<name>{PROBE_NAME}</name>" not in description:
        raise SystemExit("probe skill is missing from the tool description")
    if "<!--" in description or "platform.claude.com" in description:
        raise SystemExit("the source comment was sent in the tool description")
    if "{available_skills}" in description:
        raise SystemExit("the skill placeholder was not filled")
    if "Source:" not in index_v2_text():
        raise SystemExit("index_v2.md is missing its source comment")


def _train_cases(n: int = 10):
    cases = {c.uid: c for c in load_cases(DATA)}
    ids = [x["uid"] if isinstance(x, dict) else x
           for x in json.loads((SPLITS / "train.json").read_text(encoding="utf-8"))]
    return [cases[uid] for uid in ids[:n]]


def _require_models(ids: tuple[str, ...]) -> None:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/models", headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=60) as response:
        payload = json.loads(response.read().decode())
    have = {item.get("id") for item in payload.get("data", [])}
    missing = [model for model in ids if model not in have]
    if missing:
        raise SystemExit("model id not on OpenRouter: " + ", ".join(missing))


def _reasoning(workspace: str) -> str:
    path = Path(workspace) / ".odskill" / "transcript.json"
    if not path.is_file():
        return ""
    try:
        messages = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    for message in messages:
        if message.get("role") != "assistant":
            continue
        text = message.get("reasoning") or message.get("reasoning_content") or ""
        return " ".join(str(text).split())[:500]
    return ""


def _row(record: dict, *, model: str, noise_k: int, style: str) -> dict:
    loads = []
    for item in record.get("loaded_skills") or []:
        loads.append({"name": item.get("name", ""), "origin": item.get("origin", ""),
                      "adjacent": bool(item.get("adjacent")), "turn": item.get("turn")})
    usage = record.get("usage") or {}
    return {
        "model": model, "noise_k": noise_k, "style": style, "uid": record["uid"],
        "probe_loaded": any(item["name"] == PROBE_NAME for item in loads),
        "loads": loads,
        "first_load_turn": loads[0]["turn"] if loads else None,
        "turns": record.get("turns"), "score": record.get("score"),
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "cost_usd": usage.get("cost_usd", 0),
        "first_reasoning": _reasoning(record.get("workspace", "")),
    }


def _append(path: Path, row: dict) -> None:
    with _lock:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _done(path: Path) -> set[tuple]:
    if not path.is_file():
        return set()
    keys = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        keys.add((row["model"], row["style"], row["noise_k"], row["uid"]))
    return keys


def _cell(cases, dest: Path, model: str, noise_k: int, style: str, out: Path, done: set) -> bool:
    """Run one cell. Returns True when the budget guard stopped the cell."""
    pending = [case for case in cases if (model, style, noise_k, case.task_id) not in done]
    if not pending:
        print(f"skip {model} {style} k={noise_k} (already logged)", flush=True)
        return False
    stopped = False
    skill = probe_skill(style)

    def one(case):
        try:
            record = rollout_case(
                case, workdir=dest, model=model, skill_text=skill, mode="od", split="train",
                noise_k=noise_k, seed=0, reasoning_effort=EFFORT, index="v2")
        except BudgetExceeded:
            return None
        row = _row(record, model=model, noise_k=noise_k, style=style)
        _append(out, row)
        mark = "y" if row["probe_loaded"] else "n"
        print(f"{model.split('/')[-1]} {style} k={noise_k} {case.task_id} "
              f"probe={mark} turns={row['turns']} ${row['cost_usd']:.4f}", flush=True)
        return row

    with ThreadPoolExecutor(WORKERS) as pool:
        futures = [pool.submit(one, case) for case in pending]
        for future in as_completed(futures):
            if future.result() is None:
                stopped = True
    return stopped


def _summary(rows: list[dict], stopped: bool) -> dict:
    cells = []
    for model in MODELS:
        for noise_k in SIZES:
            for style in STYLES:
                group = [row for row in rows
                         if row["model"] == model and row["noise_k"] == noise_k and row["style"] == style]
                if not group:
                    continue
                n = len(group)
                noise = [item for row in group for item in row["loads"] if item["origin"] == "noise"]
                cells.append({
                    "model": model, "noise_k": noise_k, "style": style, "n": n,
                    "probe_loaded": sum(row["probe_loaded"] for row in group),
                    "noise_loads": len(noise),
                    "adjacent_noise_loads": sum(item["adjacent"] for item in noise),
                    "mean_turns": round(sum(row["turns"] or 0 for row in group) / n, 2),
                    "accuracy": round(sum(row["score"] or 0 for row in group) / n, 3),
                    "cost_usd": round(sum(row["cost_usd"] or 0 for row in group), 4),
                    "mean_prompt_tokens": round(sum(row["prompt_tokens"] for row in group) / n, 1),
                    "mean_completion_tokens": round(sum(row["completion_tokens"] for row in group) / n, 1),
                })
    return {"index": "v2", "effort": EFFORT, "budget_usd": float(BUDGET),
            "spent_usd": round(spent(), 4), "stopped": stopped, "n": len(rows), "cells": cells}


def _write_summary(path: Path, rows: list[dict], stopped: bool) -> None:
    path.write_text(json.dumps(_summary(rows, stopped), indent=2) + "\n", encoding="utf-8")


def _read_rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    assert_index_v2()
    load_env(PAPER / ".env")
    os.environ["ODSKILL_BUDGET_USD"] = BUDGET
    _require_models(MODELS)
    root = Path.home() / "odskill-runs" / "probe_v2"
    root.mkdir(parents=True, exist_ok=True)
    out = root / "rollouts.jsonl"
    summary_path = root / "summary.json"
    cases = _train_cases(10)
    done = _done(out)
    stopped = False
    for model in MODELS:
        for noise_k in SIZES:
            for style in STYLES:
                if stopped:
                    break
                try:
                    llm.ensure_budget()
                except BudgetExceeded:
                    stopped = True
                    break
                slug = model.split("/")[-1]
                dest = root / "work" / slug / style / f"k{noise_k}"
                print(f"cell {model} {style} k={noise_k}", flush=True)
                if _cell(cases, dest, model, noise_k, style, out, done):
                    stopped = True
                _write_summary(summary_path, _read_rows(out), stopped)
            if stopped:
                break
        if stopped:
            break
    rows = _read_rows(out)
    _write_summary(summary_path, rows, stopped)
    print(f"probe_v2 n={len(rows)} stopped={stopped} cost=${spent():.4f}", flush=True)
    if llm.sent_tool_names is not None and llm.sent_tool_names != ["bash", "load_skill"]:
        raise SystemExit(f"outgoing request tools were {llm.sent_tool_names}")


if __name__ == "__main__":
    main()
