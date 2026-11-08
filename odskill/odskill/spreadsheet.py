"""SpreadsheetBench rollout via OpenRouter, engine-compatible with wikiskill's rollout_case.

mode='all'  -> every skill injected verbatim into the prompt (original WikiSkill)
mode='od'   -> bodies via load_skill. index v2 lists skills in that tool; v1 lists them in the prompt.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path
from typing import Any

from wikiskill.benchmarks.spreadsheet import SYSTEM_PROMPT, SpreadsheetCase
from wikiskill.officeqa.rollout import SKILL_SECTION_HEADER
from wikiskill.spreadsheet.rollout import score_workbook

from .agent import run_agent
from .llm import BudgetExceeded, as_text
from .noise import mix
from .skills import render_index

SCRATCH = ".odskill"


def _sha(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def build(case: SpreadsheetCase, skills: list, workspace: Path, mode: str, index: str = "v2"):
    # v2 keeps the prompt's skill section empty: the index is the load_skill description.
    if mode == "all" and skills:
        section = f"{SKILL_SECTION_HEADER}\n\n" + "\n\n".join(s.full().strip() for s in skills)
    elif mode == "od" and index == "v1" and skills:
        section = render_index(skills)
    else:
        section = ""
    prefix = SYSTEM_PROMPT.format(skill_section=section)
    body = (f"working_directory: {workspace}\n"
            f"instruction: {case.instruction}\n"
            f"input_path: {workspace / case.init_name}\n"
            f"output_path: {workspace / 'output.xlsx'}\n"
            "Write concrete values (not formulas) into the answer region. "
            "Copy input_path to output_path first if you need a starting workbook. "
            "When the output file is written, reply with a one-line summary and stop.\n")
    return prefix, body, (skills if mode == "od" else None)


def rollout_case(case: SpreadsheetCase, *, workdir: Path, model: str, skill_text: str = "",
                 mode: str = "all", split: str = "val", max_turns: int = 25,
                 reasoning_effort: str | None = None, timeout_seconds: int = 120,
                 noise_k: int = 0, seed: int = 0, noise_library: list | None = None,
                 index: str = "v2", **_extra) -> dict[str, Any]:
    """Engine kwargs: workdir, model, reasoning_effort, skill_text, timeout_seconds."""
    if mode not in ("all", "od"):
        raise ValueError("mode must be 'all' or 'od'")
    if index not in ("v1", "v2"):
        raise ValueError("index must be v1 or v2")
    workspace = Path(workdir) / case.task_id
    if workspace.exists():
        shutil.rmtree(workspace)
    (workspace / SCRATCH).mkdir(parents=True)
    runtime = workspace / "runtime"
    runtime.mkdir()
    source = Path(case.task_dir)
    shutil.copy2(source / case.init_name, workspace / case.init_name)
    skills = mix(skill_text, noise_k, seed, noise_library)
    prefix, body, od = build(case, skills, workspace, mode, index)
    (workspace / SCRATCH / "prompt.md").write_text(prefix + "\n\n" + body, encoding="utf-8")
    t0 = time.time()
    try:
        res = run_agent(model=model, static_prefix=prefix, task_body=body, workdir=workspace,
                        skills_on_demand=od, max_turns=max_turns,
                        cmd_timeout=min(int(timeout_seconds), 120),
                        reasoning_effort=reasoning_effort, index=index,
                        transcript_path=workspace / SCRATCH / "transcript.json")
    except BudgetExceeded:
        raise
    events = res.get("tool_events") or []
    (runtime / "tool-events.jsonl").write_text(
        "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events), encoding="utf-8")
    # visible_trace falls back to session.jsonl when no tool receipts were recorded.
    (runtime / "session.jsonl").write_text("", encoding="utf-8")
    out = workspace / "output.xlsx"
    score, matched, total, scoring_error = 0.0, 0, 0, ""
    if out.is_file() and not res["error"]:
        try:
            score, matched, total = score_workbook(out, source / case.golden_name,
                                                   case.answer_sheet, case.answer_position)
            if total == 0:
                score, scoring_error = 0.0, "score_workbook compared zero cells"
        except Exception as e:  # noqa: BLE001
            scoring_error = f"{type(e).__name__}: {e}"
    if res["error"]:
        fail = "exec_raised"
    elif scoring_error:
        fail = "score_failed"
    elif score >= 1.0:
        fail = ""
    elif not out.is_file():
        fail = "missing_output_workbook"
    else:
        fail = "wrong_answer"
    rec = {
        "uid": case.task_id, "split": split, "score": score, "fail_reason": fail,
        "model": model, "reported_model": ",".join(res["usage"]["reported_models"]),
        "skill_sha256": _sha(skill_text) if skill_text.strip() else hashlib.sha256(b"").hexdigest(),
        "workspace": str(workspace), "returncode": 0 if not res["error"] else 1,
        "has_final_answer_tag": out.is_file(),
        "has_output_workbook": out.is_file(),
        "predicted": as_text(res["final"])[:500],
        "question": {"question": case.instruction, "instruction_type": case.instruction_type,
                     "answer_position": case.answer_position, "answer_sheet": case.answer_sheet},
        "matched_cells": matched, "total_cells": total, "mode": mode,
        "skill_set": [{"name": s.name, "origin": s.origin, "adjacent": s.adjacent} for s in skills],
        "loaded_skills": res["loaded_skills"], "turns": res["turns"], "usage": res["usage"],
        "duration_seconds": round(time.time() - t0, 1),
        "error": res["error"] or scoring_error,
    }
    (workspace / SCRATCH / "outcome.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
    return rec
