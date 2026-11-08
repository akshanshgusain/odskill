"""WikiSkill evolution on SpreadSheetBench, with four deployment arms.

    python -m odskill.evolve --arm wikisel --run-dir ~/odskill-runs/<name> \
        --noise-k 20 --iterations 2 --train-n 10 --val-n 10 --seed 0 --budget 1.0
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path

from wikiskill import engine
from wikiskill.benchmarks.spreadsheet import load_cases
from wikiskill.jsonl import read_jsonl
from wikiskill.paper_alignment.agents import PaperAgents, paper_prompts

from .llm import load_env, spent
from .noise import LIBRARY
from .roles import invoke
from .skills import parse
from .spreadsheet import rollout_case

PAPER = Path(__file__).resolve().parents[2]
PROMPTS = PAPER / "odskill/prompts"
DATA = PAPER / "data/spreadsheet/spreadsheetbench_verified_400"
SPLITS = PAPER / "wikiskill/src/wikiskill/resources/spreadsheet/id_split"
MODEL = "anthropic/claude-haiku-5.5"
# Same task description the upstream spreadsheet study binds into the paper prompts.
TASK = "spreadsheet manipulation tasks with isolated bash"
ARMS = ("all", "od", "od_aware", "wikisel")
FEEDBACK_FIELDS = ("fail_reason", "matched_cells", "total_cells", "has_output_workbook")
EFFORT = "low"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def ondemand_addendum() -> str:
    return (PROMPTS / "ondemand_addendum.md").read_text(encoding="utf-8")


def selection_addendum() -> str:
    return (PROMPTS / "selection_addendum.md").read_text(encoding="utf-8")


def _append(prompt: str, extra: str) -> str:
    return prompt.rstrip() + "\n\n" + extra.strip() + "\n"


def prompts_for(arm: str) -> dict[str, str]:
    """Paper prompts, plus the on-demand addendum where that arm allows it."""
    if arm not in ARMS:
        raise ValueError("unknown arm: " + arm)
    prompts = paper_prompts(TASK)
    if arm in ("od_aware", "wikisel"):
        extra = ondemand_addendum()
        prompts = {name: _append(text, extra) for name, text in prompts.items()}
    if arm == "wikisel":
        prompts["maintainer.md"] = _append(prompts["maintainer.md"], selection_addendum())
    return prompts


def train_feedback(row: dict, *, selection: bool = False) -> dict:
    """TRAIN-only harness feedback. Names and counts; never gold or answer text."""
    if row.get("split") not in (None, "train"):
        raise ValueError("TRAIN feedback only")
    out = {
        "fail_reason": row.get("fail_reason") or "",
        "matched_cells": int(row.get("matched_cells") or 0),
        "total_cells": int(row.get("total_cells") or 0),
        "has_output_workbook": bool(row.get("has_output_workbook", row.get("has_final_answer_tag"))),
    }
    if not selection:
        return out
    offered = [s["name"] for s in row.get("skill_set") or [] if s.get("origin") == "evolved"]
    loaded = []
    for item in row.get("loaded_skills") or []:
        if isinstance(item, str):
            loaded.append({"name": item, "origin": "evolved"})
        else:
            loaded.append({"name": item.get("name", ""), "origin": item.get("origin", "evolved")})
    loaded_names = {item["name"] for item in loaded}
    out["skill_selection"] = {
        "evolved_offered": offered,
        "noise_offered": sum(1 for s in row.get("skill_set") or [] if s.get("origin") == "noise"),
        "loaded": loaded,
        "evolved_not_loaded": [name for name in offered if name not in loaded_names],
    }
    return out


def _val_load_rates(root: Path, iteration: int) -> dict[str, tuple[int, int]]:
    path = root / f"iterations/{iteration:03d}/val/outcomes.jsonl"
    if not path.is_file():
        return {}
    rows = read_jsonl(path)
    hits: dict[str, int] = {}
    order: list[str] = []
    for row in rows:
        loaded = {item["name"] if isinstance(item, dict) else item for item in row.get("loaded_skills") or []}
        seen: set[str] = set()
        for skill in row.get("skill_set") or []:
            if skill.get("origin") != "evolved" or skill["name"] in seen:
                continue
            seen.add(skill["name"])
            hits.setdefault(skill["name"], 0)
            if skill["name"] not in order:
                order.append(skill["name"])
            if skill["name"] in loaded:
                hits[skill["name"]] += 1
    return {name: (hits[name], len(rows)) for name in order}


def _candidate_descriptions(root: Path, iteration: int) -> dict[str, str]:
    path = root / f"iterations/{iteration:03d}/proposal.json"
    if not path.is_file():
        return {}
    text = json.loads(path.read_text(encoding="utf-8")).get("skill_md") or ""
    return {skill.name: " ".join(skill.description.split()) for skill in parse(text)}


def sync_selection_impact(root: Path) -> None:
    """Rewrite wiki/selection-impact.md from committed gates. Harness only."""
    root = Path(root)
    lines = ["# Selection impact", "",
             "Harness aggregate of validation loads. Counts only.", ""]
    for event in engine.events(root):
        if event.get("type") != "gate" or event.get("candidate_score") is None:
            continue
        iteration = int(event["iteration"])
        rates = _val_load_rates(root, iteration)
        descriptions = _candidate_descriptions(root, iteration)
        lines.append(
            f"- Iteration {event['iteration']}, verdict {event['verdict']}, "
            f"val score {event['candidate_score']}.")
        names = list(rates)
        names += [name for name in descriptions if name not in rates]
        if not names:
            lines.append("  - no evolved skill in the val set.")
            continue
        for name in names:
            hit, total = rates.get(name, (0, 0))
            lines.append(
                f"  - {name} — {descriptions.get(name, '')} — loaded in {hit}/{total} val tasks.")
    path = root / "wiki/selection-impact.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def config_for(arm: str, *, iterations: int, train_n: int, val_n: int, seed: int,
               noise_k: int, workers: int = 2, index: str = "v2",
               model: str = MODEL, optimizer_model: str | None = None) -> dict:
    if index not in ("v1", "v2"):
        raise ValueError("index must be v1 or v2")
    feedback = list(FEEDBACK_FIELDS)
    if arm == "wikisel":
        feedback.append("skill_selection")
    aware = arm in ("od_aware", "wikisel")
    on_demand = arm != "all"
    return {
        "domain": "spreadsheet", "model": model, "optimizer_model": optimizer_model or model,
        "effort": EFFORT, "optimizer_effort": EFFORT, "reasoning_effort": EFFORT,
        "workers": workers, "iterations": iterations, "timeout": 180,
        "data": str(DATA), "split_dir": str(SPLITS),
        "arm": arm, "mode": "all" if arm == "all" else "od",
        "noise_k": noise_k, "seed": seed, "train_n": train_n, "val_n": val_n,
        "training_feedback": feedback,
        "addendum_sha256": _sha(ondemand_addendum()) if aware else "",
        "selection_addendum_sha256": _sha(selection_addendum()) if arm == "wikisel" else "",
        "index": index if on_demand else "",
        "index_v2_sha256": _sha((PROMPTS / "index_v2.md").read_text(encoding="utf-8"))
        if on_demand and index == "v2" else "",
        "noise_library_sha256": hashlib.sha256(LIBRARY.read_bytes()).hexdigest(),
    }


def _binding_identity(config: dict, cases, skill: str) -> str:
    return engine.digest({
        "cases": [asdict(case) if is_dataclass(case) else vars(case) for case in cases],
        "skill_sha256": hashlib.sha256(skill.encode()).hexdigest(),
        "config": config,
    })


def _rewrite_binding(directory: Path, config: dict, cases, skill: str) -> None:
    binding = directory / "binding.json"
    if binding.is_file():
        engine.save(binding, {"sha256": _binding_identity(config, cases, skill)})


def resume_workers(root: Path, workers: int) -> None:
    """Keep a restarted run on the same ledger when only --workers changes.

    The engine hashes workers into the manifest and into each phase binding.
    Rewriting both lets a 429 restart at workers=2 resume completed tasks.
    """
    root = Path(root)
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        return
    manifest = engine.read(manifest_path)
    if int(manifest["workers"]) == int(workers):
        return
    print(f"resume_workers {manifest['workers']} -> {workers}", flush=True)
    manifest["workers"] = int(workers)
    engine.save(manifest_path, manifest)
    engine.save(root / "manifest-lock.json", {"sha256": engine.digest(manifest)})
    current = engine.state(root)
    _train, _ = domain_loader(manifest, "train")
    val, _ = domain_loader(manifest, "val")
    if not any(event.get("type") == "baseline" for event in engine.events(root)):
        _rewrite_binding(root / "baseline" / "val", manifest, val, "")
        return
    directory = root / f"iterations/{int(current['next_iteration']):03d}"
    incumbent = (root / current["skill"]).read_text(encoding="utf-8")
    _rewrite_binding(directory / "train", manifest, _train, incumbent)
    proposal = directory / "proposal.json"
    if proposal.is_file():
        _rewrite_binding(directory / "val", manifest, val, engine.read(proposal).get("skill_md") or "")


def domain_loader(config, split):
    if split not in ("train", "val"):
        raise ValueError("Evolution only reads train and val")
    cases = {c.uid: c for c in load_cases(Path(config["data"]))}
    ids = [x["uid"] if isinstance(x, dict) else x
           for x in json.loads((Path(config["split_dir"]) / f"{split}.json").read_text())]
    n = int(config["train_n"] if split == "train" else config["val_n"])
    picked = [cases[uid] for uid in ids[:n]]
    if len({c.uid for c in picked}) != len(picked):
        raise ValueError("duplicate ids in the selected split")

    def rollout(case, **kw):
        return rollout_case(case, mode=config["mode"], noise_k=int(config["noise_k"]),
                            seed=int(config["seed"]), split=split,
                            index=config.get("index") or "v2", **kw)

    return picked, rollout


def agents_for(arm: str, seed: int, invoke_fn=invoke) -> PaperAgents:
    selection = arm == "wikisel"
    agents = PaperAgents(invoke_fn, seed=seed,
                         training_feedback=lambda row: train_feedback(row, selection=selection))
    if not selection:
        return agents
    inner = agents.maintainer_factory

    def maintainer_factory(*, model, workdir, reasoning_effort):
        run = inner(model=model, workdir=workdir, reasoning_effort=reasoning_effort)

        def wrapped(paths, *, iteration, wiki_dir):
            sync_selection_impact(Path(wiki_dir).parent)
            return run(paths, iteration=iteration, wiki_dir=wiki_dir)

        return wrapped

    agents.maintainer_factory = maintainer_factory  # type: ignore[method-assign]
    return agents


def _usage(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def accepted_without_load(root: Path) -> list[int]:
    """On-demand ACCEPTs whose evolved skills were loaded on 0 val tasks."""
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8")) if (root / "manifest.json").is_file() else {}
    if manifest.get("mode") == "all" or manifest.get("arm") == "all":
        return []
    events = read_jsonl(root / "events.jsonl") if (root / "events.jsonl").is_file() else []
    flagged = []
    for event in events:
        if event.get("type") != "gate" or not event.get("accepted"):
            continue
        rates = _val_load_rates(root, int(event["iteration"]))
        if all(hit == 0 for hit, _total in rates.values()):
            flagged.append(int(event["iteration"]))
    return flagged


def report(root: Path) -> None:
    root = Path(root)
    events = read_jsonl(root / "events.jsonl") if (root / "events.jsonl").is_file() else []
    baseline = next((e for e in events if e.get("type") == "baseline"), None)
    print(f"baseline_val={None if baseline is None else round(baseline['score'], 4)} "
          f"n={None if baseline is None else baseline.get('n')}")
    placebo = set(accepted_without_load(root))
    accepted = []
    for event in events:
        if event.get("type") != "gate":
            continue
        print(f"iteration={event['iteration']} verdict={event['verdict']} "
              f"incumbent={event['incumbent_score']} candidate={event['candidate_score']} "
              f"accepted={event['accepted']} skill={event['skill']}")
        if event.get("accepted"):
            accepted.append(event["skill"])
        rates = _val_load_rates(root, int(event["iteration"]))
        descriptions = _candidate_descriptions(root, int(event["iteration"]))
        for name, (hit, total) in rates.items():
            print(f"  val_load {name}: {hit}/{total} — {descriptions.get(name, '')}")
        if int(event["iteration"]) in placebo:
            print("  accepted_without_load")
    state = engine.state(root) if (root / "manifest.json").is_file() else {}
    print(f"r_best={state.get('r_best')} status={state.get('status')} skills_accepted={accepted}")
    print(f"accepted_without_load={len(placebo)}")
    print(f"cost_total=${spent():.4f}")
    for role in ("maintainer", "proposer"):
        for path in sorted(root.glob(f"iterations/*/{role}/runtime/usage.json")):
            usage = _usage(path)
            print(f"{role} iteration={path.parents[2].name} in={usage['prompt_tokens']} "
                  f"cached={usage['cached_tokens']} out={usage['completion_tokens']} "
                  f"calls={usage['calls']} ${usage['cost_usd']:.4f}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument("--noise-k", type=int, required=True)
    parser.add_argument("--iterations", type=int, required=True)
    parser.add_argument("--train-n", type=int, required=True)
    parser.add_argument("--val-n", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--budget", type=float, required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--index", choices=("v1", "v2"), default="v2")
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--optimizer-model", default=None,
                        help="Maintainer and Proposer model. Defaults to --model.")
    args = parser.parse_args()
    if args.budget <= 0 or args.iterations < 1 or args.train_n < 1 or args.val_n < 1:
        raise SystemExit("budget, iterations, train-n and val-n must be positive")
    load_env(PAPER / ".env")
    os.environ["ODSKILL_BUDGET_USD"] = str(args.budget)
    root = args.run_dir.expanduser().resolve()
    config = config_for(args.arm, iterations=args.iterations, train_n=args.train_n,
                        val_n=args.val_n, seed=args.seed, noise_k=args.noise_k,
                        workers=args.workers, index=args.index, model=args.model,
                        optimizer_model=args.optimizer_model or args.model)
    error = None
    try:
        if not (root / "manifest.json").exists():
            engine.initialize(root, config, agent_prompts=prompts_for(args.arm))
        else:
            resume_workers(root, args.workers)
        agents = agents_for(args.arm, args.seed)
        engine.evolve(root, domain_loader=domain_loader,
                      maintainer_factory=agents.maintainer_factory,
                      proposer_factory=agents.proposer_factory)
    except Exception as exc:  # report whatever the ledger already committed
        error = exc
    if args.arm == "wikisel" and (root / "wiki").is_dir():
        sync_selection_impact(root)
    if (root / "manifest.json").exists():
        report(root)
    if error:
        raise SystemExit(f"odskill: {error}")


if __name__ == "__main__":
    main()
