"""Optimize the six skill descriptions. Bodies, noise, and the index template stay fixed.

    python -m odskill.selection.evolve_desc --freeze-bodies
    python -m odskill.selection.evolve_desc --smoke --run-dir ~/odskill-runs/selection/smoke --budget 1
"""

from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path

from odskill.llm import BudgetExceeded, as_text, chat, load_env, spent
from odskill.selection.episode import run_games
from odskill.selection.library import (
    NAMES, ROOT, apply_descriptions, bodies, body_sha256, directive_descriptions,
    plain_descriptions, skill_text, write_bodies,
)
from odskill.selection.metrics import aggregate, per_skill
from odskill.selection.roles_desc import (
    SONNET, apply_wiki, maintain, maintainer_files, propose, proposer_files, visible,
)

HAIKU = "anthropic/claude-haiku-5.5"
PAPER = Path(__file__).resolve().parents[3]
SPLIT_DIR = PAPER / "odskill" / "splits" / "alfworld_v1"
_ASK = """Write six ALFWorld skill bodies from general household-task knowledge.
Return one JSON object and nothing else. Keys, exactly:
look_at_obj_in_light, pick_and_place, pick_clean_then_place, pick_cool_then_place, pick_heat_then_place, pick_two_obj_and_place.
Each value is markdown of at most 40 lines with these headings, each on its own line:
## When to Apply
## When NOT to Apply
## Instructions
No YAML frontmatter. No game ids, no file paths, no scores.
look_at_obj_in_light: find the object, pick it up, find a lamp, turn the lamp on, then look at the object.
pick_and_place: go to the object, open a closed receptacle, take it, go to the destination, put it. No heat, cool, or clean.
pick_clean_then_place: take the object, clean it at a sinkbasin, then place it.
pick_cool_then_place: take the object, cool it in a fridge, then place it.
pick_heat_then_place: take the object, heat it in a microwave, then place it.
pick_two_obj_and_place: find two objects of the requested kind, take both, and place both at the destination.
Tell the agent to copy admissible actions exactly and not to repeat an action that just failed.
"""


def accept(old_f1: float, new_f1: float) -> bool:
    return new_f1 > old_f1


def games_for(split: str, n: int | None, *, allow_test: bool) -> list[dict]:
    if split == "test" and not allow_test:
        raise SystemExit("refusing the test split without --i-understand-this-is-the-test-split")
    rows = json.loads((SPLIT_DIR / f"{split}.json").read_text(encoding="utf-8"))
    if n is not None:
        rows = rows[:n]
    for row in rows:
        row["split"] = split
    return rows


def metrics_text(rows: list[dict]) -> str:
    total = aggregate(rows)
    lines = [
        f"recall {total['recall']:.3f}",
        f"precision {total['precision']:.3f}",
        f"f1 {total['f1']:.3f}",
        f"noise_load_rate {total['noise_load_rate']:.3f}",
        f"wrong_type_load_rate {total['wrong_type_load_rate']:.3f}",
        "",
    ]
    for name, item in per_skill(rows).items():
        lines.append(
            f"{name}: recall {item['recall']:.3f} precision {item['precision']:.3f} "
            f"loads {item['loads']} games {item['games']}")
    return "\n".join(lines) + "\n"


def history_text(history: list[dict]) -> str:
    """Every candidate. Unevaluated iterations say so instead of printing zero metrics."""
    lines = ["# Candidate descriptions", ""]
    for item in history:
        lines.append(f"## iteration {item['iteration']} {item['verdict']}")
        for name in NAMES:
            lines.append(f"- {name}: {item['descriptions'][name]}")
        if item["verdict"] in ("unchanged", "invalid"):
            lines.append("not evaluated")
        else:
            lines.append(f"val_f1 {item['f1']:.3f}")
            skills = item.get("per_skill") or {}
            for name in NAMES:
                stat = skills.get(name) or {}
                lines.append(
                    f"- {name} — recall {stat.get('recall', 0):.3f} "
                    f"precision {stat.get('precision', 0):.3f}")
        lines.append("")
    return "\n".join(lines)


def impact_text(history: list[dict]) -> str:
    return history_text(history)


def best_accepted_f1(history: list[dict]) -> float:
    """The F1 of the descriptions still in force. A rejected candidate does not count."""
    chosen = [float(item["f1"]) for item in history if item.get("verdict") in ("baseline", "accept")]
    if not chosen:
        raise ValueError("history has no accepted val F1")
    return max(chosen)


def offered_index(descriptions: dict[str, str], noise_k: int, seed: int,
                  loads: list[str], names: str = "canonical") -> str:
    """The six type skills as the executor saw them, then any distractor this episode loaded."""
    from odskill.selection.library import library, opaque_mapping
    skills = library(descriptions, noise_k, seed)
    shown_as = {canonical: opaque for opaque, canonical in opaque_mapping().items()}
    loaded = set(loads or [])
    lines = []
    distractors = 0
    for skill in skills:
        if skill.name not in NAMES:
            distractors += 1
            continue
        if names == "opaque":
            lines.append(f"- {shown_as[skill.name]} ({skill.name}): {skill.description}")
        else:
            lines.append(f"- {skill.name}: {skill.description}")
    for skill in skills:
        if skill.name not in NAMES and skill.name in loaded:
            lines.append(f"- {skill.name}: {skill.description}")
    lines.append(f"+ {distractors} distractor skills")
    return "\n".join(lines) + "\n"


def sample_traces(rows: list[dict], descriptions: dict[str, str], noise_k: int, seed: int,
                  n: int, names: str = "canonical") -> dict[str, str]:
    usable = [row for row in rows if not row.get("error")]
    misses = [row for row in usable if not row["relevant_loaded"]]
    hits = [row for row in usable if row["relevant_loaded"]]
    rng = random.Random(seed)
    rng.shuffle(misses)
    rng.shuffle(hits)
    chosen = (misses + hits)[:n]
    traces = {}
    for i, row in enumerate(chosen, start=1):
        loaded_names = list(row.get("loads") or [])
        loaded = ", ".join(loaded_names) or "(none)"
        index = offered_index(descriptions, noise_k, seed, loaded_names, names)
        traces[f"t{i}.md"] = (
            f"Task: {row.get('task', '')}\n"
            f"Ground-truth skill: {row['relevant']}\n"
            f"Loaded, in order: {loaded}\n"
            f"Relevant loaded: {'yes' if row['relevant_loaded'] else 'no'}\n\n"
            f"Offered index:\n{index}\n"
        )
    return traces


def evolve_descriptions(*, arm: str, start: dict[str, str], iterations: int, baseline_f1: float,
                        runner, propose_fn, maintain_fn=None,
                        frozen: dict[str, str] | None = None,
                        baseline_per_skill: dict | None = None) -> tuple[dict, list[dict]]:
    """Accept a candidate only when val F1 rises. The caller owns the wiki and does not roll it back."""
    current = dict(start)
    best_f1 = baseline_f1
    history = [{"iteration": 0, "verdict": "baseline", "f1": baseline_f1, "descriptions": dict(start),
                "per_skill": dict(baseline_per_skill or {})}]
    for iteration in range(1, iterations + 1):
        train_rows = runner("train", current)
        if arm == "wikisel" and maintain_fn is not None:
            maintain_fn(train_rows, current)
        updates = propose_fn(arm, current, train_rows, history) or {}
        try:
            candidate = apply_descriptions(current, updates, frozen)
        except (KeyError, ValueError, RuntimeError) as exc:
            history.append({"iteration": iteration, "verdict": "invalid", "f1": best_f1,
                            "descriptions": dict(current), "per_skill": {}, "error": str(exc)})
            continue
        if candidate == current:
            history.append({"iteration": iteration, "verdict": "unchanged", "f1": best_f1,
                            "descriptions": dict(current), "per_skill": {}})
            continue
        val_rows = runner("val", candidate)
        new_f1 = aggregate(val_rows)["f1"]
        verdict = "accept" if accept(best_f1, new_f1) else "reject"
        history.append({"iteration": iteration, "verdict": verdict, "f1": new_f1,
                        "descriptions": dict(candidate), "per_skill": per_skill(val_rows)})
        if verdict == "accept":
            current = candidate
            best_f1 = new_f1
    return current, history


def _wiki_read(wiki: Path) -> dict[str, str]:
    if not wiki.is_dir():
        return {}
    return {str(path.relative_to(wiki)): path.read_text(encoding="utf-8")
            for path in sorted(wiki.rglob("*")) if path.is_file()}


def _init_wiki(wiki: Path, descriptions: dict[str, str]) -> None:
    wiki.mkdir(parents=True, exist_ok=True)
    (wiki / "index.md").write_text("# Index\n\nNo selection patterns yet.\n", encoding="utf-8")
    (wiki / "bodies.md").write_text(
        "\n\n".join(f"# {name}\n{bodies()[name].strip()}" for name in NAMES) + "\n", encoding="utf-8")
    (wiki / "descriptions.md").write_text(
        "\n".join(f"{name}: {descriptions[name]}" for name in NAMES) + "\n", encoding="utf-8")
    (wiki / "selection-impact.md").write_text(
        "# Selection impact\n\nHarness record. The maintainer does not edit this file.\n",
        encoding="utf-8")


def _sync_wiki_notes(wiki: Path, descriptions: dict[str, str],
                    history: list[dict] | None = None) -> None:
    """Disk record only. The proposer is not staged these pages."""
    (wiki / "descriptions.md").write_text(
        "\n".join(f"{name}: {descriptions[name]}" for name in NAMES) + "\n", encoding="utf-8")
    if history is not None:
        (wiki / "selection-impact.md").write_text(impact_text(history), encoding="utf-8")


def freeze_bodies() -> str:
    if (ROOT / "bodies.json").is_file():
        raise SystemExit("bodies are already frozen")
    load_env(PAPER / ".env")
    message = chat(SONNET, [{"role": "user", "content": _ASK}], reasoning_effort="low", max_tokens=8000)
    text = as_text(message.get("content"))
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise SystemExit("Sonnet did not return JSON")
    data = json.loads(text[start:end + 1])
    digest = write_bodies(data)
    print("froze bodies", digest)
    return digest


def _live_runner(root: Path, cfg: dict):
    def runner(split: str, descriptions: dict[str, str], label: str) -> list[dict]:
        rows = games_for(split, cfg["train_n"] if split == "train" else cfg["val_n"], allow_test=False)
        dest = root / f"{label}-{split}.jsonl"
        return run_games(rows, model=cfg["executor"], descriptions=descriptions, noise_k=cfg["noise_k"],
                         seed=cfg["seed"], dest=dest, work=root / "attempts" / label, workers=cfg["workers"],
                         split=split, agent_prompt=cfg["agent_prompt"], names=cfg["names"])
    return runner


def run_evolution(root: Path, cfg: dict, baseline_rows: list[dict] | None = None) -> dict:
    if cfg.get("split") == "test":
        raise SystemExit("run_evolution refuses split=test")
    root.mkdir(parents=True, exist_ok=True)
    digest = body_sha256()
    start = plain_descriptions()
    wiki = root / "wiki"
    if cfg["arm"] == "wikisel":
        _init_wiki(wiki, start)
    held = {"text": ""}

    def runner(split: str, descriptions: dict[str, str]) -> list[dict]:
        label = held["text"] or split
        return _live_runner(root, cfg)(split, descriptions, label)

    def propose_fn(arm, current, train_rows, history):
        if arm == "wikisel":
            _sync_wiki_notes(wiki, current, history)
        files = proposer_files(
            arm, descriptions=current, metrics=metrics_text(train_rows),
            history=history_text(history), wiki=_wiki_read(wiki))
        visible(files, arm)
        return propose(root / "roles" / held["text"] / "proposer", files,
                       model=cfg["optimizer"], arm=arm)

    def maintain_fn(train_rows, current):
        _sync_wiki_notes(wiki, current)
        traces = sample_traces(train_rows, current, cfg["noise_k"], cfg["seed"], 8, cfg["names"])
        before = (wiki / "patterns").exists()
        try:
            updated = maintain(root / "roles" / held["text"] / "maintainer",
                               maintainer_files(traces, _wiki_read(wiki)), model=cfg["optimizer"])
            apply_wiki(wiki, updated)
        except (RuntimeError, OSError, ValueError, KeyError) as exc:
            print(f"maintainer_error {exc}", flush=True)
        if not before:
            pass
        # The wiki is whatever apply_wiki wrote. A later reject does not delete it.

    if baseline_rows is None:
        held["text"] = "baseline"
        base_rows = runner("val", start)
    else:
        base_rows = baseline_rows
    base_f1 = aggregate(base_rows)["f1"]
    base_skills = per_skill(base_rows)
    (root / "baseline_metrics.json").write_text(json.dumps(aggregate(base_rows), indent=2) + "\n")

    def tagged_runner(split, descriptions):
        return runner(split, descriptions)

    # Label each iteration's files by wrapping runner.
    state = {"i": 0}

    def iter_runner(split, descriptions):
        held["text"] = f"it{state['i']}-{split}"
        return _live_runner(root, cfg)(split, descriptions, held["text"])

    def stepping_maintain(train_rows, current):
        held["text"] = f"it{state['i']}"
        maintain_fn(train_rows, current)

    def stepping_propose(arm, current, train_rows, history):
        held["text"] = f"it{state['i']}"
        return propose_fn(arm, current, train_rows, history)

    original_runner = iter_runner

    def counting_runner(split, descriptions):
        if split == "train":
            state["i"] += 1
        return original_runner(split, descriptions)

    final, history = evolve_descriptions(
        arm=cfg["arm"], start=start, iterations=cfg["iterations"], baseline_f1=base_f1,
        runner=counting_runner, propose_fn=stepping_propose,
        maintain_fn=stepping_maintain if cfg["arm"] == "wikisel" else None,
        baseline_per_skill=base_skills)
    if cfg["arm"] == "wikisel":
        _sync_wiki_notes(wiki, final, history)
    (root / "history.json").write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")
    (root / "descriptions.json").write_text(json.dumps(final, indent=2) + "\n", encoding="utf-8")
    (root / "manifest.json").write_text(json.dumps({
        **cfg, "body_sha256": digest, "final_f1": best_accepted_f1(history),
        "body_sha256_after": body_sha256(),
    }, indent=2) + "\n", encoding="utf-8")
    if digest != body_sha256():
        raise RuntimeError("frozen bodies changed during evolution")
    skill_text(final)
    return {"descriptions": final, "history": history, "baseline_f1": base_f1}


def run_eval(root: Path, cfg: dict, descriptions: dict[str, str]) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for pass_i in range(cfg["passes"]):
        games = games_for(cfg["split"], cfg["val_n"] if cfg["split"] != "test" else None,
                          allow_test=cfg["allow_test"])
        if cfg["split"] == "train":
            games = games_for("train", cfg["train_n"], allow_test=False)
        got = run_games(games, model=cfg["executor"], descriptions=descriptions, noise_k=cfg["noise_k"],
                        seed=cfg["seed"], dest=root / "rollouts.jsonl", work=root / "attempts",
                        workers=cfg["workers"], split=cfg["split"], pass_i=pass_i, full=cfg["full"],
                        agent_prompt=cfg["agent_prompt"], names=cfg["names"])
        rows = got
    summary = aggregate(rows)
    summary["by_task_type"] = {}
    summary["model"] = cfg["executor"]
    summary["arm"] = cfg["arm"]
    summary["agent_prompt"] = cfg["agent_prompt"]
    summary["names"] = cfg["names"]
    (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (root / "manifest.json").write_text(json.dumps({
        **cfg, "body_sha256": body_sha256(),
    }, indent=2) + "\n", encoding="utf-8")
    return summary


def _cfg(args) -> dict:
    return {
        "arm": args.arm, "noise_k": args.noise_k, "seed": args.seed, "iterations": args.iterations,
        "train_n": args.train_n, "val_n": args.val_n, "passes": args.passes, "workers": args.workers,
        "executor": args.executor, "optimizer": SONNET, "split": args.split, "full": args.full,
        "allow_test": args.i_understand_this_is_the_test_split, "effort": "low",
        "agent_prompt": args.agent_prompt, "names": args.names,
        "descriptions_file": str(args.descriptions or ""),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze-bodies", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--arm", default="wikisel", choices=("plain", "directive", "nowiki", "wikisel"))
    parser.add_argument("--noise-k", type=int, default=100)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--iterations", type=int, default=6)
    parser.add_argument("--train-n", type=int, default=120)
    parser.add_argument("--val-n", type=int, default=60)
    parser.add_argument("--passes", type=int, default=1)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--budget", type=float, default=0.0)
    parser.add_argument("--run-dir", type=Path, default=None)
    parser.add_argument("--split", default="val")
    parser.add_argument("--executor", default=HAIKU)
    parser.add_argument("--agent-prompt", default="forced", choices=("forced", "neutral"))
    parser.add_argument("--names", default="canonical", choices=("canonical", "opaque"))
    parser.add_argument("--descriptions", type=Path, default=None,
                        help="JSON of the six descriptions. Overrides plain/directive.")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--i-understand-this-is-the-test-split", action="store_true")
    args = parser.parse_args()
    if args.freeze_bodies:
        freeze_bodies()
        return
    if args.budget <= 0 or args.run_dir is None:
        raise SystemExit("need --budget and --run-dir")
    if args.smoke:
        args.arm = "wikisel"
        args.noise_k = 100
        args.seed = 0
        args.iterations = 1
        args.train_n = 20
        args.val_n = 20
        args.passes = 1
    load_env(PAPER / ".env")
    os.environ["ODSKILL_BUDGET_USD"] = str(args.budget)
    cfg = _cfg(args)
    root = args.run_dir.expanduser()
    if args.descriptions:
        loaded = json.loads(args.descriptions.expanduser().read_text(encoding="utf-8"))
        missing = [name for name in NAMES if name not in loaded]
        if missing:
            raise SystemExit("descriptions missing " + ", ".join(missing))
        descriptions = {name: str(loaded[name]) for name in NAMES}
    else:
        descriptions = directive_descriptions() if args.arm == "directive" else plain_descriptions()
    # A description file or the test split is an evaluation, even when --arm is nowiki or wikisel.
    evaluate = args.descriptions is not None or args.split == "test"
    evolve = not evaluate and args.arm in ("nowiki", "wikisel") and not args.full
    print(f"mode {'evolve' if evolve else 'eval'} arm={args.arm} split={args.split}", flush=True)
    try:
        if evolve:
            result = run_evolution(root, cfg)
            descriptions = result["descriptions"]
        else:
            run_eval(root, cfg, descriptions)
    except BudgetExceeded:
        print(f"budget stop spent=${spent():.4f}", flush=True)
    if args.smoke:
        rows = []
        for path in root.rglob("*.jsonl"):
            if path.name.endswith(".jsonl") and "worker" not in path.name:
                for line in path.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        rows.append(json.loads(line))
        episodes = [row for row in rows if "relevant" in row]
        cost = sum(float(row.get("cost_usd") or 0) for row in episodes)
        each = cost / len(episodes) if episodes else 0.0
        loads = sum(int(row.get("load_count") or 0) for row in episodes)
        print(f"cost_per_episode={each:.6f} n={len(episodes)} loads={loads} "
              f"spent=${spent():.4f}", flush=True)
        if each > 0.003:
            print("STOP cost per load-only episode is above $0.003", flush=True)


if __name__ == "__main__":
    main()
