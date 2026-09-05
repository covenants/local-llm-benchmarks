# Available Open-Source LLM Models Guide

> **OUTDATED as of September 2026.** The recommendations below (DeepSeek Coder
> 1.3B, StarCoder2 3B, CodeQwen 7B) date from 2024 and are no longer the right
> picks. They are kept for historical reference only.
>
> For current, measured recommendations see:
> - [`results/LOCAL_CODING_MODEL_EVAL.md`](results/LOCAL_CODING_MODEL_EVAL.md) --
>   HumanEval Pro across the current lineup, with significance testing
> - [`app_build_eval/RESULTS.md`](app_build_eval/RESULTS.md) --
>   whole-app build task, which exposes failures HumanEval Pro cannot see
> - [`agent_eval/RESULTS.md`](agent_eval/RESULTS.md) --
>   agentic tool-use loop
>
> Short version: **`qwen3-coder-30b-iq4xs` remains the best daily driver on a
> 24GB card.** Newer and larger local models were measured and did not beat it
> by a statistically significant margin.

This guide shows all viable models for your 24GB GPU, organized by parameter size and use case.

## 📊 Model Size Definitions

- **1B-2B**: Tiny, very fast, runs on CPU
- **3B-4B**: Small, still very fast, good for mobile/edge
- **6B-7B**: Balanced, good quality + speed, mainstream
- **12B-13B**: High quality, slower, still fits 24GB GPU
- **20B+**: Bleeding edge, requires 24GB+

## 🎯 Recommended for Your Setup

Based on your preferences (coding-focused, smaller models, 24GB GPU):

### ⭐ TOP PICKS FOR YOU

#### 1. DeepSeek Coder 1.3B ⭐⭐⭐ Smallest + Best Coding
```
Name: DeepSeek Coder 1.3B Instruct
Hugging Face ID: deepseek-ai/deepseek-coder-1.3b-instruct
Parameters: 1.3B
Size: ~2.6GB
Specialization: ✅ Excellent for coding
Speed: ⚡⚡⚡ Very Fast (50-70 tokens/sec on GPU)
Quality: ⭐⭐⭐⭐ Surprisingly good for size
VRAM: 3-4GB
Best For: Code generation, bug fixing, code review
```

#### 2. StarCoder2 3B ⭐⭐⭐ Small + Coding
```
Name: StarCoder2 3B
Hugging Face ID: bigcode/starcoder2-3b
Parameters: 3B
Size: ~6GB
Specialization: ✅ Purpose-built for code
Speed: ⚡⚡ Fast (35-45 tokens/sec on GPU)
Quality: ⭐⭐⭐⭐⭐ Excellent coding ability
VRAM: 7-8GB
Best For: Code generation, SQL, multiple languages
```

#### 3. CodeQwen 7B ⭐⭐⭐ Best Balance
```
Name: CodeQwen 1.5 7B Chat
Hugging Face ID: Qwen/CodeQwen1.5-7B-Chat
Parameters: 7B
Size: ~14GB
Specialization: ✅ Strong coding + general
Speed: ⚡ Moderate (20-30 tokens/sec on GPU)
Quality: ⭐⭐⭐⭐⭐ Excellent all-rounder
VRAM: 14-16GB
Best For: Code + general questions, production use
```

---

## 📚 Full Model List by Category

### 1️⃣ TINY MODELS (1B-2B) - CPU Compatible

| Model | Params | Size | Coding | Speed | VRAM |
|-------|--------|------|--------|-------|------|
| **DeepSeek Coder 1.3B** | 1.3B | 2.6GB | ✅✅✅ | 50-70 | 3-4GB |
| TinyLlama 1.1B Chat | 1.1B | 2.2GB | ✅ | 60+ | 2-3GB |
| Phi-2 Mini | 2.7B | 5.5GB | ✅✅ | 40+ | 6-7GB |

### 2️⃣ SMALL MODELS (3B-4B) - Laptop Friendly

| Model | Params | Size | Coding | Speed | VRAM |
|-------|--------|------|--------|-------|------|
| **StarCoder2 3B** | 3B | 6GB | ✅✅✅ | 35-45 | 7-8GB |
| Qwen1.5 3B | 3B | 6.1GB | ✅✅ | 35-45 | 7-8GB |
| Mistral 3B | 3B | 6GB | ✅✅ | 35-45 | 7-8GB |
| CodeShell 7B | 7B | 14GB | ✅✅✅ | 20-30 | 14-16GB |

### 3️⃣ BALANCED MODELS (6B-7B) - Sweet Spot

| Model | Params | Size | Coding | Speed | VRAM |
|-------|--------|------|--------|-------|------|
| **CodeQwen 7B** | 7B | 14GB | ✅✅✅ | 20-30 | 14-16GB |
| **Mistral 7B** | 7B | 14GB | ✅✅ | 25-35 | 14-16GB |
| Llama-2 7B Chat | 7B | 14GB | ✅✅ | 15-25 | 14-16GB |
| Phi-2 | 2.7B | 5.5GB | ✅✅ | 40+ | 6-8GB |
| **Neural Chat 7B** | 7B | 14GB | ✅✅✅ | 20-30 | 14-16GB |

### 4️⃣ LARGER MODELS (10B-13B) - High Quality

These need careful management on 24GB:

| Model | Params | Size | Coding | Speed | VRAM |
|-------|--------|------|--------|-------|------|
| **OpenHermes 2.5 (7B)** | 7B | 14GB | ✅✅ | 20-25 | 14-16GB |
| Dolphin 2.5 (7B) | 7B | 14GB | ✅✅ | 20-25 | 14-16GB |
| Qwen 7B Chat | 7B | 14GB | ✅✅ | 20-30 | 14-16GB |

---

## 🔧 Model Selection by Use Case

### 🚀 Best for Pure Coding

**Tier 1 (Recommended)**:
- DeepSeek Coder 1.3B - Tiny, excellent quality, very fast
- StarCoder2 3B - Small, specialized, great results

**Tier 2 (Best Quality)**:
- CodeQwen 7B - Largest coding specialist, best results
- Code Llama 7B - Meta's coding model (may need to accept terms)

### ⚡ Best for Speed

1. TinyLlama 1.1B - 60+ tokens/sec, general purpose
2. DeepSeek Coder 1.3B - 50-70 tokens/sec, coding
3. StarCoder2 3B - 35-45 tokens/sec, coding
4. Phi-2 - 40+ tokens/sec, general

### 🎯 Best All-Rounder

1. CodeQwen 7B - Excellent coding + general knowledge
2. Mistral 7B - Popular, reliable, good coding
3. Neural Chat 7B - Balanced performance across tasks

### 💻 Best for Limited Resources

- TinyLlama 1.1B (2.2GB) - Runs on most systems
- DeepSeek Coder 1.3B (2.6GB) - Coding + tiny size
- Phi-2 (5.5GB) - Good quality, still small

---

## 📥 Downloading Models Manually

If you want to experiment with other models:

```bash
# Download any model from Hugging Face
huggingface-cli download <model-id> --local-dir ./models/hf_models/<model-name>

# Examples:
huggingface-cli download deepseek-ai/deepseek-coder-1.3b-instruct --local-dir ./models/hf_models/DeepSeek-1.3B
huggingface-cli download meta-llama/Llama-2-7b-chat-hf --local-dir ./models/hf_models/Llama-2-7B
huggingface-cli download NousResearch/Hermes-2.5-Mistral-7B --local-dir ./models/hf_models/Hermes-7B
```

---

## 🔍 How to Find More Models

### On Hugging Face
1. Go to https://huggingface.co/models
2. Filter by:
   - **Task**: Text Generation
   - **Size**: 1B-13B parameter range
   - **License**: Open (MIT, Apache, etc.)

### Search Terms for Coding Models
- "code model"
- "coder" (DeepSeek Coder, StarCoder)
- "programming" (Code Llama, CodeGeeX)
- "instruct" or "chat" (instruction-tuned variants)

---

## 📈 Performance Comparison Table

### Tokens per Second (Higher = Faster)

```
TinyLlama 1.1B     ████████████████ 60+ tok/s
DeepSeek 1.3B      ██████████████ 50-70 tok/s
StarCoder2 3B      █████████ 35-45 tok/s
Phi-2 2.7B         █████████ 40+ tok/s
CodeQwen 7B        ██████ 20-30 tok/s
Mistral 7B         ████████ 25-35 tok/s
Llama-2 7B         █████ 15-25 tok/s
```

### Model Quality (Lower = Better for coding)

```
TinyLlama 1.1B     ⭐⭐⭐ Good for size
StarCoder2 3B      ⭐⭐⭐⭐ Very good
DeepSeek 1.3B      ⭐⭐⭐⭐ Excellent for 1.3B
CodeQwen 7B        ⭐⭐⭐⭐⭐ Excellent
Mistral 7B         ⭐⭐⭐⭐ Very good
```

---

## 🎓 Which Models to Test?

### Option 1: Quick Testing (2 hours)
- DeepSeek Coder 1.3B (2.6GB, very fast)
- StarCoder2 3B (6GB, specialized)
- CodeQwen 7B (14GB, best quality)

**Total size**: ~23GB ✅ Fits perfectly on your 24GB GPU

### Option 2: Comprehensive Testing (3 hours)
Add Mistral 7B or Phi-2 to Option 1

### Option 3: Maximum Coverage (4 hours)
- TinyLlama 1.1B (baseline)
- DeepSeek 1.3B (tiny coding)
- StarCoder2 3B (small coding)
- Phi-2 (balanced general)
- CodeQwen 7B (best coding)

---

## ⚙️ What We're Installing

The updated setup script includes:

1. ✅ **TinyLlama 1.1B** - General baseline
2. ✅ **DeepSeek Coder 1.3B** - Tiny + coding
3. ✅ **Phi-2 2.7B** - Balanced general
4. ✅ **StarCoder2 3B** - Small coding specialist
5. ✅ **CodeQwen 7B** - Best coding model

**Total**: 5 models, ~30GB, ~2 hours download, ~2 hours testing

---

## 🚀 Next Steps

1. Choose which models to test (use "Option 1: Quick Testing" as default)
2. Run `python scripts/setup_models.py`
3. Run `python scripts/inference_test.py`
4. Review results in `results/INFERENCE_RESULTS.md`
5. Pick best models for your use cases

---

## 📚 Resources

- **Hugging Face Models**: https://huggingface.co/models
- **Code Models**: https://huggingface.co/spaces/bigcode/leaderboard
- **Leaderboards**: https://huggingface.co/spaces/lmsys/chatbot-arena-leaderboard

