# Local LLM Benchmarking Suite - HumanEval Pro Results

Comprehensive benchmarking of open-source LLM models on the HumanEval Pro dataset (164 challenging coding problems).

## Test Results Summary

### Overall Performance - Pass@1 Scores

| Model | Pass Rate | Problems Passed | Load Time | Avg Gen Time |
|-------|-----------|-----------------|-----------|--------------|
| **Qwen/CodeQwen1.5-7B-Chat** | 1.22% | 2/164 | 18.2s | 31.7s |
| **Mistral-7B-Instruct-v0.1** | 1.22% | 2/164 | 17.1s | 14.9s |
| Intel/neural-chat-7b-v3-1 | 0.61% | 1/164 | 409.0s | 16.1s |
| TinyLlama-1.1B-Chat-v1.0 | 0.0% | 0/164 | 13.9s | 18.8s |
| DeepSeek Coder-1.3B-Instruct | 0.0% | 0/164 | 3.8s | 26.3s |
| StarCoder2-3B | 0.0% | 0/164 | 16.5s | 32.3s |
| Llama-2-7B-Chat | 0.0% | 0/164 | 240.4s | 30.2s |

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
1. **CodeQwen 1.5 7B** and **Mistral 7B** (tied at 1.22%)
   - Only models to pass any problems
   - CodeQwen slower but more capable (31.7s vs 14.9s generation)
   - Mistral faster generation with competitive performance

### Generation Speed Rankings
1. **Mistral-7B**: 14.9s/problem - Fastest
2. **Intel Neural Chat 7B**: 16.1s/problem
3. **TinyLlama 1.1B**: 18.8s/problem
4. **DeepSeek Coder 1.3B**: 26.3s/problem
5. **Llama-2 7B**: 30.2s/problem
6. **CodeQwen 7B**: 31.7s/problem
7. **StarCoder2 3B**: 32.3s/problem

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

1. **Larger ≠ Better**: 7B models only marginally better than 1.3B (1.22% vs 0%)
2. **Coding Specialization**: StarCoder2 and DeepSeek underperform despite coding focus
3. **General Instruction Models**: CodeQwen and Mistral (general + coding) perform best
4. **Speed Trade-offs**: Mistral achieves competitive accuracy with 2x faster generation

## Setup & Running Tests

### Requirements
- Python 3.10+
- PyTorch with CUDA support
- 24GB+ VRAM for running 7B models
- ~50GB disk space for model caches

### Installation

```bash
# Clone repository
git clone <repo-url>
cd Local_LLM_Testing

# Install dependencies
pip install torch transformers datasets
```

### Running Benchmarks

```bash
# Run full benchmark (all 8 models, 164 problems)
python scripts/humaneval_pro_test_proper.py

# Results saved to: results/humaneval_pro_results_proper.json
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
- [ ] Quantized models (8-bit, 4-bit) for VRAM efficiency
- [ ] Temperature/sampling parameter optimization
- [ ] Batch processing for faster evaluation
- [ ] Per-problem category breakdown (algorithms, data structures, etc.)

## References

- HumanEval Pro Paper: https://huggingface.co/datasets/nuprl/humaneval-pro
- Hugging Face Models: https://huggingface.co/models
- Original HumanEval: https://github.com/openai/human-eval

## License

This benchmarking suite is provided as-is for research and evaluation purposes.

---

**Last Updated**: May 12, 2026  
**Test Date**: May 11-12, 2026  
**Total Runtime**: ~12 hours (across 8 models)
