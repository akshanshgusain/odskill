"""Frozen noise skills sampled from the public SRA-Bench corpus.

The sample is data/noise_skills/noise_300.jsonl. Evolved skill text is never
rewritten; noise is only appended, then the combined list is shuffled.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import unicodedata
from dataclasses import replace
from pathlib import Path

from .skills import Skill

PAPER = Path(__file__).resolve().parents[2]
LIBRARY = PAPER / "data/noise_skills/noise_300.jsonl"
MANIFEST = PAPER / "data/noise_skills/manifest.json"

# Name + one-line description only. Bodies stay intact and are not used to classify.
ADJACENT = re.compile(
    r"spreadsheet|\bexcel\b|\bxlsx\b|\bxls\b|workbook|worksheet|openpyxl|\bxlwt\b|\bxlrd\b|"
    r"vlookup|pivot table|\bcsv\b|tabular|dataframe",
    re.I,
)
SAMPLE_N = 300
ADJACENT_N = 30  # 10% of the frozen sample
SOURCE = "https://huggingface.co/datasets/WeihangSu/SRA-Bench"
REVISION = "6143f2634eb284955ce312213bac24b582d039f3"


def one_line(text: str, limit: int = 240) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut or text[:limit]


def snake_name(name: str, source_id: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_")
    slug = re.sub(r"_+", "_", slug)
    if not re.fullmatch(r"[a-z][a-z0-9_]*", slug or ""):
        tail = re.sub(r"[^a-z0-9]+", "_", source_id.lower()).strip("_") or "unnamed"
        slug = "skill_" + tail
    return slug[:80].strip("_")


def _skill_from_row(row: dict) -> Skill:
    skill = Skill(row["name"], row["description"], row.get("body") or "",
                  origin="noise", adjacent=bool(row.get("adjacent")))
    return replace(skill, raw=skill.full())


def load(path: Path | None = None) -> list[Skill]:
    path = Path(path or LIBRARY)
    skills = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            skills.append(_skill_from_row(json.loads(line)))
    return skills


def mix(skill_text: str, noise_k: int, seed: int, library: list[Skill] | None = None) -> list[Skill]:
    """Evolved blocks, unchanged, plus the first noise_k library skills, shuffled."""
    from .skills import parse

    evolved = [replace(s, origin="evolved", adjacent=False) for s in parse(skill_text)]
    if noise_k <= 0:
        return evolved
    noise = list(library if library is not None else load())[:noise_k]
    taken = {s.name for s in evolved}
    adjusted = []
    for skill in noise:
        name = skill.name
        if name in taken:
            name = f"{name}_noise"
            skill = replace(skill, name=name, raw="")
            skill = replace(skill, raw=skill.full())
        taken.add(skill.name)
        adjusted.append(skill)
    pool = evolved + adjusted
    random.Random(seed).shuffle(pool)
    return pool


def is_adjacent(record: dict) -> bool:
    return bool(ADJACENT.search(f"{record.get('name', '')}\n{record.get('description', '')}"))


def sample_corpus(corpus_path: Path, dest: Path = LIBRARY, *, seed: int = 0,
                  n: int = SAMPLE_N, adjacent_n: int = ADJACENT_N) -> dict:
    """Draw a frozen sample from corpus.json. Does not invent skill text."""
    records = json.loads(Path(corpus_path).read_text(encoding="utf-8"))
    adjacent, rest = [], []
    for record in records:
        (adjacent if is_adjacent(record) else rest).append(record)
    adjacent.sort(key=lambda r: r["skill_id"])
    rest.sort(key=lambda r: r["skill_id"])
    if len(adjacent) < adjacent_n:
        raise RuntimeError(f"only {len(adjacent)} spreadsheet-adjacent skills; need {adjacent_n}")
    rng = random.Random(seed)
    picked = rng.sample(adjacent, adjacent_n) + rng.sample(rest, n - adjacent_n)
    rng.shuffle(picked)
    used: set[str] = set()
    rows = []
    for record in picked:
        base = snake_name(record.get("name") or "", record["skill_id"])
        name, i = base, 2
        while name in used:
            name = f"{base}_{i}"
            i += 1
        used.add(name)
        description = one_line(record.get("description") or "")
        if not description:
            description = one_line(record.get("content") or "") or record["skill_id"]
        body = record.get("content") or ""
        rows.append({
            "source_id": record["skill_id"],
            "original_name": record.get("name") or "",
            "name": name,
            "description": description,
            "body": body,
            "adjacent": is_adjacent(record),
        })
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    dest.write_text(payload, encoding="utf-8")
    manifest_path = dest.parent / "manifest.json"
    manifest = {
        "source": SOURCE,
        "paper": "Skill Retrieval Augmentation for Agentic AI (arXiv 2604.24594)",
        "revision": REVISION,
        "seed": seed,
        "count": len(rows),
        "corpus_count": len(records),
        "adjacent_pool": len(adjacent),
        "adjacent_count": sum(r["adjacent"] for r in rows),
        "adjacent_rule": ADJACENT.pattern,
        "adjacent": [{"source_id": r["source_id"], "name": r["name"],
                      "original_name": r["original_name"]} for r in rows if r["adjacent"]],
        "sha256": hashlib.sha256(payload.encode()).hexdigest(),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
