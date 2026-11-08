import json
from pathlib import Path

from odskill.llm import Usage
from odskill.selection.episode import NEUTRAL, _STATIC, first_turn, static_prompt
from odskill.selection.evolve_desc import (
    accept, best_accepted_f1, evolve_descriptions, history_text, offered_index, sample_traces,
)
from odskill.selection.library import (
    NAMES, apply_descriptions, body_sha256, canonical_name, library, opaque_mapping, plain_descriptions,
    present, render_skill, skill_text, validate_bodies,
)
from odskill.selection.metrics import aggregate, bootstrap_diff, per_skill, score_loads
from odskill.selection.roles_desc import (
    _MAINTAINER, maintain, maintainer_files, propose, proposer_files, proposer_prompt, visible,
)
from odskill.skills import load_skill_tool

FROZEN = {name: f"## When to Apply\n{name}\n## When NOT to Apply\nno\n## Instructions\ndo the task\n"
          for name in NAMES}
DESC = {name: f"plain {name}" for name in NAMES}


def _row(uid, relevant, loads, task_type=None, noise=0, wrong=0):
    names = [item["name"] for item in loads]
    return {
        "uid": uid, "relevant": relevant, "task_type": task_type or relevant,
        "loads": names, "load_count": len(names),
        "relevant_load_count": sum(1 for name in names if name == relevant),
        "relevant_loaded": any(name == relevant for name in names),
        "noise_loads": noise, "wrong_type_loads": wrong, "loaded_any": bool(names),
        "pass": 0, "task": "heat the apple",
    }


def test_metrics_count_a_relevant_load_and_ignore_errors():
    loads = score_loads(
        [{"name": "pick_heat_then_place", "origin": "evolved"},
         {"name": "pick_cool_then_place", "origin": "evolved"},
         {"name": "some_noise", "origin": "noise"}],
        "pick_heat_then_place")
    assert loads["relevant_loaded"] is True
    assert loads["wrong_type_loads"] == 1
    assert loads["noise_loads"] == 1
    rows = [
        _row("a", "pick_heat_then_place", [{"name": "pick_heat_then_place"}], wrong=0),
        _row("b", "pick_cool_then_place", [{"name": "some_noise"}], noise=1),
        {"uid": "c", "relevant": "pick_and_place", "error": "model_error", "pass": 0,
         "relevant_loaded": False, "load_count": 0, "relevant_load_count": 0,
         "noise_loads": 0, "wrong_type_loads": 0, "loaded_any": False, "loads": []},
    ]
    summary = aggregate(rows)
    assert summary["n"] == 2
    assert summary["recall"] == 0.5
    assert summary["precision"] == 0.5
    skills = per_skill(rows)
    assert skills["pick_heat_then_place"]["recall"] == 1
    assert skills["pick_cool_then_place"]["recall"] == 0


def test_bootstrap_difference_is_stable():
    left = [_row(str(i), "pick_heat_then_place", []) for i in range(10)]
    right = [_row(str(i), "pick_heat_then_place",
                  [{"name": "pick_heat_then_place"}] if i < 8 else []) for i in range(10)]
    one = bootstrap_diff(left, right, "recall", resamples=200, seed=0)
    two = bootstrap_diff(left, right, "recall", resamples=200, seed=0)
    assert one["ci95"] == two["ci95"]
    assert one["estimate"] == 0.8
    assert one["ci95"][0] > 0


def test_descriptions_can_change_and_bodies_cannot():
    updated = apply_descriptions(DESC, {"pick_heat_then_place": "Load this when the goal says heat."}, FROZEN)
    assert updated["pick_heat_then_place"].startswith("Load this")
    assert "When to Apply" in skill_text(updated, FROZEN)
    before = skill_text(DESC, FROZEN)
    after = skill_text(updated, FROZEN)
    assert "do the task" in before and "do the task" in after
    try:
        apply_descriptions(DESC, {"not_a_skill": "x"}, FROZEN)
    except KeyError:
        pass
    else:
        raise AssertionError("unknown skill was accepted")


def test_validate_bodies_rejects_a_long_or_incomplete_body():
    good = {name: FROZEN[name] for name in NAMES}
    assert validate_bodies(good)["pick_and_place"].startswith("## When to Apply")
    bad = dict(good)
    bad["pick_and_place"] = "no headings\n"
    try:
        validate_bodies(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("missing headings were accepted")


def test_reject_rolls_descriptions_back_and_leaves_the_wiki():
    wiki = {"page": "original"}

    def runner(split, descriptions):
        heated = "heat" in descriptions["pick_heat_then_place"]
        hit = heated and split == "val"
        return [_row("a", "pick_heat_then_place",
                     [{"name": "pick_heat_then_place"}] if hit else [])]

    def propose_fn(arm, current, train_rows, history):
        assert arm == "nowiki"
        assert "traces/" not in json.dumps(history)
        return {"pick_heat_then_place": "still plain"}

    final, history = evolve_descriptions(
        arm="nowiki", start=DESC, iterations=1, baseline_f1=0.0,
        runner=runner, propose_fn=propose_fn, frozen=FROZEN)
    assert history[-1]["verdict"] == "reject"
    assert final == DESC
    assert wiki == {"page": "original"}


def test_wiki_edit_survives_a_rejected_description():
    wiki = {}

    def runner(split, descriptions):
        return [_row("a", "pick_heat_then_place", [])]

    def maintain_fn(train_rows, current):
        wiki["patterns/selection-missed-heat.md"] = "missed heat"

    def propose_fn(arm, current, train_rows, history):
        return {"pick_heat_then_place": "a different line that does not help"}

    final, history = evolve_descriptions(
        arm="wikisel", start=DESC, iterations=1, baseline_f1=0.5,
        runner=runner, propose_fn=propose_fn, maintain_fn=maintain_fn, frozen=FROZEN)
    assert history[-1]["verdict"] == "reject"
    assert final["pick_heat_then_place"] == DESC["pick_heat_then_place"]
    assert "missed heat" in wiki["patterns/selection-missed-heat.md"]


def test_arms_see_only_their_files():
    nowiki = proposer_files("nowiki", descriptions=DESC, metrics="f1 0.1\n", history="none\n",
                            wiki={"index.md": "secret trace"}, bodies_text="bodies")
    visible(nowiki, "nowiki")
    assert set(nowiki) == {"descriptions.md", "bodies.md", "train_metrics.md", "history.md"}
    assert "secret" not in json.dumps(nowiki)
    wiki = {"index.md": "# Index\n", "selection-impact.md": "impact\n"}
    wikisel = proposer_files("wikisel", descriptions=DESC, metrics="nope", history="nope", wiki=wiki)
    visible(wikisel, "wikisel")
    assert "traces/" not in json.dumps(list(wikisel))
    traces = maintainer_files({"t1.md": "Task: heat\n"}, wiki)
    assert "traces/t1.md" in traces and "wiki/index.md" in traces


def test_accept_requires_a_strict_gain():
    assert accept(0.2, 0.21)
    assert not accept(0.2, 0.2)


def test_render_round_trip_keeps_the_body():
    text = render_skill("pick_heat_then_place", "plain pick_heat_then_place", FROZEN["pick_heat_then_place"])
    assert "name: pick_heat_then_place" in text
    assert text.strip().endswith("do the task")


_OLD_STATIC = (
    "You are an expert agent operating in the ALFRED Embodied Environment. "
    "A load_skill tool lists skills by name and description. "
    "Before you act, call load_skill for the skill whose description matches this task. "
    "You may call it more than once. Then output exactly one admissible action "
    "inside <action> tags.\n"
)


def test_forced_prompt_is_the_old_static_text():
    assert _STATIC == _OLD_STATIC
    assert static_prompt("forced") == _STATIC
    assert NEUTRAL == (
        "You are an expert agent operating in the ALFRED Embodied Environment. "
        "Output exactly one admissible action inside <action> tags.\n"
    )


def test_neutral_first_turn_has_no_load_or_skill_outside_the_tool():
    prompt = first_turn("neutral", "put a mug on the desk", "You are in the room.", ["go to desk 1"])
    assert "load" not in prompt.lower()
    assert "skill" not in prompt.lower()
    tool = load_skill_tool(present(library(plain_descriptions(), 1, 0), "canonical"), "v2")
    assert "load" in tool["function"]["description"].lower()


def test_opaque_load_hides_canonical_names_and_scores_the_same():
    before = body_sha256()
    mapping = opaque_mapping()
    shown = present(library(plain_descriptions(), 4, 0), "opaque")
    opaque = next(key for key, name in mapping.items() if name == "pick_heat_then_place")
    skill = next(item for item in shown if item.name == opaque)
    text = skill.full()
    assert f"name: {opaque}" in text
    assert "name: pick_heat_then_place" not in text
    assert canonical_name(opaque, "opaque") == "pick_heat_then_place"
    index = load_skill_tool(shown, "v2")["function"]["description"]
    for name in NAMES:
        assert name not in index
    for key in mapping:
        assert key in index
    canonical = score_loads(
        [{"name": "pick_heat_then_place", "origin": "evolved"}], "pick_heat_then_place")
    renamed = score_loads(
        [{"name": canonical_name(skill.name, "opaque"), "origin": skill.origin}],
        "pick_heat_then_place")
    assert renamed == canonical
    assert body_sha256() == before


def test_wikisel_proposer_adds_only_maintainer_pages():
    wiki = {
        "index.md": "index\n",
        "log.md": "log\n",
        "patterns/selection-missed-heat.md": "heat\n",
        "catalog.md": "distractors\n",
        "bodies.md": "bodies copy\n",
        "descriptions.md": "desc copy\n",
        "selection-impact.md": "impact\n",
    }
    kwargs = dict(descriptions=DESC, metrics="f1 0.5\n", history="history\n",
                  wiki=wiki, bodies_text="bodies\n")
    nowiki = proposer_files("nowiki", **kwargs)
    wikisel = proposer_files("wikisel", **kwargs)
    extra = set(wikisel) - set(nowiki)
    assert extra == {"wiki/index.md", "wiki/log.md", "wiki/patterns/selection-missed-heat.md"}
    assert "catalog.md" not in json.dumps(list(nowiki))
    assert "catalog.md" not in json.dumps(list(wikisel))
    for name in nowiki:
        assert nowiki[name] == wikisel[name]
    assert proposer_prompt("wikisel") == (
        proposer_prompt("nowiki") + " The wiki/ folder holds pattern pages written from training load traces.")
    assert "You cannot change skill bodies." in proposer_prompt("nowiki")


def test_history_has_baseline_metrics_and_marks_skipped_iterations():
    row = _row("a", "pick_heat_then_place", [{"name": "pick_heat_then_place"}])
    skills = per_skill([row])

    def runner(split, descriptions):
        return [row]

    def propose_fn(arm, current, train_rows, history):
        assert history[0]["per_skill"]["pick_heat_then_place"]["recall"] == 1
        return {}

    _final, history = evolve_descriptions(
        arm="nowiki", start=DESC, iterations=1, baseline_f1=1.0,
        runner=runner, propose_fn=propose_fn, frozen=FROZEN, baseline_per_skill=skills)
    text = history_text(history)
    assert "iteration 0 baseline" in text
    assert "recall 1.000" in text
    assert "not evaluated" in text
    skipped = text.split("## iteration 1 unchanged", 1)[1]
    assert "recall 0.000" not in skipped
    assert best_accepted_f1([
        {"verdict": "baseline", "f1": 0.4},
        {"verdict": "accept", "f1": 0.7},
        {"verdict": "reject", "f1": 0.5},
    ]) == 0.7


def test_opaque_trace_names_the_six_skills_and_skips_unloaded_distractors():
    skills = library(plain_descriptions(), 5, 0)
    noise = [skill.name for skill in skills if skill.name not in NAMES]
    loaded = ["pick_heat_then_place", noise[0]]
    text = offered_index(plain_descriptions(), 5, 0, loaded, "opaque")
    for name in NAMES:
        assert name in text
    assert "skill_0" in text
    assert noise[0] in text
    for name in noise[1:]:
        assert name not in text
    assert "+ 5 distractor skills" in text
    traces = sample_traces(
        [{"task": "heat the apple", "relevant": "pick_heat_then_place", "loads": loaded,
          "relevant_loaded": True, "error": ""}],
        plain_descriptions(), 5, 0, 1, "opaque")
    assert "Loaded, in order: pick_heat_then_place, " + noise[0] in traces["t1.md"]


def test_role_usage_is_written(tmp_path: Path):
    def priced(model, messages, tools=None, usage=None, **_kwargs):
        if usage is not None:
            usage.add({"prompt_tokens": 4, "completion_tokens": 2, "cost": 0.01}, model)
        reads = sum(1 for message in messages if message.get("role") == "tool")
        if reads:
            return {"role": "assistant", "content": "", "tool_calls": [{
                "id": "fin", "type": "function",
                "function": {"name": "finish", "arguments": json.dumps(
                    {"descriptions": {"pick_and_place": "a new line"}})}}]}
        return {"role": "assistant", "content": "", "tool_calls": [{
            "id": "rd", "type": "function",
            "function": {"name": "read_file", "arguments": json.dumps({"path": "descriptions.md"})}}]}

    dest = tmp_path / "proposer"
    propose(dest, {"descriptions.md": "pick_and_place: old\n"}, chat_fn=priced, arm="nowiki")
    saved = json.loads((dest / "usage.json").read_text(encoding="utf-8"))
    assert saved["prompt_tokens"] >= 4 and saved["cost_usd"] > 0

    def maintainer_chat(model, messages, tools=None, usage=None, **_kwargs):
        if isinstance(usage, Usage) or usage is not None:
            usage.add({"prompt_tokens": 6, "completion_tokens": 3, "cost": 0.02}, model)
        return {"role": "assistant", "content": "", "tool_calls": [{
            "id": "fin", "type": "function",
            "function": {"name": "finish", "arguments": json.dumps({"proposal": {
                "create_patterns": [], "update_patterns": [],
                "update_index": "# Index\n", "append_log": "Reviewed traces.",
            }})}}]}

    role = tmp_path / "maintainer"
    maintain(role, {"wiki/index.md": "# Index\n", "traces/t1.md": "Task: heat\n"}, chat_fn=maintainer_chat)
    role_usage = json.loads((role / "runtime" / "usage.json").read_text(encoding="utf-8"))
    assert role_usage["prompt_tokens"] >= 6 and role_usage["cost_usd"] > 0
    assert "traces" in _MAINTAINER
