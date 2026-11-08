"""Positive-control injection and the paired stats. No network."""

from __future__ import annotations

import hashlib
from pathlib import Path

from odskill.posctrl import SOL, assert_injection, pick_open_model, skill_text
from odskill.stats import bootstrap_diff, formula_split, majority_table, paired_flips, summarize


def _row(uid, condition, pass_i, score, instruction="Fill the cells."):
    return {"uid": uid, "condition": condition, "pass": pass_i, "score": score,
            "instruction": instruction, "turns": 2, "prompt_tokens": 10,
            "completion_tokens": 5, "cost_usd": 0.01, "has_output_workbook": True,
            "malformed": False}


def test_skill_is_injected_verbatim_and_bash_only():
    text = skill_text()
    assert text == Path(SOL).read_text(encoding="utf-8")
    assert "name: recalculate_and_validate_formula_workbooks" in text
    assert hashlib.sha256(text.encode()).hexdigest() == (
        "7876c7ecb4b2aad0e55d7623335bd3781512247a1723815c2deec0036e1cc0bf")
    assert_injection(text)


def test_open_model_prefers_qwen_9b_when_it_lists_tools():
    catalog = [
        {"id": "google/gemma-4-31b-it", "supported_parameters": ["tools"]},
        {"id": "qwen/qwen3.6-27b", "supported_parameters": ["tools"]},
        {"id": "qwen/qwen3.5-9b", "supported_parameters": ["tools", "tool_choice"]},
    ]
    model, why = pick_open_model(catalog)
    assert model == "qwen/qwen3.5-9b"
    assert "tools" in why


def test_open_model_falls_through_when_9b_has_no_tools():
    catalog = [
        {"id": "qwen/qwen3.5-9b", "supported_parameters": ["temperature"]},
        {"id": "qwen/qwen3.6-27b", "supported_parameters": ["tools"]},
        {"id": "google/gemma-4-31b-it", "supported_parameters": ["tools"]},
    ]
    assert pick_open_model(catalog)[0] == "qwen/qwen3.6-27b"
    catalog[1]["supported_parameters"] = []
    assert pick_open_model(catalog)[0] == "google/gemma-4-31b-it"


def test_paired_stats_and_formula_split():
    rows = []
    # Task A always fails empty and passes with the skill. Task B passes empty
    # and drops the skill on the last pass only.
    for pass_i, skill_b in ((0, 1), (1, 1), (2, 0)):
        rows.append(_row("A", "empty", pass_i, 0, "Write a formula for C2"))
        rows.append(_row("A", "skill", pass_i, 1, "Write a formula for C2"))
        rows.append(_row("B", "empty", pass_i, 1, "Sort column H"))
        rows.append(_row("B", "skill", pass_i, skill_b, "Sort column H"))
    summary = summarize(rows)
    assert summary["empty"]["per_pass"] == [0.5, 0.5, 0.5]
    assert summary["empty"]["mean"] == 0.5
    assert summary["skill"]["per_pass"] == [1.0, 1.0, 0.5]
    assert abs(summary["skill"]["mean"] - (2.5 / 3)) < 1e-9
    flips = paired_flips(rows)
    assert flips["fail_to_pass"] == 3
    assert flips["pass_to_fail"] == 1
    table = majority_table(rows)
    assert table == {"both_pass": 1, "empty_only": 0, "skill_only": 1, "both_fail": 0, "n": 2}
    diff = bootstrap_diff(rows, resamples=200, seed=0)
    assert abs(diff["estimate"] - (summary["skill"]["mean"] - summary["empty"]["mean"])) < 1e-9
    assert diff["ci95"][0] <= diff["estimate"] <= diff["ci95"][1]
    again = bootstrap_diff(rows, resamples=200, seed=0)
    assert again["ci95"] == diff["ci95"]
    formula = formula_split(rows)
    assert formula["formula"] == {"n_tasks": 1, "accuracy": 0.0}
    assert formula["other"] == {"n_tasks": 1, "accuracy": 1.0}
    assert summary["verdict"] in ("skill helps", "no detectable effect", "skill hurts")
