# Local Coding Model Evaluation — September 2026

Re-evaluation of the local coding model lineup on HumanEval Pro, prompted by the
question of whether the 2024-era recommendations in `AVAILABLE_MODELS.md`
(DeepSeek Coder V2, Qwen2.5-Coder) are still the right picks.

## Hardware

| | |
|---|---|
| GPU | NVIDIA RTX 3090, 24 GB VRAM (~20 GB free) |
| System RAM | 256 GB |
| Runtime | Ollama 0.33.3 |

The 256 GB of system RAM matters: it makes MoE models far larger than VRAM
viable via expert offload, which is how `qwen3-coder-next` (53 GB) runs here at all.

## Results — HumanEval Pro, 164 problems

See `MODEL_COMPARISON.md` for the generated table, significance tests and
per-problem divergence. Summary:

| Model | Size | Pass rate | Speed | GPU/CPU split |
|---|---:|---:|---:|---|
| `qwen3-coder-next:q4_K_M` | 53 GB | **64.0%** (105/164) | 7.6 s/prob, 23.5 tok/s | 43% GPU / 57% CPU |
| `qwen3-coder-30b-iq4xs` (incumbent) | 16 GB | 60.4% (99/164) | 2.7 s/prob | ~100% GPU |
| `qwen3.6:35b-a3b-coding` | 22 GB | 59.8% (98/164) | 6.6 s/prob, 38.1 tok/s | 97% GPU |

## Findings

**1. No difference here is statistically significant.**
Exact McNemar over paired per-problem outcomes gives p = 0.26, 0.25 and 1.00 for
the three pairwise comparisons. At n=164 a 3-4 point gap is within noise. The
apparent ranking should not drive a migration decision on its own.

**2. The newest model is not the best model for this hardware.**
`qwen3-coder-next` leads on raw pass rate but is a 53 GB model on a 24 GB card.
It runs 57% on CPU and delivers 23.5 tok/s against the incumbent's ~2.7 s/problem
at full GPU residency. Roughly 3x the wall time for a difference that does not
clear significance.

**3. `qwen3.6:35b-a3b-coding` did not beat the incumbent** despite being newer and
larger, under matched (non-thinking) conditions — see the caveat below.

**4. The models are more complementary than their aggregate scores suggest.**
Only 85 problems (51.8%) are solved by all three, but 116 (70.7%) are solved by
at least one. That 70.7% oracle ceiling is ~7 points above any single model,
so routing or best-of-n across two models buys more than swapping one for another.

## On reasoning: disabling it was not a handicap

Qwen 3.6 and 3.8 builds return their chain of thought in a **separate `thinking`
response field and leave `content` empty**. The prompt-level `/no_think` token the
original baseline script relied on is silently ignored by these builds. Left
uncorrected, the model exhausts its entire token budget reasoning, returns no
parseable code, and scores 0% -- a harness artifact, not a capability measurement.

`scripts/humaneval_pro_ollama.py` therefore controls reasoning through Ollama's
API-level `think` flag, defaulting to **off** so results stay comparable to the
non-thinking `qwen3-coder-30b` baseline.

That default was initially assumed to understate Qwen 3.6. It does not. Measured
on the same 30 problems with an 8192-token budget:

| `qwen3.6:35b-a3b-coding` | Pass rate | Avg gen |
|---|---:|---:|
| thinking off | 16/30 (53.3%) | 7.0 s |
| thinking on | 14/30 (46.7%) | 28.4 s |

Three problems regressed and one improved. Only one regression was a token
cap-out; the other two produced confidently wrong code after reasoning. At n=30
the difference is not significant on its own, but there is no sign of the gain
that would justify 4x the wall time, so the non-thinking configuration is used
throughout and the main results are not depressed by that choice.

## Recommendation

**Stay on `qwen3-coder-30b-iq4xs` as the daily driver.** It fits entirely in VRAM,
is ~3x faster per problem, and its accuracy is statistically indistinguishable
from both newer models.

Keep `qwen3-coder-next` for work where quality matters more than latency — it
solved 10 problems no other model got. Reach for it deliberately, not by default.

`qwen3.6:35b-a3b-coding` has no clear niche on this hardware. It is neither
faster nor more accurate than the incumbent, and enabling its reasoning mode
made it slower and slightly worse rather than better.

## Reproducing

```bash
python scripts/humaneval_pro_ollama.py --model <ollama-tag>
python scripts/compare_humaneval_pro.py results/*.json --out results/MODEL_COMPARISON.md
```

Benchmark numbers quoted in vendor announcements and aggregator blogs were not
reproduced here and should not be treated as comparable to these runs.
