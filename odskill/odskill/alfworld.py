"""Per-step ALFWorld agent on OpenRouter, plus the frozen alfworld_v1 splits.

The simulator is wikiskill's stepper, running in ALFWORLD_PYTHON. This module
replaces the Codex episode driver: each turn the model sees the paper prompt
and returns one action. No bash tool and no evolution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import select
import subprocess
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from wikiskill.benchmarks.alfworld import SYSTEM_PROMPT, extract_action
from wikiskill.officeqa.rollout import SKILL_SECTION_HEADER

from .llm import BudgetExceeded, LLMError, Usage, as_text, chat, load_env, spent
from .stats import summarize

PAPER = Path(__file__).resolve().parents[2]
WIKISKILL_SRC = PAPER / "wikiskill" / "src"
WORKER = Path(__file__).resolve().parent / "alfworld_worker.py"
PROCEDURE = PAPER / "odskill" / "prompts" / "alfworld_procedure.md"
SPLIT_DIR = PAPER / "odskill" / "splits" / "alfworld_v1"
DATA_CANDIDATES = (
    Path.home() / ".cache" / "alfworld" / "json_2.1.1",
    Path.home() / ".cache" / "alfworld" / "json_2.1.2",
)
ALF_PYTHON = PAPER / ".venv-alfworld" / "bin" / "python"
MAX_STEPS = 50
SEED = 0
EFFORT = "low"
TYPES = (
    "look_at_obj_in_light",
    "pick_and_place_simple",
    "pick_clean_then_place_in_recep",
    "pick_cool_then_place_in_recep",
    "pick_heat_then_place_in_recep",
    "pick_two_obj_and_place",
)
_lock = threading.Lock()
_STATIC = (
    "You are an expert agent operating in the ALFRED Embodied Environment. "
    "On every turn, reason briefly inside <think> tags and output exactly one "
    "admissible action inside <action> tags. Copy the action string exactly.\n"
)


def alfworld_python() -> Path:
    chosen = os.environ.get("ALFWORLD_PYTHON")
    path = Path(chosen) if chosen else ALF_PYTHON
    if not path.is_file():
        raise SystemExit("ALFWORLD_PYTHON is not set and .venv-alfworld is missing")
    return path


def data_root() -> Path:
    for path in DATA_CANDIDATES:
        if (path / "valid_seen").is_dir() and (path / "valid_unseen").is_dir():
            return path
    raise FileNotFoundError("ALFWorld json data not found under ~/.cache/alfworld")


def task_type_of(uid: str) -> str:
    folder = Path(uid).parts[1]
    for name in sorted(TYPES, key=len, reverse=True):
        if folder.startswith(name):
            return name
    return folder.split("-", 1)[0]


def collect_games(root: Path) -> dict[str, list[str]]:
    found = {}
    for split in ("train", "valid_seen", "valid_unseen"):
        directory = root / split
        games = sorted(path.relative_to(root).as_posix() for path in directory.rglob("*.tw-pddl"))
        if not games:
            raise FileNotFoundError(f"no games under {directory}")
        found[split] = games
    return found


def _counts(uids: list[str]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for uid in uids:
        counts[task_type_of(uid)] += 1
    return dict(sorted(counts.items()))


def build_splits(games: dict[str, list[str]], *, seed: int = SEED,
                 train_n: int = 120, val_n: int = 60) -> dict[str, list[str]]:
    """Train from the TRAIN games. Val is a balanced sample of valid_seen. Test is valid_unseen."""
    rng = random.Random(seed)
    train = list(games["train"])
    rng.shuffle(train)
    train = train[:train_n]
    groups: dict[str, list[str]] = defaultdict(list)
    for uid in games["valid_seen"]:
        groups[task_type_of(uid)].append(uid)
    for name in groups:
        rng.shuffle(groups[name])
    val: list[str] = []
    while len(val) < val_n:
        grew = False
        for name in TYPES:
            if groups[name]:
                val.append(groups[name].pop())
                grew = True
                if len(val) == val_n:
                    break
        if not grew:
            break
    test = list(games["valid_unseen"])
    splits = {"train": train, "val": val, "test": test}
    ids = [uid for rows in splits.values() for uid in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("alfworld_v1 splits overlap")
    if len(val) != val_n or len(train) != train_n:
        raise ValueError(f"short split train={len(train)} val={len(val)}")
    return splits


def write_splits(root: Path | None = None, dest: Path = SPLIT_DIR, seed: int = SEED) -> dict:
    games = collect_games(root or data_root())
    splits = build_splits(games, seed=seed)
    dest.mkdir(parents=True, exist_ok=True)
    blobs = {}
    for name, uids in splits.items():
        payload = [{"uid": uid, "task_type": task_type_of(uid)} for uid in uids]
        text = json.dumps(payload, indent=2) + "\n"
        (dest / f"{name}.json").write_text(text, encoding="utf-8")
        blobs[name] = text
    digest = hashlib.sha256("".join(blobs[name] for name in ("train", "val", "test")).encode()).hexdigest()
    manifest = {
        "name": "alfworld_v1",
        "seed": seed,
        "source": "alfworld-download (json_2.1.1 json/pddl plus json_2.1.2 tw-pddl)",
        "data_root": str(root or data_root()),
        "counts": {name: len(uids) for name, uids in splits.items()},
        "task_types": {name: _counts(uids) for name, uids in splits.items()},
        "sha256": digest,
    }
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def load_split(name: str, n: int | None = None) -> list[dict]:
    if name == "test":
        raise ValueError("the test split is not for this check")
    rows = json.loads((SPLIT_DIR / f"{name}.json").read_text(encoding="utf-8"))
    return rows if n is None else rows[:n]


def procedure_text() -> str:
    return PROCEDURE.read_text(encoding="utf-8")


def skill_section(text: str) -> str:
    body = (text or "").strip()
    if not body:
        return ""
    return f"{SKILL_SECTION_HEADER}\n\n{body}"


def task_description(root: Path, uid: str) -> str:
    traj = root / Path(uid).parent / "traj_data.json"
    if traj.is_file():
        payload = json.loads(traj.read_text(encoding="utf-8"))
        anns = ((payload.get("turk_annotations") or {}).get("anns")) or []
        if anns:
            desc = anns[0].get("task_desc") or ""
            if isinstance(desc, str) and desc.strip():
                return desc.strip()
        if payload.get("task_type"):
            return str(payload["task_type"])
    return Path(uid).parent.name


def parse_action(text: str, admissible: list[str]) -> tuple[str, bool]:
    """Return (action, admissible). Prefer <action> tags, then an exact list match."""
    raw = extract_action(text or "") or ""
    if not raw:
        lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
        raw = lines[-1] if lines else ""
        raw = re.sub(r"^action\s*:\s*", "", raw, flags=re.I).strip().strip("`\"'")
    folded = {re.sub(r"\s+", " ", item).strip().lower(): item for item in admissible}
    key = re.sub(r"\s+", " ", raw).strip().lower()
    if key in folded:
        return folded[key], True
    return raw, False


def _paper_prompt(task: str, skill: str, trace: list[dict], observation: str,
                  admissible: list[str]) -> str:
    recent = trace[-6:]
    history = "\n".join(f"> {item['action']}\n{item['observation'][:400]}" for item in recent) or "(none yet)"
    return SYSTEM_PROMPT.format(
        task_description=task,
        skill_section=skill,
        step_count=len(trace),
        history_length=len(recent),
        action_history=history,
        current_step=len(trace) + 1,
        current_observation=observation,
        admissible_actions=", ".join(admissible),
    )


class Session:
    """One ALFWORLD_PYTHON process. Reset it for each game."""

    def __init__(self, log_path: Path):
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self._err = log_path.open("w", encoding="utf-8")
        env = dict(os.environ)
        env["PYTHONPATH"] = str(WIKISKILL_SRC) + os.pathsep + env.get("PYTHONPATH", "")
        env.setdefault("ALFWORLD_DATA", str(Path.home() / ".cache" / "alfworld"))
        env.pop("OPENROUTER_API_KEY", None)
        self.proc = subprocess.Popen(
            [str(alfworld_python()), "-u", str(WORKER)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._err,
            text=True, env=env)

    def request(self, payload: dict, timeout: int = 180) -> dict:
        assert self.proc.stdin and self.proc.stdout
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()
        ready, _, _ = select.select([self.proc.stdout], [], [], timeout)
        if not ready:
            raise TimeoutError("ALFWorld worker timed out")
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError("ALFWorld worker closed its output")
        return json.loads(line)

    def close(self) -> None:
        try:
            if self.proc.stdin:
                self.proc.stdin.write(json.dumps({"op": "close"}) + "\n")
                self.proc.stdin.flush()
        except OSError:
            pass
        self.proc.kill()
        self._err.close()


def rollout_case(*, uid: str, model: str, skill_text: str = "", split: str = "val",
                 workspace: Path, session: Session, root: Path | None = None) -> dict:
    """One episode. score is 1 only when the environment reports won."""
    root = root or data_root()
    game = root / uid
    workspace.mkdir(parents=True, exist_ok=True)
    runtime = workspace / "runtime"
    runtime.mkdir(exist_ok=True)
    events_path = runtime / "tool-events.jsonl"
    events_path.write_text("", encoding="utf-8")
    task = task_description(root, uid)
    section = skill_section(skill_text)
    static = _STATIC + ("\n" + section if section else "")
    usage = Usage()
    trace: list[dict] = []
    invalid = 0
    error = ""
    won = False
    observation = ""
    admissible: list[str] = []
    try:
        state = session.request({"op": "reset", "game": str(game), "max_steps": MAX_STEPS})
        observation = str(state.get("observation") or "")
        admissible = [str(item) for item in state.get("admissible_actions") or []]
        won = bool(state.get("won"))
        for _ in range(MAX_STEPS):
            if won:
                break
            prompt = _paper_prompt(task, section, trace, observation, admissible)
            try:
                message = chat(model, [{"role": "user", "content": [
                    {"type": "text", "text": static, "cache_control": {"type": "ephemeral"}},
                    {"type": "text", "text": prompt},
                ]}], usage=usage, reasoning_effort=EFFORT, max_tokens=1024)
            except BudgetExceeded:
                raise
            except LLMError as exc:
                error = f"model_error: {exc}"
                break
            text = as_text(message.get("content"))
            action, ok = parse_action(text, admissible)
            if not ok:
                invalid += 1
                observation = "That action is not admissible. Copy one action from the list exactly."
                trace.append({"action": action or "(unparsed)", "observation": observation, "invalid": True})
                _event(events_path, action, observation, ok=False)
                continue
            state = session.request({"op": "step", "action": action, "step": len(trace) + 1})
            observation = str(state.get("observation") or "")
            admissible = [str(item) for item in state.get("admissible_actions") or []]
            won = bool(state.get("won"))
            trace.append({"action": action, "observation": observation, "invalid": False})
            _event(events_path, action, observation, ok=True)
            if won or state.get("done"):
                break
    except BudgetExceeded:
        raise
    except Exception as exc:  # the worker, not the model
        error = f"{type(exc).__name__}: {exc}"
    steps = len(trace)
    score = 1.0 if won and not error else 0.0
    if error.startswith("model_error"):
        fail = "model_error"
    elif error:
        fail = "exec_raised"
    elif score >= 1.0:
        fail = ""
    elif steps >= MAX_STEPS:
        fail = "step_cap"
    else:
        fail = "goal_unsatisfied"
    repeats = _repeat(trace)
    record = {
        "uid": uid, "split": split, "score": score, "fail_reason": fail,
        "model": model, "reported_model": ",".join(usage.as_dict()["reported_models"]),
        "skill_sha256": hashlib.sha256(skill_text.encode()).hexdigest() if skill_text.strip()
        else hashlib.sha256(b"").hexdigest(),
        "workspace": str(workspace), "returncode": 0 if not error else 1,
        "question": {"question": task, "task_type": task_type_of(uid)},
        "predicted": (trace[-1]["action"] if trace else "")[:500],
        "task_type": task_type_of(uid), "success": score >= 1.0,
        "steps": steps, "invalid_actions": invalid, "turns": steps,
        "repeated_action": repeats,
        "prompt_tokens": usage.prompt_tokens, "completion_tokens": usage.completion_tokens,
        "cost_usd": usage.as_dict()["cost_usd"], "usage": usage.as_dict(),
        "error": error,
    }
    (workspace / "outcome.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def _event(path: Path, action: str, observation: str, *, ok: bool) -> None:
    row = {"tool": "act", "arguments": {"action": action}, "ok": ok, "result": observation[:500]}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")


def _repeat(trace: list[dict]) -> str:
    best, run, prev = 0, 0, ""
    action = ""
    for item in trace:
        if item["action"] == prev:
            run += 1
        else:
            prev, run = item["action"], 1
        if run > best:
            best, action = run, item["action"]
    return action if best >= 4 else ""


def _done(path: Path) -> set[tuple]:
    if not path.is_file():
        return set()
    found = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("fail_reason") == "exec_raised" and not row.get("steps"):
            continue
        if row.get("score") in (0, 1, 0.0, 1.0):
            found.add((row.get("condition"), int(row.get("pass", 0)), row["uid"]))
    return found


def _append(path: Path, row: dict) -> None:
    with _lock:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")


def run_batch(rows: list[dict], *, model: str, condition: str, skill_text: str,
              pass_i: int, dest: Path, work: Path, workers: int) -> None:
    pending = [row for row in rows if (condition, pass_i, row["uid"]) not in _done(dest)]
    print(f"{model} {condition} pass={pass_i} pending {len(pending)}/{len(rows)} "
          f"spent=${spent():.4f}", flush=True)
    if not pending:
        return
    local = threading.local()

    def session() -> Session:
        held = getattr(local, "session", None)
        if held is None or held.proc.poll() is not None:
            held = Session(work / f"worker-{threading.get_ident()}.log")
            local.session = held
        return held

    def one(item: dict) -> dict:
        try:
            record = rollout_case(
                uid=item["uid"], model=model, skill_text=skill_text, split="val",
                workspace=work / f"p{pass_i}-{condition}" / Path(item["uid"]).parts[-3],
                session=session())
        except BudgetExceeded:
            raise
        except Exception as exc:
            record = {"uid": item["uid"], "score": 0, "fail_reason": "exec_raised",
                      "steps": 0, "invalid_actions": 0, "turns": 0, "cost_usd": 0.0,
                      "prompt_tokens": 0, "completion_tokens": 0, "success": False,
                      "task_type": item.get("task_type") or task_type_of(item["uid"]),
                      "error": f"{type(exc).__name__}: {exc}", "repeated_action": ""}
            print(f"error {item['uid']}: {record['error']}", flush=True)
        record["condition"] = condition
        record["pass"] = pass_i
        record["model"] = model
        _append(dest, record)
        return record

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(one, item): item["uid"] for item in pending}
        try:
            for future in as_completed(futures):
                future.result()
        except BudgetExceeded:
            print(f"budget stop spent=${spent():.4f}", flush=True)
            raise


def success_by_type(rows: list[dict]) -> dict:
    """Mean of per-pass success, by condition and ALFWorld task type."""
    grouped: dict[tuple, list[float]] = defaultdict(list)
    for row in rows:
        if row.get("fail_reason") == "exec_raised" and row.get("score") not in (0, 1, 0.0, 1.0):
            continue
        grouped[(row["condition"], int(row["pass"]), row.get("task_type") or task_type_of(row["uid"]))].append(
            float(row["score"]))
    by_pass: dict[tuple, list[float]] = defaultdict(list)
    for (condition, _pass, task), scores in grouped.items():
        by_pass[(condition, task)].append(sum(scores) / len(scores))
    out: dict[str, dict[str, float]] = defaultdict(dict)
    for (condition, task), accuracies in sorted(by_pass.items()):
        out[condition][task] = sum(accuracies) / len(accuracies)
    return dict(out)


def _summarize_file(path: Path) -> dict:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    # stats pairs the condition named "skill" with "empty".
    summary = summarize(rows)
    summary["by_task_type"] = success_by_type(rows)
    summary["invalid_action_rate"] = _invalid_rate(rows)
    summary["avg_steps"] = _avg_steps(rows)
    summary["repeat_loops"] = sum(1 for row in rows if row.get("repeated_action"))
    return summary


def _invalid_rate(rows: list[dict]) -> float | None:
    steps = sum(int(row.get("steps") or 0) for row in rows)
    invalid = sum(int(row.get("invalid_actions") or 0) for row in rows)
    return invalid / steps if steps else None


def _avg_steps(rows: list[dict]) -> float | None:
    if not rows:
        return None
    return sum(int(row.get("steps") or 0) for row in rows) / len(rows)


def smoke_report(path: Path) -> dict:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    kept = [row for row in rows if row.get("fail_reason") != "exec_raised" or row.get("steps")]
    n = len(rows)
    success = sum(float(row.get("score") or 0) for row in rows) / n if n else 0.0
    cost = sum(float(row.get("cost_usd") or 0) for row in rows)
    return {"n": n, "success": success, "avg_steps": _avg_steps(rows),
            "invalid_action_rate": _invalid_rate(rows),
            "cost_per_episode": cost / n if n else None, "spent": cost,
            "kept_rows": len(kept)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze-splits", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--model", default="")
    parser.add_argument("--run-dir", type=Path, default=None)
    parser.add_argument("--budget", type=float, default=0.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--smoke-n", type=int, default=10)
    args = parser.parse_args()
    if args.freeze_splits:
        manifest = write_splits()
        print(json.dumps(manifest["counts"]), json.dumps(manifest["task_types"]["val"]))
        return
    if args.budget <= 0 or not args.model or args.run_dir is None:
        raise SystemExit("smoke and run need --model, --run-dir, and --budget")
    load_env(PAPER / ".env")
    os.environ["ODSKILL_BUDGET_USD"] = str(args.budget)
    root = args.run_dir.expanduser()
    root.mkdir(parents=True, exist_ok=True)
    skill = procedure_text()
    games = load_split("val", args.smoke_n if args.smoke else None)
    dest = root / ("smoke.jsonl" if args.smoke else "rollouts.jsonl")
    stopped = False
    try:
        if args.smoke:
            run_batch(games, model=args.model, condition="empty", skill_text="",
                      pass_i=0, dest=dest, work=root / "attempts", workers=1)
        elif args.run:
            for pass_i in range(2):
                for condition, text in (("empty", ""), ("skill", skill)):
                    run_batch(games, model=args.model, condition=condition, skill_text=text,
                              pass_i=pass_i, dest=dest, work=root / "attempts",
                              workers=args.workers)
        else:
            raise SystemExit("pass --freeze-splits, --smoke, or --run")
    except BudgetExceeded:
        stopped = True
    if dest.is_file() and args.smoke:
        print(json.dumps(smoke_report(dest)), flush=True)
    elif dest.is_file():
        summary = _summarize_file(dest)
        summary.update({"model": args.model, "stopped": stopped, "effort": EFFORT})
        (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        diff = summary["difference"]
        print(f"verdict={summary['verdict']} empty={summary['empty']['mean']:.4f} "
              f"skill={summary['skill']['mean']:.4f} ci={diff['ci95']} stopped={stopped}", flush=True)
    print(f"spent=${spent():.4f}", flush=True)


if __name__ == "__main__":
    main()
