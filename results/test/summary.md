# Test

Noise shuffle seed 0 for every evaluation. Intervals resample games and keep a game's passes together, 10,000 draws, seed 0.

## anthropic/claude-haiku-5.5

| arm | per-seed F1 | mean | sd |
|---|---|---:|---:|
| plain | s0=0.000 | 0.000 | 0.000 |
| directive | s0=0.078 | 0.078 | 0.000 |
| nowiki | s0=0.851, s1=0.744, s2=0.007 | 0.534 | 0.459 |
| wikisel | s0=0.000, s1=0.000, s2=0.000 | 0.000 | 0.000 |

### wikisel − nowiki

- recall: -0.456 [-0.493, -0.419]
- precision: -0.966 [-0.982, -0.949]
- f1: -0.620 [-0.653, -0.584]

### nowiki − plain

- recall: 0.456 [0.419, 0.493]
- precision: 0.966 [0.949, 0.982]
- f1: 0.620 [0.584, 0.653]

### wikisel − plain

- recall: 0.000 [0.000, 0.000]
- precision: 0.000 [0.000, 0.000]
- f1: 0.000 [0.000, 0.000]

### nowiki − directive

- recall: 0.415 [0.372, 0.456]
- precision: 0.029 [-0.047, 0.147]
- f1: 0.542 [0.482, 0.595]

### wikisel − directive

- recall: -0.041 [-0.075, -0.015]
- precision: -0.938 [-1.000, -0.818]
- f1: -0.078 [-0.137, -0.029]

## deepseek/deepseek-v4.1-flash-1017

| arm | per-seed F1 | mean | sd |
|---|---|---:|---:|
| plain | s0=0.015 | 0.015 | 0.000 |
| directive | s0=0.000 | 0.000 | 0.000 |
| nowiki | s0=0.681, s1=0.584, s2=0.641 | 0.635 | 0.049 |
| wikisel | s0=0.015, s1=0.014, s2=0.442 | 0.157 | 0.247 |

### wikisel − nowiki

- recall: -0.470 [-0.522, -0.415]
- precision: 0.055 [-0.029, 0.141]
- f1: -0.451 [-0.496, -0.405]

### nowiki − plain

- recall: 0.570 [0.505, 0.632]
- precision: -0.285 [-0.337, 0.764]
- f1: 0.624 [0.570, 0.674]

### wikisel − plain

- recall: 0.100 [0.072, 0.129]
- precision: -0.230 [-0.294, 0.823]
- f1: 0.173 [0.126, 0.218]

### nowiki − directive

- recall: 0.577 [0.512, 0.639]
- precision: 0.715 [0.658, 0.774]
- f1: 0.639 [0.592, 0.682]

### wikisel − directive

- recall: 0.107 [0.082, 0.134]
- precision: 0.770 [0.691, 0.852]
- f1: 0.188 [0.147, 0.228]
