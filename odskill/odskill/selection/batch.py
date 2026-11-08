"""Run Experiments 1 and 2 and the test evaluation.

The parent process does not call the model. It starts the planned commands, watches
their logs, and stops when the $40 ceiling or the Experiment 1 cap would be crossed.
"""

from __future__ import annotations

import atexit
import json
import os
import signal
import subprocess
import time
from pathlib import Path

from odskill.selection.decide import HAIKU, decide, eligible
from odskill.selection.evolve_desc import games_for
from odskill.selection.library import NAMES
from odskill.selection.orchestrate import (
    BATCH_CEILING, DEEPSEEK, EPISODES, EXP1_CAP, PAPER, RESULTS, WORKERS,
    eval_jobs, exp1_budget, exp1_cells, exp1_command, exp2_jobs, exp2_projection,
    exp2_run_cap, on_429, provider, slots, test_projection, within_ceiling,
)
from odskill.selection.report import cell_record, write_exp1, write_test

LOGS = RESULTS / "logs"
STATE_PATH = LOGS / "state.json"
RUNNING: list[dict] = []
STOP = False


def paired_cells(records: list[dict]) -> list[dict]:
    """One decision row per prompt, names, noise, and executor. Needs both arms."""
    grouped: dict[tuple, dict] = {}
    for record in records:
        key = (record["executor"], record["agent_prompt"], record["names"], int(record["noise_k"]))
        short = "haiku" if record["executor"] == HAIKU else "deepseek"
        slot = grouped.setdefault(key, {
            "executor": record["executor"], "agent_prompt": record["agent_prompt"],
            "names": record["names"], "noise_k": int(record["noise_k"]),
            "cell": f"{record['agent_prompt']}-{record['names']}-k{record['noise_k']}-{short}",
        })
        if record["arm"] in ("plain", "directive"):
            slot[f"{record['arm']}_f1"] = float(record["f1"])
    return [slot for slot in grouped.values() if "plain_f1" in slot and "directive_f1" in slot]


def done_count(path: Path, pass_i: int) -> int:
    """Games finished for one pass. An error row with no model call is not finished."""
    if not path.is_file():
        return 0
    found = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if int(row.get("pass", 0)) != pass_i or bool(row.get("full")):
            continue
        if row.get("error") and not row.get("turns"):
            continue
        uid = row.get("uid")
        if uid:
            found.add(uid)
    return len(found)


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _rollout_file(path: Path) -> bool:
    if path.suffix != ".jsonl" or "worker" in path.name or path.name == "cells.jsonl":
        return False
    return path.name == "rollouts.jsonl" or path.name.startswith("it")


def dir_spend(root: Path) -> tuple[float, float]:
    """Executor cost from rollout rows, and role cost from usage.json. Missing dir is zero."""
    executor = roles = 0.0
    if not root.is_dir():
        return 0.0, 0.0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if _rollout_file(path):
            for row in _read_jsonl(path):
                executor += float(row.get("cost_usd") or 0)
        elif path.name == "usage.json":
            try:
                roles += float(json.loads(path.read_text(encoding="utf-8")).get("cost_usd") or 0)
            except (OSError, json.JSONDecodeError, TypeError):
                continue
    return executor, roles


def total_spend() -> float:
    executor, roles = dir_spend(RESULTS)
    return executor + roles


def _money(amount: float) -> str:
    text = f"{amount:.2f}"
    if amount > 0 and float(text) <= 0:
        return "0.01"
    return text


def _set_flag(argv: list[str], flag: str, value: str) -> list[str]:
    out = list(argv)
    out[out.index(flag) + 1] = value
    return out


def _log(message: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} {message}", flush=True)


def _save(state: dict) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _finished_eval(job: dict) -> bool:
    path = job["run_dir"] / "rollouts.jsonl"
    return all(done_count(path, pass_i) >= job["games"] for pass_i in range(job["passes"]))


def _finished_evolve(job: dict) -> bool:
    history_path = job["run_dir"] / "history.json"
    descriptions = job["run_dir"] / "descriptions.json"
    if not history_path.is_file() or not descriptions.is_file():
        return False
    try:
        history = json.loads(history_path.read_text(encoding="utf-8"))
        loaded = json.loads(descriptions.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return isinstance(history, list) and len(history) >= 7 and all(name in loaded for name in NAMES)


def finished(job: dict) -> bool:
    if job["kind"] == "evolve":
        return _finished_evolve(job)
    return _finished_eval(job)


def _contaminated(job: dict) -> bool:
    """An evolution restart would reuse iteration files written for an earlier proposal."""
    if job["kind"] != "evolve" or finished(job):
        return False
    return any(job["run_dir"].glob("it*.jsonl"))


def _machine_cpu() -> float:
    try:
        out = subprocess.check_output(["ps", "-A", "-o", "%cpu="], text=True, timeout=15)
        total = sum(float(part) for part in out.split())
    except (OSError, subprocess.SubprocessError, ValueError):
        return 0.0
    return total / (os.cpu_count() or 1)


def _worker_problems(dirs: list[Path]) -> int:
    found = 0
    for root in dirs:
        if not root.is_dir():
            continue
        for path in root.rglob("*.jsonl"):
            if not _rollout_file(path):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            found += text.count("ALFWorld worker")
            found += text.count("TimeoutError")
        for path in root.rglob("worker-*.log"):
            if "Traceback" in path.read_text(encoding="utf-8", errors="replace"):
                found += 1
    return found


def _stop_process(item: dict) -> None:
    proc = item["proc"]
    if proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except OSError:
            proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                proc.kill()
            proc.wait(timeout=10)
    item["handle"].close()


def _start(job: dict, argv: list[str]) -> dict:
    log_path = LOGS / f"{job['name']}.log"
    handle = log_path.open("a", encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        argv, cwd=PAPER, stdout=handle, stderr=subprocess.STDOUT,
        start_new_session=True, env=env)
    item = {"proc": proc, "handle": handle, "job": job, "argv": argv, "offset": log_path.stat().st_size,
            "log": log_path, "workers": int(argv[argv.index("--workers") + 1]),
            "budget": float(argv[argv.index("--budget") + 1]), "intentional": False}
    RUNNING.append(item)
    _log(f"start {job['name']} workers={item['workers']} budget=${item['budget']:.2f} pid={proc.pid}")
    return item


def _read_new(item: dict) -> str:
    try:
        size = item["log"].stat().st_size
    except OSError:
        return ""
    if size < item["offset"]:
        item["offset"] = 0
    with item["log"].open("r", encoding="utf-8", errors="replace") as handle:
        handle.seek(item["offset"])
        text = handle.read()
        item["offset"] = handle.tell()
    return text


def _assign_budget(job: dict, running: list[dict]) -> float:
    if job.get("budget_mode") == "exp1":
        running_dirs = {item["job"]["run_dir"] for item in running}
        spent = 0.0
        root = RESULTS / "exp1"
        if root.is_dir():
            for child in root.iterdir():
                if child in running_dirs or not child.is_dir():
                    continue
                executor, roles = dir_spend(child)
                spent += executor + roles
        reserved = sum(item["budget"] for item in running)
        return exp1_budget(spent, reserved)
    executor, roles = dir_spend(job["run_dir"])
    return max(0.0, float(job["cap"]) - executor - roles)


def _on_signal(signum, _frame) -> None:
    global STOP
    STOP = True
    _log(f"signal {signum}; stopping children")


def run_pool(jobs: list[dict], *, parallel: int, cpu_watch: bool, state: dict) -> dict:
    """Start `parallel` jobs. Experiment 1 drops to 4 cells and stays there."""
    pending = [job for job in jobs if not finished(job)]
    running: list[dict] = []
    failed: list[str] = []
    retries: dict[str, int] = {}
    dropped = False
    hot = 0
    workers = {"anthropic": WORKERS, "deepseek": WORKERS}
    peak_jobs = peak_workers = 0
    while pending or running:
        if STOP or total_spend() > BATCH_CEILING:
            _log(f"STOP ceiling or signal spent=${total_spend():.4f}")
            for item in running:
                _stop_process(item)
            RUNNING.clear()
            failed.extend(item["job"]["name"] for item in running)
            failed.extend(job["name"] for job in pending)
            return {"failed": failed, "peak_jobs": peak_jobs, "peak_workers": peak_workers,
                    "dropped": dropped, "aborted": True}
        limit = parallel
        if cpu_watch:
            cpu = _machine_cpu()
            problems = _worker_problems([item["job"]["run_dir"] for item in running])
            if cpu > 90:
                hot += 1
            else:
                hot = 0
            if hot >= 2 or problems:
                if not dropped:
                    _log(f"dropping to 4 cells cpu={cpu:.0f}% worker_problems={problems}")
                dropped = True
                state["dropped_to_4"] = True
            limit = slots(91 if hot >= 2 else 0, 1 if problems else 0, dropped=dropped)
        limited: set[str] = set()
        for item in running:
            if "openrouter_429" in _read_new(item):
                limited.add(item["job"]["provider"])
        for name in limited:
            updated = on_429(workers, name)
            state.setdefault("halvings", []).append({"provider": name, "workers": updated})
            _log(f"429 {name}; workers now {updated}")
            for item in list(running):
                if item["job"]["provider"] != name or item["job"]["kind"] == "evolve":
                    continue
                if item["workers"] <= updated:
                    continue
                item["intentional"] = True
                _stop_process(item)
                running.remove(item)
                if item in RUNNING:
                    RUNNING.remove(item)
                pending.insert(0, item["job"])
        while pending and len(running) < limit:
            job = pending.pop(0)
            if _contaminated(job):
                failed.append(job["name"])
                state.setdefault("notes", []).append(f"{job['name']} stopped with iteration files and no history")
                _log(f"not restarting {job['name']}; iteration files already exist")
                continue
            budget = _assign_budget(job, running)
            if budget <= 0 or total_spend() + budget > BATCH_CEILING:
                failed.append(job["name"])
                _log(f"no room for {job['name']} budget=${budget:.2f} spent=${total_spend():.4f}")
                if total_spend() + max(budget, 0) > BATCH_CEILING or job.get("budget_mode") == "exp1":
                    failed.extend(item["name"] for item in pending)
                    pending.clear()
                continue
            argv = _set_flag(job["argv"], "--workers", str(workers[job["provider"]]))
            argv = _set_flag(argv, "--budget", _money(budget))
            running.append(_start(job, argv))
        peak_jobs = max(peak_jobs, len(running))
        peak_workers = max(peak_workers, sum(item["workers"] for item in running))
        still = []
        for item in running:
            code = item["proc"].poll()
            if code is None:
                still.append(item)
                continue
            item["handle"].close()
            if item in RUNNING:
                RUNNING.remove(item)
            job = item["job"]
            if item["intentional"]:
                continue
            if finished(job):
                _log(f"done {job['name']} exit={code}")
                continue
            retries[job["name"]] = retries.get(job["name"], 0) + 1
            if retries[job["name"]] <= 1 and job["kind"] != "evolve":
                _log(f"resume {job['name']} exit={code}")
                pending.append(job)
            elif job["kind"] == "evolve" and not _contaminated(job) and retries[job["name"]] <= 1:
                _log(f"resume {job['name']} exit={code}")
                pending.append(job)
            else:
                failed.append(job["name"])
                _log(f"failed {job['name']} exit={code}")
        running = still
        state["peak_jobs"] = max(state.get("peak_jobs", 0), peak_jobs)
        state["peak_workers"] = max(state.get("peak_workers", 0), peak_workers)
        _save(state)
        time.sleep(10)
    return {"failed": failed, "peak_jobs": peak_jobs, "peak_workers": peak_workers,
            "dropped": dropped, "aborted": False}


def _guard(state: dict, phase: str, projection: float) -> bool:
    spent = total_spend()
    ok = within_ceiling(spent, projection)
    _log(f"{phase} spent=${spent:.4f} projection=${projection:.2f} "
         f"sum=${spent + projection:.2f} ceiling=${BATCH_CEILING:.0f} {'ok' if ok else 'STOP'}")
    state.setdefault("projections", {})[phase] = {"spent": round(spent, 4), "projection": round(projection, 2)}
    _save(state)
    return ok


def _exp1_jobs() -> list[dict]:
    jobs = []
    for cell in exp1_cells():
        run_dir = RESULTS / "exp1" / cell["cell"]
        jobs.append({
            "name": cell["cell"], "kind": "eval", "provider": provider(cell["executor"]),
            "argv": exp1_command(cell, 1.0), "run_dir": run_dir, "passes": 1,
            "games": EPISODES["val"], "budget_mode": "exp1",
        })
    return jobs


def _wrap_exp2(cell: dict, cap: float, baseline_cap: float) -> tuple[list[dict], list[dict]]:
    baselines, evolutions = [], []
    for job in exp2_jobs(cell, cap, baseline_budget=baseline_cap):
        run_dir = Path(job["argv"][job["argv"].index("--run-dir") + 1])
        job.update({
            "name": f"{job['kind']}-{job['arm']}-s{job['seed']}",
            "provider": "anthropic", "run_dir": run_dir, "passes": 1,
            "games": EPISODES["val"], "budget_mode": "fixed",
            "cap": cap if job["kind"] == "evolve" else baseline_cap,
        })
        (evolutions if job["kind"] == "evolve" else baselines).append(job)
    return baselines, evolutions


def _wrap_test(cell: dict, haiku_cap: float, deepseek_cap: float) -> list[dict]:
    jobs = []
    for job in eval_jobs(cell, lambda executor: haiku_cap if executor == HAIKU else deepseek_cap):
        run_dir = Path(job["argv"][job["argv"].index("--run-dir") + 1])
        passes = int(job["argv"][job["argv"].index("--passes") + 1])
        job.update({
            "name": f"test-{run_dir.parent.name}-{run_dir.name}",
            "kind": "eval", "provider": provider(job["executor"]), "run_dir": run_dir,
            "passes": passes, "games": EPISODES["test"], "budget_mode": "fixed",
            "cap": haiku_cap if job["executor"] == HAIKU else deepseek_cap,
        })
        jobs.append(job)
    return jobs


def _summarize_exp1() -> list[dict]:
    records = []
    for cell in exp1_cells():
        rows = _read_jsonl(RESULTS / "exp1" / cell["cell"] / "rollouts.jsonl")
        records.append(cell_record(cell, rows))
    write_exp1(records, RESULTS / "exp1" / "summary.md")
    return records


def resume_cap(job: dict, unit_cost: float) -> float:
    """Finish a partial eval. Remaining episodes use the higher of the planned rate and this directory's mean, times 1.3."""
    path = job["run_dir"] / "rollouts.jsonl"
    rows = _read_jsonl(path)
    spent = sum(float(row.get("cost_usd") or 0) for row in rows)
    done = sum(done_count(path, pass_i) for pass_i in range(int(job["passes"])))
    remaining = max(0, int(job["passes"]) * int(job["games"]) - done)
    observed = spent / len(rows) if rows else 0.0
    rate = max(float(unit_cost), observed)
    return spent + remaining * rate * 1.3


def _condition_cpe(records: list[dict], executor: str, cell: dict) -> float | None:
    matched = [row for row in records
               if row["executor"] == executor and row["agent_prompt"] == cell["agent_prompt"]
               and row["names"] == cell["names"] and int(row["noise_k"]) == int(cell["noise_k"])]
    episodes = sum(int(row["episodes"]) for row in matched)
    if not episodes:
        return None
    return sum(float(row["cost_usd"]) for row in matched) / episodes


def _write_decision(cells: list[dict], chosen: dict | None) -> None:
    lines = ["# Decision", ""]
    if chosen is None:
        lines.append("No eligible cell has directive F1 − plain F1 ≥ 0.10. Experiment 2 will not run.")
    else:
        lines.append(f"Chosen: `{chosen['cell']}`.")
        lines.append("")
        lines.append(
            f"Haiku, agent-prompt {chosen['agent_prompt']}, names {chosen['names']}, "
            f"noise {chosen['noise_k']}. Plain F1 {chosen['plain_f1']:.3f}, "
            f"directive F1 {chosen['directive_f1']:.3f}.")
    lines += ["", "| cell | plain F1 | directive F1 | gap |", "|---|---:|---:|---:|"]
    for cell in cells:
        if not eligible(cell):
            continue
        gap = cell["directive_f1"] - cell["plain_f1"]
        lines.append(f"| {cell['cell']} | {cell['plain_f1']:.3f} | {cell['directive_f1']:.3f} | {gap:.3f} |")
    lines.append("")
    (RESULTS / "decision.md").write_text("\n".join(lines), encoding="utf-8")


def _load_test_groups() -> dict:
    groups = {HAIKU: {}, DEEPSEEK: {}}
    for executor, short in ((HAIKU, "haiku"), (DEEPSEEK, "deepseek")):
        root = RESULTS / "test" / short
        if not root.is_dir():
            continue
        for path in sorted(root.iterdir()):
            rows = _read_jsonl(path / "rollouts.jsonl")
            arm, _, seed = path.name.partition("-s")
            if seed:
                for row in rows:
                    row["seed"] = int(seed)
            groups[executor].setdefault(arm, []).extend(rows)
    return groups


def _pilot_cpe() -> float | None:
    path = Path.home() / "odskill-runs" / "selection" / "plain-k100-s0" / "rollouts.jsonl"
    rows = _read_jsonl(path)
    if not rows:
        return None
    return sum(float(row.get("cost_usd") or 0) for row in rows) / len(rows)


def _write_report(state: dict) -> None:
    executor, roles = dir_spend(RESULTS / "exp1")
    exp2_exec, exp2_roles = dir_spend(RESULTS / "exp2")
    test_exec, test_roles = dir_spend(RESULTS / "test")
    lines = [
        "# Batch report",
        "",
        f"Wall clock from supervisor start: {(time.time() - state['t0']) / 60:.1f} min.",
        f"Peak concurrent jobs {state.get('peak_jobs', 0)}, peak worker slots {state.get('peak_workers', 0)}.",
        f"Dropped Experiment 1 to 4 cells: {bool(state.get('dropped_to_4'))}.",
        f"429 halvings: {json.dumps(state.get('halvings') or [])}.",
        "",
        "## Cost",
        "",
        f"- Experiment 1 executor ${executor:.4f}, roles ${roles:.4f}.",
        f"- Experiment 2 executor ${exp2_exec:.4f}, roles ${exp2_roles:.4f}.",
        f"- Test executor ${test_exec:.4f}, roles ${test_roles:.4f}.",
        f"- Total ${executor + roles + exp2_exec + exp2_roles + test_exec + test_roles:.4f}.",
        "",
        "## Notes",
        "",
    ]
    notes = state.get("notes") or []
    lines.extend(f"- {note}" for note in notes)
    if not notes:
        lines.append("- None.")
    lines.append("")
    (RESULTS / "batch_report.md").write_text("\n".join(lines), encoding="utf-8")


def _shutdown_children() -> None:
    for item in list(RUNNING):
        if item["proc"].poll() is None:
            _stop_process(item)
    RUNNING.clear()


def _aborted(result: dict) -> bool:
    return bool(result.get("aborted") or STOP)


def run_batch() -> None:
    """Phases 3–6. Refuses to start a second supervisor while one is alive."""
    global STOP
    LOGS.mkdir(parents=True, exist_ok=True)
    pid_path = LOGS / "batch.pid"
    if pid_path.is_file():
        try:
            old = int(pid_path.read_text(encoding="utf-8"))
            os.kill(old, 0)
        except (OSError, ValueError):
            old = 0
        if old and old != os.getpid():
            raise SystemExit(f"batch already running as pid {old}")
    pid_path.write_text(str(os.getpid()), encoding="utf-8")
    atexit.register(_shutdown_children)
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
    state = {"t0": time.time(), "notes": [], "halvings": []}
    _save(state)
    val_n = len(games_for("val", EPISODES["val"], allow_test=False))
    test_n = len(games_for("test", None, allow_test=True))
    if val_n != EPISODES["val"] or test_n != EPISODES["test"]:
        _log(f"STOP split sizes val={val_n} test={test_n}")
        return
    pilot = _pilot_cpe()
    estimate = (pilot if pilot is not None else 0.001) * len(exp1_cells()) * EPISODES["val"]
    _log(f"phase 3 estimate ${estimate:.2f} from "
         f"{'pilot' if pilot is not None else 'placeholder'} "
         f"${(pilot if pilot is not None else 0.001):.6f}/episode; hard cap ${EXP1_CAP:.0f}")
    if not _guard(state, "phase 3", EXP1_CAP):
        _write_report(state)
        return
    exp1 = run_pool(_exp1_jobs(), parallel=8, cpu_watch=True, state=state)
    if _aborted(exp1):
        _summarize_exp1()
        state["notes"].append("Stopped during Experiment 1.")
        _save(state)
        _write_report(state)
        return
    records = _summarize_exp1()
    incomplete = [job["name"] for job in _exp1_jobs() if not finished(job)]
    if exp1["failed"] or incomplete:
        state["notes"].append("Experiment 1 incomplete: " + ", ".join(sorted(set(exp1["failed"] + incomplete))))
        _save(state)
        _log("STOP Experiment 1 incomplete; not deciding")
        _write_report(state)
        return
    cells = paired_cells(records)
    chosen = decide(cells)
    _write_decision(cells, chosen)
    _log(f"decision {chosen['cell'] if chosen else 'None'}")
    if chosen is None:
        state["notes"].append("No cell qualified. Experiment 2 and the test were not run.")
        _save(state)
        _write_report(state)
        return
    cpe = _condition_cpe(records, HAIKU, chosen)
    deep_cpe = _condition_cpe(records, DEEPSEEK, chosen)
    if not cpe or not deep_cpe:
        state["notes"].append("Missing a measured cost per episode for the chosen condition.")
        _save(state)
        _log("STOP no measured cost")
        _write_report(state)
        return
    projection = exp2_projection(cpe)
    _log(f"phase 5 Haiku ${cpe:.6f}/episode per-run cap ${exp2_run_cap(cpe):.2f} "
         f"six runs ${projection['six_runs']:.2f} baselines ${projection['baselines']:.2f}")
    if not _guard(state, "phase 5", projection["total"]):
        state["notes"].append("Experiment 2 projection crossed the $40 ceiling. Not started.")
        _save(state)
        _write_report(state)
        return
    baselines, evolutions = _wrap_exp2(chosen, projection["per_run"], projection["baselines"] / 3)
    base_result = run_pool(baselines, parallel=3, cpu_watch=False, state=state)
    if _aborted(base_result):
        state["notes"].append("Stopped during the Experiment 2 baselines.")
        _save(state)
        _write_report(state)
        return
    if base_result["failed"] or any(not finished(job) for job in baselines):
        state["notes"].append("A baseline did not finish. Evolutions were not started.")
        _save(state)
        _log("STOP baseline incomplete")
        _write_report(state)
        return
    evo_result = run_pool(evolutions, parallel=6, cpu_watch=False, state=state)
    if _aborted(evo_result):
        state["notes"].append("Stopped during Experiment 2.")
        _save(state)
        _write_report(state)
        return
    if evo_result["failed"] or any(not finished(job) for job in evolutions):
        state["notes"].append("An evolution did not finish. The test split was not run.")
        _save(state)
        _log("STOP evolution incomplete")
        _write_report(state)
        return
    test_cost = test_projection(cpe, deep_cpe)
    _log(f"phase 6 Haiku ${cpe:.6f}/episode × {test_cost['haiku_episodes']} × 1.3 = ${test_cost['haiku']:.2f}; "
         f"DeepSeek ${deep_cpe:.6f}/episode × {test_cost['deepseek_episodes']} × 1.3 = ${test_cost['deepseek']:.2f}")
    if not _guard(state, "phase 6", test_cost["total"]):
        state["notes"].append("Test projection crossed the $40 ceiling. The test split was not run.")
        _save(state)
        _write_report(state)
        return
    test_jobs = _wrap_test(chosen, test_cost["haiku"] / 8, test_cost["deepseek"] / 8)
    if any((job["run_dir"] / "rollouts.jsonl").is_file() for job in test_jobs):
        for job in test_jobs:
            unit = cpe if job["executor"] == HAIKU else deep_cpe
            job["cap"] = resume_cap(job, unit)
        executor_cost, role_cost = dir_spend(RESULTS / "test")
        already = executor_cost + role_cost
        remaining_auth = sum(max(0.0, job["cap"] - sum(dir_spend(job["run_dir"]))) for job in test_jobs)
        _log(f"phase 6 resume: arms that load cost more than the Experiment 1 rate. "
             f"Remaining authorization ${remaining_auth:.2f} on top of test spend ${already:.2f}.")
        if not _guard(state, "phase 6 resume", remaining_auth):
            state["notes"].append("Test resume crossed the $40 ceiling. Left unfinished.")
            _save(state)
            _write_report(state)
            return
    test_result = run_pool(test_jobs, parallel=16, cpu_watch=False, state=state)
    if _aborted(test_result):
        state["notes"].append("Stopped during the test evaluation.")
    elif test_result["failed"] or any(not finished(job) for job in test_jobs):
        state["notes"].append("A test evaluation did not finish.")
    write_test(_load_test_groups(), RESULTS / "test" / "summary.md")
    _save(state)
    _write_report(state)
    _log(f"batch finished spent=${total_spend():.4f}")
