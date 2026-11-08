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
