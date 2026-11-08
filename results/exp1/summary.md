# Experiment 1

F1 intervals resample games, 10,000 draws, seed 0. A cell is flagged when its error rate is above 5%.

| cell | recall | precision | F1 | F1 95% CI | wrong-type | noise-load | loaded-any | errors | error rate | cost | $/episode | flag |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| forced-canonical-k20-haiku-plain | 0.967 | 0.866 | 0.913 | [0.855, 0.960] | 0.134 | 0.000 | 1.000 | 0 | 0.000 | 0.0245 | 0.000408 |  |
| forced-canonical-k20-haiku-directive | 0.983 | 0.894 | 0.937 | [0.889, 0.976] | 0.106 | 0.000 | 1.000 | 0 | 0.000 | 0.0247 | 0.000412 |  |
| forced-canonical-k20-deepseek-plain | 0.967 | 0.868 | 0.915 | [0.851, 0.976] | 0.105 | 0.026 | 0.983 | 0 | 0.000 | 0.0306 | 0.000510 |  |
| forced-canonical-k20-deepseek-directive | 0.883 | 0.914 | 0.899 | [0.838, 0.952] | 0.071 | 0.000 | 0.900 | 0 | 0.000 | 0.0263 | 0.000438 |  |
| forced-canonical-k100-haiku-plain | 0.967 | 0.906 | 0.935 | [0.880, 0.983] | 0.094 | 0.000 | 1.000 | 0 | 0.000 | 0.0356 | 0.000593 |  |
| forced-canonical-k100-haiku-directive | 1.000 | 0.938 | 0.968 | [0.938, 0.992] | 0.062 | 0.000 | 1.000 | 0 | 0.000 | 0.0359 | 0.000598 |  |
| forced-canonical-k100-deepseek-plain | 0.767 | 0.839 | 0.801 | [0.708, 0.891] | 0.161 | 0.000 | 0.767 | 0 | 0.000 | 0.0466 | 0.000776 |  |
| forced-canonical-k100-deepseek-directive | 0.833 | 0.911 | 0.870 | [0.792, 0.938] | 0.089 | 0.000 | 0.850 | 0 | 0.000 | 0.0494 | 0.000823 |  |
| forced-canonical-k300-haiku-plain | 0.933 | 0.918 | 0.926 | [0.872, 0.974] | 0.082 | 0.000 | 0.950 | 0 | 0.000 | 0.0705 | 0.001175 |  |
| forced-canonical-k300-haiku-directive | 1.000 | 0.952 | 0.976 | [0.945, 1.000] | 0.048 | 0.000 | 1.000 | 0 | 0.000 | 0.0650 | 0.001083 |  |
| forced-canonical-k300-deepseek-plain | 0.783 | 0.981 | 0.871 | [0.800, 0.930] | 0.019 | 0.000 | 0.783 | 0 | 0.000 | 0.1121 | 0.001868 |  |
| forced-canonical-k300-deepseek-directive | 0.867 | 0.952 | 0.907 | [0.847, 0.958] | 0.048 | 0.000 | 0.867 | 0 | 0.000 | 0.0908 | 0.001513 |  |
| neutral-canonical-k20-haiku-plain | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 0 | 0.000 | 0.0106 | 0.000176 |  |
| neutral-canonical-k20-haiku-directive | 0.100 | 0.857 | 0.179 | [0.063, 0.301] | 0.143 | 0.000 | 0.100 | 0 | 0.000 | 0.0131 | 0.000218 |  |
| neutral-canonical-k20-deepseek-plain | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 0 | 0.000 | 0.0106 | 0.000177 |  |
| neutral-canonical-k20-deepseek-directive | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 0 | 0.000 | 0.0125 | 0.000209 |  |
| neutral-canonical-k100-haiku-plain | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 0 | 0.000 | 0.0175 | 0.000292 |  |
| neutral-canonical-k100-haiku-directive | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 0 | 0.000 | 0.0173 | 0.000289 |  |
| neutral-canonical-k100-deepseek-plain | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 0 | 0.000 | 0.0185 | 0.000309 |  |
| neutral-canonical-k100-deepseek-directive | 0.033 | 1.000 | 0.065 | [0.000, 0.154] | 0.000 | 0.000 | 0.033 | 0 | 0.000 | 0.0233 | 0.000388 |  |
| neutral-canonical-k300-haiku-plain | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 0 | 0.000 | 0.0337 | 0.000562 |  |
| neutral-canonical-k300-haiku-directive | 0.017 | 1.000 | 0.033 | [0.000, 0.095] | 0.000 | 0.000 | 0.017 | 0 | 0.000 | 0.0345 | 0.000575 |  |
| neutral-canonical-k300-deepseek-plain | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | 0.000 | 1.000 | 0.017 | 0 | 0.000 | 0.0442 | 0.000737 |  |
| neutral-canonical-k300-deepseek-directive | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 0 | 0.000 | 0.0427 | 0.000711 |  |
| neutral-opaque-k100-haiku-plain | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 0 | 0.000 | 0.0201 | 0.000334 |  |
| neutral-opaque-k100-haiku-directive | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 0 | 0.000 | 0.0180 | 0.000300 |  |
| neutral-opaque-k100-deepseek-plain | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 0 | 0.000 | 0.0367 | 0.000612 |  |
| neutral-opaque-k100-deepseek-directive | 0.000 | 0.000 | 0.000 | [0.000, 0.000] | 0.000 | 0.000 | 0.000 | 0 | 0.000 | 0.0361 | 0.000601 |  |

## Recall by task type

### forced-canonical-k20-haiku-plain
- look_at_obj_in_light: 0.900
- pick_and_place_simple: 1.000
- pick_clean_then_place_in_recep: 1.000
- pick_cool_then_place_in_recep: 1.000
- pick_heat_then_place_in_recep: 1.000
- pick_two_obj_and_place: 0.900

### forced-canonical-k20-haiku-directive
- look_at_obj_in_light: 1.000
- pick_and_place_simple: 1.000
- pick_clean_then_place_in_recep: 1.000
- pick_cool_then_place_in_recep: 1.000
- pick_heat_then_place_in_recep: 1.000
- pick_two_obj_and_place: 0.900

### forced-canonical-k20-deepseek-plain
- look_at_obj_in_light: 1.000
- pick_and_place_simple: 1.000
- pick_clean_then_place_in_recep: 0.900
- pick_cool_then_place_in_recep: 1.000
- pick_heat_then_place_in_recep: 1.000
- pick_two_obj_and_place: 0.900

### forced-canonical-k20-deepseek-directive
- look_at_obj_in_light: 0.900
- pick_and_place_simple: 1.000
- pick_clean_then_place_in_recep: 1.000
- pick_cool_then_place_in_recep: 0.900
- pick_heat_then_place_in_recep: 0.600
- pick_two_obj_and_place: 0.900

### forced-canonical-k100-haiku-plain
- look_at_obj_in_light: 0.900
- pick_and_place_simple: 1.000
- pick_clean_then_place_in_recep: 0.900
- pick_cool_then_place_in_recep: 1.000
- pick_heat_then_place_in_recep: 1.000
- pick_two_obj_and_place: 1.000

### forced-canonical-k100-haiku-directive
- look_at_obj_in_light: 1.000
- pick_and_place_simple: 1.000
- pick_clean_then_place_in_recep: 1.000
- pick_cool_then_place_in_recep: 1.000
- pick_heat_then_place_in_recep: 1.000
- pick_two_obj_and_place: 1.000

### forced-canonical-k100-deepseek-plain
- look_at_obj_in_light: 0.500
- pick_and_place_simple: 0.600
- pick_clean_then_place_in_recep: 0.800
- pick_cool_then_place_in_recep: 0.900
- pick_heat_then_place_in_recep: 0.800
- pick_two_obj_and_place: 1.000

### forced-canonical-k100-deepseek-directive
- look_at_obj_in_light: 0.800
- pick_and_place_simple: 0.700
- pick_clean_then_place_in_recep: 0.700
- pick_cool_then_place_in_recep: 0.900
- pick_heat_then_place_in_recep: 1.000
- pick_two_obj_and_place: 0.900

### forced-canonical-k300-haiku-plain
- look_at_obj_in_light: 0.800
- pick_and_place_simple: 1.000
- pick_clean_then_place_in_recep: 1.000
- pick_cool_then_place_in_recep: 1.000
- pick_heat_then_place_in_recep: 1.000
- pick_two_obj_and_place: 0.800

### forced-canonical-k300-haiku-directive
- look_at_obj_in_light: 1.000
- pick_and_place_simple: 1.000
- pick_clean_then_place_in_recep: 1.000
- pick_cool_then_place_in_recep: 1.000
- pick_heat_then_place_in_recep: 1.000
- pick_two_obj_and_place: 1.000

### forced-canonical-k300-deepseek-plain
- look_at_obj_in_light: 0.900
- pick_and_place_simple: 0.900
- pick_clean_then_place_in_recep: 0.700
- pick_cool_then_place_in_recep: 0.700
- pick_heat_then_place_in_recep: 0.800
- pick_two_obj_and_place: 0.700

### forced-canonical-k300-deepseek-directive
- look_at_obj_in_light: 1.000
- pick_and_place_simple: 0.700
- pick_clean_then_place_in_recep: 0.900
- pick_cool_then_place_in_recep: 0.800
- pick_heat_then_place_in_recep: 0.900
- pick_two_obj_and_place: 0.900

### neutral-canonical-k20-haiku-plain
- look_at_obj_in_light: 0.000
- pick_and_place_simple: 0.000
- pick_clean_then_place_in_recep: 0.000
- pick_cool_then_place_in_recep: 0.000
- pick_heat_then_place_in_recep: 0.000
- pick_two_obj_and_place: 0.000

### neutral-canonical-k20-haiku-directive
- look_at_obj_in_light: 0.400
- pick_and_place_simple: 0.000
- pick_clean_then_place_in_recep: 0.100
- pick_cool_then_place_in_recep: 0.100
- pick_heat_then_place_in_recep: 0.000
- pick_two_obj_and_place: 0.000

### neutral-canonical-k20-deepseek-plain
- look_at_obj_in_light: 0.000
- pick_and_place_simple: 0.000
- pick_clean_then_place_in_recep: 0.000
- pick_cool_then_place_in_recep: 0.000
- pick_heat_then_place_in_recep: 0.000
- pick_two_obj_and_place: 0.000

### neutral-canonical-k20-deepseek-directive
- look_at_obj_in_light: 0.000
- pick_and_place_simple: 0.000
- pick_clean_then_place_in_recep: 0.000
- pick_cool_then_place_in_recep: 0.000
- pick_heat_then_place_in_recep: 0.000
- pick_two_obj_and_place: 0.000

### neutral-canonical-k100-haiku-plain
- look_at_obj_in_light: 0.000
- pick_and_place_simple: 0.000
- pick_clean_then_place_in_recep: 0.000
- pick_cool_then_place_in_recep: 0.000
- pick_heat_then_place_in_recep: 0.000
- pick_two_obj_and_place: 0.000

### neutral-canonical-k100-haiku-directive
- look_at_obj_in_light: 0.000
- pick_and_place_simple: 0.000
- pick_clean_then_place_in_recep: 0.000
- pick_cool_then_place_in_recep: 0.000
- pick_heat_then_place_in_recep: 0.000
- pick_two_obj_and_place: 0.000

### neutral-canonical-k100-deepseek-plain
- look_at_obj_in_light: 0.000
- pick_and_place_simple: 0.000
- pick_clean_then_place_in_recep: 0.000
- pick_cool_then_place_in_recep: 0.000
- pick_heat_then_place_in_recep: 0.000
- pick_two_obj_and_place: 0.000

### neutral-canonical-k100-deepseek-directive
- look_at_obj_in_light: 0.000
- pick_and_place_simple: 0.000
- pick_clean_then_place_in_recep: 0.000
- pick_cool_then_place_in_recep: 0.100
- pick_heat_then_place_in_recep: 0.100
- pick_two_obj_and_place: 0.000

### neutral-canonical-k300-haiku-plain
- look_at_obj_in_light: 0.000
- pick_and_place_simple: 0.000
- pick_clean_then_place_in_recep: 0.000
- pick_cool_then_place_in_recep: 0.000
- pick_heat_then_place_in_recep: 0.000
- pick_two_obj_and_place: 0.000

### neutral-canonical-k300-haiku-directive
- look_at_obj_in_light: 0.000
- pick_and_place_simple: 0.000
- pick_clean_then_place_in_recep: 0.000
- pick_cool_then_place_in_recep: 0.100
- pick_heat_then_place_in_recep: 0.000
- pick_two_obj_and_place: 0.000

### neutral-canonical-k300-deepseek-plain
- look_at_obj_in_light: 0.000
- pick_and_place_simple: 0.000
- pick_clean_then_place_in_recep: 0.000
- pick_cool_then_place_in_recep: 0.000
- pick_heat_then_place_in_recep: 0.000
- pick_two_obj_and_place: 0.000

### neutral-canonical-k300-deepseek-directive
- look_at_obj_in_light: 0.000
- pick_and_place_simple: 0.000
- pick_clean_then_place_in_recep: 0.000
- pick_cool_then_place_in_recep: 0.000
- pick_heat_then_place_in_recep: 0.000
- pick_two_obj_and_place: 0.000

### neutral-opaque-k100-haiku-plain
- look_at_obj_in_light: 0.000
- pick_and_place_simple: 0.000
- pick_clean_then_place_in_recep: 0.000
- pick_cool_then_place_in_recep: 0.000
- pick_heat_then_place_in_recep: 0.000
- pick_two_obj_and_place: 0.000

### neutral-opaque-k100-haiku-directive
- look_at_obj_in_light: 0.000
- pick_and_place_simple: 0.000
- pick_clean_then_place_in_recep: 0.000
- pick_cool_then_place_in_recep: 0.000
- pick_heat_then_place_in_recep: 0.000
- pick_two_obj_and_place: 0.000

### neutral-opaque-k100-deepseek-plain
- look_at_obj_in_light: 0.000
- pick_and_place_simple: 0.000
- pick_clean_then_place_in_recep: 0.000
- pick_cool_then_place_in_recep: 0.000
- pick_heat_then_place_in_recep: 0.000
- pick_two_obj_and_place: 0.000

### neutral-opaque-k100-deepseek-directive
- look_at_obj_in_light: 0.000
- pick_and_place_simple: 0.000
- pick_clean_then_place_in_recep: 0.000
- pick_cool_then_place_in_recep: 0.000
- pick_heat_then_place_in_recep: 0.000
- pick_two_obj_and_place: 0.000
