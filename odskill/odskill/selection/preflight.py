"""Write the phase-0 pilot check and the phase-2 preflight. No model calls.

    python -m odskill.selection.preflight
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from odskill.alfworld import Session, data_root, task_description
from odskill.selection.episode import first_turn
from odskill.selection.evolve_desc import games_for, history_text, offered_index, sample_traces
from odskill.selection.library import NAMES, library, opaque_mapping, plain_descriptions, present
from odskill.selection.metrics import aggregate, per_skill
from odskill.selection.roles_desc import _MAINTAINER, proposer_files, proposer_prompt
from odskill.skills import load_skill_tool

PAPER = Path(__file__).resolve().parents[3]
RUNS = Path.home() / "odskill-runs" / "selection"
RESULTS = PAPER / "results"
PREFLIGHT = PAPER / "preflight"
CHECKS = (
    ("forced prompt is byte-identical to the old static text",
     "test_forced_prompt_is_the_old_static_text"),
    ("neutral first-turn prompt has no load or skill outside the tool",
     "test_neutral_first_turn_has_no_load_or_skill_outside_the_tool"),
    ("opaque load_skill returns the body, hides canonical names, and scores the same",
     "test_opaque_load_hides_canonical_names_and_scores_the_same"),
    ("wikisel proposer files minus nowiki are index, log, and patterns only",
     "test_wikisel_proposer_adds_only_maintainer_pages"),
    ("history.md has baseline per-skill metrics and says not evaluated",
     "test_history_has_baseline_metrics_and_marks_skipped_iterations"),
    ("final_f1 is the best accepted val F1 when the history ends in a reject",
     "test_history_has_baseline_metrics_and_marks_skipped_iterations"),
    ("an opaque trace shows both names and skips unloaded distractors",
     "test_opaque_trace_names_the_six_skills_and_skips_unloaded_distractors"),
    ("proposer and maintainer usage is written to disk",
     "test_role_usage_is_written"),
    ("bodies never change",
     "test_descriptions_can_change_and_bodies_cannot"),
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_pilot() -> None:
    print("phase 0 projected cost $0", flush=True)
    lines = [
        "# Pilot check",
        "",
        "Projected API cost: $0. Actual API cost: $0.",
        "Recomputed with `odskill.selection.metrics.aggregate` from the raw rollout files.",
        "Aggregate drops a row when its `error` field is non-empty. The error count is those rows.",
        "Val, 2 passes, noise shuffle seed 0. Episodes is the raw row count.",
        "",
        "| arm | noise_k | recall | precision | F1 | wrong-type rate | episodes | errored episodes |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for arm in ("plain", "directive"):
        for noise in (100, 20):
            path = RUNS / f"{arm}-k{noise}-s0" / "rollouts.jsonl"
            rows = _rows(path)
            summary = aggregate(rows)
            errors = sum(1 for row in rows if row.get("error"))
            lines.append(
                f"| {arm} | {noise} | {summary['recall']:.6f} | {summary['precision']:.6f} | "
                f"{summary['f1']:.6f} | {summary['wrong_type_load_rate']:.6f} | {len(rows)} | {errors} |"
            )
    lines.append("")
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "pilot_check.md").write_text("\n".join(lines), encoding="utf-8")
    print("phase 0 actual cost $0", flush=True)


def write_mapping() -> dict[str, str]:
    mapping = opaque_mapping()
    payload = {
        "seed": 0,
        "opaque_to_canonical": mapping,
        "canonical_to_opaque": {canonical: opaque for opaque, canonical in mapping.items()},
    }
    (RESULTS / "opaque_mapping.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return mapping


def _opening() -> tuple[str, str, list[str]]:
    game = games_for("val", 1, allow_test=False)[0]
    root = data_root()
    task = task_description(root, game["uid"])
    log = PREFLIGHT / "reset-worker.log"
    session = Session(log)
    try:
        state = session.request({"op": "reset", "game": str(root / game["uid"]), "max_steps": 50})
    finally:
        session.close()
    observation = str(state.get("observation") or "")
    admissible = [str(item) for item in state.get("admissible_actions") or []]
    return task, observation, admissible


def write_exp1(task: str, observation: str, admissible: list[str]) -> None:
    descriptions = plain_descriptions()
    skills = present(library(descriptions, 100, 0), "canonical")
    opaque_skills = present(library(descriptions, 100, 0), "opaque")
    views = {
        "forced-canonical": ("forced", skills),
        "neutral-canonical": ("neutral", skills),
        "neutral-opaque": ("neutral", opaque_skills),
    }
    out = PREFLIGHT / "exp1"
    out.mkdir(parents=True, exist_ok=True)
    for name, (agent_prompt, shown) in views.items():
        tool = load_skill_tool(shown, "v2")["function"]["description"]
        prompt = first_turn(agent_prompt, task, observation, admissible)
        text = (
            f"skills_in_index {len(shown)}\n"
            "noise_k 100\n"
            "seed 0\n"
            "descriptions plain\n\n"
            "===== first-turn user text =====\n"
            f"{prompt}\n"
            "===== load_skill tool description =====\n"
            f"{tool}"
        )
        (out / f"{name}.txt").write_text(text, encoding="utf-8")


def _history() -> tuple[list[dict], list[dict]]:
    descriptions = plain_descriptions()
    row = {
        "uid": "synthetic", "relevant": "pick_heat_then_place", "task_type": "pick_heat_then_place",
        "loads": ["pick_heat_then_place"], "load_count": 1, "relevant_load_count": 1,
        "relevant_loaded": True, "noise_loads": 0, "wrong_type_loads": 0, "loaded_any": True,
        "pass": 0, "error": "",
    }
    skills = per_skill([row])
    baseline = {"iteration": 0, "verdict": "baseline", "f1": aggregate([row])["f1"],
                "descriptions": dict(descriptions), "per_skill": skills}
    edited = dict(descriptions)
    edited["pick_heat_then_place"] = "Procedure for heating an object in a microwave, then putting it somewhere."
    accepted = {"iteration": 1, "verdict": "accept", "f1": 1.0,
                "descriptions": edited, "per_skill": skills}
    return [baseline], [baseline, accepted]


def _listing(files: dict[str, str]) -> str:
    lines = []
    for name in sorted(files):
        text = files[name]
        lines.append(f"{name}  bytes={len(text.encode())}  sha256={_sha(text)}")
    return "\n".join(lines)


def write_exp2() -> None:
    descriptions = plain_descriptions()
    bodies = "\n\n".join(f"# {name}\n(frozen body omitted from this synthetic listing header)" for name in NAMES)
    # The staged bodies are the real frozen text, not the header above.
    from odskill.selection.roles_desc import _bodies_text
    bodies = _bodies_text()
    metrics = "recall 1.000\nprecision 1.000\nf1 1.000\nnoise_load_rate 0.000\nwrong_type_load_rate 0.000\n"
    first, second = _history()
    wiki_it1 = {
        "index.md": "# Index\n\n- selection-missed-heat: a heat task loaded another skill.\n",
        "log.md": "# Evolution log\n\nReviewed the first train batch.\n",
        "patterns/selection-missed-heat.md": "A heat task loaded a different type skill.\n",
        "catalog.md": "must not be staged\n",
        "bodies.md": "must not be staged\n",
        "descriptions.md": "must not be staged\n",
        "selection-impact.md": "must not be staged\n",
    }
    wiki_it2 = dict(wiki_it1)
    wiki_it2["patterns/selection-missed-two.md"] = "A two-object task loaded one object.\n"
    wiki_it2["index.md"] = wiki_it1["index.md"] + "- selection-missed-two: count cue missed.\n"
    noise = [skill.name for skill in library(descriptions, 5, 0) if skill.name not in NAMES]
    trace_row = [{
        "task": "heat the apple and put it on the table",
        "relevant": "pick_heat_then_place",
        "loads": ["pick_heat_then_place", noise[0]],
        "relevant_loaded": True,
        "error": "",
    }]
    traces = {
        names: sample_traces(trace_row, descriptions, 5, 0, 1, names)["t1.md"]
        for names in ("canonical", "opaque")
    }
    # offered_index is what the trace embeds; keep the import used.
    assert "Offered index" in traces["canonical"] and offered_index(
        descriptions, 5, 0, trace_row[0]["loads"], "canonical")
    iterations = {1: (history_text(first), wiki_it1), 2: (history_text(second), wiki_it2)}
    for arm in ("nowiki", "wikisel"):
        chunks = [
            "Synthetic iteration-1 and iteration-2 proposer inputs. No API call.",
            "The common files are built once and staged to both arms.",
            "",
            "===== proposer prompt =====",
            proposer_prompt(arm),
            "",
            "===== maintainer prompt =====",
            _MAINTAINER,
            "",
            "===== history.md at iteration 1 =====",
            iterations[1][0],
        ]
        for iteration, (history, wiki) in iterations.items():
            files = proposer_files(
                arm, descriptions=descriptions if iteration == 1 else second[-1]["descriptions"],
                metrics=metrics, history=history, wiki=wiki, bodies_text=bodies)
            chunks.append(f"===== iteration {iteration} staged files =====")
            chunks.append(_listing(files))
            chunks.append("")
        chunks.append("===== staged trace, canonical names =====")
        chunks.append(traces["canonical"])
        chunks.append("===== staged trace, opaque names =====")
        chunks.append(traces["opaque"])
        dest = PREFLIGHT / "exp2" / arm
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "staged_files.txt").write_text("\n".join(chunks), encoding="utf-8")


def write_checks(pytest_output: str) -> None:
    lines = ["# Offline checks", "", "Projected API cost: $0. Actual API cost: $0.", ""]
    for label, test_name in CHECKS:
        status = "pass" if f"{test_name} PASSED" in pytest_output else "fail"
        lines.append(f"- {status}: {label} (`{test_name}`)")
    lines.append("")
    (PREFLIGHT / "checks.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    print("phase 1 projected cost $0 (code and tests, no API)", flush=True)
    print("phase 2 projected cost $0", flush=True)
    write_pilot()
    write_mapping()
    task, observation, admissible = _opening()
    write_exp1(task, observation, admissible)
    write_exp2()
    print("phase 2 actual cost $0", flush=True)
    print(f"wrote {RESULTS} and {PREFLIGHT}", flush=True)


if __name__ == "__main__":
    main()
