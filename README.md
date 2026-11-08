# On-demand skill loading

Code and results for the paper experiments. Two projects sit side by side:

- `odskill/` is the experiment code. The importable package is `odskill/odskill/`.
- `wikiskill/` is [Stahl-G/wikiskill](https://github.com/Stahl-G/wikiskill) pinned at `da6984c`.

`data/` holds the frozen noise skills and spreadsheet tasks. `results/` holds the Experiment 1 cells, the Experiment 2 runs, and the test rollouts. `preflight/` holds the prompts and commands checked before those runs.

The OpenRouter key is not in this repository. Locally it belongs in `.env` as `OPEN_ROUTER_KEY`.

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e "./wikiskill[spreadsheet,paper]" -e ./odskill
git submodule update --init wikiskill
```

ALFWorld uses a separate environment, `.venv-alfworld`, which is not part of this repository.
