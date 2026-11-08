# Phases 3–6

Projected API cost of building this page: $0. Nothing here was launched.
Before a live phase the parent prints `spent + projection` and stops when that exceeds $40.

## Concurrency

- Experiment 1: at most 8 cells at once, 6 workers each. If CPU stays above 90% or an ALFWorld worker errors, drop to 4 cells and stay there.
- Each Experiment 1 process is capped at `min($1, $8 − spent − reserved)`. Eight running cells reserve at most $8.
- Experiment 2: write the three baselines first. Then the six evolutions run in parallel, detached, 6 workers each. Iterations inside a run stay sequential.
- Test: all 16 evaluations in parallel, 6 workers each.
- On HTTP 429, halve workers for that provider only (Anthropic or DeepSeek), then resume. Completed rows are kept.

## Phase 3 — Experiment 1

28 cells. Val 60, 1 pass, noise seed 0. The parent appends each process's stdout to `results/logs/<cell>.log`.

.venv/bin/python -u -m odskill.selection.exp1 --arm plain --agent-prompt forced --names canonical --noise-k 20 --executor anthropic/claude-haiku-5.5 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/forced-canonical-k20-haiku-plain

.venv/bin/python -u -m odskill.selection.exp1 --arm directive --agent-prompt forced --names canonical --noise-k 20 --executor anthropic/claude-haiku-5.5 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/forced-canonical-k20-haiku-directive

.venv/bin/python -u -m odskill.selection.exp1 --arm plain --agent-prompt forced --names canonical --noise-k 20 --executor deepseek/deepseek-v4.1-flash-1017 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/forced-canonical-k20-deepseek-plain

.venv/bin/python -u -m odskill.selection.exp1 --arm directive --agent-prompt forced --names canonical --noise-k 20 --executor deepseek/deepseek-v4.1-flash-1017 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/forced-canonical-k20-deepseek-directive

.venv/bin/python -u -m odskill.selection.exp1 --arm plain --agent-prompt forced --names canonical --noise-k 100 --executor anthropic/claude-haiku-5.5 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/forced-canonical-k100-haiku-plain

.venv/bin/python -u -m odskill.selection.exp1 --arm directive --agent-prompt forced --names canonical --noise-k 100 --executor anthropic/claude-haiku-5.5 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/forced-canonical-k100-haiku-directive

.venv/bin/python -u -m odskill.selection.exp1 --arm plain --agent-prompt forced --names canonical --noise-k 100 --executor deepseek/deepseek-v4.1-flash-1017 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/forced-canonical-k100-deepseek-plain

.venv/bin/python -u -m odskill.selection.exp1 --arm directive --agent-prompt forced --names canonical --noise-k 100 --executor deepseek/deepseek-v4.1-flash-1017 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/forced-canonical-k100-deepseek-directive

.venv/bin/python -u -m odskill.selection.exp1 --arm plain --agent-prompt forced --names canonical --noise-k 300 --executor anthropic/claude-haiku-5.5 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/forced-canonical-k300-haiku-plain

.venv/bin/python -u -m odskill.selection.exp1 --arm directive --agent-prompt forced --names canonical --noise-k 300 --executor anthropic/claude-haiku-5.5 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/forced-canonical-k300-haiku-directive

.venv/bin/python -u -m odskill.selection.exp1 --arm plain --agent-prompt forced --names canonical --noise-k 300 --executor deepseek/deepseek-v4.1-flash-1017 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/forced-canonical-k300-deepseek-plain

.venv/bin/python -u -m odskill.selection.exp1 --arm directive --agent-prompt forced --names canonical --noise-k 300 --executor deepseek/deepseek-v4.1-flash-1017 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/forced-canonical-k300-deepseek-directive

.venv/bin/python -u -m odskill.selection.exp1 --arm plain --agent-prompt neutral --names canonical --noise-k 20 --executor anthropic/claude-haiku-5.5 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/neutral-canonical-k20-haiku-plain

.venv/bin/python -u -m odskill.selection.exp1 --arm directive --agent-prompt neutral --names canonical --noise-k 20 --executor anthropic/claude-haiku-5.5 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/neutral-canonical-k20-haiku-directive

.venv/bin/python -u -m odskill.selection.exp1 --arm plain --agent-prompt neutral --names canonical --noise-k 20 --executor deepseek/deepseek-v4.1-flash-1017 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/neutral-canonical-k20-deepseek-plain

.venv/bin/python -u -m odskill.selection.exp1 --arm directive --agent-prompt neutral --names canonical --noise-k 20 --executor deepseek/deepseek-v4.1-flash-1017 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/neutral-canonical-k20-deepseek-directive

.venv/bin/python -u -m odskill.selection.exp1 --arm plain --agent-prompt neutral --names canonical --noise-k 100 --executor anthropic/claude-haiku-5.5 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/neutral-canonical-k100-haiku-plain

.venv/bin/python -u -m odskill.selection.exp1 --arm directive --agent-prompt neutral --names canonical --noise-k 100 --executor anthropic/claude-haiku-5.5 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/neutral-canonical-k100-haiku-directive

.venv/bin/python -u -m odskill.selection.exp1 --arm plain --agent-prompt neutral --names canonical --noise-k 100 --executor deepseek/deepseek-v4.1-flash-1017 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/neutral-canonical-k100-deepseek-plain

.venv/bin/python -u -m odskill.selection.exp1 --arm directive --agent-prompt neutral --names canonical --noise-k 100 --executor deepseek/deepseek-v4.1-flash-1017 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/neutral-canonical-k100-deepseek-directive

.venv/bin/python -u -m odskill.selection.exp1 --arm plain --agent-prompt neutral --names canonical --noise-k 300 --executor anthropic/claude-haiku-5.5 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/neutral-canonical-k300-haiku-plain

.venv/bin/python -u -m odskill.selection.exp1 --arm directive --agent-prompt neutral --names canonical --noise-k 300 --executor anthropic/claude-haiku-5.5 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/neutral-canonical-k300-haiku-directive

.venv/bin/python -u -m odskill.selection.exp1 --arm plain --agent-prompt neutral --names canonical --noise-k 300 --executor deepseek/deepseek-v4.1-flash-1017 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/neutral-canonical-k300-deepseek-plain

.venv/bin/python -u -m odskill.selection.exp1 --arm directive --agent-prompt neutral --names canonical --noise-k 300 --executor deepseek/deepseek-v4.1-flash-1017 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/neutral-canonical-k300-deepseek-directive

.venv/bin/python -u -m odskill.selection.exp1 --arm plain --agent-prompt neutral --names opaque --noise-k 100 --executor anthropic/claude-haiku-5.5 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/neutral-opaque-k100-haiku-plain

.venv/bin/python -u -m odskill.selection.exp1 --arm directive --agent-prompt neutral --names opaque --noise-k 100 --executor anthropic/claude-haiku-5.5 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/neutral-opaque-k100-haiku-directive

.venv/bin/python -u -m odskill.selection.exp1 --arm plain --agent-prompt neutral --names opaque --noise-k 100 --executor deepseek/deepseek-v4.1-flash-1017 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/neutral-opaque-k100-deepseek-plain

.venv/bin/python -u -m odskill.selection.exp1 --arm directive --agent-prompt neutral --names opaque --noise-k 100 --executor deepseek/deepseek-v4.1-flash-1017 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 1.00 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp1/neutral-opaque-k100-deepseek-directive

## Phase 4 — decision

`decide(cells)` returns the chosen cell, or None. A gap qualifies at `directive − plain >= 0.10 − 1e-9`.
Outputs below are from the synthetic cases.

### one clear winner

- neutral-canonical-k20-claude-haiku-5.5: plain 0.30, directive 0.55, gap 0.25
- neutral-canonical-k300-claude-haiku-5.5: plain 0.50, directive 0.80, gap 0.30
- decide -> neutral-canonical-k20-claude-haiku-5.5

### tie on plain F1

- neutral-canonical-k20-claude-haiku-5.5: plain 0.40, directive 0.55, gap 0.15
- neutral-opaque-k100-claude-haiku-5.5: plain 0.40, directive 0.55, gap 0.15
- neutral-canonical-k100-claude-haiku-5.5: plain 0.40, directive 0.55, gap 0.15
- decide -> neutral-canonical-k100-claude-haiku-5.5

### no gap of 0.10

- neutral-canonical-k20-claude-haiku-5.5: plain 0.40, directive 0.49, gap 0.09
- neutral-canonical-k300-claude-haiku-5.5: plain 0.20, directive 0.29, gap 0.09
- neutral-opaque-k100-claude-haiku-5.5: plain 0.10, directive 0.19, gap 0.09
- decide -> None

### deepseek and forced are not eligible

- neutral-canonical-k300-deepseek-v4.1-flash-1017: plain 0.05, directive 0.90, gap 0.85
- forced-canonical-k300-claude-haiku-5.5: plain 0.05, directive 0.90, gap 0.85
- neutral-canonical-k100-claude-haiku-5.5: plain 0.80, directive 0.85, gap 0.05
- decide -> None

### gap of 0.6 - 0.5

- neutral-canonical-k100-claude-haiku-5.5: plain 0.50, directive 0.60, gap 0.10
- decide -> neutral-canonical-k100-claude-haiku-5.5

## Phase 5 — Experiment 2

Commands use a placeholder Haiku cost of $0.001 per episode so the budget field is filled.
Per-run cap = 0.001 × 1140 × 1.3 + 2.50 = $3.98.
Six runs = $23.89. Three baselines = $0.23.
The live numbers replace 0.001 with the chosen cell's measured Haiku cost per episode.
Both arms of a seed are called as `run_evolution(root, cfg, baseline_rows=<that seed's rollouts>)`.

# baseline seed 0 plain
.venv/bin/python -u -m odskill.selection.exp1 --arm plain --agent-prompt neutral --names canonical --noise-k 100 --executor anthropic/claude-haiku-5.5 --seed 0 --split val --val-n 60 --passes 1 --workers 6 --budget 0.08 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp2/baseline-s0

# baseline seed 1 plain
.venv/bin/python -u -m odskill.selection.exp1 --arm plain --agent-prompt neutral --names canonical --noise-k 100 --executor anthropic/claude-haiku-5.5 --seed 1 --split val --val-n 60 --passes 1 --workers 6 --budget 0.08 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp2/baseline-s1

# baseline seed 2 plain
.venv/bin/python -u -m odskill.selection.exp1 --arm plain --agent-prompt neutral --names canonical --noise-k 100 --executor anthropic/claude-haiku-5.5 --seed 2 --split val --val-n 60 --passes 1 --workers 6 --budget 0.08 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp2/baseline-s2

# evolve seed 0 nowiki
.venv/bin/python -u -m odskill.selection.orchestrate exp2-run --go --arm nowiki --seed 0 --baseline /Users/akshanshgusain/AWorkSpace/paper/results/exp2/baseline-s0/rollouts.jsonl --agent-prompt neutral --names canonical --noise-k 100 --workers 6 --budget 3.98 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp2/nowiki-s0

# evolve seed 0 wikisel
.venv/bin/python -u -m odskill.selection.orchestrate exp2-run --go --arm wikisel --seed 0 --baseline /Users/akshanshgusain/AWorkSpace/paper/results/exp2/baseline-s0/rollouts.jsonl --agent-prompt neutral --names canonical --noise-k 100 --workers 6 --budget 3.98 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp2/wikisel-s0

# evolve seed 1 nowiki
.venv/bin/python -u -m odskill.selection.orchestrate exp2-run --go --arm nowiki --seed 1 --baseline /Users/akshanshgusain/AWorkSpace/paper/results/exp2/baseline-s1/rollouts.jsonl --agent-prompt neutral --names canonical --noise-k 100 --workers 6 --budget 3.98 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp2/nowiki-s1

# evolve seed 1 wikisel
.venv/bin/python -u -m odskill.selection.orchestrate exp2-run --go --arm wikisel --seed 1 --baseline /Users/akshanshgusain/AWorkSpace/paper/results/exp2/baseline-s1/rollouts.jsonl --agent-prompt neutral --names canonical --noise-k 100 --workers 6 --budget 3.98 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp2/wikisel-s1

# evolve seed 2 nowiki
.venv/bin/python -u -m odskill.selection.orchestrate exp2-run --go --arm nowiki --seed 2 --baseline /Users/akshanshgusain/AWorkSpace/paper/results/exp2/baseline-s2/rollouts.jsonl --agent-prompt neutral --names canonical --noise-k 100 --workers 6 --budget 3.98 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp2/nowiki-s2

# evolve seed 2 wikisel
.venv/bin/python -u -m odskill.selection.orchestrate exp2-run --go --arm wikisel --seed 2 --baseline /Users/akshanshgusain/AWorkSpace/paper/results/exp2/baseline-s2/rollouts.jsonl --agent-prompt neutral --names canonical --noise-k 100 --workers 6 --budget 3.98 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/exp2/wikisel-s2

## Phase 6 — test

134 games, noise seed 0 on every command, including descriptions that were evolved at seed 1 or 2.
Haiku: 2 passes, 8 description sets, 2144 episodes. DeepSeek: 1 pass, 8 sets, 1072 episodes.
Placeholder costs $0.001 Haiku and $0.002 DeepSeek give caps $2.79 and $2.79.

.venv/bin/python -u -m odskill.selection.evolve_desc --arm plain --agent-prompt neutral --names canonical --noise-k 100 --executor anthropic/claude-haiku-5.5 --seed 0 --split test --i-understand-this-is-the-test-split --passes 2 --workers 6 --budget 0.35 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/test/haiku/plain

.venv/bin/python -u -m odskill.selection.evolve_desc --arm directive --agent-prompt neutral --names canonical --noise-k 100 --executor anthropic/claude-haiku-5.5 --seed 0 --split test --i-understand-this-is-the-test-split --passes 2 --workers 6 --budget 0.35 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/test/haiku/directive

.venv/bin/python -u -m odskill.selection.evolve_desc --descriptions /Users/akshanshgusain/AWorkSpace/paper/results/exp2/nowiki-s0/descriptions.json --arm nowiki --agent-prompt neutral --names canonical --noise-k 100 --executor anthropic/claude-haiku-5.5 --seed 0 --split test --i-understand-this-is-the-test-split --passes 2 --workers 6 --budget 0.35 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/test/haiku/nowiki-s0

.venv/bin/python -u -m odskill.selection.evolve_desc --descriptions /Users/akshanshgusain/AWorkSpace/paper/results/exp2/nowiki-s1/descriptions.json --arm nowiki --agent-prompt neutral --names canonical --noise-k 100 --executor anthropic/claude-haiku-5.5 --seed 0 --split test --i-understand-this-is-the-test-split --passes 2 --workers 6 --budget 0.35 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/test/haiku/nowiki-s1

.venv/bin/python -u -m odskill.selection.evolve_desc --descriptions /Users/akshanshgusain/AWorkSpace/paper/results/exp2/nowiki-s2/descriptions.json --arm nowiki --agent-prompt neutral --names canonical --noise-k 100 --executor anthropic/claude-haiku-5.5 --seed 0 --split test --i-understand-this-is-the-test-split --passes 2 --workers 6 --budget 0.35 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/test/haiku/nowiki-s2

.venv/bin/python -u -m odskill.selection.evolve_desc --descriptions /Users/akshanshgusain/AWorkSpace/paper/results/exp2/wikisel-s0/descriptions.json --arm wikisel --agent-prompt neutral --names canonical --noise-k 100 --executor anthropic/claude-haiku-5.5 --seed 0 --split test --i-understand-this-is-the-test-split --passes 2 --workers 6 --budget 0.35 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/test/haiku/wikisel-s0

.venv/bin/python -u -m odskill.selection.evolve_desc --descriptions /Users/akshanshgusain/AWorkSpace/paper/results/exp2/wikisel-s1/descriptions.json --arm wikisel --agent-prompt neutral --names canonical --noise-k 100 --executor anthropic/claude-haiku-5.5 --seed 0 --split test --i-understand-this-is-the-test-split --passes 2 --workers 6 --budget 0.35 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/test/haiku/wikisel-s1

.venv/bin/python -u -m odskill.selection.evolve_desc --descriptions /Users/akshanshgusain/AWorkSpace/paper/results/exp2/wikisel-s2/descriptions.json --arm wikisel --agent-prompt neutral --names canonical --noise-k 100 --executor anthropic/claude-haiku-5.5 --seed 0 --split test --i-understand-this-is-the-test-split --passes 2 --workers 6 --budget 0.35 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/test/haiku/wikisel-s2

.venv/bin/python -u -m odskill.selection.evolve_desc --arm plain --agent-prompt neutral --names canonical --noise-k 100 --executor deepseek/deepseek-v4.1-flash-1017 --seed 0 --split test --i-understand-this-is-the-test-split --passes 1 --workers 6 --budget 0.35 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/test/deepseek/plain

.venv/bin/python -u -m odskill.selection.evolve_desc --arm directive --agent-prompt neutral --names canonical --noise-k 100 --executor deepseek/deepseek-v4.1-flash-1017 --seed 0 --split test --i-understand-this-is-the-test-split --passes 1 --workers 6 --budget 0.35 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/test/deepseek/directive

.venv/bin/python -u -m odskill.selection.evolve_desc --descriptions /Users/akshanshgusain/AWorkSpace/paper/results/exp2/nowiki-s0/descriptions.json --arm nowiki --agent-prompt neutral --names canonical --noise-k 100 --executor deepseek/deepseek-v4.1-flash-1017 --seed 0 --split test --i-understand-this-is-the-test-split --passes 1 --workers 6 --budget 0.35 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/test/deepseek/nowiki-s0

.venv/bin/python -u -m odskill.selection.evolve_desc --descriptions /Users/akshanshgusain/AWorkSpace/paper/results/exp2/nowiki-s1/descriptions.json --arm nowiki --agent-prompt neutral --names canonical --noise-k 100 --executor deepseek/deepseek-v4.1-flash-1017 --seed 0 --split test --i-understand-this-is-the-test-split --passes 1 --workers 6 --budget 0.35 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/test/deepseek/nowiki-s1

.venv/bin/python -u -m odskill.selection.evolve_desc --descriptions /Users/akshanshgusain/AWorkSpace/paper/results/exp2/nowiki-s2/descriptions.json --arm nowiki --agent-prompt neutral --names canonical --noise-k 100 --executor deepseek/deepseek-v4.1-flash-1017 --seed 0 --split test --i-understand-this-is-the-test-split --passes 1 --workers 6 --budget 0.35 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/test/deepseek/nowiki-s2

.venv/bin/python -u -m odskill.selection.evolve_desc --descriptions /Users/akshanshgusain/AWorkSpace/paper/results/exp2/wikisel-s0/descriptions.json --arm wikisel --agent-prompt neutral --names canonical --noise-k 100 --executor deepseek/deepseek-v4.1-flash-1017 --seed 0 --split test --i-understand-this-is-the-test-split --passes 1 --workers 6 --budget 0.35 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/test/deepseek/wikisel-s0

.venv/bin/python -u -m odskill.selection.evolve_desc --descriptions /Users/akshanshgusain/AWorkSpace/paper/results/exp2/wikisel-s1/descriptions.json --arm wikisel --agent-prompt neutral --names canonical --noise-k 100 --executor deepseek/deepseek-v4.1-flash-1017 --seed 0 --split test --i-understand-this-is-the-test-split --passes 1 --workers 6 --budget 0.35 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/test/deepseek/wikisel-s1

.venv/bin/python -u -m odskill.selection.evolve_desc --descriptions /Users/akshanshgusain/AWorkSpace/paper/results/exp2/wikisel-s2/descriptions.json --arm wikisel --agent-prompt neutral --names canonical --noise-k 100 --executor deepseek/deepseek-v4.1-flash-1017 --seed 0 --split test --i-understand-this-is-the-test-split --passes 1 --workers 6 --budget 0.35 --run-dir /Users/akshanshgusain/AWorkSpace/paper/results/test/deepseek/wikisel-s2

## Synthetic Experiment 1 summary

# Experiment 1

F1 intervals resample games, 10,000 draws, seed 0. A cell is flagged when its error rate is above 5%.

| cell | recall | precision | F1 | F1 95% CI | wrong-type | noise-load | loaded-any | errors | error rate | cost | $/episode | flag |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| synthetic-flagged | 1.000 | 1.000 | 1.000 | [1.000, 1.000] | 0.000 | 0.000 | 1.000 | 1 | 0.250 | 0.0040 | 0.001000 | YES |
| synthetic-clean | 1.000 | 1.000 | 1.000 | [1.000, 1.000] | 0.000 | 0.000 | 1.000 | 0 | 0.000 | 0.0040 | 0.001000 |  |

## Recall by task type

### synthetic-flagged
- pick_and_place_simple: 1.000
- pick_heat_then_place_in_recep: 1.000

### synthetic-clean
- pick_and_place_simple: 1.000
- pick_heat_then_place_in_recep: 1.000

## Synthetic test summary

# Test

Noise shuffle seed 0 for every evaluation. Intervals resample games and keep a game's passes together, 10,000 draws, seed 0.

## anthropic/claude-haiku-5.5

| arm | per-seed F1 | mean | sd |
|---|---|---:|---:|
| plain | s0=0.500 | 0.500 | 0.000 |
| directive | s0=0.750 | 0.750 | 0.000 |
| nowiki | s0=0.500, s1=0.500, s2=0.500 | 0.500 | 0.000 |
| wikisel | s0=0.750, s1=0.750, s2=0.750 | 0.750 | 0.000 |

### wikisel − nowiki

- recall: 0.250 [0.000, 0.750]
- precision: 0.250 [0.000, 0.750]
- f1: 0.250 [0.000, 0.750]

### nowiki − plain

- recall: 0.000 [0.000, 0.000]
- precision: 0.000 [0.000, 0.000]
- f1: 0.000 [0.000, 0.000]

### wikisel − plain

- recall: 0.250 [0.000, 0.750]
- precision: 0.250 [0.000, 0.750]
- f1: 0.250 [0.000, 0.750]

### nowiki − directive

- recall: -0.250 [-0.750, 0.000]
- precision: -0.250 [-0.750, 0.000]
- f1: -0.250 [-0.750, 0.000]

### wikisel − directive

- recall: 0.000 [0.000, 0.000]
- precision: 0.000 [0.000, 0.000]
- f1: 0.000 [0.000, 0.000]

## deepseek/deepseek-v4.1-flash-1017

| arm | per-seed F1 | mean | sd |
|---|---|---:|---:|
| plain | s0=0.500 | 0.500 | 0.000 |
| directive | s0=0.750 | 0.750 | 0.000 |
| nowiki | s0=0.500, s1=0.500, s2=0.500 | 0.500 | 0.000 |
| wikisel | s0=0.750, s1=0.750, s2=0.750 | 0.750 | 0.000 |

### wikisel − nowiki

- recall: 0.250 [0.000, 0.750]
- precision: 0.250 [0.000, 0.750]
- f1: 0.250 [0.000, 0.750]

### nowiki − plain

- recall: 0.000 [0.000, 0.000]
- precision: 0.000 [0.000, 0.000]
- f1: 0.000 [0.000, 0.000]

### wikisel − plain

- recall: 0.250 [0.000, 0.750]
- precision: 0.250 [0.000, 0.750]
- f1: 0.250 [0.000, 0.750]

### nowiki − directive

- recall: -0.250 [-0.750, 0.000]
- precision: -0.250 [-0.750, 0.000]
- f1: -0.250 [-0.750, 0.000]

### wikisel − directive

- recall: 0.000 [0.000, 0.000]
- precision: 0.000 [0.000, 0.000]
- f1: 0.000 [0.000, 0.000]
