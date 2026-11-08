"""Offline checks for the evolution wiring. No network."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from wikiskill import engine
from wikiskill.benchmarks.spreadsheet import load_cases
from wikiskill.paper_alignment.agents import PaperAgents, paper_prompts
from wikiskill.paper_alignment.evidence import visible_trace

from odskill import llm
from odskill.llm import BudgetExceeded, chat
from odskill.noise import LIBRARY, MANIFEST, mix
from odskill.roles import invoke
from odskill.skills import Skill
from odskill.spreadsheet import rollout_case

DATA = Path(__file__).resolve().parents[2] / "data/spreadsheet/spreadsheetbench_verified_400"
SKILL = (
    "---\nname: compare_periods\ndescription: Verify period labels before comparison.\n---\n"
    "## When to Apply\nPeriod comparisons.\n## When NOT to Apply\nNo comparison requested.\n"
    "## Instructions\nRead both period labels before calculating the change.\n"
)
PURPOSE = (
    "## Origin\nSynthetic TRAIN traces.\n## Patterns Addressed\nPeriod alignment.\n"
    "## Evolution History\nInitial creation.\n"
)


def _call(name, args, content="Fixture submission."):
    return {"role": "assistant", "content": content, "tool_calls": [{
        "id": "call-" + name, "type": "function",
        "function": {"name": name, "arguments": json.dumps(args)}}]}


def test_budget_aborts_before_request(monkeypatch):
    monkeypatch.setenv("ODSKILL_BUDGET_USD", "0")
    monkeypatch.setattr(llm, "_spent", 0.0)

    def boom(*_a, **_k):
        raise AssertionError("request was sent")

    monkeypatch.setattr(llm.urllib.request, "urlopen", boom)
    with pytest.raises(BudgetExceeded):
        chat("anthropic/claude-haiku-5.5", [{"role": "user", "content": "hi"}])


def test_mix_keeps_evolved_text_and_labels_noise():
    noise = Skill("csv_tables", "Read a csv table.", "Use the csv module.\n",
                  origin="noise", adjacent=True)
    noise = replace(noise, raw=noise.full())
    first = [s.name for s in mix(SKILL, 1, 0, [noise])]
    second = [s.name for s in mix(SKILL, 1, 0, [noise])]
    assert first == second
    mixed = mix(SKILL, 1, 0, [noise])
    evolved = next(s for s in mixed if s.origin == "evolved")
    assert evolved.raw.strip() == SKILL.strip()
    assert evolved.full().strip() == SKILL.strip()
    assert next(s for s in mixed if s.origin == "noise").adjacent is True
    assert [s.name for s in mix(SKILL, 0, 0, [noise])] == ["compare_periods"]


def test_rollout_record_is_visible_to_the_paper_trace(tmp_path, monkeypatch):
    case = next(c for c in load_cases(DATA) if c.uid == "22-47")
    noise = replace(Skill("csv_tables", "Read a csv table.", "Use the csv module.\n",
                           origin="noise", adjacent=True), raw="")
    noise = replace(noise, raw=noise.full())

    def fake(**kwargs):
        kwargs["transcript_path"].write_text("[]", encoding="utf-8")
        return {"final": "wrote the sheet", "error": "", "turns": 2,
                "loaded_skills": [{"name": "csv_tables", "origin": "noise", "adjacent": True}],
                "tool_events": [{"tool": "bash", "arguments": {"command": "ls"}, "result": "ok"}],
                "usage": {"reported_models": ["anthropic/claude-haiku-5.5"], "prompt_tokens": 3,
                          "completion_tokens": 1, "cached_tokens": 0, "cost_usd": 0.0}}

    monkeypatch.setattr("odskill.spreadsheet.run_agent", fake)
    record = rollout_case(case, workdir=tmp_path, model="offline", skill_text=SKILL, mode="all",
                          reasoning_effort="low", timeout_seconds=180, noise_k=1, seed=0,
                          noise_library=[noise])
    assert record["question"]["question"] == case.instruction
    assert record["question"]["answer_position"] == case.answer_position
    assert record["predicted"] == "wrote the sheet"
    assert {item["name"]: item["origin"] for item in record["skill_set"]} == {
        "compare_periods": "evolved", "csv_tables": "noise"}
    assert record["loaded_skills"][0]["origin"] == "noise"
    prompt = (Path(record["workspace"]) / ".odskill/prompt.md").read_text(encoding="utf-8")
    assert SKILL.strip() in prompt
    trace = visible_trace(record, record["question"])
    assert "TOOL bash" in trace
    assert case.instruction[:40] in trace
    events = (Path(record["workspace"]) / "runtime/tool-events.jsonl").read_text(encoding="utf-8")
    assert json.loads(events)["tool"] == "bash"


def test_frozen_noise_library():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    raw = LIBRARY.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == manifest["sha256"]
    assert manifest["source"].endswith("WeihangSu/SRA-Bench")
    assert manifest["revision"] == "6143f2634eb284955ce312213bac24b582d039f3"
    assert manifest["seed"] == 0 and manifest["count"] == 300
    rows = [json.loads(line) for line in raw.decode().splitlines() if line.strip()]
    assert len(rows) == 300
    assert sum(bool(row["adjacent"]) for row in rows) == 30
    assert all(re.fullmatch(r"[a-z][a-z0-9_]*", row["name"]) for row in rows)
    assert len({row["source_id"] for row in rows}) == 300


def test_fake_chat_drives_one_engine_iteration(tmp_path, monkeypatch):
    monkeypatch.setenv("ODSKILL_BUDGET_USD", "0")
    monkeypatch.setattr(llm.urllib.request, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("network")))

    def scripted(directory, mode, _messages):
        if mode == "maintainer":
            return _call("finish", {"proposal": {
                "create_patterns": [{"name": "periods", "content": "Read both period labels."}],
                "update_patterns": [],
                "update_index": "# Wiki\n- [periods](wiki/patterns/periods.md): Read period labels.",
                "append_log": "Reviewed TRAIN."}})
        summary = json.loads((directory / "input/trace-summary.json").read_text(encoding="utf-8"))
        seen = list((directory / "runtime").glob("tool-events.jsonl"))
        n = 0
        if seen and seen[0].is_file():
            n = sum(1 for line in seen[0].read_text().splitlines() if line.strip())
        if n < 4:
            return _call("read_file", {"path": summary[n]["path"]}, content="")
        return _call("finish", {"proposal": {
            "action": "create", "name": "compare_periods", "skill_md": SKILL, "purpose_md": PURPOSE}})

    def invoke_fake(directory, payload, system, user, mode, model, effort):
        def fake(*_a, **_k):
            return scripted(directory, mode, _a)
        return invoke(directory, payload, system, user, mode, model, effort, chat_fn=fake)

    root = tmp_path / "study"
    config = {"domain": "synthetic-finance", "model": "fixture", "optimizer_model": "fixture",
              "effort": "low", "optimizer_effort": "low", "workers": 1, "iterations": 1, "timeout": 1}
    engine.initialize(root, config, wiki_template="officeqa", agent_prompts=paper_prompts("financial questions"))

    def load(_config, split):
        cases = [SimpleNamespace(uid=f"{split}-{i}", split=split) for i in range(4 if split == "train" else 2)]

        def rollout(case, **kw):
            archive = Path(kw["workdir"]) / "runtime"
            archive.mkdir(parents=True)
            (archive / "tool-events.jsonl").write_text(
                json.dumps({"tool": "bash", "arguments": {"command": "echo"}, "result": "ok"}) + "\n",
                encoding="utf-8")
            return {"uid": case.uid, "predicted": "fixture", "workspace": str(kw["workdir"]),
                    "question": {"question": "Compare the two periods.", "instruction_type": "Cell-Level",
                                 "answer_position": "A1", "answer_sheet": None},
                    "score": int(bool(str(kw["skill_text"]).strip())), "fail_reason": ""}

        return cases, rollout

    agents = PaperAgents(invoke_fake, seed=0)
    state = engine.evolve(root, domain_loader=load, maintainer_factory=agents.maintainer_factory,
                          proposer_factory=agents.proposer_factory)
    assert [gate["verdict"] for gate in state["history"]] == ["ACCEPT"]
    assert state["r_best"] == 1
    page = (root / "wiki/patterns/periods.md").read_text(encoding="utf-8")
    assert "period labels" in page
    proposed = (root / "skills/iteration-001.md").read_text(encoding="utf-8")
    assert proposed.strip() == SKILL.strip()
