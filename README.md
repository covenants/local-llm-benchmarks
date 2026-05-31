# Local LLM Benchmarking Suite - HumanEval Pro Results

Comprehensive benchmarking of open-source LLM models on the HumanEval Pro dataset (164 challenging coding problems).

## Test Results Summary

### Overall Performance - Pass@1 Scores

| Model | Pass Rate | Problems Passed | Quant | Avg Gen Time | Via |
|-------|-----------|-----------------|-------|--------------|-----|
| **Qwen3-Coder-30B-A3B-Instruct** | **60.4%** | **99/164** | IQ4_XS (15.3GB) | 2.7s | Ollama |
| Qwen/CodeQwen1.5-7B-Chat | 1.22% | 2/164 | FP16 | 31.7s | Transformers |
| Mistral-7B-Instruct-v0.1 | 1.22% | 2/164 | FP16 | 14.9s | Transformers |
| Intel/neural-chat-7b-v3-1 | 0.61% | 1/164 | FP16 | 16.1s | Transformers |
| TinyLlama-1.1B-Chat-v1.0 | 0.0% | 0/164 | FP16 | 18.8s | Transformers |
| DeepSeek Coder-1.3B-Instruct | 0.0% | 0/164 | FP16 | 26.3s | Transformers |
| StarCoder2-3B | 0.0% | 0/164 | FP16 | 32.3s | Transformers |
| Llama-2-7B-Chat | 0.0% | 0/164 | FP16 | 30.2s | Transformers |

> All tests run on an RTX 3090 (24GB VRAM). Qwen3-Coder result added May 31, 2026.

## Benchmark Details

### What is HumanEval Pro?

HumanEval Pro is a significantly harder variant of the original HumanEval benchmark. Each problem includes:

1. **Raw Problem**: The base function specification
2. **Raw Solution**: Reference implementation 
3. **New Problem**: An enhanced, harder version of the original
4. **Test Code**: Comprehensive test assertions
5. **Verification**: Pass@1 metric - the generated solution must pass all tests

The benchmark consists of **164 challenging coding problems** that test:
- Algorithm design and implementation
- Edge case handling
- Code correctness and efficiency
- Complex problem-solving abilities

### Evaluation Methodology

**Pass@1 Metric**: A solution is considered correct if it passes all test assertions on the first generation attempt without modification.

**Scoring**:
- Models generate code for the harder "new_problem" variant
- Generated code is combined with test assertions
- Tests are executed in a sandboxed environment
- Pass rate = (Passed / Total Problems) × 100%

## Key Findings

### Top Performers
1. **Qwen3-Coder-30B-A3B IQ4_XS** — 60.4% pass rate, 2.7s/problem
   - 50× improvement over the previous best (1.22%)
   - MoE architecture: 30B total / 3B active params — fits a 24GB card at 4-bit quant
   - 107 tok/s generation speed (faster than most 7B dense models due to MoE)
   - Served via Ollama using GGUF IQ4_XS (15.3GB on disk)
2. **CodeQwen 1.5 7B** and **Mistral 7B** (tied at 1.22%)
   - Best performers among dense FP16 models tested
   - CodeQwen slower but more capable (31.7s vs 14.9s generation)

### Generation Speed Rankings
1. **Qwen3-Coder-30B-A3B**: 2.7s/problem (107 tok/s — MoE advantage)
2. **Mistral-7B**: 14.9s/problem
3. **Intel Neural Chat 7B**: 16.1s/problem
4. **TinyLlama 1.1B**: 18.8s/problem
5. **DeepSeek Coder 1.3B**: 26.3s/problem
6. **Llama-2 7B**: 30.2s/problem
7. **CodeQwen 7B**: 31.7s/problem
8. **StarCoder2 3B**: 32.3s/problem

### Loading Performance
- **Fastest**: DeepSeek Coder 1.3B (3.8s)
- **Moderate**: TinyLlama 1.1B (13.9s), Mistral 7B (17.1s), CodeQwen 7B (18.2s)
- **Slowest**: Llama-2 7B (240.4s) - network download delays
- **Issue**: Neural Chat 7B (409.0s) - network timeouts during download

## Model Profiles

### Small Models (< 4B)
- **DeepSeek Coder 1.3B**: Fastest loading, poor performance (0%)
- **TinyLlama 1.1B**: General-purpose, baseline performance (0%)
- **StarCoder2 3B**: Coding-specialized, disappointing results (0%)

### Medium Models (7B)
- **CodeQwen 1.5 7B**: Best performer (1.22%), trade-off between quality and speed
- **Mistral 7B**: Fast + capable (1.22%), best speed/quality ratio
- **Llama-2 7B**: Popular baseline, no passes (0%), slow loading
- **Intel Neural Chat 7B**: Marginally better than 1B models (0.61%)

## Observations

### Why Low Pass Rates?

HumanEval Pro is significantly more difficult than the original HumanEval:
- Problems require deeper algorithmic understanding
- Edge cases are more complex and subtle
- Model training data may have limited coverage of these harder variants
- 1.22% pass rate is reasonable for models in this size range

### Model Patterns

1. **MoE architecture is a game-changer**: Qwen3-Coder-30B-A3B at 60.4% vs 1.22% for the best dense 7B — quantized MoE delivers far more capability per VRAM than dense models
2. **Larger ≠ Better (for dense)**: 7B dense models only marginally better than 1.3B (1.22% vs 0%)
3. **Coding Specialization**: StarCoder2 and DeepSeek underperform despite coding focus
4. **Speed paradox**: The 30B MoE generates faster than all 7B dense models (2.7s vs 14.9s+) because only 3B params are active per token

## Getting Started

### Requirements

- **Python 3.10+**
- **Ollama** — handles GPU acceleration, no CUDA toolkit needed
- **NVIDIA GPU with 20GB+ VRAM** (e.g. RTX 3090 / 4090) for full GPU inference
  - Smaller GPU or CPU: the model will still work but will be slower
- **~16GB free disk space** for the model file

---

### Step 1 — Install Ollama

Download and run the installer from **[ollama.com](https://ollama.com)**.

Ollama installs as a background service and starts automatically. You can verify it's running:

```bash
ollama --version
```

---

### Step 2 — Clone the repo and install Python packages

```bash
git clone https://github.com/covenants/local-llm-benchmarks.git
cd local-llm-benchmarks
pip install ollama huggingface_hub fastapi uvicorn
```

---

### Step 3 — Download the model (one-time, ~15.3 GB)

```bash
python scripts/qwen3_coder_smoke_test.py
```

This downloads the Qwen3-Coder-30B IQ4_XS GGUF file from Hugging Face, registers it with Ollama, runs a single coding prompt, and prints the throughput. Expected output on a 24GB GPU: **100+ tokens/sec**.

You only need to do this once. The model file is cached locally and reused on every subsequent run.

---

### Step 4 — Launch the code editor

```bash
python editor/app.py
```

Then open **http://localhost:8000** in your browser.

The editor gives you:
- **Monaco editor** (same engine as VS Code) with syntax highlighting and a minimap
- **AI panel** with one-click actions: Explain, Fix Bugs, Complete, Refactor, Write Tests, Add Docs
- **Streaming responses** — output appears token by token as the model generates
- **Insert into editor** — any code block in the AI response can be inserted directly at the cursor
- **File open / save** — works with `.py`, `.js`, `.ts`, `.java`, `.cpp`, `.rs`, `.go`, and more
- **Drag-to-resize** panel divider

To use it: write or paste code in the left panel, select a snippet if you want to target just that part, then click an action button or type a question in the chat input and press **Ctrl+Enter**.

---

### Using the model without the editor

**Terminal (interactive chat):**

```bash
ollama run qwen3-coder-30b-iq4xs
```

**Python script:**

```python
import ollama

response = ollama.chat(
    model="qwen3-coder-30b-iq4xs",
    messages=[{"role": "user", "content": "Write a binary search in Python. /no_think"}],
)
print(response["message"]["content"])
```

> Tip: append `/no_think` to your prompt to skip the model's internal reasoning step and get faster, more direct responses for straightforward coding tasks.

---

## Running the Benchmarks

```bash
# Qwen3-Coder-30B — full 164-problem HumanEval Pro
python scripts/qwen3_coder_humaneval_pro.py

# Smaller 7B dense models (requires PyTorch + CUDA, no Ollama needed)
pip install torch transformers datasets accelerate
python scripts/humaneval_pro_test_proper.py
```

### Customizing Tests

Edit `scripts/humaneval_pro_test_proper.py`:

```python
# Change models tested
MODELS = [
    "model1/name",
    "model2/name",
]

# Change problem count
MAX_PROBLEMS = 50  # Test only first 50 problems

# Adjust generation parameters
outputs = self.model.generate(
    inputs,
    max_new_tokens=512,      # Increase for longer solutions
    temperature=0.7,         # 0.0 = deterministic, 1.0 = random
    top_p=0.95,             # Nucleus sampling parameter
)
```

## File Structure

```
Local_LLM_Testing/
├── README.md                          # This file
├── scripts/
│   ├── humaneval_pro_test_proper.py   # Main benchmark script
│   ├── debug_test.py                  # Debug single model
│   └── verify_humaneval_setup.py      # Check dataset
├── humaneval_pro/
│   └── dataset/
│       └── humaneval_pro.json         # 164 benchmark problems
└── results/
    └── humaneval_pro_results_proper.json  # Test results
```

## Results Files

### `results/humaneval_pro_results_proper.json`

JSON file containing detailed results for each model:

```json
{
  "model": "model-name",
  "load_time": 18.19,          # Seconds to load model
  "total_problems": 164,        # Number of problems tested
  "passed": 2,                  # Number of correct solutions
  "failed": 162,                # Solutions that failed tests
  "timeout": 0,                 # Execution timeouts
  "error": 0,                   # Generation errors
  "pass_rate": 1.22,           # Percentage passed
  "avg_generation_time": 31.73  # Avg seconds per problem
}
```

## Recommendations

### For Production Code Generation
- **Best Choice**: Mistral 7B (fast, capable, no licensing restrictions)
- **Alternative**: CodeQwen 7B (slightly better quality, slower)

### For Research
- Use as-is for HumanEval Pro benchmarking
- Compare against other benchmark suites (HumanEval, MBPP)
- Fine-tune better-performing models on coding tasks

### For Limited Resources
- DeepSeek Coder 1.3B: Fastest loading and inference
- TinyLlama 1.1B: CPU-compatible baseline
- Trade-off: Performance for speed/memory

## Known Issues

1. **Phi-2 Model**: Failed to load - model ID format issue
   - Fix: Use `microsoft/phi-2` instead of `Phi-2`

2. **Download Timeouts**: Some models (Llama-2, Neural Chat) have network download issues
   - Hugging Face cache system limitations on Windows
   - Retries are automatic but slow

3. **Attention Mask Warnings**: Expected warnings when pad_token == eos_token
   - Does not affect results
   - Can be suppressed with attention mask implementation

## Future Improvements

- [ ] Add HumanEval (original) benchmark comparison
- [ ] Test MBPP (Mostly Basic Programming Problems) dataset
- [ ] Fine-tuned model evaluation
- [x] Quantized models (4-bit GGUF via Ollama) — Qwen3-Coder IQ4_XS added May 2026
- [ ] Temperature/sampling parameter optimization
- [ ] Batch processing for faster evaluation
- [ ] Per-problem category breakdown (algorithms, data structures, etc.)
- [ ] SWE-Bench Verified evaluation for Qwen3-Coder

## References

- HumanEval Pro Paper: https://huggingface.co/datasets/nuprl/humaneval-pro
- Hugging Face Models: https://huggingface.co/models
- Original HumanEval: https://github.com/openai/human-eval

## License

This benchmarking suite is provided as-is for research and evaluation purposes.

---

**Last Updated**: May 31, 2026  
**Test Dates**: May 11-12, 2026 (7B models) · May 31, 2026 (Qwen3-Coder-30B)  
**Total Runtime**: ~12 hours (7B dense models) · 7.9 min (Qwen3-Coder-30B IQ4_XS)
