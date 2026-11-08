"""Pilot: run N SpreadsheetBench train tasks with no skills and report accuracy + real cost.

    python -m odskill.pilot --model anthropic/claude-haiku-5.5 --n 5
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from wikiskill.benchmarks.spreadsheet import load_cases

from .llm import load_env
from .spreadsheet import rollout_case

PAPER = Path(__file__).resolve().parents[2]
SPLITS = PAPER / "wikiskill/src/wikiskill/resources/spreadsheet/id_split"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="anthropic/claude-haiku-5.5")
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--split", default="train")
    ap.add_argument("--data", default=str(PAPER / "data/spreadsheet/spreadsheetbench_verified_400"))
    ap.add_argument("--runs", default=str(Path.home() / "odskill-runs/pilot"))
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    load_env(PAPER / ".env")
    cases = {c.uid: c for c in load_cases(Path(a.data))}
    ids = [x["uid"] if isinstance(x, dict) else x for x in json.loads((SPLITS / f"{a.split}.json").read_text())]
    picked = [cases[i] for i in ids[: a.n]]
    runs = Path(a.runs) / a.model.replace("/", "_")
    runs.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(a.workers) as ex:
        recs = list(ex.map(lambda c: rollout_case(c, workdir=runs, model=a.model, split=a.split), picked))
    for r in recs:
        u = r["usage"]
        print(f"{r['uid']:>10}  score={r['score']:.0f}  {r['fail_reason'] or 'ok':<24} turns={r['turns']:>2} "
              f"in={u['prompt_tokens']:>7} cached={u['cached_tokens']:>7} out={u['completion_tokens']:>6} "
              f"${u['cost_usd']:.4f}  {r['error'][:80]}")
    n = len(recs)
    tot = {k: sum(r["usage"][k] for r in recs) for k in ("prompt_tokens", "cached_tokens", "completion_tokens", "cost_usd")}
    print(f"\nmodel={a.model} n={n} acc={sum(r['score'] for r in recs)/n:.2f} "
          f"avg_in={tot['prompt_tokens']/n:.0f} avg_out={tot['completion_tokens']/n:.0f} "
          f"cache_hit={tot['cached_tokens']/max(1,tot['prompt_tokens']):.0%} "
          f"cost_total=${tot['cost_usd']:.4f} cost_per_task=${tot['cost_usd']/n:.4f}")
    (runs / "pilot_summary.json").write_text(json.dumps({"records": recs, "totals": tot}, indent=2, default=str))


if __name__ == "__main__":
    main()
