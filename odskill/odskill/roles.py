"""OpenRouter transport for the paper Maintainer and Proposer.

invoke() matches the PaperAgents contract: stage the payload, run read_file
and finish, and return the runtime directory. Bash is not offered to roles.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from wikiskill.isolated.tools_server import RoleTools, specs

from .llm import Usage, as_text, chat

MAX_TURNS = 40


def _openai_tool(spec: dict) -> dict:
    return {"type": "function", "function": {
        "name": spec["name"], "description": spec["description"],
        "parameters": spec["inputSchema"]}}


def _args(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _accepted_train_rates(skills_json: str, directory: Path) -> str:
    """Aggregate TRAIN load rates for the accepted skill map. Names and counts only."""
    try:
        skills = json.loads(skills_json or "{}")
    except json.JSONDecodeError:
        skills = {}
    if not isinstance(skills, dict) or not skills:
        return "No accepted skill in the latest TRAIN batch."
    path = directory.parent / "train" / "outcomes.jsonl"
    if not path.is_file():
        return "Latest TRAIN batch is not available."
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    lines = []
    for name in sorted(skills):
        hits = 0
        for row in rows:
            loaded = {item["name"] if isinstance(item, dict) else item
                      for item in row.get("loaded_skills") or []}
            if name in loaded:
                hits += 1
        lines.append(f"{name}: loaded in {hits}/{len(rows)} TRAIN tasks.")
    return "\n".join(lines)


def selection_evidence(payload: dict, directory: Path) -> str:
    """Wikisel-only block. Other arms do not stage wiki/selection-impact.md."""
    if "wiki/selection-impact.md" not in payload:
        return ""
    impact = str(payload["wiki/selection-impact.md"]).strip()
    rates = _accepted_train_rates(payload.get("skills.json") or "{}", directory)
    return (
        "Selection evidence\n"
        "Harness aggregates only. No per-task validation details.\n\n"
        f"{impact}\n\n"
        "Accepted skills, latest TRAIN batch:\n"
        f"{rates}\n"
    )


def invoke(directory, payload, system, user, mode, model, effort, *, chat_fn=None):
    """Stage directory/input, run the role, and return directory/runtime."""
    if mode not in ("maintainer", "proposer"):
        raise ValueError("role tools are read_file and finish only")
    directory = Path(directory)
    block = selection_evidence(payload, directory)
    if block:
        user = block + "\n" + user
    work = directory / "input"
    control = directory / "runtime"
    control.mkdir(parents=True, exist_ok=True)
    for name, text in payload.items():
        path = work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    events_path = control / "tool-events.jsonl"
    if events_path.exists() and not (control / "submission.json").exists():
        events_path.unlink()
    server = RoleTools(work, control, mode, sys.executable)
    tools = [_openai_tool(spec) for spec in specs(mode) if spec["name"] != "bash"]
    messages = [
        {"role": "system", "content": [
            {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]},
        {"role": "user", "content": user}]
    usage = Usage()
    complete = chat_fn or chat
    final = ""
    finished = False

    def dump() -> None:
        (control / "transcript.json").write_text(
            json.dumps(messages, indent=1, default=str), encoding="utf-8")
        (control / "usage.json").write_text(
            json.dumps(usage.as_dict(), indent=2) + "\n", encoding="utf-8")

    try:
        for turn in range(1, MAX_TURNS + 1):
            msg = complete(model, messages, tools, usage=usage,
                           reasoning_effort=effort or None, max_tokens=8192)
            calls = msg.get("tool_calls") or []
            messages.append({k: v for k, v in msg.items() if k in ("role", "content", "tool_calls")})
            text = as_text(msg.get("content"))
            if text:
                final = text
            if not calls:
                break
            for call in calls:
                name = call["function"]["name"]
                args = _args(call["function"].get("arguments"))
                record = {"tool": name, "arguments": args}
                try:
                    if name == "bash":
                        raise PermissionError("bash is not available to paper roles")
                    value = server.call(name, args)
                    record.update(ok=True, result=value)
                    content = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
                    finished = name == "finish"
                except Exception as exc:  # ContractError and the rest go back to the model
                    record.update(ok=False, error=f"{type(exc).__name__}: {exc}")
                    content = record["error"]
                with events_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                messages.append({"role": "tool", "tool_call_id": call.get("id") or f"call-{turn}",
                                 "content": content})
                if finished:
                    break
            if finished:
                break
        else:
            raise RuntimeError(f"{mode} did not finish within {MAX_TURNS} turns")
        if not (control / "submission.json").is_file():
            raise RuntimeError(f"{mode} stopped without a finish submission")
        (control / "final.txt").write_text(final or "Submission recorded.\n", encoding="utf-8")
        return control
    finally:
        dump()
