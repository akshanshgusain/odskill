"""Pre-registered choice of the Experiment 2 cell. No I/O."""

from __future__ import annotations

HAIKU = "anthropic/claude-haiku-5.5"
GAP = 0.10


def eligible(cell: dict) -> bool:
    """Haiku, neutral prompt, canonical at noise 20/100/300, or opaque at noise 100."""
    if cell.get("executor") != HAIKU or cell.get("agent_prompt") != "neutral":
        return False
    noise = int(cell.get("noise_k") or 0)
    names = cell.get("names")
    if names == "canonical":
        return noise in (20, 100, 300)
    if names == "opaque":
        return noise == 100
    return False


def decide(cells: list[dict]) -> dict | None:
    """Lowest plain F1 among eligible cells whose directive F1 leads by at least 0.10.

    Ties break toward the larger noise library, then canonical names.
    DeepSeek and forced-prompt cells are never eligible. None means do not run Experiment 2.
    """
    # 0.6 - 0.5 is 0.0999... in binary, so a true tenth must not fall short of GAP.
    qualified = [cell for cell in cells
                 if eligible(cell)
                 and float(cell["directive_f1"]) - float(cell["plain_f1"]) >= GAP - 1e-9]
    if not qualified:
        return None

    def key(cell: dict) -> tuple:
        canonical = 0 if cell["names"] == "canonical" else 1
        return (float(cell["plain_f1"]), -int(cell["noise_k"]), canonical)

    return min(qualified, key=key)


def _cell(executor: str, prompt: str, names: str, noise: int, plain: float, directive: float) -> dict:
    return {
        "cell": f"{prompt}-{names}-k{noise}-{executor.split('/')[-1]}",
        "executor": executor, "agent_prompt": prompt, "names": names, "noise_k": noise,
        "plain_f1": plain, "directive_f1": directive,
    }


DEEPSEEK = "deepseek/deepseek-v4.1-flash-1017"


def examples() -> list[tuple[str, list[dict], str]]:
    """The four cases the unit tests cover, and the cell id decide() returns."""
    winner = [
        _cell(HAIKU, "neutral", "canonical", 20, 0.30, 0.55),
        _cell(HAIKU, "neutral", "canonical", 300, 0.50, 0.80),
    ]
    tie = [
        _cell(HAIKU, "neutral", "canonical", 20, 0.40, 0.55),
        _cell(HAIKU, "neutral", "opaque", 100, 0.40, 0.55),
        _cell(HAIKU, "neutral", "canonical", 100, 0.40, 0.55),
    ]
    short = [
        _cell(HAIKU, "neutral", "canonical", 20, 0.40, 0.49),
        _cell(HAIKU, "neutral", "canonical", 300, 0.20, 0.29),
        _cell(HAIKU, "neutral", "opaque", 100, 0.10, 0.19),
    ]
    ineligible = [
        _cell(DEEPSEEK, "neutral", "canonical", 300, 0.05, 0.90),
        _cell(HAIKU, "forced", "canonical", 300, 0.05, 0.90),
        _cell(HAIKU, "neutral", "canonical", 100, 0.80, 0.85),
    ]
    tenth = [_cell(HAIKU, "neutral", "canonical", 100, 0.5, 0.6)]
    out = []
    for label, cells in (
        ("one clear winner", winner),
        ("tie on plain F1", tie),
        ("no gap of 0.10", short),
        ("deepseek and forced are not eligible", ineligible),
        ("gap of 0.6 - 0.5", tenth),
    ):
        chosen = decide(cells)
        out.append((label, cells, chosen["cell"] if chosen else "None"))
    return out
