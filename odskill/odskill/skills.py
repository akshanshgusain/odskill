"""Parse a skill set and render it either all-in-prompt or as an on-demand index.

A skill set is stored as one text (the engine's format). Individual skills are
delimited by YAML-style frontmatter blocks:

    ---
    name: fix-date-columns
    description: Use when dates are stored as text ...
    ---
    <body>
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path

_FM = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S | re.M)


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    body: str
    raw: str = ""
    origin: str = "evolved"
    adjacent: bool = False

    def full(self) -> str:
        # raw is the original block. Evolved skills are never re-serialized.
        if self.raw:
            return self.raw if self.raw.endswith("\n") else self.raw + "\n"
        return f"---\nname: {self.name}\ndescription: {self.description}\n---\n{self.body.strip()}\n"


def parse(text: str) -> list[Skill]:
    text = text or ""
    starts = [m for m in _FM.finditer(text)]
    if not starts:
        body = text.strip()
        return [Skill("skill", "General guidance for this task type.", body, raw=body)] if body else []
    out = []
    for i, m in enumerate(starts):
        meta = {}
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip().lower()] = v.strip()
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        raw = text[m.start():end].strip()
        out.append(Skill(meta.get("name", f"skill-{i}"), meta.get("description", ""),
                         text[m.end():end], raw=raw))
    return out


def render_all(skills: list[Skill]) -> str:
    return "\n".join(s.full() for s in skills)


def render_index(skills: list[Skill]) -> str:
    """v1: name/description index in the task prompt."""
    if not skills:
        return ""
    lines = ["## Available skills (load on demand)",
             "Call the `load_skill` tool with a skill name to read its full instructions. "
             "Load a skill only if its description matches your task; you may load none.", ""]
    lines += [f"- **{s.name}**: {s.description}" for s in skills]
    return "\n".join(lines)


_INDEX_V2 = Path(__file__).resolve().parents[1] / "prompts" / "index_v2.md"


def index_v2_text() -> str:
    return _INDEX_V2.read_text(encoding="utf-8")


def index_v2_description(skills: list[Skill]) -> str:
    """v2: the tool description itself is the index. The comment in the file is not sent."""
    text = index_v2_text()
    if text.startswith("<!--"):
        text = text.split("-->", 1)[1]
    blocks = []
    for skill in skills:
        name = html.escape(" ".join(skill.name.split()), quote=False)
        description = html.escape(" ".join(skill.description.split()), quote=False)
        blocks.append(f"<skill>\n<name>{name}</name>\n<description>{description}</description>\n</skill>")
    return text.strip().replace("{available_skills}", "\n".join(blocks)) + "\n"


LOAD_SKILL_TOOL = {
    "type": "function",
    "function": {
        "name": "load_skill",
        "description": "Load the full instructions of one skill from the available skills index.",
        "parameters": {"type": "object",
            "properties": {"name": {"type": "string", "description": "Exact skill name from the index."}},
            "required": ["name"]},
    },
}


def load_skill_tool(skills: list[Skill], index: str = "v2") -> dict:
    if index == "v1":
        return LOAD_SKILL_TOOL
    if index != "v2":
        raise ValueError("index must be v1 or v2")
    return {"type": "function", "function": {
        "name": "load_skill",
        "description": index_v2_description(skills),
        "parameters": {"type": "object",
            "properties": {"name": {"type": "string",
                                    "description": "Exact skill name from <available_skills>."}},
            "required": ["name"]},
    }}
