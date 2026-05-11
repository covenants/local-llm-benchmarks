# Local LLM Benchmarking Suite

Comprehensive benchmarking and comparison of open-source language models for local inference. Tests 8 models across 4 tiers (1B to 13B parameters) with speed, quality, and resource usage metrics.

## Overview

This project benchmarks open-source LLMs on a **hard coding problem** (find longest substring without repeating characters) to evaluate:
- **Inference speed** (tokens/second)
- **Code quality** (0-10 scale based on function completeness, comments, docstrings, examples, error handling)
- **Resource usage** (VRAM, load time)
- **Practical viability** (time-to-first-output, interactive responsiveness)

**Hardware**: RTX 3090 (25.7GB VRAM)  
**Test Date**: May 11, 2026

---

## Key Results

| Model | Tier | Speed | Quality | Load Time | Status |
|-------|------|-------|---------|-----------|--------|
| **DeepSeek Coder 1.3B** | 1 | 18.70 tok/s | 6.0/10 | 29s | OK |
| **TinyLlama 1.1B** | 1 | 18.67 tok/s | 7.0/10 | 35s | OK |
| **StarCoder2 3B** [BEST] | 2 | 15.38 tok/s | 8.5/10 | 315s | OK |
| **Mistral 7B** | 3 | 12.47 tok/s | 6.5/10 | 322s | OK |
| Phi-2 2.7B | 2 | 5.47 tok/s | 0.0/10 | 59s | FAILED |
| CodeQwen 7B | 3 | 1.22 tok/s | 0.0/10 | 309s | FAILED |
| Llama-2 13B | 4 | 0.65 tok/s | 7.0/10 | 599s | TOO SLOW |
| DeepSeek Coder 6.7B | 3.5 | - | - | 311s | ERROR |

---

## Documentation

### Main Reports
- **FINAL_8_MODEL_COMPARISON_TABLE.md** - Complete comparison tables, rankings, and recommendations by use case
- **DETAILED_TIMING_ANALYSIS.md** - Comprehensive timing breakdowns with timelines and performance graphs for each model
- **LATEST_TIER34_REPORT.md** - Detailed Tier 3 & 4 testing results
- **COMPREHENSIVE_8_MODEL_COMPARISON.md** - Speed vs Quality analysis across all tiers

### Raw Data
- `latest_detailed_results.json` - Complete JSON results for all models
- `latest_tier34_results.json` - Tier 3 & 4 specific results

---

## Production Recommendations

### Best Overall: StarCoder2 3B
- Best balance of quality (8.5/10) and speed (15.38 tok/s)
- Ideal for: Production code generation, complex algorithms
- VRAM: 6GB
- Load time: 315s (worth it for persistent services)

### Best for Real-time APIs: DeepSeek Coder 1.3B
- Fastest overall (18.70 tok/s, 29s load)
- Ideal for: Time-critical applications, edge deployment
- VRAM: 3GB
- Quality: 6.0/10

### Best for Speed: TinyLlama 1.1B
- Fastest general model (18.67 tok/s, 2GB VRAM)
- Ideal for: Lightweight, high-throughput applications
- Quality: 7.0/10

### Avoid
- Phi-2 2.7B - Failed to generate output
- CodeQwen 7B - Generated only 1 token despite coding specialist label
- Llama-2 13B - Impractically slow (10+ minutes for first output)
- DeepSeek Coder 6.7B - Device mismatch error (GPU memory overflow)

---

## Testing Problem

All models tested with the same hard problem:

Find longest substring without repeating characters
Requirements:
1. Handle edge cases (empty string, single character, all repeating)
2. Optimize for O(n) time complexity
3. Include detailed comments explaining the algorithm
4. Add example usage and test cases
5. Produce complete, production-ready solution

---

## Key Insights

1. Size does not equal Quality: Phi-2 (2.7B) failed while DeepSeek (1.3B) succeeded
2. Specialization Matters: Coding-focused models outperform general models on code tasks
3. Load Time Varies Widely: 29s (DeepSeek) to 599s (Llama-2)
4. Speed/Quality Trade-off: Can't have both; StarCoder2 is best compromise
5. GPU Memory Critical: 13B+ models nearly max out 25.7GB GPU
6. Time-to-First-Output: Most important metric for user experience

---

## Quick Start

### Requirements
```
pip install -r requirements.txt
```

### Run Inference Test
```
python scripts/simple_inference_test.py
```

---

**Created**: May 11, 2026  
**GPU**: RTX 3090 (25.7GB VRAM)  
**Status**: Testing Complete
