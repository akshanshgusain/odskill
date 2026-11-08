"""Positive control: spreadsheet-SKILL.md injected in full, versus an empty skill, on the val split.

No evolution and no test split. Three passes per condition.
A 3-task empty-skill smoke must drive bash and write output.xlsx before the matrix.

    python -m odskill.posctrl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from wikiskill.benchmarks.spreadsheet import load_cases
from wikiskill.officeqa.rollout import SKILL_SECTION_HEADER

from .agent import executor_tools
from .llm import BudgetExceeded, load_env, spent
from .noise import mix
from .spreadsheet import build, rollout_case
from .stats import summarize

PAPER = Path(__file__).resolve().parents[2]
DATA = PAPER / "data/spreadsheet/spreadsheetbench_verified_400"
SPLITS = PAPER / "wikiskill/src/wikiskill/resources/spreadsheet/id_split"
SOL = PAPER / "wikiskill/src/wikiskill/resources/research/final-20260907/spreadsheet-SKILL.md"
SKILL_SHA256 = "7876c7ecb4b2aad0e55d7623335bd3781512247a1723815c2deec0036e1cc0bf"
OUT = Path.home() / "odskill-runs/posctrl"
OPEN_PREFERENCE = (
    "qwen/qwen3.5-9b",
    "qwen/qwen3.6-27b",
    "google/gemma-4-31b-it",
)
DEEPSEEK = "deepseek/deepseek-v4.1-flash-1017"
HAIKU = "anthropic/claude-haiku-5.5"
EFFORT = "low"
WORKERS = 4
SMOKE_N = 3
PASSES = 3
_lock = threading.Lock()


def val_cases(n: int | None = None) -> list:
    cases = {c.uid: c for c in load_cases(DATA)}
    ids = json.loads((SPLITS / "val.json").read_text(encoding="utf-8"))
    ids = [item["uid"] if isinstance(item, dict) else item for item in ids]
    picked = [cases[uid] for uid in (ids if n is None else ids[:n])]
    if len({c.uid for c in picked}) != len(picked):
        raise ValueError("duplicate val ids")
    return picked


def skill_text() -> str:
    text = SOL.read_text(encoding="utf-8")
    digest = hashlib.sha256(text.encode()).hexdigest()
    if digest != SKILL_SHA256:
        raise SystemExit(f"skill sha256 {digest} != {SKILL_SHA256}")
    return text


def assert_injection(text: str) -> None:
    """The frozen skill is in the prompt under the upstream header. No load_skill tool."""
    case = val_cases(1)[0]
    skills = mix(text, 0, 0)
    prefix, _body, offered = build(case, skills, Path("/tmp"), "all")
    marker = "Never deliver the pre-recalculation workbook"
    if SKILL_SECTION_HEADER not in prefix or marker not in prefix:
        raise SystemExit("spreadsheet-SKILL.md was not injected under the skill header")
    if "General guidance for this task type." in prefix:
        raise SystemExit("spreadsheet-SKILL.md was rewritten with a synthetic description")
    names = [tool["function"]["name"] for tool in executor_tools(bool(offered), offered)]
    if names != ["bash"]:
        raise SystemExit(f"positive control tools are {names}")
    empty_prefix, _body, empty_offered = build(case, [], Path("/tmp"), "all")
    if SKILL_SECTION_HEADER in empty_prefix or empty_offered:
        raise SystemExit("empty skill still exposes a skill")


def _catalog() -> list[dict]:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/models", headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode()).get("data", [])


def pick_open_model(catalog: list[dict]) -> tuple[str, str]:
    by_id = {item.get("id"): item for item in catalog}
    for model in OPEN_PREFERENCE:
        params = (by_id.get(model) or {}).get("supported_parameters") or []
        if model in by_id and "tools" in params:
            return model, f"{model} is listed and supports tools"
    raise SystemExit("none of Qwen-3.5-9B, Qwen-3.6-27B, or Gemma-4-31B list tool calling")


def _done(path: Path) -> set[tuple]:
    if not path.is_file():
        return set()
    found = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        # An exec_raised row is retried on resume (a 429 restart, for example).
        if row.get("fail_reason") == "exec_raised":
            continue
        if row.get("score") in (0, 1, 0.0, 1.0):
            found.add((row["condition"], int(row["pass"]), row["uid"]))
    return found


def _tools(workspace: str) -> dict:
    path = Path(workspace) / "runtime" / "tool-events.jsonl"
    events = []
    if path.is_file():
        events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    n_bash = 0
    malformed = False
    for event in events:
        command = str((event.get("arguments") or {}).get("command") or "").strip()
        if event.get("tool") == "bash" and command:
            n_bash += 1
        else:
            malformed = True
    return {"n_tool_calls": len(events), "n_bash": n_bash, "malformed": malformed}


def _row(record: dict, *, model: str, condition: str, pass_i: int) -> dict:
    usage = record.get("usage") or {}
    tools = _tools(record.get("workspace") or "")
    return {
        "uid": record["uid"], "model": model, "condition": condition, "pass": pass_i,
        "score": record.get("score"), "fail_reason": record.get("fail_reason") or "",
        "turns": record.get("turns") or 0,
        "prompt_tokens": usage.get("prompt_tokens") or 0,
        "completion_tokens": usage.get("completion_tokens") or 0,
        "cost_usd": float(usage.get("cost_usd") or 0),
        "has_output_workbook": bool(record.get("has_output_workbook")),
        "instruction": (record.get("question") or {}).get("question") or "",
        "error": record.get("error") or "",
        **tools,
    }


def _reliable(row: dict) -> bool:
    return row["n_bash"] >= 1 and row["has_output_workbook"] and not row["malformed"]


def _append(path: Path, row: dict) -> None:
    with _lock:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")


def _run_many(cases, *, model: str, condition: str, pass_i: int, text: str,
              dest: Path, work: Path, workers: int = WORKERS) -> list[dict]:
    done = _done(dest)
    pending = [case for case in cases if (condition, pass_i, case.uid) not in done]
    print(f"{model} {condition} pass={pass_i} pending {len(pending)}/{len(cases)} "
          f"spent=${spent():.4f}", flush=True)
    rows = []

    def one(case):
        try:
            record = rollout_case(
                case, workdir=work / f"p{pass_i}-{condition}", model=model, skill_text=text,
                mode="all", split="val", reasoning_effort=EFFORT, timeout_seconds=180,
                noise_k=0, seed=0)
            row = _row(record, model=model, condition=condition, pass_i=pass_i)
        except BudgetExceeded:
            raise
        except Exception as exc:
            row = {"uid": case.uid, "model": model, "condition": condition, "pass": pass_i,
                   "score": 0, "fail_reason": "exec_raised", "turns": 0, "prompt_tokens": 0,
                   "completion_tokens": 0, "cost_usd": 0.0, "has_output_workbook": False,
                   "instruction": case.instruction, "error": f"{type(exc).__name__}: {exc}",
                   "n_tool_calls": 0, "n_bash": 0, "malformed": True}
            print(f"error {case.uid}: {row['error']}", flush=True)
        _append(dest, row)
        return row

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(one, case): case.uid for case in pending}
        for future in as_completed(futures):
            try:
                rows.append(future.result())
            except BudgetExceeded:
                print(f"budget stop spent=${spent():.4f}", flush=True)
                raise
    return rows


def smoke(model: str, root: Path, text_unused: str = "", workers: int = WORKERS) -> bool:
    dest = root / "smoke.jsonl"
    cases = val_cases(SMOKE_N)
    work = root / "smoke"
    try:
        rows = _run_many(cases, model=model, condition="empty", pass_i=-1, text="",
                         dest=dest, work=work, workers=workers)
    except BudgetExceeded:
        raise
    fresh = [row for row in rows if row["pass"] == -1]
    # A resumed smoke file may already hold the three rows.
    if len(fresh) < SMOKE_N and dest.is_file():
        fresh = [json.loads(line) for line in dest.read_text(encoding="utf-8").splitlines() if line.strip()]
    ok = sum(1 for row in fresh if _reliable(row))
    print(f"smoke {model}: {ok}/{len(fresh)} drove bash and wrote output.xlsx", flush=True)
    if fresh and ok == 0:
        reasons = []
        if all(row["n_bash"] == 0 for row in fresh):
            reasons.append("no bash tool calls")
        if all(row["malformed"] for row in fresh):
            reasons.append("malformed tool calls")
        if all(not row["has_output_workbook"] for row in fresh):
            reasons.append("no output.xlsx")
        errors = sorted({row["error"] for row in fresh if row.get("error")})
        print("skip:", "; ".join(reasons) or "unreliable tool use", flush=True)
        if errors:
            print("smoke error:", errors[0][:300], flush=True)
        return False
    return True


def run_model(model: str, root: Path, text: str, workers: int = WORKERS) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    if not smoke(model, root, workers=workers):
        summary = {"model": model, "skipped": True, "effort": EFFORT}
        (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        return summary
    dest = root / "rollouts.jsonl"
    cases = val_cases()
    stopped = False
    try:
        for pass_i in range(PASSES):
            for condition, body in (("empty", ""), ("skill", text)):
                _run_many(cases, model=model, condition=condition, pass_i=pass_i, text=body,
                          dest=dest, work=root / "attempts", workers=workers)
    except BudgetExceeded:
        stopped = True
    rows = [json.loads(line) for line in dest.read_text(encoding="utf-8").splitlines() if line.strip()] if dest.is_file() else []
    summary = summarize(rows)
    summary.update({
        "model": model, "effort": EFFORT, "skipped": False, "stopped": stopped,
        "skill_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "mode": "all", "split": "val", "n_tasks": len(cases), "passes": PASSES,
    })
    (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"{model} verdict={summary['verdict']} empty={summary['empty']['mean']:.4f} "
          f"skill={summary['skill']['mean']:.4f} stopped={stopped}", flush=True)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="", help="Executor id. Default: the open model that lists tools.")
    parser.add_argument("--pair", action="store_true",
                        help="Haiku and DeepSeek together, one shared budget, val only.")
    parser.add_argument("--run-dir", type=Path, default=None)
    parser.add_argument("--budget", type=float, required=True)
    parser.add_argument("--workers", type=int, default=WORKERS)
    parser.add_argument("--smoke-only", action="store_true")
    args = parser.parse_args()
    if args.budget <= 0 or args.workers < 1:
        raise SystemExit("budget and workers must be positive")
    load_env(PAPER / ".env")
    os.environ["ODSKILL_BUDGET_USD"] = str(args.budget)
    text = skill_text()
    assert_injection(text)
    catalog = _catalog()
    have = {item.get("id") for item in catalog}
    if args.pair:
        missing = [model for model in (HAIKU, DEEPSEEK) if model not in have]
        if missing:
            raise SystemExit("model id not on OpenRouter: " + ", ".join(missing))
        base = (args.run_dir or (OUT / "final-20260907")).expanduser()

        def go(model: str) -> None:
            try:
                run_model(model, base / model, text, workers=args.workers)
            except BudgetExceeded:
                print(f"budget ${args.budget} reached during {model}; stopping", flush=True)

        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(go, (HAIKU, DEEPSEEK)))
        print(f"spent=${spent():.4f}", flush=True)
        return
    if args.model:
        model = args.model
        if model not in have:
            raise SystemExit("model id not on OpenRouter: " + model)
    else:
        model, why = pick_open_model(catalog)
        print("open model:", why, flush=True)
    root = (args.run_dir or (OUT / model)).expanduser()
    if args.smoke_only:
        root.mkdir(parents=True, exist_ok=True)
        ok = smoke(model, root, workers=args.workers)
        print(f"spent=${spent():.4f}", flush=True)
        raise SystemExit(0 if ok else 2)
    try:
        run_model(model, root, text, workers=args.workers)
    except BudgetExceeded:
        print(f"budget ${args.budget} reached during {model}; stopping", flush=True)
    print(f"spent=${spent():.4f}", flush=True)


if __name__ == "__main__":
    main()
