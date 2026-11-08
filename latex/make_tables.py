"""Appendix table of every Experiment 1 cell, straight from results/exp1/cells.jsonl."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
cells = [json.loads(l) for l in (HERE.parent / "results/exp1/cells.jsonl").read_text().splitlines() if l.strip()]
assert len(cells) == 28
EXE = {"anthropic/claude-haiku-5.5": "Haiku", "deepseek/deepseek-v4.1-flash-1017": "DeepSeek"}
order = {"forced": 0, "neutral": 1}
cells.sort(key=lambda c: (c["names"] != "canonical", order[c["agent_prompt"]], c["noise_k"], c["executor"] != "anthropic/claude-haiku-5.5", c["arm"] != "plain"))
f = lambda v: f"{v:.3f}"
lines = []
prev = None
for c in cells:
    group = (c["names"], c["agent_prompt"])
    if prev is not None and group != prev:
        lines.append(r"\midrule")
    prev = group
    lo, hi = c["f1_ci95"]
    lines.append(" & ".join([c["agent_prompt"], "descriptive" if c["names"] == "canonical" else "opaque", str(c["noise_k"]),
                             EXE[c["executor"]], c["arm"], f(c["recall"]), f(c["precision"]), f(c["f1"]),
                             f"[{lo:.3f}, {hi:.3f}]", f(c["wrong_type_load_rate"]), f(c["noise_load_rate"]),
                             f(c["loaded_any"])]) + r" \\")
(HERE / "tables").mkdir(exist_ok=True)
(HERE / "tables/exp1_cells.tex").write_text("\n".join(lines) + "\n")
print(len(lines))
