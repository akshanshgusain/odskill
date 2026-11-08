"""Decision rule, grids, and summaries. No network."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from odskill.selection.decide import GAP, HAIKU, decide, examples
from odskill.selection.evolve_desc import main, run_evolution
from odskill.selection.library import NAMES
from odskill.selection.orchestrate import (
    DEEPSEEK, eval_jobs, exp1_cells, exp2_jobs, exp2_run, on_429, slots,
)
from odskill.selection.report import cell_record, write_exp1, write_test


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_decide_examples():
    found = {label: result for label, _cells, result in examples()}
    assert found["one clear winner"].endswith("k20-claude-haiku-5.5")
    assert found["tie on plain F1"].endswith("canonical-k100-claude-haiku-5.5")
    assert "opaque" not in found["tie on plain F1"]
    assert found["no gap of 0.10"] == "None"
    assert found["deepseek and forced are not eligible"] == "None"
    assert decide([]) is None


def test_gap_of_point_one_from_halves_qualifies():
    cell = {
        "cell": "tenth", "executor": HAIKU, "agent_prompt": "neutral", "names": "canonical",
        "noise_k": 100, "plain_f1": 0.5, "directive_f1": 0.6,
    }
    gap = cell["directive_f1"] - cell["plain_f1"]
    assert gap < GAP
    assert gap >= GAP - 1e-9
    assert decide([cell])["cell"] == "tenth"


def test_descriptions_file_on_the_test_split_never_evolves(tmp_path, monkeypatch):
    written = {name: f"line for {name}" for name in NAMES}
    path = tmp_path / "descriptions.json"
    path.write_text(json.dumps(written), encoding="utf-8")
    seen = {"eval": [], "evolve": 0}
    monkeypatch.setenv("ODSKILL_BUDGET_USD", "")
    monkeypatch.setattr("odskill.selection.evolve_desc.load_env", lambda *_a, **_k: None)

    def fake_eval(_root, _cfg, descriptions):
        seen["eval"].append(descriptions)
        return {}

    def fake_evolve(*_a, **_k):
        seen["evolve"] += 1
        raise AssertionError("run_evolution")

    monkeypatch.setattr("odskill.selection.evolve_desc.run_eval", fake_eval)
    monkeypatch.setattr("odskill.selection.evolve_desc.run_evolution", fake_evolve)
    for arm in ("wikisel", "nowiki"):
        monkeypatch.setattr("sys.argv", [
            "evolve_desc", "--arm", arm, "--descriptions", str(path), "--split", "test",
            "--i-understand-this-is-the-test-split", "--budget", "1",
            "--run-dir", str(tmp_path / arm),
        ])
        main()
    assert seen["evolve"] == 0
    assert seen["eval"] == [written, written]


def test_run_evolution_refuses_the_test_split(tmp_path):
    with pytest.raises(SystemExit, match="refuses split=test"):
        run_evolution(tmp_path / "run", {"split": "test", "arm": "wikisel"})
    assert not (tmp_path / "run").exists()


def test_resume_cap_prices_the_remaining_episodes_at_the_observed_rate(tmp_path):
    from odskill.selection.batch import resume_cap

    path = tmp_path / "rollouts.jsonl"
    path.write_text("\n".join(
        json.dumps({"uid": f"g{i}", "pass": 0, "turns": 1, "error": "", "cost_usd": 0.0004})
        for i in range(10)) + "\n", encoding="utf-8")
    cap = resume_cap({"run_dir": tmp_path, "passes": 1, "games": 134}, 0.0002)
    assert cap == pytest.approx(0.004 + 124 * 0.0004 * 1.3)


def test_done_count_ignores_an_error_that_never_called_the_model(tmp_path):
    from odskill.selection.batch import done_count, paired_cells

    path = tmp_path / "rollouts.jsonl"
    path.write_text("\n".join([
        json.dumps({"uid": "a", "pass": 0, "error": "", "turns": 1}),
        json.dumps({"uid": "b", "pass": 0, "error": "TimeoutError: worker", "turns": 0}),
        json.dumps({"uid": "c", "pass": 1, "error": "", "turns": 1}),
    ]) + "\n", encoding="utf-8")
    assert done_count(path, 0) == 1
    records = [
        {"executor": HAIKU, "agent_prompt": "neutral", "names": "canonical", "noise_k": 100,
         "arm": "plain", "f1": 0.5, "cell": "plain"},
        {"executor": HAIKU, "agent_prompt": "neutral", "names": "canonical", "noise_k": 100,
         "arm": "directive", "f1": 0.6, "cell": "directive"},
    ]
    assert decide(paired_cells(records))["plain_f1"] == 0.5


def test_deepseek_and_forced_lose_to_a_qualifying_haiku():
    cells = [
        {"cell": "deep", "executor": DEEPSEEK, "agent_prompt": "neutral", "names": "canonical",
         "noise_k": 300, "plain_f1": 0.01, "directive_f1": 0.90},
        {"cell": "forced", "executor": HAIKU, "agent_prompt": "forced", "names": "canonical",
         "noise_k": 300, "plain_f1": 0.01, "directive_f1": 0.90},
        {"cell": "kept", "executor": HAIKU, "agent_prompt": "neutral", "names": "opaque",
         "noise_k": 100, "plain_f1": 0.40, "directive_f1": 0.55},
    ]
    assert decide(cells)["cell"] == "kept"


def test_grids_and_concurrency():
    cells = exp1_cells()
    assert len(cells) == 28
    assert sum(1 for cell in cells if cell["names"] == "opaque") == 4
    assert all(cell["seed"] == 0 and cell["passes"] == 1 and cell["workers"] == 6 for cell in cells)
    assert slots(10, 0) == 8
    assert slots(95, 0) == 4
    assert slots(10, 2) == 4
    assert slots(10, 0, dropped=True) == 4
    workers = {"anthropic": 6, "deepseek": 6}
    assert on_429(workers, "anthropic") == 3
    assert workers["deepseek"] == 6
    assert on_429(workers, "anthropic") == 1


def test_matched_baseline_and_test_seed():
    cell = {"agent_prompt": "neutral", "names": "canonical", "noise_k": 100}
    jobs = exp2_jobs(cell, 3.0)
    evolve = [job for job in jobs if job["kind"] == "evolve"]
    assert len(evolve) == 6
    for seed in (0, 1, 2):
        paths = {job["baseline"] for job in evolve if job["seed"] == seed}
        assert len(paths) == 1
        assert paths.pop().endswith(f"baseline-s{seed}/rollouts.jsonl")
    test = eval_jobs(cell, lambda _executor: 1.0)
    assert len(test) == 16
    for job in test:
        argv = job["argv"]
        assert argv[argv.index("--seed") + 1] == "0"
        if job["evolution_seed"] is not None:
            assert "--descriptions" in argv
            assert f"-s{job['evolution_seed']}" in " ".join(argv)


def test_exp2_run_passes_the_baseline_rows(tmp_path, monkeypatch):
    baseline = tmp_path / "rollouts.jsonl"
    baseline.write_text(json.dumps({"uid": "a", "error": ""}) + "\n", encoding="utf-8")
    seen = {}

    def fake(root, cfg, baseline_rows=None):
        seen["root"] = root
        seen["rows"] = baseline_rows
        seen["seed"] = cfg["seed"]
        seen["arm"] = cfg["arm"]
        return {}

    monkeypatch.setattr("odskill.selection.orchestrate.run_evolution", fake)
    exp2_run(tmp_path / "run", {"seed": 2, "arm": "wikisel"}, baseline)
    assert seen["rows"] == [{"uid": "a", "error": ""}]
    assert seen["seed"] == 2 and seen["arm"] == "wikisel"


def test_summaries_on_synthetic_rows(tmp_path):
    rows = []
    for index in range(4):
        rows.append({
            "uid": f"g{index}", "pass": 0, "task_type": "pick_and_place_simple",
            "relevant": "pick_and_place", "relevant_loaded": index < 3,
            "load_count": 1, "relevant_load_count": 1 if index < 3 else 0,
            "noise_loads": 0, "wrong_type_loads": 0, "loaded_any": True,
            "error": "model_error" if index == 3 else "", "cost_usd": 0.002,
        })
    record = cell_record({"cell": "flagged"}, rows)
    assert record["error_flag"] is True
    assert record["errors"] == 1
    text = write_exp1([record], tmp_path / "exp1" / "summary.md")
    assert "YES" in text and "F1 95% CI" in text
    assert (tmp_path / "exp1" / "cells.jsonl").is_file()
    plain = [{**row, "error": "", "relevant_loaded": False, "seed": 0} for row in rows]
    wiki = [{**row, "error": "", "relevant_loaded": True, "seed": seed} for seed in (0, 1) for row in rows]
    summary = write_test(
        {"anthropic/claude-haiku-5.5": {"plain": plain, "nowiki": wiki, "wikisel": wiki,
                                        "directive": plain}},
        tmp_path / "test" / "summary.md")
    assert "wikisel − nowiki" in summary
    assert "nowiki − plain" in summary
