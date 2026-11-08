"""Accuracy, paired flips, majority table, and a task-level bootstrap CI.

A task passes a pass when its score is 1. Mean accuracy is the mean of the
per-pass accuracies. The bootstrap resamples tasks, keeping every pass of a
drawn task, and uses a fixed seed.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

RESAMPLES = 10_000
SEED = 0


def _score(row: dict) -> float:
    return float(row["score"])


def _groups(rows: list[dict]) -> dict[tuple, dict[str, float]]:
    """(condition, pass, uid) -> score. Later rows replace earlier ones."""
    out = {}
    for row in rows:
        out[(row["condition"], int(row["pass"]), row["uid"])] = _score(row)
    return out


def _passes(groups: dict, condition: str) -> list[int]:
    return sorted({pass_i for (cond, pass_i, _uid) in groups if cond == condition})


def per_pass_accuracy(rows: list[dict], condition: str) -> list[float]:
    groups = _groups(rows)
    accuracies = []
    for pass_i in _passes(groups, condition):
        scores = [score for (cond, p, _uid), score in groups.items()
                  if cond == condition and p == pass_i]
        accuracies.append(sum(scores) / len(scores) if scores else 0.0)
    return accuracies


def mean_accuracy(rows: list[dict], condition: str) -> float:
    accuracies = per_pass_accuracy(rows, condition)
    return sum(accuracies) / len(accuracies) if accuracies else 0.0


def paired_flips(rows: list[dict]) -> dict:
    """Sum fail→pass and pass→fail over pass indices, pairing empty i with skill i."""
    groups = _groups(rows)
    passes = sorted(set(_passes(groups, "empty")) & set(_passes(groups, "skill")))
    fail_to_pass = pass_to_fail = 0
    per_pass = []
    for pass_i in passes:
        uids = {uid for (cond, p, uid) in groups if p == pass_i and cond == "empty"}
        uids &= {uid for (cond, p, uid) in groups if p == pass_i and cond == "skill"}
        fp = pf = 0
        for uid in uids:
            empty, skill = groups[("empty", pass_i, uid)], groups[("skill", pass_i, uid)]
            if empty < 1 and skill >= 1:
                fp += 1
            elif empty >= 1 and skill < 1:
                pf += 1
        fail_to_pass += fp
        pass_to_fail += pf
        per_pass.append({"pass": pass_i, "fail_to_pass": fp, "pass_to_fail": pf, "n": len(uids)})
    return {"fail_to_pass": fail_to_pass, "pass_to_fail": pass_to_fail, "per_pass": per_pass}


def majority_table(rows: list[dict]) -> dict:
    """2×2 of tasks that pass on a majority of the shared passes.

    A task needs a score in every pass that both conditions ran. With 3 passes
    that is at least 2 successes; with 2 passes both must succeed.
    """
    groups = _groups(rows)
    passes = sorted(set(_passes(groups, "empty")) & set(_passes(groups, "skill")))
    need = len(passes)
    by_task: dict[str, dict[str, list[float]]] = defaultdict(lambda: {"empty": [], "skill": []})
    for (cond, pass_i, uid), score in groups.items():
        if cond in ("empty", "skill") and pass_i in passes:
            by_task[uid][cond].append(score)
    counts = {"both_pass": 0, "empty_only": 0, "skill_only": 0, "both_fail": 0, "n": 0}
    for scores in by_task.values():
        if need == 0 or len(scores["empty"]) < need or len(scores["skill"]) < need:
            continue
        empty = sum(score >= 1 for score in scores["empty"]) > need / 2
        skill = sum(score >= 1 for score in scores["skill"]) > need / 2
        counts["n"] += 1
        if empty and skill:
            counts["both_pass"] += 1
        elif empty:
            counts["empty_only"] += 1
        elif skill:
            counts["skill_only"] += 1
        else:
            counts["both_fail"] += 1
    return counts


def _percentile(sorted_vals: list[float], p: float) -> float:
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def _task_means(rows: list[dict]) -> list[tuple[float, float]]:
    """One (empty mean, skill mean) per task that has the same passes in both."""
    groups = _groups(rows)
    passes = sorted(set(_passes(groups, "empty")) & set(_passes(groups, "skill")))
    uids = {uid for (cond, p, uid) in groups if cond == "empty" and p in passes}
    paired = []
    for uid in sorted(uids):
        if any(("skill", p, uid) not in groups or ("empty", p, uid) not in groups for p in passes):
            continue
        empty = [groups[("empty", p, uid)] for p in passes]
        skill = [groups[("skill", p, uid)] for p in passes]
        paired.append((sum(empty) / len(empty), sum(skill) / len(skill)))
    return paired


def bootstrap_diff(rows: list[dict], *, resamples: int = RESAMPLES, seed: int = SEED) -> dict:
    """95% CI for mean(skill − empty), resampling tasks with replacement."""
    paired = _task_means(rows)
    if not paired:
        return {"estimate": None, "ci95": [None, None], "n_tasks": 0,
                "resamples": resamples, "seed": seed}
    estimate = sum(skill - empty for empty, skill in paired) / len(paired)
    rng = random.Random(seed)
    n = len(paired)
    samples = []
    for _ in range(resamples):
        draw = [paired[rng.randrange(n)] for _ in range(n)]
        samples.append(sum(skill - empty for empty, skill in draw) / n)
    samples.sort()
    return {"estimate": estimate, "ci95": [_percentile(samples, 0.025), _percentile(samples, 0.975)],
            "n_tasks": n, "resamples": resamples, "seed": seed}


def verdict(diff: dict) -> str:
    estimate, (lo, hi) = diff.get("estimate"), diff.get("ci95") or [None, None]
    if estimate is None or lo is None:
        return "no detectable effect"
    if lo > 0 and estimate > 0:
        return "skill helps"
    if hi < 0 and estimate < 0:
        return "skill hurts"
    return "no detectable effect"


def formula_split(rows: list[dict]) -> dict:
    """Empty-skill accuracy split by whether the instruction mentions 'formula'."""
    buckets: dict[str, dict[str, list[float]]] = {
        "formula": defaultdict(list), "other": defaultdict(list)}
    for row in rows:
        if row.get("condition") != "empty":
            continue
        key = "formula" if "formula" in str(row.get("instruction") or "").lower() else "other"
        buckets[key][row["uid"]].append(_score(row))
    out = {}
    for key, tasks in buckets.items():
        means = [sum(scores) / len(scores) for scores in tasks.values() if scores]
        out[key] = {"n_tasks": len(means),
                    "accuracy": (sum(means) / len(means) if means else None)}
    return out


def usage_summary(rows: list[dict]) -> dict:
    n = len(rows)
    if not n:
        return {"rollouts": 0, "avg_turns": None, "avg_prompt_tokens": None,
                "avg_completion_tokens": None, "avg_cost": None, "total_cost": 0.0}
    turns = sum(int(row.get("turns") or 0) for row in rows)
    prompt = sum(int(row.get("prompt_tokens") or 0) for row in rows)
    completion = sum(int(row.get("completion_tokens") or 0) for row in rows)
    cost = sum(float(row.get("cost_usd") or 0) for row in rows)
    return {"rollouts": n, "avg_turns": turns / n, "avg_prompt_tokens": prompt / n,
            "avg_completion_tokens": completion / n, "avg_cost": cost / n, "total_cost": cost}


def summarize(rows: list[dict]) -> dict:
    diff = bootstrap_diff(rows)
    return {
        "empty": {"mean": mean_accuracy(rows, "empty"),
                  "per_pass": per_pass_accuracy(rows, "empty")},
        "skill": {"mean": mean_accuracy(rows, "skill"),
                  "per_pass": per_pass_accuracy(rows, "skill")},
        "flips": paired_flips(rows),
        "majority": majority_table(rows),
        "difference": diff,
        "verdict": verdict(diff),
        "formula": formula_split(rows),
        "usage": usage_summary(rows),
        "malformed_rollouts": sum(1 for row in rows if row.get("malformed")),
        "missing_output": sum(1 for row in rows if not row.get("has_output_workbook")),
    }


def summarize_dir(root: Path) -> dict:
    root = Path(root)
    rows = [json.loads(line) for line in (root / "rollouts.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    summary = summarize(rows)
    path = root / "summary.json"
    if path.is_file():
        previous = json.loads(path.read_text(encoding="utf-8"))
        previous.update(summary)
        summary = previous
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary
