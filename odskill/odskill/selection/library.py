"""Frozen ALFWorld type skills. Descriptions are swappable. Bodies are not."""

from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import replace
from pathlib import Path

from odskill.noise import mix
from odskill.skills import Skill, parse

ROOT = Path(__file__).resolve().parent / "frozen"
NAMES = (
    "look_at_obj_in_light",
    "pick_and_place",
    "pick_clean_then_place",
    "pick_cool_then_place",
    "pick_heat_then_place",
    "pick_two_obj_and_place",
)
# Game-folder prefix -> the one relevant skill.
TYPE_TO_SKILL = {
    "look_at_obj_in_light": "look_at_obj_in_light",
    "pick_and_place_simple": "pick_and_place",
    "pick_clean_then_place_in_recep": "pick_clean_then_place",
    "pick_cool_then_place_in_recep": "pick_cool_then_place",
    "pick_heat_then_place_in_recep": "pick_heat_then_place",
    "pick_two_obj_and_place": "pick_two_obj_and_place",
}
HEADINGS = ("When to Apply", "When NOT to Apply", "Instructions")


def opaque_mapping() -> dict[str, str]:
    """Fixed seed-0 shuffle. Opaque name -> canonical name. Noise skills are not in this map."""
    order = list(NAMES)
    random.Random(0).shuffle(order)
    return {f"skill_{i:02d}": name for i, name in enumerate(order, start=1)}


def present(skills: list[Skill], names: str) -> list[Skill]:
    """The library the executor sees. Opaque mode renames only the six type skills."""
    if names == "canonical":
        return list(skills)
    if names != "opaque":
        raise ValueError("names must be canonical or opaque")
    shown_as = {canonical: opaque for opaque, canonical in opaque_mapping().items()}
    out = []
    for skill in skills:
        opaque = shown_as.get(skill.name)
        if opaque is None:
            out.append(skill)
            continue
        raw = render_skill(opaque, skill.description, skill.body)
        out.append(replace(skill, name=opaque, raw=raw))
    return out


def canonical_name(shown: str, names: str) -> str:
    """Map a name the executor used back to the metric name. Noise names pass through."""
    if names == "opaque":
        return opaque_mapping().get(shown, shown)
    if names != "canonical":
        raise ValueError("names must be canonical or opaque")
    return shown


def relevant_skill(task_type: str) -> str:
    if task_type not in TYPE_TO_SKILL:
        raise KeyError("no selection skill for task type " + task_type)
    return TYPE_TO_SKILL[task_type]


def _read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = [name for name in NAMES if name not in data]
    if missing:
        raise KeyError("frozen file is missing " + ", ".join(missing))
    return {name: " ".join(str(data[name]).split()) for name in NAMES}


def plain_descriptions() -> dict[str, str]:
    return _read_json(ROOT / "plain.json")


def directive_descriptions() -> dict[str, str]:
    return _read_json(ROOT / "directive.json")


def bodies() -> dict[str, str]:
    path = ROOT / "bodies.json"
    if not path.is_file():
        raise FileNotFoundError("frozen bodies are missing; run --freeze-bodies once")
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = [name for name in NAMES if not str(data.get(name) or "").strip()]
    if missing:
        raise KeyError("frozen bodies missing " + ", ".join(missing))
    return {name: str(data[name]).strip() + "\n" for name in NAMES}


def body_sha256() -> str:
    payload = json.dumps(bodies(), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def render_skill(name: str, description: str, body: str) -> str:
    description = " ".join(description.split())
    return f"---\nname: {name}\ndescription: {description}\n---\n{body.strip()}\n"


def skill_text(descriptions: dict[str, str], frozen: dict[str, str] | None = None) -> str:
    """Six skills. The body bytes come from the frozen file, never from descriptions."""
    frozen = frozen if frozen is not None else bodies()
    blocks = [render_skill(name, descriptions[name], frozen[name]) for name in NAMES]
    text = "\n".join(blocks)
    for skill in parse(text):
        if skill.body.strip() != frozen[skill.name].strip():
            raise RuntimeError("skill body changed: " + skill.name)
    return text


def library(descriptions: dict[str, str], noise_k: int, seed: int,
            frozen: dict[str, str] | None = None) -> list[Skill]:
    """Six type skills plus the first noise_k noise skills, shuffled with seed."""
    text = skill_text(descriptions, frozen)
    skills = mix(text, noise_k, seed)
    frozen_bodies = {skill.name: skill.body.strip() for skill in parse(text)}
    out = []
    for skill in skills:
        if skill.name in NAMES and skill.body.strip() != frozen_bodies[skill.name]:
            raise RuntimeError("library rewrote a frozen body: " + skill.name)
        origin = "evolved" if skill.name in NAMES else "noise"
        out.append(replace(skill, origin=origin, adjacent=False))
    return out


def descriptions_of(text: str) -> dict[str, str]:
    found = {skill.name: " ".join(skill.description.split()) for skill in parse(text)}
    return {name: found.get(name, "") for name in NAMES}


def apply_descriptions(current: dict[str, str], updates: dict[str, str],
                       frozen: dict[str, str] | None = None) -> dict[str, str]:
    """Change only named descriptions. Unknown names are refused. Bodies are not here."""
    out = dict(current)
    for name, description in updates.items():
        if name not in NAMES:
            raise KeyError("unknown skill " + str(name))
        text = " ".join(str(description).split())
        if not text:
            raise ValueError("empty description for " + name)
        out[name] = text[:500]
    skill_text(out, frozen)
    return out


def validate_bodies(data: dict) -> dict[str, str]:
    out = {}
    for name in NAMES:
        body = str(data.get(name) or "").strip()
        if not body:
            raise ValueError("empty body for " + name)
        lines = body.splitlines()
        if len(lines) > 40:
            raise ValueError(f"{name} body is {len(lines)} lines; the cap is 40")
        for heading in HEADINGS:
            if not re.search(r"^#{1,6}\s+" + re.escape(heading) + r"\s*$", body, re.M):
                raise ValueError(f"{name} is missing {heading}")
        out[name] = body + "\n"
    return out


def write_bodies(data: dict, *, overwrite: bool = False) -> str:
    path = ROOT / "bodies.json"
    if path.is_file() and not overwrite:
        raise FileExistsError("bodies are frozen; refusing to write them again")
    cleaned = validate_bodies(data)
    path.write_text(json.dumps(cleaned, indent=2) + "\n", encoding="utf-8")
    digest = body_sha256()
    manifest = {
        "body_sha256": digest,
        "plain_sha256": hashlib.sha256((ROOT / "plain.json").read_bytes()).hexdigest(),
        "directive_sha256": hashlib.sha256((ROOT / "directive.json").read_bytes()).hexdigest(),
        "names": list(NAMES),
        "lines": {name: len(cleaned[name].strip().splitlines()) for name in NAMES},
    }
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return digest
