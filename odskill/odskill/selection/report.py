"""Markdown summaries for Experiment 1 and the test evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean, stdev

from odskill.selection.metrics import aggregate, bootstrap_ci, bootstrap_diff, by_task_type

ERROR_FLAG = 0.05


def _fmt(value) -> str:
    if value is None:
        return ""
    return f"{float(value):.3f}"


def _ci(diff: dict) -> str:
    lo, hi = diff.get("ci95") or [None, None]
    if lo is None:
        return ""
    return f"[{lo:.3f}, {hi:.3f}]"


def cell_record(cell: dict, rows: list[dict]) -> dict:
    """Metrics for one Experiment 1 cell. Errored rows stay in the error rate and out of the rates."""
    summary = aggregate(rows)
    errors = sum(1 for row in rows if row.get("error"))
    cost = sum(float(row.get("cost_usd") or 0) for row in rows)
    rate = errors / len(rows) if rows else 0.0
    types = {name: item["recall"] for name, item in by_task_type(rows).items()}
    return {
        **cell,
        "recall": summary["recall"],
        "precision": summary["precision"],
        "f1": summary["f1"],
        "f1_ci95": bootstrap_ci(rows, "f1")["ci95"],
        "wrong_type_load_rate": summary["wrong_type_load_rate"],
        "noise_load_rate": summary["noise_load_rate"],
        "loaded_any": summary["loaded_any"],
        "episodes": len(rows),
        "errors": errors,
        "error_rate": rate,
        "error_flag": rate > ERROR_FLAG,
        "cost_usd": cost,
        "cost_per_episode": cost / len(rows) if rows else 0.0,
        "recall_by_task_type": types,
    }


def write_exp1(records: list[dict], dest: Path) -> str:
    """results/exp1/summary.md and cells.jsonl. `records` come from cell_record."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Experiment 1",
        "",
        "F1 intervals resample games, 10,000 draws, seed 0. A cell is flagged when its error rate is above 5%.",
        "",
        "| cell | recall | precision | F1 | F1 95% CI | wrong-type | noise-load | loaded-any | errors | error rate | cost | $/episode | flag |",
        "|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for record in records:
        ci = record.get("f1_ci95") or [None, None]
        lines.append(
            f"| {record['cell']} | {_fmt(record['recall'])} | {_fmt(record['precision'])} | "
            f"{_fmt(record['f1'])} | [{_fmt(ci[0])}, {_fmt(ci[1])}] | "
            f"{_fmt(record['wrong_type_load_rate'])} | {_fmt(record['noise_load_rate'])} | "
            f"{_fmt(record['loaded_any'])} | {record['errors']} | {_fmt(record['error_rate'])} | "
            f"{record['cost_usd']:.4f} | {record['cost_per_episode']:.6f} | "
            f"{'YES' if record['error_flag'] else ''} |"
        )
    lines += ["", "## Recall by task type", ""]
    for record in records:
        lines.append(f"### {record['cell']}")
        for name, recall in record["recall_by_task_type"].items():
            lines.append(f"- {name}: {_fmt(recall)}")
        lines.append("")
    text = "\n".join(lines)
    dest.write_text(text, encoding="utf-8")
    jsonl = dest.parent / "cells.jsonl"
    jsonl.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
    return text


def _f1(rows: list[dict]) -> float:
    return aggregate(rows)["f1"]


def _per_seed(rows: list[dict]) -> tuple[dict[int, float], float, float]:
    seeds = sorted({int(row.get("seed", 0)) for row in rows})
    scores = {seed: _f1([row for row in rows if int(row.get("seed", 0)) == seed]) for seed in seeds}
    values = list(scores.values())
    return scores, mean(values), stdev(values) if len(values) > 1 else 0.0


def _compare(left: list[dict], right: list[dict], label: str) -> list[str]:
    lines = [f"### {label}", ""]
    for metric in ("recall", "precision", "f1"):
        diff = bootstrap_diff(left, right, metric)
        lines.append(f"- {metric}: {_fmt(diff['estimate'])} {_ci(diff)}")
    lines.append("")
    return lines


def write_test(groups: dict[str, dict[str, list[dict]]], dest: Path) -> str:
    """results/test/summary.md. Each group is an executor -> arm name -> pooled rows.

    Comparisons are right − left: wikisel − nowiki, and each of those minus plain and minus directive.
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Test",
        "",
        "Noise shuffle seed 0 for every evaluation. Intervals resample games and keep a game's passes together, 10,000 draws, seed 0.",
        "",
    ]
    for executor, arms in groups.items():
        lines += [f"## {executor}", ""]
        lines.append("| arm | per-seed F1 | mean | sd |")
        lines.append("|---|---|---:|---:|")
        for arm in ("plain", "directive", "nowiki", "wikisel"):
            rows = arms.get(arm) or []
            if not rows:
                continue
            scores, avg, spread = _per_seed(rows)
            detail = ", ".join(f"s{seed}={_fmt(score)}" for seed, score in scores.items())
            lines.append(f"| {arm} | {detail} | {_fmt(avg)} | {_fmt(spread)} |")
        lines.append("")
        plain, directive = arms.get("plain") or [], arms.get("directive") or []
        nowiki, wikisel = arms.get("nowiki") or [], arms.get("wikisel") or []
        if nowiki and wikisel:
            lines += _compare(nowiki, wikisel, "wikisel − nowiki")
        if plain and nowiki:
            lines += _compare(plain, nowiki, "nowiki − plain")
        if plain and wikisel:
            lines += _compare(plain, wikisel, "wikisel − plain")
        if directive and nowiki:
            lines += _compare(directive, nowiki, "nowiki − directive")
        if directive and wikisel:
            lines += _compare(directive, wikisel, "wikisel − directive")
    text = "\n".join(lines)
    dest.write_text(text, encoding="utf-8")
    return text
