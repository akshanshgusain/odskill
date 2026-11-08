# Pilot check

Projected API cost: $0. Actual API cost: $0.
Recomputed with `odskill.selection.metrics.aggregate` from the raw rollout files.
Aggregate drops a row when its `error` field is non-empty. The error count is those rows.
Val, 2 passes, noise shuffle seed 0. Episodes is the raw row count.

| arm | noise_k | recall | precision | F1 | wrong-type rate | episodes | errored episodes |
|---|---:|---:|---:|---:|---:|---:|---:|
| plain | 100 | 0.958333 | 0.942623 | 0.950413 | 0.057377 | 120 | 0 |
| plain | 20 | 0.983333 | 0.929191 | 0.955481 | 0.070809 | 120 | 0 |
| directive | 100 | 0.991667 | 0.944444 | 0.967480 | 0.055556 | 120 | 0 |
| directive | 20 | 0.991667 | 0.881585 | 0.933378 | 0.111062 | 120 | 0 |
