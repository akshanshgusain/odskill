# odskill

On-demand skill loading + wiki-guided skill selection, built on Stahl-G/wikiskill.

## Setup (Mac, once)

```bash
cd ~/AWorkSpace/paper
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ./wikiskill[spreadsheet,paper] -e ./odskill
```

Key lives in `paper/.env` as `OPENROUTER_API_KEY=...` (git-ignored, never passed to model-run commands).

## Pilot (≈ $0.10–1)

```bash
python -m odskill.pilot --model anthropic/claude-haiku-5.5 --n 5
```

Runs 5 SpreadSheetBench train tasks with no skills. Prints accuracy, tokens and real cost per task.
Workspaces go to `~/odskill-runs/pilot/`.

Safety: the agent runs model-written shell commands inside each task workspace.
Fine for a small pilot; run full experiments inside Docker.

## Layout

- `odskill/llm.py` – OpenRouter client, usage + cost tracking, retries
- `odskill/agent.py` – tool loop (`bash`, optional `load_skill`)
- `odskill/skills.py` – skill-set parsing; all-in-prompt vs on-demand index
- `odskill/spreadsheet.py` – engine-compatible rollout (`mode='all'` or `'od'`), repo scorer
- `odskill/pilot.py` – pilot runner
