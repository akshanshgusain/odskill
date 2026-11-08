"""Plans for Experiments 1 and 2 and the test evaluation.

Importing this module does not call the network. `main` prints the plan.
It launches only when passed `--go`, which this preflight does not.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from odskill.selection.decide import HAIKU
from odskill.selection.evolve_desc import PAPER, load_env, run_evolution

DEEPSEEK = "deepseek/deepseek-v4.1-flash-1017"
PYTHON = ".venv/bin/python"
EXP1_CAP = 8.0
BATCH_CEILING = 40.0
WORKERS = 6
MAX_CELLS = 8
RESULTS = PAPER / "results"
EPISODES = {"train": 120, "val": 60, "test": 134}
EVOLVE_EPISODES = 1140  # 60 baseline is separate; 6 * (120 train + 60 val)


def provider(model: str) -> str:
    return model.split("/", 1)[0]


def within_ceiling(spent: float, projection: float, ceiling: float = BATCH_CEILING) -> bool:
    return spent + projection <= ceiling


def slots(cpu_percent: float, worker_errors: int, *, dropped: bool = False) -> int:
    """At most 8 Experiment 1 cells. Drop to 4 when the machine is hot or a worker errors."""
    if dropped or cpu_percent > 90 or worker_errors > 0:
        return 4
    return MAX_CELLS


def on_429(workers_by_provider: dict[str, int], provider_name: str) -> int:
    """Halve one provider's workers. The other provider is left alone. Floor is 1."""
    current = workers_by_provider.get(provider_name, WORKERS)
    workers_by_provider[provider_name] = max(1, current // 2)
    return workers_by_provider[provider_name]


def exp1_cells() -> list[dict]:
    """24 canonical cells plus 4 opaque cells. Val, 1 pass, noise seed 0."""
    cells = []
    for agent_prompt in ("forced", "neutral"):
        for noise in (20, 100, 300):
            for executor in (HAIKU, DEEPSEEK):
                for arm in ("plain", "directive"):
                    cells.append(_cell(agent_prompt, "canonical", noise, executor, arm))
    for executor in (HAIKU, DEEPSEEK):
        for arm in ("plain", "directive"):
            cells.append(_cell("neutral", "opaque", 100, executor, arm))
    return cells


def _cell(agent_prompt: str, names: str, noise: int, executor: str, arm: str) -> dict:
    short = "haiku" if executor == HAIKU else "deepseek"
    name = f"{agent_prompt}-{names}-k{noise}-{short}-{arm}"
    return {
        "cell": name, "agent_prompt": agent_prompt, "names": names, "noise_k": noise,
        "executor": executor, "arm": arm, "seed": 0, "split": "val", "passes": 1,
        "workers": WORKERS,
    }


def _argv(module: str, args: list[str]) -> list[str]:
    return [PYTHON, "-u", "-m", module, *args]


def exp1_command(cell: dict, budget: float) -> list[str]:
    return _argv("odskill.selection.exp1", [
        "--arm", cell["arm"],
        "--agent-prompt", cell["agent_prompt"],
        "--names", cell["names"],
        "--noise-k", str(cell["noise_k"]),
        "--executor", cell["executor"],
        "--seed", "0",
        "--split", "val",
        "--val-n", "60",
        "--passes", "1",
        "--workers", str(cell["workers"]),
        "--budget", f"{budget:.2f}",
        "--run-dir", str(RESULTS / "exp1" / cell["cell"]),
    ])


def exp1_budget(spent: float, reserved: float) -> float:
    """Process cap. Running cells have already reserved their caps. Never above $1, never past $8."""
    room = EXP1_CAP - spent - reserved
    return max(0.0, min(1.0, room))


def exp2_run_cap(cost_per_episode: float) -> float:
    return cost_per_episode * EVOLVE_EPISODES * 1.3 + 2.50


def exp2_projection(cost_per_episode: float) -> dict:
    """Six evolution caps, plus three 60-game baselines with the same 1.3 cushion."""
    run = exp2_run_cap(cost_per_episode)
    baselines = 3 * EPISODES["val"] * cost_per_episode * 1.3
    return {"per_run": run, "six_runs": 6 * run, "baselines": baselines,
            "total": 6 * run + baselines}


def exp2_jobs(cell: dict, budget: float, baseline_budget: float | None = None) -> list[dict]:
    """Three baselines, then six evolutions. A seed's two arms share one baseline file."""
    jobs = []
    base_budget = budget if baseline_budget is None else baseline_budget
    for seed in (0, 1, 2):
        base = RESULTS / "exp2" / f"baseline-s{seed}"
        jobs.append({
            "kind": "baseline", "seed": seed, "arm": "plain",
            "baseline": str(base / "rollouts.jsonl"),
            "argv": _argv("odskill.selection.exp1", [
                "--arm", "plain",
                "--agent-prompt", cell["agent_prompt"],
                "--names", cell["names"],
                "--noise-k", str(cell["noise_k"]),
                "--executor", HAIKU,
                "--seed", str(seed),
                "--split", "val",
                "--val-n", "60",
                "--passes", "1",
                "--workers", str(WORKERS),
                "--budget", f"{base_budget:.2f}",
                "--run-dir", str(base),
            ]),
        })
    for seed in (0, 1, 2):
        baseline = str(RESULTS / "exp2" / f"baseline-s{seed}" / "rollouts.jsonl")
        for arm in ("nowiki", "wikisel"):
            root = RESULTS / "exp2" / f"{arm}-s{seed}"
            jobs.append({
                "kind": "evolve", "seed": seed, "arm": arm, "baseline": baseline,
                "argv": _argv("odskill.selection.orchestrate", [
                    "exp2-run", "--go",
                    "--arm", arm,
                    "--seed", str(seed),
                    "--baseline", baseline,
                    "--agent-prompt", cell["agent_prompt"],
                    "--names", cell["names"],
                    "--noise-k", str(cell["noise_k"]),
                    "--workers", str(WORKERS),
                    "--budget", f"{budget:.2f}",
                    "--run-dir", str(root),
                ]),
            })
    return jobs


def eval_jobs(cell: dict, budget_for) -> list[dict]:
    """16 evaluations. Every one shuffles noise with seed 0, including evolved seeds 1 and 2."""
    jobs = []
    sets = [("plain", None), ("directive", None)]
    for arm in ("nowiki", "wikisel"):
        for seed in (0, 1, 2):
            sets.append((arm, seed))
    for executor, passes in ((HAIKU, 2), (DEEPSEEK, 1)):
        short = "haiku" if executor == HAIKU else "deepseek"
        for arm, seed in sets:
            label = arm if seed is None else f"{arm}-s{seed}"
            args = [
                "--arm", arm,
                "--agent-prompt", cell["agent_prompt"],
                "--names", cell["names"],
                "--noise-k", str(cell["noise_k"]),
                "--executor", executor,
                "--seed", "0",
                "--split", "test",
                "--i-understand-this-is-the-test-split",
                "--passes", str(passes),
                "--workers", str(WORKERS),
                "--budget", f"{budget_for(executor):.2f}",
                "--run-dir", str(RESULTS / "test" / short / label),
            ]
            if seed is not None:
                args = ["--descriptions", str(RESULTS / "exp2" / label / "descriptions.json"), *args]
            jobs.append({"executor": executor, "arm": arm, "evolution_seed": seed, "noise_seed": 0,
                         "argv": _argv("odskill.selection.evolve_desc", args)})
    return jobs


def test_projection(haiku_cost: float, deepseek_cost: float) -> dict:
    haiku_n = 8 * EPISODES["test"] * 2
    deepseek_n = 8 * EPISODES["test"] * 1
    haiku = haiku_cost * haiku_n * 1.3
    deepseek = deepseek_cost * deepseek_n * 1.3
    return {"haiku_episodes": haiku_n, "deepseek_episodes": deepseek_n,
            "haiku": haiku, "deepseek": deepseek, "total": haiku + deepseek}


def exp2_run(root: Path, cfg: dict, baseline: Path) -> dict:
    """Load the seed's baseline rows and evolve. Does not read .env; the caller already did."""
    rows = [json.loads(line) for line in baseline.read_text(encoding="utf-8").splitlines() if line.strip()]
    return run_evolution(root, cfg, baseline_rows=rows)


def _exp2_cfg(args) -> dict:
    return {
        "arm": args.arm, "noise_k": args.noise_k, "seed": args.seed, "iterations": 6,
        "train_n": 120, "val_n": 60, "passes": 1, "workers": args.workers,
        "executor": HAIKU, "optimizer": "anthropic/claude-sonnet-5.5", "split": "val",
        "full": False, "allow_test": False, "effort": "low",
        "agent_prompt": args.agent_prompt, "names": args.names, "descriptions_file": "",
    }


def _sh(argv: list[str]) -> str:
    return " ".join(argv)


def _synthetic_rows(hit_until: int, *, error_at: int | None, seed: int, passes: int, arm: str) -> list[dict]:
    rows = []
    types = ("pick_heat_then_place_in_recep", "pick_and_place_simple")
    skills = ("pick_heat_then_place", "pick_and_place")
    for pass_i in range(passes):
        for index in range(4):
            relevant = skills[index % 2]
            hit = index < hit_until
            rows.append({
                "uid": f"g{index}", "pass": pass_i, "seed": seed, "arm": arm,
                "task_type": types[index % 2], "relevant": relevant,
                "relevant_loaded": hit, "load_count": 1, "relevant_load_count": 1 if hit else 0,
                "noise_loads": 0, "wrong_type_loads": 0 if hit else 1, "loaded_any": True,
                "error": "model_error" if error_at == index and pass_i == 0 else "",
                "cost_usd": 0.001,
            })
    return rows


def write_phase_doc(path: Path) -> None:
    """preflight/phase3-6.md from the planners and from synthetic rows. No API calls."""
    from odskill.selection.decide import examples
    from odskill.selection.report import cell_record, write_exp1, write_test

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    synthetic = path.parent / "synthetic"
    chosen = {"agent_prompt": "neutral", "names": "canonical", "noise_k": 100}
    exp2_budget = exp2_run_cap(0.001)
    lines = [
        "# Phases 3–6",
        "",
        "Projected API cost of building this page: $0. Nothing here was launched.",
        "Before a live phase the parent prints `spent + projection` and stops when that exceeds $40.",
        "",
        "## Concurrency",
        "",
        "- Experiment 1: at most 8 cells at once, 6 workers each. If CPU stays above 90% or an ALFWorld worker errors, drop to 4 cells and stay there.",
        "- Each Experiment 1 process is capped at `min($1, $8 − spent − reserved)`. Eight running cells reserve at most $8.",
        "- Experiment 2: write the three baselines first. Then the six evolutions run in parallel, detached, 6 workers each. Iterations inside a run stay sequential.",
        "- Test: all 16 evaluations in parallel, 6 workers each.",
        "- On HTTP 429, halve workers for that provider only (Anthropic or DeepSeek), then resume. Completed rows are kept.",
        "",
        "## Phase 3 — Experiment 1",
        "",
        "28 cells. Val 60, 1 pass, noise seed 0. The parent appends each process's stdout to `results/logs/<cell>.log`.",
        "",
    ]
    for cell in exp1_cells():
        lines.append(_sh(exp1_command(cell, exp1_budget(0.0, 0.0))))
        lines.append("")
    lines += [
        "## Phase 4 — decision",
        "",
        "`decide(cells)` returns the chosen cell, or None. A gap qualifies at `directive − plain >= 0.10 − 1e-9`.",
        "Outputs below are from the synthetic cases.",
        "",
    ]
    for label, cells, result in examples():
        lines.append(f"### {label}")
        lines.append("")
        for cell in cells:
            gap = cell["directive_f1"] - cell["plain_f1"]
            lines.append(
                f"- {cell['cell']}: plain {cell['plain_f1']:.2f}, directive {cell['directive_f1']:.2f}, gap {gap:.2f}")
        lines.append(f"- decide -> {result}")
        lines.append("")
    lines += [
        "## Phase 5 — Experiment 2",
        "",
        "Commands use a placeholder Haiku cost of $0.001 per episode so the budget field is filled.",
        f"Per-run cap = 0.001 × 1140 × 1.3 + 2.50 = ${exp2_budget:.2f}.",
        f"Six runs = ${6 * exp2_budget:.2f}. Three baselines = ${3 * 60 * 0.001 * 1.3:.2f}.",
        "The live numbers replace 0.001 with the chosen cell's measured Haiku cost per episode.",
        "Both arms of a seed are called as `run_evolution(root, cfg, baseline_rows=<that seed's rollouts>)`.",
        "",
    ]
    for job in exp2_jobs(chosen, exp2_budget, baseline_budget=EPISODES["val"] * 0.001 * 1.3):
        lines.append(f"# {job['kind']} seed {job['seed']} {job['arm']}")
        lines.append(_sh(job["argv"]))
        lines.append("")
    test_budget = test_projection(0.001, 0.002)
    lines += [
        "## Phase 6 — test",
        "",
        "134 games, noise seed 0 on every command, including descriptions that were evolved at seed 1 or 2.",
        "Haiku: 2 passes, 8 description sets, 2144 episodes. DeepSeek: 1 pass, 8 sets, 1072 episodes.",
        "Placeholder costs $0.001 Haiku and $0.002 DeepSeek give caps "
        f"${test_budget['haiku']:.2f} and ${test_budget['deepseek']:.2f}.",
        "",
    ]
    haiku_cap = test_budget["haiku"] / 8
    deepseek_cap = test_budget["deepseek"] / 8
    for job in eval_jobs(chosen, lambda executor: haiku_cap if executor == HAIKU else deepseek_cap):
        lines.append(_sh(job["argv"]))
        lines.append("")
    flagged = cell_record(
        {"cell": "synthetic-flagged"},
        _synthetic_rows(3, error_at=3, seed=0, passes=1, arm="plain"))
    clean = cell_record(
        {"cell": "synthetic-clean"},
        _synthetic_rows(4, error_at=None, seed=0, passes=1, arm="plain"))
    exp1_text = write_exp1([flagged, clean], synthetic / "exp1" / "summary.md")
    groups = {}
    for executor, passes in ((HAIKU, 2), (DEEPSEEK, 1)):
        groups[executor] = {
            "plain": _synthetic_rows(2, error_at=None, seed=0, passes=passes, arm="plain"),
            "directive": _synthetic_rows(3, error_at=None, seed=0, passes=passes, arm="directive"),
            "nowiki": sum((_synthetic_rows(2, error_at=None, seed=seed, passes=passes, arm="nowiki")
                           for seed in (0, 1, 2)), []),
            "wikisel": sum((_synthetic_rows(3, error_at=None, seed=seed, passes=passes, arm="wikisel")
                            for seed in (0, 1, 2)), []),
        }
    test_text = write_test(groups, synthetic / "test" / "summary.md")
    lines += [
        "## Synthetic Experiment 1 summary",
        "",
        exp1_text,
        "## Synthetic test summary",
        "",
        test_text,
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", nargs="?", default="plan", choices=("plan", "exp2-run", "batch"))
    parser.add_argument("--go", action="store_true")
    parser.add_argument("--arm", default="nowiki")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--baseline", type=Path, default=None)
    parser.add_argument("--agent-prompt", default="neutral")
    parser.add_argument("--names", default="canonical")
    parser.add_argument("--noise-k", type=int, default=100)
    parser.add_argument("--workers", type=int, default=WORKERS)
    parser.add_argument("--budget", type=float, default=0.0)
    parser.add_argument("--run-dir", type=Path, default=None)
    args = parser.parse_args()
    if args.phase == "batch":
        if not args.go:
            print("phase plan only; not launching", flush=True)
            return
        from odskill.selection.batch import run_batch
        run_batch()
        return
    if args.phase == "plan" or not args.go:
        print("phase plan only; not launching", flush=True)
        print(f"exp1 cells {len(exp1_cells())}", flush=True)
        return
    if args.phase != "exp2-run" or args.baseline is None or args.run_dir is None or args.budget <= 0:
        raise SystemExit("exp2-run --go needs --baseline, --run-dir, and --budget")
    load_env(PAPER / ".env")
    os.environ["ODSKILL_BUDGET_USD"] = str(args.budget)
    exp2_run(args.run_dir.expanduser(), _exp2_cfg(args), args.baseline.expanduser())


if __name__ == "__main__":
    main()
