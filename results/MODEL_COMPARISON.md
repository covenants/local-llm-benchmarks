# HumanEval Pro — Local Model Comparison

All runs use the same harness (`scripts/humaneval_pro_ollama.py`): identical
system prompt, temperature 0.0, 164 problems, generated code
executed against the dataset's assert test cases with a 10s timeout.

| Model | Pass | Fail | Pass rate | Avg gen | Throughput | Wall time |
|---|---:|---:|---:|---:|---:|---:|
| `qwen3-coder-next:q4_K_M` | 105 | 59 | **64.0%** | 7.6s | 23.5 tok/s | 21.3 min |
| `qwen3-coder-30b-iq4xs` | 99 | 65 | **60.4%** | 2.7s | n/a | 7.9 min |
| `qwen3.6:35b-a3b-coding` | 98 | 66 | **59.8%** | 6.6s | 38.1 tok/s | 18.6 min |

## Significance (exact McNemar, paired per-problem)

| A | B | A only | B only | p |
|---|---|---:|---:|---:|
| `qwen3-coder-next:q4_K_M` | `qwen3-coder-30b-iq4xs` | 13 | 7 | 0.263 (n.s.) |
| `qwen3-coder-next:q4_K_M` | `qwen3.6:35b-a3b-coding` | 17 | 10 | 0.248 (n.s.) |
| `qwen3-coder-30b-iq4xs` | `qwen3.6:35b-a3b-coding` | 8 | 7 | 1.000 (n.s.) |

Of 164 problems: **85** (51.8%) solved by every model, **116** (70.7%) by at least one (the oracle ceiling for routing between them), **48** (29.3%) by none.

## Divergence

- `qwen3-coder-next:q4_K_M`: solved alone: 10 [10, 11, 18, 41, 42, 72, 101, 119, 120, 126]; failed alone: 6 [67, 70, 77, 103, 118, 134]
- `qwen3-coder-30b-iq4xs`: solved alone: 1 [24]; failed alone: 3 [8, 91, 127]
- `qwen3.6:35b-a3b-coding`: solved alone: 4 [9, 19, 117, 154]; failed alone: 7 [59, 95, 99, 122, 137, 145, 150]
