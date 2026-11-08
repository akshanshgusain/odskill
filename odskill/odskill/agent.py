"""Generic tool-calling agent loop: a bash tool plus optional on-demand skill loading."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from .llm import BudgetExceeded, LLMError, Usage, as_text, chat
from .skills import Skill, load_skill_tool

BASH_TOOL = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Run a shell command (bash) in the working directory. Python 3 with openpyxl and pandas is available as `python`.",
        "parameters": {"type": "object",
            "properties": {"command": {"type": "string", "description": "The command to run."}},
            "required": ["command"]},
    },
}

MAX_TOOL_OUTPUT = 6000


def _run_bash(cmd: str, cwd: Path, timeout: int) -> str:
    env = dict(os.environ)
    env.pop("OPENROUTER_API_KEY", None)  # never expose the key to model-run code
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    try:
        p = subprocess.run(["bash", "-lc", cmd], cwd=cwd, capture_output=True, text=True,
                           timeout=timeout, env=env)
        out = (p.stdout or "") + (("\n[stderr]\n" + p.stderr) if p.stderr else "")
        out += f"\n[exit {p.returncode}]"
    except subprocess.TimeoutExpired:
        out = f"[timed out after {timeout}s]"
    if len(out) > MAX_TOOL_OUTPUT:
        out = out[:MAX_TOOL_OUTPUT // 2] + "\n...[truncated]...\n" + out[-MAX_TOOL_OUTPUT // 2:]
    return out


def _args(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def executor_tools(on_demand: bool, skills: list[Skill] | None = None, index: str = "v2") -> list:
    """Tool list placed on the outgoing executor request."""
    if not on_demand:
        return [BASH_TOOL]
    return [BASH_TOOL, load_skill_tool(skills or [], index)]


def run_agent(*, model: str, static_prefix: str, task_body: str, workdir: Path,
              skills_on_demand: list[Skill] | None = None, max_turns: int = 25,
              cmd_timeout: int = 120, transcript_path: Path | None = None,
              reasoning_effort: str | None = None, index: str = "v2") -> dict:
    """Run until the model stops calling tools. Returns usage, final text, loads, turns."""
    usage = Usage()
    # Static prefix (system frame + skills/index) is identical across tasks: mark it cacheable.
    messages = [{"role": "user", "content": [
        {"type": "text", "text": static_prefix, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": task_body}]}]
    transcript: list = []
    tools = executor_tools(bool(skills_on_demand), skills_on_demand, index)
    by_name: dict[str, Skill] = {}
    for skill in skills_on_demand or []:
        # An evolved skill keeps its name if a noise skill collides with it.
        if skill.origin == "evolved" or skill.name not in by_name:
            by_name[skill.name] = skill
    loaded: list[dict] = []
    events: list[dict] = []
    final, error, turns = "", "", 0
    for turns in range(1, max_turns + 1):
        try:
            msg = chat(model, messages, tools, usage=usage, reasoning_effort=reasoning_effort)
        except BudgetExceeded:
            raise
        except LLMError as e:
            error = str(e)
            break
        calls = msg.get("tool_calls") or []
        wire = {k: v for k, v in msg.items() if k in ("role", "content", "tool_calls")}
        messages.append(wire)
        extra = {k: msg[k] for k in ("reasoning", "reasoning_content", "reasoning_details") if msg.get(k)}
        transcript.append({**wire, **extra})
        if not calls:
            final = as_text(msg.get("content"))
            break
        for c in calls:
            name = c["function"]["name"]
            args = _args(c["function"].get("arguments"))
            if name == "bash":
                result = _run_bash(str(args.get("command", "")), workdir, cmd_timeout)
            elif name == "load_skill" and by_name:
                skill = by_name.get(str(args.get("name", "")).strip())
                if skill:
                    loaded.append({"name": skill.name, "origin": skill.origin,
                                   "adjacent": skill.adjacent, "turn": turns})
                    result = skill.full()
                else:
                    result = "Unknown skill. Available: " + ", ".join(by_name)
            else:
                result = f"Unknown tool {name}"
            events.append({"tool": name, "arguments": args, "result": result})
            tool_msg = {"role": "tool", "tool_call_id": c.get("id") or f"call-{turns}", "content": result}
            messages.append(tool_msg)
            transcript.append(tool_msg)
    else:
        error = error or f"max_turns ({max_turns}) reached"
    if transcript_path:
        transcript_path.write_text(json.dumps(transcript, indent=1, default=str), encoding="utf-8")
    return {"final": final, "error": error, "turns": turns, "loaded_skills": loaded,
            "tool_events": events, "usage": usage.as_dict()}
