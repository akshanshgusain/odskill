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
