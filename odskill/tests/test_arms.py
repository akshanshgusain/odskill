"""Arm prompts, TRAIN feedback, and the harness selection log. No network."""

from __future__ import annotations

import hashlib
import json
import sys

import pytest
from pathlib import Path
from types import SimpleNamespace

from wikiskill import engine
from wikiskill.isolated.tools_server import RoleTools
from wikiskill.paper_alignment.agents import paper_prompts
from wikiskill.paper_alignment.contracts import read_wiki, wiki_update

from odskill.agent import executor_tools
from odskill.evolve import (
    ARMS, EFFORT, FEEDBACK_FIELDS, MODEL, TASK, _binding_identity, accepted_without_load,
    agents_for, config_for, domain_loader, ondemand_addendum, prompts_for, resume_workers,
    selection_addendum, sync_selection_impact, train_feedback,
)
from odskill.noise import LIBRARY, mix
from odskill.skills import LOAD_SKILL_TOOL, Skill, index_v2_text
from odskill.spreadsheet import build
from odskill.roles import invoke, selection_evidence
from odskill import test_eval

SKILL = (
    "---\nname: compare_periods\ndescription: Verify period labels before comparison.\n---\n"
    "## When to Apply\nPeriod comparisons.\n## When NOT to Apply\nNo comparison requested.\n"
    "## Instructions\nRead both period labels before calculating the change.\n"
)
PURPOSE = (
    "## Origin\nSynthetic TRAIN traces.\n## Patterns Addressed\nPeriod alignment.\n"
    "## Evolution History\nInitial creation.\n"
)
ADDENDUM = (
    "Deployment note: the executor does not see skill bodies by default. It sees an index "
    "containing only each skill's name and description, mixed with many unrelated skills, and "
    "must call load_skill to read one. A skill that is never loaded has no effect. The name, "
    "description and 'When to Apply' section therefore decide whether a skill is ever used. "
    "You may create or patch skills to improve how reliably they are loaded on the tasks they "
    "help, and not loaded on tasks they don't."
)
SELECTION = (
    "Also record skill-selection failures as their own patterns, named with the prefix "
    "selection-: a relevant evolved skill was not loaded; an unrelated or noise skill was "
    "loaded; a skill was loaded but its instructions did not fit the task. Use the "
    "skill_selection feedback to identify them."
)


def _call(name, args, content="Fixture submission."):
    return {"role": "assistant", "content": content, "tool_calls": [{
        "id": "call-" + name, "type": "function",
        "function": {"name": name, "arguments": json.dumps(args)}}]}


def test_addendum_files_match_the_specified_text():
    assert ondemand_addendum().strip() == ADDENDUM
    assert selection_addendum().strip() == SELECTION


def test_prompts_are_paper_plus_the_arm_addendum_only():
    base = paper_prompts(TASK)
    assert prompts_for("all") == base
    assert prompts_for("od") == base
    shared_proposer = base["proposer.md"].rstrip() + "\n\n" + ADDENDUM + "\n"
    shared_maintainer = base["maintainer.md"].rstrip() + "\n\n" + ADDENDUM + "\n"
    assert prompts_for("od_aware")["proposer.md"] == shared_proposer
    assert prompts_for("od_aware")["maintainer.md"] == shared_maintainer
    assert prompts_for("wikisel")["proposer.md"] == shared_proposer
    assert prompts_for("wikisel")["maintainer.md"] == shared_maintainer.rstrip() + "\n\n" + SELECTION + "\n"


def test_manifest_records_low_effort_and_feedback_fields():
    plain = config_for("od", iterations=1, train_n=4, val_n=2, seed=0, noise_k=20)
    wiki = config_for("wikisel", iterations=1, train_n=4, val_n=2, seed=0, noise_k=20)
    assert plain["effort"] == plain["optimizer_effort"] == plain["reasoning_effort"] == EFFORT == "low"
    assert plain["training_feedback"] == list(FEEDBACK_FIELDS)
    assert wiki["training_feedback"] == list(FEEDBACK_FIELDS) + ["skill_selection"]
    assert plain["addendum_sha256"] == "" and wiki["addendum_sha256"]
    assert wiki["selection_addendum_sha256"]
    assert plain["index"] == wiki["index"] == "v2"
    assert plain["index_v2_sha256"] == wiki["index_v2_sha256"]
    assert plain["index_v2_sha256"] == hashlib.sha256(index_v2_text().encode()).hexdigest()
    v1 = config_for("od", iterations=1, train_n=4, val_n=2, seed=0, noise_k=20, index="v1")
    assert v1["index"] == "v1" and v1["index_v2_sha256"] == ""
    assert config_for("all", iterations=1, train_n=4, val_n=2, seed=0, noise_k=20)["index"] == ""
    assert plain != wiki and plain != v1


def test_feedback_hides_gold_and_selection_is_wikisel_only():
    row = {
        "split": "train", "fail_reason": "wrong_answer", "matched_cells": 1, "total_cells": 4,
        "has_output_workbook": True, "golden_path": "/tmp/task/1_golden.xlsx",
        "answer": "secret cell value", "predicted": "secret cell value",
        "skill_set": [
            {"name": "compare_periods", "origin": "evolved"},
            {"name": "csv_tables", "origin": "noise", "body": "do not copy"},
        ],
        "loaded_skills": [{"name": "csv_tables", "origin": "noise", "adjacent": True}],
    }
    plain = train_feedback(row, selection=False)
    rich = train_feedback(row, selection=True)
    assert "skill_selection" not in plain
    blob = json.dumps(rich)
    assert "golden" not in blob and "secret" not in blob and "do not copy" not in blob
    assert rich["skill_selection"] == {
        "evolved_offered": ["compare_periods"],
        "noise_offered": 1,
        "loaded": [{"name": "csv_tables", "origin": "noise"}],
        "evolved_not_loaded": ["compare_periods"],
    }


def test_selection_evidence_is_absent_without_the_impact_file(tmp_path):
    role = tmp_path / "iterations" / "001" / "maintainer"
    train = role.parent / "train"
    train.mkdir(parents=True)
    (train / "outcomes.jsonl").write_text(
        json.dumps({"loaded_skills": [{"name": "compare_periods", "origin": "evolved"}]}) + "\n"
        + json.dumps({"loaded_skills": []}) + "\n", encoding="utf-8")
    impact = ("# Selection impact\n\n- Iteration 1, verdict REJECT, val score 0.5.\n"
              "  - compare_periods — Verify period labels before comparison. — loaded in 0/2 val tasks.\n")
    skills = json.dumps({"compare_periods": {"skill_md": SKILL, "purpose_md": PURPOSE}})
    payload = {"wiki/index.md": "# Wiki index\n", "wiki/log.md": "# log\n",
               "wiki/skill-impact.md": "# impact\n", "skills.json": skills,
               "wiki/selection-impact.md": impact}
    block = selection_evidence(payload, role)
    assert block.startswith("Selection evidence\n")
    assert "Verify period labels before comparison." in block
    assert "compare_periods: loaded in 1/2 TRAIN tasks." in block
    assert "secret" not in block and "golden" not in block
    assert selection_evidence({"skills.json": skills}, role) == ""

    seen = {}

    def chat(_model, messages, _tools, **_kw):
        seen["user"] = messages[1]["content"]
        return _call("finish", {"proposal": {
            "create_patterns": [], "update_patterns": [],
            "update_index": "# Wiki index\n", "append_log": "Reviewed TRAIN."}})

    invoke(role, payload, "system", '{"iteration": 1}', "maintainer", "offline", "low", chat_fn=chat)
    assert seen["user"].startswith("Selection evidence\n")
    plain = tmp_path / "other"
    invoke(plain, {"wiki/index.md": "# Wiki index\n", "wiki/log.md": "# log\n",
                   "wiki/skill-impact.md": "# impact\n", "skills.json": "{}"},
           "system", "handoff-only", "maintainer", "offline", "low", chat_fn=chat)
    assert seen["user"] == "handoff-only"


def test_test_eval_refuses_the_test_split_without_the_flag(tmp_path, monkeypatch):
    monkeypatch.setattr("odskill.llm.urllib.request.urlopen",
                        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("network")))
    with pytest.raises(SystemExit, match="TEST split"):
        test_eval.main(["--run-dir", str(tmp_path), "--budget", "1"])


def test_test_eval_records_score_loads_and_cost(tmp_path, monkeypatch):
    root = tmp_path / "run"
    (root / "skills").mkdir(parents=True)
    (root / "skills" / "S0.md").write_text("ACCEPTED SKILL\n", encoding="utf-8")
    (root / "events.jsonl").write_text("", encoding="utf-8")
    (root / "manifest.json").write_text(json.dumps({
        "domain": "spreadsheet", "model": "anthropic/claude-haiku-5.5", "iterations": 1,
        "arm": "od", "mode": "od", "noise_k": 100, "index": "v2", "seed": 0,
        "reasoning_effort": "low",
    }), encoding="utf-8")
    seen = []

    def fake(case, **kw):
        seen.append(kw)
        return {"uid": case.uid, "score": 1, "fail_reason": "", "turns": 2,
                "loaded_skills": [{"name": "compare_periods", "origin": "evolved"}],
                "usage": {"cost_usd": 0.01, "prompt_tokens": 10, "completion_tokens": 2}}

    monkeypatch.setattr(test_eval, "rollout_case", fake)
    monkeypatch.setattr(test_eval, "test_cases", lambda: [
        SimpleNamespace(uid="t1", task_id="t1"), SimpleNamespace(uid="t2", task_id="t2")])
    test_eval.evaluate(root, no_skills=False, budget=1, workers=1)
    assert [kw["skill_text"] for kw in seen] == ["ACCEPTED SKILL\n", "ACCEPTED SKILL\n"]
    assert {kw["mode"] for kw in seen} == {"od"} and {kw["noise_k"] for kw in seen} == {100}
    assert {kw["index"] for kw in seen} == {"v2"}
    rows = [json.loads(line) for line in (root / "test_eval" / "outcomes.jsonl").read_text().splitlines()]
    assert {row["uid"] for row in rows} == {"t1", "t2"}
    assert rows[0]["score"] == 1 and rows[0]["loads"][0]["name"] == "compare_periods"
    assert rows[0]["cost_usd"] == 0.01
    seen.clear()
    test_eval.evaluate(root, no_skills=True, budget=1, workers=1)
    assert all(kw["skill_text"] == "" and kw["noise_k"] == 0 and kw["mode"] == "all" for kw in seen)
    assert (root / "test_eval_baseline" / "summary.json").is_file()


def test_executor_request_includes_load_skill_in_od_mode():
    names = [tool["function"]["name"] for tool in executor_tools(True)]
    assert names == ["bash", "load_skill"]
    assert "<available_skills>" in executor_tools(True)[1]["function"]["description"]
    assert [tool["function"]["name"] for tool in executor_tools(False)] == ["bash"]


def test_index_v2_is_the_tool_description_and_v1_stays_in_the_prompt(tmp_path):
    skill = Skill("spreadsheet_task_workflow", "Workflow for spreadsheet manipulation tasks.", "body\n")
    case = SimpleNamespace(instruction="Fill C2.", init_name="in.xlsx")
    prefix, _body, offered = build(case, [skill], tmp_path, "od", index="v2")
    assert "Available skills" not in prefix and "you may load none" not in prefix
    assert skill.name not in prefix and skill.description not in prefix
    description = executor_tools(True, offered, "v2")[1]["function"]["description"]
    assert description.startswith("Check whether an available skill matches the task.")
    assert "When one does, load it with this tool before starting the work." in description
    assert "<name>spreadsheet_task_workflow</name>" in description
    assert "<description>Workflow for spreadsheet manipulation tasks.</description>" in description
    assert "you may load none" not in description and "<!--" not in description
    assert "platform.claude.com" in index_v2_text()
    v1_prefix, _, _ = build(case, [skill], tmp_path, "od", index="v1")
    assert "you may load none" in v1_prefix and skill.name in v1_prefix
    assert executor_tools(True, offered, "v1")[1] is LOAD_SKILL_TOOL


def test_selection_impact_file_is_readable_and_kept_by_the_wiki_contract(tmp_path):
    wiki = tmp_path / "wiki"
    (wiki / "patterns").mkdir(parents=True)
    (wiki / "index.md").write_text("# Wiki index\n", encoding="utf-8")
    (wiki / "log.md").write_text("# log\n", encoding="utf-8")
    (wiki / "skill-impact.md").write_text("# impact\n", encoding="utf-8")
    (wiki / "selection-impact.md").write_text(
        "# Selection impact\n\n- Iteration 1, verdict REJECT, val score 0. loaded in 0/2 val tasks.\n",
        encoding="utf-8")
    existing = read_wiki(wiki)
    _normalized, updated = wiki_update({
        "create_patterns": [], "update_patterns": [],
        "update_index": "# Wiki index\n", "append_log": "Reviewed TRAIN."}, existing)
    assert "selection-impact.md" in updated
    work, control = tmp_path / "input", tmp_path / "runtime"
    control.mkdir()
    for name, text in updated.items():
        path = work / "wiki" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (work / "skills.json").write_text("{}", encoding="utf-8")
    body = RoleTools(work, control, "proposer", sys.executable).call(
        "read_file", {"path": "wiki/selection-impact.md"})
    assert "loaded in 0/2" in body


def test_each_arm_runs_one_iteration(tmp_path, monkeypatch):
    monkeypatch.setattr("odskill.llm.urllib.request.urlopen",
                        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("network")))

    def scripted(directory, mode):
        if mode == "maintainer":
            return _call("finish", {"proposal": {
                "create_patterns": [{"name": "periods", "content": "Read both period labels."}],
                "update_patterns": [],
                "update_index": "# Wiki\n- [periods](wiki/patterns/periods.md): Read period labels.",
                "append_log": "Reviewed TRAIN."}})
        summary = json.loads((directory / "input/trace-summary.json").read_text(encoding="utf-8"))
        events = directory / "runtime/tool-events.jsonl"
        n = len([line for line in events.read_text().splitlines() if line.strip()]) if events.is_file() else 0
        if n < 4:
            return _call("read_file", {"path": summary[n]["path"]}, content="")
        return _call("finish", {"proposal": {
            "action": "create", "name": "compare_periods", "skill_md": SKILL, "purpose_md": PURPOSE}})

    for arm in ARMS:
        captured = {"systems": {}, "feedback": [], "wiki_files": set()}

        def invoke_fake(directory, payload, system, user, mode, model, effort, arm=arm, captured=captured):
            captured["systems"][mode] = system
            captured["wiki_files"].update(k for k in payload if k.startswith("wiki/"))
            for key, text in payload.items():
                if key.startswith("traces/"):
                    blob = text.split("TRAIN evaluator feedback:\n", 1)[1]
                    captured["feedback"].append(json.loads(blob))

            def fake(*_a, **_k):
                return scripted(directory, mode)

            return invoke(directory, payload, system, user, mode, model, effort, chat_fn=fake)

        root = tmp_path / arm
        config = config_for(arm, iterations=1, train_n=4, val_n=2, seed=0, noise_k=2, workers=1)
        config["domain"] = "synthetic-finance"
        config["timeout"] = 1
        engine.initialize(root, config, wiki_template="officeqa", agent_prompts=prompts_for(arm))
        written = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        assert written["reasoning_effort"] == "low"
        assert written["training_feedback"] == config["training_feedback"]

        def load(_config, split):
            cases = [SimpleNamespace(uid=f"{split}-{i}", split=split) for i in range(4 if split == "train" else 2)]

            def rollout(case, **kw):
                archive = Path(kw["workdir"]) / "runtime"
                archive.mkdir(parents=True)
                (archive / "tool-events.jsonl").write_text(
                    json.dumps({"tool": "bash", "arguments": {"command": "echo"}, "result": "ok"}) + "\n",
                    encoding="utf-8")
                offered = []
                if str(kw["skill_text"]).strip():
                    offered = [{"name": "compare_periods", "origin": "evolved"},
                               {"name": "csv_tables", "origin": "noise"}]
                return {"uid": case.uid, "predicted": "fixture", "workspace": str(kw["workdir"]),
                        "question": {"question": "Compare the two periods.", "instruction_type": "Cell-Level",
                                     "answer_position": "A1", "answer_sheet": None},
                        "score": 0, "fail_reason": "wrong_answer", "matched_cells": 1, "total_cells": 4,
                        "has_output_workbook": True, "skill_set": offered, "loaded_skills": [],
                        "golden_path": "/tmp/1_golden.xlsx", "answer": "secret cell value"}

            return cases, rollout

        agents = agents_for(arm, 0, invoke_fake)
        engine.evolve(root, domain_loader=load, maintainer_factory=agents.maintainer_factory,
                      proposer_factory=agents.proposer_factory)
        if arm == "wikisel":
            sync_selection_impact(root)
        expected = prompts_for(arm)
        assert captured["systems"] == {"maintainer": expected["maintainer.md"],
                                       "proposer": expected["proposer.md"]}
        assert captured["feedback"]
        for item in captured["feedback"]:
            blob = json.dumps(item)
            assert "golden" not in blob and "secret" not in blob
            assert ("skill_selection" in item) is (arm == "wikisel")
            assert set(FEEDBACK_FIELDS) <= set(item)
        impact = root / "wiki/selection-impact.md"
        assert impact.is_file() is (arm == "wikisel")
        assert ("wiki/selection-impact.md" in captured["wiki_files"]) is (arm == "wikisel")
        for role in ("maintainer", "proposer"):
            transcript = json.loads(
                (root / f"iterations/001/{role}/runtime/transcript.json").read_text(encoding="utf-8"))
            user = transcript[1]["content"]
            assert ("Selection evidence" in user) is (arm == "wikisel")
            if arm == "wikisel":
                assert "No accepted skill in the latest TRAIN batch." in user
                assert "executor_visibility" in user
                assert "secret" not in user
        if arm == "wikisel":
            text = impact.read_text(encoding="utf-8")
            assert "verdict REJECT" in text
            assert "compare_periods — Verify period labels before comparison. — loaded in 0/2 val tasks." in text


LAUNCHES = (
    ("all-n0", "all", 0),
    ("od-n0", "od", 0),
    ("od-n100", "od", 100),
    ("od_aware-n100", "od_aware", 100),
    ("wikisel-n100", "wikisel", 100),
)


def _tool_names(on_demand, skills, index):
    return [tool["function"]["name"] for tool in executor_tools(on_demand, skills, index)]


def test_five_launch_configs_match_the_locked_design(tmp_path, monkeypatch):
    """Manifest fields, prompt contents, and one fake iteration for each seed-0 run."""
    monkeypatch.setattr("odskill.llm.urllib.request.urlopen",
                        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("network")))
    library_sha = hashlib.sha256(LIBRARY.read_bytes()).hexdigest()
    noise_name = json.loads(LIBRARY.read_text(encoding="utf-8").splitlines()[0])["name"]
    case = SimpleNamespace(instruction="Fill C2.", init_name="in.xlsx")
    paper = paper_prompts(TASK)

    def scripted(directory, mode):
        if mode == "maintainer":
            return _call("finish", {"proposal": {
                "create_patterns": [{"name": "periods", "content": "Read both period labels."}],
                "update_patterns": [],
                "update_index": "# Wiki\n- [periods](wiki/patterns/periods.md): Read period labels.",
                "append_log": "Reviewed TRAIN."}})
        summary = json.loads((directory / "input/trace-summary.json").read_text(encoding="utf-8"))
        events = directory / "runtime/tool-events.jsonl"
        n = len([line for line in events.read_text().splitlines() if line.strip()]) if events.is_file() else 0
        if n < 4:
            return _call("read_file", {"path": summary[n]["path"]}, content="")
        return _call("finish", {"proposal": {
            "action": "create", "name": "compare_periods", "skill_md": SKILL, "purpose_md": PURPOSE}})

    for name, arm, noise_k in LAUNCHES:
        config = config_for(arm, iterations=6, train_n=80, val_n=40, seed=0,
                            noise_k=noise_k, workers=3, index="v2")
        assert config["model"] == config["optimizer_model"] == "anthropic/claude-haiku-5.5"
        assert config["effort"] == config["optimizer_effort"] == config["reasoning_effort"] == "low"
        assert config["arm"] == arm
        assert config["mode"] == ("all" if arm == "all" else "od")
        assert config["noise_k"] == noise_k
        assert config["noise_library_sha256"] == library_sha
        assert config["seed"] == 0 and config["train_n"] == 80 and config["val_n"] == 40
        assert config["iterations"] == 6
        assert config["training_feedback"][:4] == list(FEEDBACK_FIELDS)
        assert ("skill_selection" in config["training_feedback"]) is (arm == "wikisel")
        assert bool(config["addendum_sha256"]) is (arm in ("od_aware", "wikisel"))
        assert bool(config["selection_addendum_sha256"]) is (arm == "wikisel")
        assert config["index"] == ("" if arm == "all" else "v2")
        assert bool(config["index_v2_sha256"]) is (arm != "all")
        prompts = prompts_for(arm)
        if arm in ("all", "od"):
            assert prompts == paper
        if arm in ("od_aware", "wikisel"):
            assert prompts["proposer.md"].rstrip().endswith(ADDENDUM)
            assert prompts["maintainer.md"].count(ADDENDUM) == 1
        assert (SELECTION in prompts["maintainer.md"]) is (arm == "wikisel")
        assert SELECTION not in prompts["proposer.md"]

        skills = mix(SKILL, noise_k, 0)
        prefix, _body, offered = build(case, skills, tmp_path / name, config["mode"], config["index"] or "v2")
        names = _tool_names(bool(offered), offered, config["index"] or "v2")
        evolved = [skill.name for skill in skills if skill.origin == "evolved"]
        assert evolved == ["compare_periods"]
        if arm == "all" and noise_k == 0:
            assert "compare_periods" in prefix and noise_name not in prefix
            assert names == ["bash"]
        if arm == "od" and noise_k == 0:
            assert "compare_periods" not in prefix and noise_name not in prefix
            description = executor_tools(True, offered, "v2")[1]["function"]["description"]
            assert "<name>compare_periods</name>" in description
            assert f"<name>{noise_name}</name>" not in description
            assert names == ["bash", "load_skill"]

        root = tmp_path / "run" / name
        engine.initialize(root, config, wiki_template="officeqa", agent_prompts=prompts)
        written = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        for key in ("model", "optimizer_model", "effort", "optimizer_effort", "index",
                    "index_v2_sha256", "noise_k", "noise_library_sha256",
                    "training_feedback", "addendum_sha256", "selection_addendum_sha256", "seed",
                    "train_n", "val_n", "iterations", "arm", "mode"):
            assert written[key] == config[key]
        assert set(written["prompt_hashes"]) == {"maintainer.md", "proposer.md"}
        for prompt_name, text in prompts.items():
            assert written["prompt_hashes"][prompt_name] == hashlib.sha256(text.encode()).hexdigest()

        captured = {"user": {}}

        def invoke_fake(directory, payload, system, user, mode, model, effort,
                        arm=arm, captured=captured):
            def fake(*_a, **_k):
                return scripted(directory, mode)

            archive = invoke(directory, payload, system, user, mode, model, effort, chat_fn=fake)
            transcript = json.loads((archive / "transcript.json").read_text(encoding="utf-8"))
            captured["user"][mode] = transcript[1]["content"]
            return archive

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
                        "score": 0, "fail_reason": "wrong_answer", "matched_cells": 0, "total_cells": 1,
                        "has_output_workbook": False, "skill_set": [], "loaded_skills": []}

            return cases, rollout

        # One iteration only. The launch manifest above still records iterations=6.
        short = dict(written)
        short["iterations"] = 1
        (root / "manifest.json").write_text(json.dumps(short), encoding="utf-8")
        (root / "manifest-lock.json").write_text(
            json.dumps({"sha256": engine.digest(short)}), encoding="utf-8")
        agents = agents_for(arm, 0, invoke_fake)
        engine.evolve(root, domain_loader=load, maintainer_factory=agents.maintainer_factory,
                      proposer_factory=agents.proposer_factory)
        assert ("Selection evidence" in captured["user"]["maintainer"]) is (arm == "wikisel")
        assert ("Selection evidence" in captured["user"]["proposer"]) is (arm == "wikisel")
        if arm != "wikisel":
            assert "Selection evidence" not in json.dumps(captured["user"])


def test_resume_rewrites_workers_without_dropping_the_phase_binding(tmp_path):
    config = config_for("od", iterations=1, train_n=4, val_n=2, seed=0, noise_k=0, workers=3)
    root = tmp_path / "resume"
    engine.initialize(root, config, wiki_template="officeqa", agent_prompts=prompts_for("od"))
    manifest = engine.read(root / "manifest.json")
    _train, _ = domain_loader(manifest, "train")
    # Baseline has not been scored, so a worker change must refresh that binding.
    binding_dir = root / "baseline" / "val"
    binding_dir.mkdir(parents=True)
    engine.save(binding_dir / "binding.json", {"sha256": _binding_identity(manifest, _train, "")})
    resume_workers(root, 2)
    updated = engine.read(root / "manifest.json")
    assert updated["workers"] == 2
    assert engine.read(root / "manifest-lock.json")["sha256"] == engine.digest(updated)
    val, _ = domain_loader(updated, "val")
    assert engine.read(binding_dir / "binding.json")["sha256"] == _binding_identity(updated, val, "")


SONNET = "anthropic/claude-sonnet-5.5"


def _scripted_role(directory, mode):
    if mode == "maintainer":
        return _call("finish", {"proposal": {
            "create_patterns": [{"name": "periods", "content": "Read both period labels."}],
            "update_patterns": [],
            "update_index": "# Wiki\n- [periods](wiki/patterns/periods.md): Read period labels.",
            "append_log": "Reviewed TRAIN."}})
    summary = json.loads((directory / "input/trace-summary.json").read_text(encoding="utf-8"))
    events = directory / "runtime/tool-events.jsonl"
    n = len([line for line in events.read_text().splitlines() if line.strip()]) if events.is_file() else 0
    if n < 4:
        return _call("read_file", {"path": summary[n]["path"]}, content="")
    return _call("finish", {"proposal": {
        "action": "create", "name": "compare_periods", "skill_md": SKILL, "purpose_md": PURPOSE}})


def _fake_iteration(tmp_path, arm, *, noise_k, model, optimizer_model):
    """One engine iteration with a scripted role and a fake executor."""
    seen = {"roles": set(), "executor": set()}

    def invoke_fake(directory, payload, system, user, mode, role_model, effort):
        seen["roles"].add((mode, role_model, effort))

        def fake(*_a, **_k):
            return _scripted_role(directory, mode)

        return invoke(directory, payload, system, user, mode, role_model, effort, chat_fn=fake)

    def load(_config, split):
        cases = [SimpleNamespace(uid=f"{split}-{i}", split=split) for i in range(4 if split == "train" else 2)]

        def rollout(case, **kw):
            seen["executor"].add((kw["model"], kw["reasoning_effort"]))
            archive = Path(kw["workdir"]) / "runtime"
            archive.mkdir(parents=True)
            (archive / "tool-events.jsonl").write_text(
                json.dumps({"tool": "bash", "arguments": {"command": "echo"}, "result": "ok"}) + "\n",
                encoding="utf-8")
            return {"uid": case.uid, "predicted": "fixture", "workspace": str(kw["workdir"]),
                    "question": {"question": "Compare the two periods.", "instruction_type": "Cell-Level",
                                 "answer_position": "A1", "answer_sheet": None},
                    "score": 0, "fail_reason": "wrong_answer", "matched_cells": 0, "total_cells": 1,
                    "has_output_workbook": False, "skill_set": [], "loaded_skills": []}

        return cases, rollout

    root = tmp_path / f"{arm}-k{noise_k}"
    config = config_for(arm, iterations=1, train_n=4, val_n=2, seed=0, noise_k=noise_k,
                        workers=1, model=model, optimizer_model=optimizer_model)
    engine.initialize(root, config, wiki_template="officeqa", agent_prompts=prompts_for(arm))
    written = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    agents = agents_for(arm, 0, invoke_fake)
    engine.evolve(root, domain_loader=load, maintainer_factory=agents.maintainer_factory,
                  proposer_factory=agents.proposer_factory)
    return written, seen


def test_optimizer_model_is_separate_and_defaults_to_the_executor(tmp_path, monkeypatch):
    monkeypatch.setattr("odskill.llm.urllib.request.urlopen",
                        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("network")))
    same = config_for("all", iterations=1, train_n=4, val_n=2, seed=0, noise_k=0)
    assert same["model"] == same["optimizer_model"] == MODEL
    assert same["optimizer_effort"] == "low"
    split = config_for("all", iterations=1, train_n=4, val_n=2, seed=0, noise_k=0,
                       model=MODEL, optimizer_model=SONNET)
    assert split["model"] == MODEL and split["optimizer_model"] == SONNET
    assert engine.digest(same) != engine.digest(split)

    written, seen = _fake_iteration(tmp_path, "all", noise_k=0, model=MODEL, optimizer_model=SONNET)
    assert written["model"] == MODEL
    assert written["optimizer_model"] == SONNET
    assert written["effort"] == written["optimizer_effort"] == "low"
    assert seen["roles"] == {("maintainer", SONNET, "low"), ("proposer", SONNET, "low")}
    assert seen["executor"] == {(MODEL, "low")}


def test_q2_configs_at_noise_20_take_a_separate_optimizer(tmp_path, monkeypatch):
    monkeypatch.setattr("odskill.llm.urllib.request.urlopen",
                        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("network")))
    for arm in ("od", "od_aware", "wikisel"):
        written, seen = _fake_iteration(tmp_path, arm, noise_k=20, model=MODEL, optimizer_model=SONNET)
        assert written["arm"] == arm and written["mode"] == "od" and written["noise_k"] == 20
        assert written["index"] == "v2"
        assert written["model"] == MODEL and written["optimizer_model"] == SONNET
        assert written["optimizer_effort"] == "low"
        assert seen["roles"] == {("maintainer", SONNET, "low"), ("proposer", SONNET, "low")}
        assert seen["executor"] == {(MODEL, "low")}
        assert (written["addendum_sha256"] != "") is (arm in ("od_aware", "wikisel"))


def test_accepted_without_load_flags_unloaded_on_demand_accepts(tmp_path):
    root = tmp_path / "od"
    for iteration, loaded in ((1, False), (2, True)):
        directory = root / f"iterations/{iteration:03d}/val"
        directory.mkdir(parents=True)
        row = {"skill_set": [{"name": "checklist", "origin": "evolved"}],
               "loaded_skills": [{"name": "checklist", "origin": "evolved"}] if loaded else []}
        (directory / "outcomes.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    events = [
        {"type": "gate", "iteration": 1, "accepted": True, "verdict": "ACCEPT"},
        {"type": "gate", "iteration": 2, "accepted": True, "verdict": "ACCEPT"},
        {"type": "gate", "iteration": 3, "accepted": False, "verdict": "REJECT"},
    ]
    (root / "events.jsonl").write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
    (root / "manifest.json").write_text(json.dumps({"arm": "od", "mode": "od"}), encoding="utf-8")
    assert accepted_without_load(root) == [1]
    (root / "manifest.json").write_text(json.dumps({"arm": "all", "mode": "all"}), encoding="utf-8")
    assert accepted_without_load(root) == []
