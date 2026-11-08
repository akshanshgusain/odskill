from odskill.alfworld import (
    SKILL_SECTION_HEADER, _paper_prompt, build_splits, parse_action, procedure_text,
    skill_section, task_type_of)
from odskill.skills import parse

TYPES = (
    "look_at_obj_in_light", "pick_and_place_simple", "pick_clean_then_place_in_recep",
    "pick_cool_then_place_in_recep", "pick_heat_then_place_in_recep", "pick_two_obj_and_place",
)


def _games(n_per_type: int, split: str) -> list[str]:
    rows = []
    for name in TYPES:
        for index in range(n_per_type):
            rows.append(f"{split}/{name}-Obj-{index}/trial/game.tw-pddl")
    return rows


def test_task_type_matches_the_longest_prefix():
    uid = "valid_seen/pick_and_place_simple-Book-None-SideTable-329/trial/game.tw-pddl"
    assert task_type_of(uid) == "pick_and_place_simple"


def test_splits_are_disjoint_and_val_is_balanced():
    games = {
        "train": _games(40, "train"),
        "valid_seen": _games(20, "valid_seen"),
        "valid_unseen": _games(10, "valid_unseen"),
    }
    splits = build_splits(games, seed=0, train_n=120, val_n=60)
    assert len(splits["train"]) == 120
    assert len(splits["val"]) == 60
    assert len(splits["test"]) == 60
    assert set(splits["train"]).isdisjoint(splits["val"])
    assert set(splits["val"]).isdisjoint(splits["test"])
    counts = {}
    for uid in splits["val"]:
        counts[task_type_of(uid)] = counts.get(task_type_of(uid), 0) + 1
    assert set(counts) == set(TYPES)
    assert max(counts.values()) - min(counts.values()) <= 1


def test_procedure_skill_has_the_three_sections():
    skill = parse(procedure_text())[0]
    body = skill.body.lower()
    assert "go to a location" in body
    assert "microwave" in body and "fridge" in body and "sinkbasin" in body
    assert "do not repeat" in body


def test_skill_is_injected_and_the_prompt_has_no_bash_tool():
    section = skill_section(procedure_text())
    assert section.startswith(SKILL_SECTION_HEADER)
    prompt = _paper_prompt("put the book on the table", section, [], "you are in a kitchen",
                           ["go to fridge", "look"])
    assert SKILL_SECTION_HEADER in prompt
    assert "go to fridge" in prompt
    assert "bash" not in prompt.lower()
    assert "load_skill" not in prompt


def test_parse_accepts_the_tagged_action_and_rejects_the_rest():
    text = "<think>go</think>\n<action>go to fridge</action>"
    action, ok = parse_action(text, ["look", "go to fridge"])
    assert (action, ok) == ("go to fridge", True)
    action, ok = parse_action("open fridge", ["look", "go to fridge"])
    assert ok is False
    action, ok = parse_action("  Go   to   fridge ", ["go to fridge"])
    assert (action, ok) == ("go to fridge", True)
