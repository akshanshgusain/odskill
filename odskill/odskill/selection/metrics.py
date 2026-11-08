"""Load metrics. A game counts as recalled when its one relevant skill was loaded."""

from __future__ import annotations

import random
from collections import defaultdict

from odskill.stats import RESAMPLES, SEED

from .library import NAMES


def score_loads(loads: list[dict], relevant: str) -> dict:
    """loads are {name, origin} in call order."""
    names = [item["name"] for item in loads]
    wrong = sum(1 for name in names if name in NAMES and name != relevant)
    noise = sum(1 for item in loads if item.get("origin") == "noise")
    relevant_loads = sum(1 for name in names if name == relevant)
    return {
        "loads": names,
        "load_count": len(names),
        "relevant_load_count": relevant_loads,
        "relevant_loaded": relevant_loads > 0,
        "wrong_type_loads": wrong,
        "noise_loads": noise,
        "loaded_any": bool(names),
    }


def _rates(rows: list[dict]) -> dict:
    if not rows:
        return {"n": 0, "recall": 0.0, "precision": 0.0, "f1": 0.0,
                "noise_load_rate": 0.0, "wrong_type_load_rate": 0.0, "loaded_any": 0.0}
    recall = sum(bool(row["relevant_loaded"]) for row in rows) / len(rows)
    loads = sum(int(row["load_count"]) for row in rows)
    relevant = sum(int(row["relevant_load_count"]) for row in rows)
    noise = sum(int(row["noise_loads"]) for row in rows)
    wrong = sum(int(row["wrong_type_loads"]) for row in rows)
    precision = relevant / loads if loads else 0.0
    f1 = 0.0 if recall + precision == 0 else 2 * recall * precision / (recall + precision)
    return {
        "n": len(rows),
        "recall": recall,
        "precision": precision,
        "f1": f1,
        "noise_load_rate": noise / loads if loads else 0.0,
        "wrong_type_load_rate": wrong / loads if loads else 0.0,
        "loaded_any": sum(bool(row["loaded_any"]) for row in rows) / len(rows),
    }


def _by_pass(rows: list[dict]) -> list[list[dict]]:
    passes = sorted({int(row.get("pass", 0)) for row in rows})
    if not passes:
        return []
    return [[row for row in rows if int(row.get("pass", 0)) == pass_i] for pass_i in passes]


def aggregate(rows: list[dict]) -> dict:
    """Mean of the per-pass rates. One pass is just that pass. Unscored errors are left out."""
    rows = [row for row in rows if not row.get("error")]
    groups = _by_pass(rows)
    if not groups:
        return _rates([])
    parts = [_rates(group) for group in groups]
    keys = ("recall", "precision", "f1", "noise_load_rate", "wrong_type_load_rate", "loaded_any")
    out = {key: sum(part[key] for part in parts) / len(parts) for key in keys}
    out["n"] = sum(part["n"] for part in parts)
    out["per_pass"] = parts
    return out


def by_task_type(rows: list[dict]) -> dict[str, dict]:
    types = sorted({row.get("task_type") or row.get("relevant") for row in rows})
    return {task: aggregate([row for row in rows if (row.get("task_type") or row.get("relevant")) == task])
            for task in types}


def per_skill(rows: list[dict]) -> dict[str, dict]:
    """Val or train recall and precision of each type skill. Recall is on its own games."""
    rows = [row for row in rows if not row.get("error")]
    out = {}
    for name in NAMES:
        own = [row for row in rows if row.get("relevant") == name]
        loads = sum(int(row["load_count"]) for row in rows)
        # Precision of this skill: loads of this name that were on its own games / loads of this name.
        hits = 0
        called = 0
        for row in rows:
            called += sum(1 for item in row.get("loads") or [] if item == name)
            if row.get("relevant") == name:
                hits += sum(1 for item in row.get("loads") or [] if item == name)
        recall = (sum(bool(row["relevant_loaded"]) for row in own) / len(own)) if own else 0.0
        out[name] = {
            "games": len(own),
            "recall": recall,
            "precision": hits / called if called else 0.0,
            "loads": called,
            "library_loads": loads,
        }
    return out


def _percentile(sorted_vals: list[float], p: float) -> float:
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def _tasks(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row.get("error"):
            continue
        grouped[row["uid"]].append(row)
    return grouped


def bootstrap_diff(left: list[dict], right: list[dict], metric: str, *,
                   resamples: int = RESAMPLES, seed: int = SEED) -> dict:
    """95% CI for mean(right − left), resampling games. All passes of a drawn game stay together."""
    a = _tasks(left)
    b = _tasks(right)
    uids = sorted(set(a) & set(b))
    if not uids or metric not in ("recall", "precision", "f1"):
        return {"estimate": None, "ci95": [None, None], "n_tasks": 0,
                "resamples": resamples, "seed": seed, "metric": metric}

    def value(drawn: list[str], source: dict[str, list[dict]]) -> float:
        rows = [row for uid in drawn for row in source[uid]]
        return aggregate(rows)[metric]

    estimate = value(uids, b) - value(uids, a)
    rng = random.Random(seed)
    n = len(uids)
    samples = []
    for _ in range(resamples):
        drawn = [uids[rng.randrange(n)] for _ in range(n)]
        samples.append(value(drawn, b) - value(drawn, a))
    samples.sort()
    return {"estimate": estimate, "ci95": [_percentile(samples, 0.025), _percentile(samples, 0.975)],
            "n_tasks": n, "resamples": resamples, "seed": seed, "metric": metric}


def bootstrap_ci(rows: list[dict], metric: str = "f1", *,
                 resamples: int = RESAMPLES, seed: int = SEED) -> dict:
    """95% CI for one metric, resampling games. All passes of a drawn game stay together."""
    grouped = _tasks(rows)
    uids = sorted(grouped)
    if not uids or metric not in ("recall", "precision", "f1"):
        return {"estimate": None, "ci95": [None, None], "n_tasks": 0,
                "resamples": resamples, "seed": seed, "metric": metric}

    def value(drawn: list[str]) -> float:
        return aggregate([row for uid in drawn for row in grouped[uid]])[metric]

    estimate = value(uids)
    rng = random.Random(seed)
    n = len(uids)
    samples = [value([uids[rng.randrange(n)] for _ in range(n)]) for _ in range(resamples)]
    samples.sort()
    return {"estimate": estimate, "ci95": [_percentile(samples, 0.025), _percentile(samples, 0.975)],
            "n_tasks": n, "resamples": resamples, "seed": seed, "metric": metric}
