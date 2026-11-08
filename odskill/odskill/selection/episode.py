"""ALFWorld episodes that stop at the first environment action, plus a full episode.

The load-only episode exists to score skill selection. It does not play the game out.
"""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from wikiskill.benchmarks.alfworld import SYSTEM_PROMPT

from odskill.alfworld import (
    MAX_STEPS, Session, data_root, parse_action, task_description, task_type_of,
)
from odskill.llm import BudgetExceeded, LLMError, Usage, as_text, chat
from odskill.skills import load_skill_tool

from .library import canonical_name, library, present, relevant_skill
from .metrics import score_loads

LOAD_TURNS = 5
EFFORT = "low"
_STATIC = (
    "You are an expert agent operating in the ALFRED Embodied Environment. "
    "A load_skill tool lists skills by name and description. "
    "Before you act, call load_skill for the skill whose description matches this task. "
    "You may call it more than once. Then output exactly one admissible action "
    "inside <action> tags.\n"
)
NEUTRAL = (
    "You are an expert agent operating in the ALFRED Embodied Environment. "
    "Output exactly one admissible action inside <action> tags.\n"
)
_lock = threading.Lock()


def static_prompt(agent_prompt: str) -> str:
    if agent_prompt == "forced":
        return _STATIC
    if agent_prompt == "neutral":
        return NEUTRAL
    raise ValueError("agent prompt must be forced or neutral")


def first_turn(agent_prompt: str, task: str, observation: str, admissible: list[str]) -> str:
    """The two user-text blocks of turn 1, in order. The tool description is separate."""
    return static_prompt(agent_prompt) + _prompt(task, observation, admissible, [])


def _prompt(task: str, observation: str, admissible: list[str], trace: list[dict]) -> str:
    recent = trace[-6:]
    history = "\n".join(
        f"> {item['action']}\n{item['observation'][:400]}" for item in recent) or "(none yet)"
    return SYSTEM_PROMPT.format(
        task_description=task, skill_section="", step_count=len(trace),
        history_length=len(recent), action_history=history,
        current_step=len(trace) + 1, current_observation=observation,
        admissible_actions=", ".join(admissible))


def _calls(message: dict) -> list[dict]:
    calls = []
    for call in message.get("tool_calls") or []:
        fn = call.get("function") or {}
        raw = fn.get("arguments")
        if isinstance(raw, dict):
            args = raw
        else:
            try:
                args = json.loads(raw or "{}")
            except json.JSONDecodeError:
                args = {}
        calls.append({"id": call.get("id") or "", "name": fn.get("name") or "", "arguments": args})
    return calls


def _act(text: str, admissible: list[str]) -> str:
    """The first environment action, or empty when this turn only loaded skills."""
    if "<action>" not in (text or "").lower() and not text.strip():
        return ""
    action, _ok = parse_action(text, admissible)
    if "<action>" in (text or "").lower():
        return action or "(unparsed)"
    return ""


class _Sessions:
    def __init__(self, work: Path):
        self.work = work
        self.local = threading.local()

    def get(self) -> Session:
        held = getattr(self.local, "session", None)
        if held is None or held.proc.poll() is not None:
            held = Session(self.work / f"worker-{threading.get_ident()}.log")
            self.local.session = held
        return held


def play(game: dict, *, model: str, descriptions: dict[str, str], noise_k: int, seed: int,
         session: Session, full: bool = False, root: Path | None = None,
         agent_prompt: str = "forced", names: str = "canonical") -> dict:
    """One game. full=False stops at the first action or 5 turns. full=True plays to 50."""
    root = root or data_root()
    uid = game["uid"]
    task_type = game.get("task_type") or task_type_of(uid)
    relevant = relevant_skill(task_type)
    skills = present(library(descriptions, noise_k, seed), names)
    by_name = {skill.name: skill for skill in skills}
    usage = Usage()
    loads: list[dict] = []
    error = ""
    action = ""
    won = False
    steps = 0
    invalid = 0
    observation = ""
    admissible: list[str] = []
    trace: list[dict] = []
    task = task_description(root, uid)
    tools = [load_skill_tool(skills, "v2")]
    messages = [{"role": "user", "content": [
        {"type": "text", "text": static_prompt(agent_prompt), "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": ""},
    ]}]
    limit = MAX_STEPS if full else LOAD_TURNS
    try:
        state = session.request({"op": "reset", "game": str(root / uid), "max_steps": MAX_STEPS})
        observation = str(state.get("observation") or "")
        admissible = [str(item) for item in state.get("admissible_actions") or []]
        won = bool(state.get("won"))
        for _turn in range(limit):
            if won:
                break
            messages[0]["content"][1]["text"] = _prompt(task, observation, admissible, trace)
            try:
                message = chat(model, messages, tools, usage=usage, reasoning_effort=EFFORT, max_tokens=1024)
            except BudgetExceeded:
                raise
            except LLMError as exc:
                error = f"model_error: {exc}"
                break
            text = as_text(message.get("content"))
            calls = _calls(message)
            wire = {"role": "assistant", "content": message.get("content")}
            if message.get("tool_calls"):
                wire["tool_calls"] = message["tool_calls"]
            messages.append(wire)
            for call in calls:
                if call["name"] != "load_skill":
                    result = "Unknown tool. Use load_skill, then an <action>."
                else:
                    name = str(call["arguments"].get("name") or "").strip()
                    skill = by_name.get(name)
                    if skill is None:
                        result = "Unknown skill. Use an exact name from the index."
                        loads.append({"name": name or "(unknown)", "origin": "unknown"})
                    else:
                        loads.append({
                            "name": canonical_name(skill.name, names),
                            "origin": skill.origin,
                        })
                        result = skill.full()
                messages.append({"role": "tool", "tool_call_id": call["id"] or f"load-{len(loads)}",
                                 "content": result[:6000]})
            proposed = _act(text, admissible)
            if not full:
                if proposed or not calls:
                    action = proposed
                    break
                continue
            if not proposed:
                if not calls:
                    break
                continue
            chosen, admissible_ok = parse_action(text, admissible)
            action = chosen or proposed
            if not admissible_ok:
                invalid += 1
                observation = "That action is not admissible. Copy one action from the list exactly."
                trace.append({"action": action, "observation": observation})
                steps += 1
                continue
            state = session.request({"op": "step", "action": chosen, "step": steps + 1})
            observation = str(state.get("observation") or "")
            admissible = [str(item) for item in state.get("admissible_actions") or []]
            won = bool(state.get("won"))
            trace.append({"action": chosen, "observation": observation})
            steps += 1
            action = chosen
            if won or state.get("done"):
                break
    except BudgetExceeded:
        raise
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    scored = score_loads(loads, relevant)
    record = {
        "uid": uid, "split": game.get("split", ""), "task_type": task_type, "relevant": relevant,
        "task": task, "model": model, "action": action, "won": won, "score": 1.0 if won and not error else 0.0,
        "steps": steps, "invalid_actions": invalid, "turns": usage.calls, "error": error,
        "cost_usd": usage.as_dict()["cost_usd"], "usage": usage.as_dict(),
        "full": full, **scored,
    }
    return record


def run_games(games: list[dict], *, model: str, descriptions: dict, noise_k: int, seed: int,
              dest: Path, work: Path, workers: int, full: bool = False, pass_i: int = 0,
              split: str = "val", agent_prompt: str = "forced", names: str = "canonical") -> list[dict]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    done = _done(dest, pass_i=pass_i, full=full)
    pending = [game for game in games if game["uid"] not in done]
    print(f"{model} {split} pass={pass_i} full={full} pending {len(pending)}/{len(games)}", flush=True)
    if not pending:
        return _rows(dest)
    sessions = _Sessions(work)
    written: list[dict] = []

    def one(game: dict) -> dict:
        record = play(game, model=model, descriptions=descriptions, noise_k=noise_k, seed=seed,
                      session=sessions.get(), full=full, agent_prompt=agent_prompt, names=names)
        record["pass"] = pass_i
        record["split"] = split
        _append(dest, record)
        return record

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(one, game) for game in pending]
        try:
            for future in as_completed(futures):
                written.append(future.result())
        except BudgetExceeded:
            print("budget stop", flush=True)
            raise
    return _rows(dest)


def _rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _done(path: Path, *, pass_i: int, full: bool) -> set[str]:
    found = set()
    for row in _rows(path):
        if int(row.get("pass", 0)) != pass_i or bool(row.get("full")) != full:
            continue
        if row.get("error") and not row.get("turns"):
            continue
        found.add(row["uid"])
    return found


def _append(path: Path, row: dict) -> None:
    with _lock:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")
