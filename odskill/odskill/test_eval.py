"""Score a finished run's accepted skills on the official TEST split.

Refuses to start unless --i-understand-this-is-the-test-split is passed.
This module is not part of evolution and is not run by the seed-0 campaigns.
"""

from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from wikiskill import engine
from wikiskill.benchmarks.spreadsheet import load_cases

from .llm import BudgetExceeded, load_env
from .spreadsheet import rollout_case

PAPER = Path(__file__).resolve().parents[2]
DATA = PAPER / "data/spreadsheet/spreadsheetbench_verified_400"
TEST_SPLIT = PAPER / "wikiskill/src/wikiskill/resources/spreadsheet/id_split/test.json"
FLAG = "--i-understand-this-is-the-test-split"


def test_cases() -> list:
    cases = {case.uid: case for case in load_cases(DATA)}
    ids = [item["uid"] if isinstance(item, dict) else item
           for item in json.loads(TEST_SPLIT.read_text(encoding="utf-8"))]
    missing = [uid for uid in ids if uid not in cases]
    if missing:
        raise SystemExit(f"{len(missing)} TEST ids are not in the dataset")
    if len(set(ids)) != len(ids):
        raise SystemExit("TEST split has duplicate ids")
    return [cases[uid] for uid in ids]


def _row(record: dict) -> dict:
    usage = record.get("usage") or {}
    return {
        "uid": record.get("uid"),
        "score": record.get("score"),
        "fail_reason": record.get("fail_reason") or "",
        "loads": record.get("loaded_skills") or [],
        "turns": record.get("turns"),
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "cost_usd": usage.get("cost_usd", 0),
    }


def evaluate(root: Path, *, no_skills: bool, budget: float, workers: int = 2,
             rollout=None) -> Path:
    """Write test_eval/outcomes.jsonl under the run directory. Returns that path."""
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    skill = ""
    mode, noise_k, index = "all", 0, "v2"
    if not no_skills:
        current = engine.state(root)
        skill = (root / current["skill"]).read_text(encoding="utf-8")
        mode = manifest["mode"]
        noise_k = int(manifest["noise_k"])
        index = manifest.get("index") or "v2"
    rollout = rollout or rollout_case
    os.environ["ODSKILL_BUDGET_USD"] = str(budget)
    dest = root / "test_eval"
    if no_skills:
        dest = root / "test_eval_baseline"
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / "outcomes.jsonl"
    cases = test_cases()

    def one(case):
        record = rollout(
            case, workdir=dest / "work", model=manifest["model"], skill_text=skill,
            mode=mode, split="test", noise_k=noise_k, seed=int(manifest.get("seed", 0)),
            reasoning_effort=manifest.get("reasoning_effort") or "low", index=index if mode == "od" else "v2")
        return _row(record)

    rows = []
    stopped = False
    with ThreadPoolExecutor(max(1, workers)) as pool:
        futures = [pool.submit(one, case) for case in cases]
        for future in as_completed(futures):
            try:
                rows.append(future.result())
            except BudgetExceeded:
                stopped = True
    out.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    scored = [row for row in rows if row.get("score") is not None]
    summary = {
        "n": len(rows), "expected": len(cases), "stopped": stopped, "no_skills": no_skills,
        "arm": manifest.get("arm"), "mode": mode, "index": index if not no_skills else "",
        "noise_k": noise_k, "accuracy": None if not scored else round(
            sum(row["score"] or 0 for row in scored) / len(scored), 4),
        "cost_usd": round(sum(row.get("cost_usd") or 0 for row in rows), 4),
    }
    (dest / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary), flush=True)
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Evaluate a finished run on the official TEST split.")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--no-skills", action="store_true")
    parser.add_argument("--budget", type=float, required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument(FLAG, action="store_true")
    args = parser.parse_args(argv)
    if not getattr(args, "i_understand_this_is_the_test_split"):
        raise SystemExit(
            "Refusing to evaluate the official TEST split without --i-understand-this-is-the-test-split")
    if args.budget <= 0:
        raise SystemExit("budget must be positive")
    load_env(PAPER / ".env")
    evaluate(args.run_dir.expanduser().resolve(), no_skills=args.no_skills,
             budget=args.budget, workers=args.workers)


if __name__ == "__main__":
    main()
