"""Description-only Maintainer and Proposer. Bodies are not a field they can edit.

nowiki sees descriptions, bodies, aggregate train metrics, and candidate history.
wikisel's proposer sees the wiki. Its maintainer sees sampled load traces.
"""

from __future__ import annotations

import json
from pathlib import Path

from wikiskill.paper_alignment.contracts import read_wiki, wiki_update

from odskill.llm import Usage, as_text, chat
from odskill.roles import invoke

from .library import NAMES, bodies as frozen_bodies

HAIKU = "anthropic/claude-haiku-5.5"
SONNET = "anthropic/claude-sonnet-5.5"
EFFORT = "low"
PROTECTED = {"selection-impact.md", "bodies.md", "descriptions.md", "catalog.md"}
_PROPOSER = (
    "You edit ALFWorld skill descriptions so the executor loads the one relevant skill. "
    "You cannot change skill bodies. Call read_file on the staged files, then finish "
    "with JSON {\"descriptions\": {skill_name: one line}}. Omit a skill to leave it unchanged. "
    "Names must be one of: " + ", ".join(NAMES) + "."
)
_WIKI_SENTENCE = " The wiki/ folder holds pattern pages written from training load traces."
_MAINTAINER = (
    "You keep a wiki of skill-selection failures. Read the staged traces. "
    "Each trace has the task text, the offered index, the loads, and the ground-truth skill. "
    "Write pattern pages named selection-<what happened>, for example "
    "selection-missed-heat-when-microwave-mentioned. "
    "finish with the four paper fields create_patterns, update_patterns, update_index, append_log. "
    "update_index must mention every pattern stem. Do not edit selection-impact, bodies, "
    "descriptions, or catalog."
)


def proposer_prompt(arm: str) -> str:
    if arm == "nowiki":
        return _PROPOSER
    if arm == "wikisel":
        return _PROPOSER + _WIKI_SENTENCE
    raise ValueError("no proposer for arm " + arm)


def proposer_files(arm: str, *, descriptions: dict[str, str], metrics: str, history: str,
                   wiki: dict[str, str], bodies_text: str | None = None) -> dict[str, str]:
    """Shared files, plus the maintainer's pattern pages for wikisel. Nothing else is staged."""
    files = {
        "descriptions.md": _describe(descriptions),
        "bodies.md": bodies_text if bodies_text is not None else _bodies_text(),
        "train_metrics.md": metrics,
        "history.md": history,
    }
    if arm == "nowiki":
        return files
    if arm != "wikisel":
        raise ValueError("no proposer for arm " + arm)
    for name, text in wiki.items():
        if name in ("index.md", "log.md") or name.startswith("patterns/"):
            files[f"wiki/{name}"] = text
    return files


def maintainer_files(traces: dict[str, str], wiki: dict[str, str]) -> dict[str, str]:
    files = {f"wiki/{name}": text for name, text in wiki.items()}
    files.update({f"traces/{name}": text for name, text in traces.items()})
    return files


def visible(files: dict[str, str], arm: str) -> None:
    """Raise if a payload contains something that arm must not see."""
    if arm == "nowiki":
        bad = [name for name in files if name.startswith("wiki/") or name.startswith("traces/")]
        if bad:
            raise RuntimeError("nowiki proposer can see " + ", ".join(bad))
    if arm == "wikisel":
        bad = [name for name in files if name.startswith("traces/")]
        if bad:
            raise RuntimeError("wikisel proposer can see traces")


def propose(directory: Path, files: dict[str, str], *, model: str = SONNET,
            chat_fn=None, arm: str = "nowiki") -> dict[str, str]:
    directory = Path(directory)
    work = directory / "input"
    for name, text in files.items():
        path = work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    tools = [
        {"type": "function", "function": {
            "name": "read_file",
            "description": "Read one staged file.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}},
                           "required": ["path"]}}},
        {"type": "function", "function": {
            "name": "finish",
            "description": "Submit description edits. This ends the turn.",
            "parameters": {"type": "object", "properties": {
                "descriptions": {"type": "object",
                                 "additionalProperties": {"type": "string"}}},
                "required": ["descriptions"]}}},
    ]
    listing = "\n".join(f"- {name}" for name in sorted(files))
    messages = [
        {"role": "system", "content": proposer_prompt(arm)},
        {"role": "user", "content": "Read the staged files, then finish with description edits only.\n" + listing}]
    complete = chat_fn or chat
    usage = Usage()
    seen: set[str] = set()
    updates: dict[str, str] = {}
    try:
        for turn in range(1, 9):
            message = complete(model, messages, tools, usage=usage, reasoning_effort=EFFORT, max_tokens=2048)
            calls = message.get("tool_calls") or []
            messages.append({"role": "assistant", "content": message.get("content"),
                             **({"tool_calls": calls} if calls else {})})
            if not calls:
                break
            for call in calls:
                name = call["function"]["name"]
                try:
                    args = json.loads(call["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                if name == "read_file":
                    path = str(args.get("path") or "")
                    seen.add(path)
                    content = _read(work, path)
                elif name == "finish":
                    if not seen:
                        content = "Read at least one staged file before finish."
                    else:
                        raw = args.get("descriptions") or {}
                        if not isinstance(raw, dict):
                            raise ValueError("descriptions must be an object")
                        updates = {str(k): str(v) for k, v in raw.items()}
                        (directory / "proposal.json").write_text(
                            json.dumps({"descriptions": updates}, indent=2) + "\n", encoding="utf-8")
                        return updates
                else:
                    content = "Unknown tool"
                messages.append({"role": "tool", "tool_call_id": call.get("id") or f"c{turn}",
                                 "content": content})
        return updates
    finally:
        (directory / "usage.json").write_text(
            json.dumps(usage.as_dict(), indent=2) + "\n", encoding="utf-8")


def maintain(directory: Path, files: dict[str, str], *, model: str = SONNET, chat_fn=None) -> dict:
    """Paper maintainer tools. Returns the wiki files after the edit. Protected pages stay."""
    directory = Path(directory)
    listing = "\n".join(f"- {name}" for name in sorted(files))
    invoke(directory, files, _MAINTAINER,
           "Read every traces/ file below, then finish with selection patterns.\n" + listing,
           "maintainer", model, EFFORT, chat_fn=chat_fn)
    proposal = json.loads((directory / "runtime" / "submission.json").read_text(encoding="utf-8"))
    _normalized, result = wiki_update(proposal["proposal"], read_wiki(directory / "input" / "wiki"))
    return {key: text for key, text in result.items() if key not in PROTECTED}


def apply_wiki(wiki_dir: Path, updated: dict[str, str]) -> None:
    for key, text in updated.items():
        if key in PROTECTED:
            continue
        path = wiki_dir / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _describe(descriptions: dict[str, str]) -> str:
    return "\n".join(f"{name}: {descriptions[name]}" for name in NAMES) + "\n"


def _bodies_text() -> str:
    frozen = frozen_bodies()
    return "\n\n".join(f"# {name}\n{frozen[name].strip()}" for name in NAMES) + "\n"


def _read(root: Path, name: str) -> str:
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        return "Not a file"
    return path.read_text(encoding="utf-8")


def read_text_arg(message: dict) -> str:
    return as_text(message.get("content"))
