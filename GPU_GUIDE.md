# GPU Requirements & Configuration Guide

## 🎮 Your Hardware: GTX 24GB NVIDIA

Great! Your 24GB NVIDIA GPU is **excellent for local LLM inference**. Here's exactly what you can do:

## 📊 GPU Memory Requirements per Model

| Model | Size | VRAM Required | Can Run? | Performance |
|-------|------|---------------|----------|-------------|
| TinyLlama-1.1B | 2.2GB | 2-4GB | ✅ Yes | Excellent (40-60 tokens/sec) |
| Phi-2 (2.7B) | 5.5GB | 6-8GB | ✅ Yes | Great (25-40 tokens/sec) |
| Mistral-7B | 14GB | 14-16GB | ✅ Yes | Good (15-25 tokens/sec) |
| Llama-2-7B | 14GB | 14-16GB | ✅ Yes | Good (12-20 tokens/sec) |
| **All 4 together** | ~36GB | ~36GB | ⚠️ Marginal | Sequential testing only |

**Bottom Line**: With your 24GB GPU, you can comfortably:
- Run any single model at full quality
- Test all models sequentially (one at a time)
- Use FP16 precision (half-precision) to save ~50% memory if needed

## 🚀 Is GPU Required? Answer: NO, But Highly Recommended

### GPU vs CPU Performance

```
TinyLlama-1.1B Inference:
├── GPU (Your 24GB GTX): 40-60 tokens/sec  ⚡ Fast
└── CPU (8-core): 2-4 tokens/sec            🐢 10-15x slower

Mistral-7B Inference:
├── GPU (Your 24GB GTX): 15-25 tokens/sec  ⚡ Usable
└── CPU (8-core): 0.5-1 token/sec           🐢 20-30x slower
```

**Verdict**:
- ✅ GPU recommended: Makes a huge difference (10-30x speedup)
- ✅ You have good GPU: Your 24GB GTX is ideal
- ⚠️ CPU only possible: But responses will take 10-30 seconds for small text

## 🔧 GPU Configuration for Your Setup

### 1. Check Your GPU

Run this to verify GPU detection:

```powershell
python -c "import torch; print(f'GPU Available: {torch.cuda.is_available()}'); print(f'Device Name: {torch.cuda.get_device_name()}'); print(f'Device Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f}GB')"
```

Expected output:
```
GPU Available: True
Device Name: NVIDIA GeForce GTX ...
Device Memory: 24.00GB
```

### 2. Precision Options (Memory vs Quality)

Your 24GB GPU supports multiple precision levels:

#### FP32 (Full Precision)
```python
torch_dtype=torch.float32
```
- ✅ Best quality
- ⚠️ Uses full memory (requires ~2x model size)
- Recommended for: Testing, fine-tuning

#### FP16 (Half Precision) ⭐ Recommended
```python
torch_dtype=torch.float16
```
- ✅ Excellent quality, minimal loss
- ✅ Uses ~50% less VRAM
- ✅ Faster computation
- Recommended for: Production inference

#### INT8 (Quantized)
```python
load_in_8bit=True
```
- ✅ Uses ~75% less VRAM
- ⚠️ Slight quality reduction
- Recommended for: Very large models or low VRAM

### 3. Memory Management Script

Add this to `inference_test.py` to monitor GPU:

```python
import torch

def check_gpu_memory():
    """Check available GPU memory."""
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1e9
        total = torch.cuda.get_device_properties(0).total_memory / 1e9
        available = (total - allocated) / 1e9
        
        print(f"GPU Memory:")
        print(f"  Total: {total:.2f}GB")
        print(f"  Allocated: {allocated:.2f}GB")
        print(f"  Available: {available:.2f}GB")
        print(f"  Usage: {(allocated/total)*100:.1f}%")

# Call this before/after loading models
check_gpu_memory()
```

## 📋 Recommended Setup for Your 24GB GPU

### Option 1: Test All Models (Sequential) ⭐ Recommended

Load and test models one at a time:
```python
# In inference_test.py
for model_path in models:
    testor.test_model(model_path)
    torch.cuda.empty_cache()  # Clear memory between models
    time.sleep(2)  # Brief pause
```

**Advantages**:
- Tests all models
- No OOM errors
- ~60-90 minutes total runtime

### Option 2: Parallel Model Loading (Advanced)

Only test smaller models together:
```python
# Load TinyLlama + Phi-2 simultaneously (8GB total)
# Keep Mistral and Llama-2 for separate runs
```

## ⚡ Performance Expectations

### With Your 24GB GTX GPU

| Model | Precision | Load Time | Tokens/Sec | Total 128-Token Response |
|-------|-----------|-----------|------------|-------------------------|
| TinyLlama | FP16 | 2-3s | 45-55 | ~2.3 sec |
| Phi-2 | FP16 | 5-8s | 30-40 | ~3.2 sec |
| Mistral-7B | FP16 | 10-15s | 18-25 | ~5.1 sec |
| Llama-2-7B | FP16 | 10-15s | 15-22 | ~5.8 sec |

## 🔍 GPU Monitoring During Tests

### Real-time GPU Monitoring

Open a separate PowerShell window and run:
```powershell
# Option 1: Using nvidia-smi (if installed)
while($true) { nvidia-smi; Start-Sleep -Seconds 2; Clear-Host }

# Option 2: Using Python
python -c "
import torch, time
while True:
    if torch.cuda.is_available():
        print(f'GPU Memory: {torch.cuda.memory_allocated()/1e9:.2f}GB / {torch.cuda.get_device_properties(0).total_memory/1e9:.2f}GB')
    time.sleep(1)
"
```

## 🚨 Troubleshooting GPU Issues

### GPU Not Being Used

**Problem**: CPU usage 100%, GPU usage 0%
**Solution**:
```python
# Check device in code
device = "cuda" if torch.cuda.is_available() else "cpu"
if device == "cpu":
    print("⚠️ GPU not available! Check drivers and CUDA installation")
```

### Out of Memory (OOM) Error

**Problem**: `RuntimeError: CUDA out of memory`
**Solutions** (in order):
1. Clear cache: `torch.cuda.empty_cache()`
2. Use FP16 instead of FP32
3. Reduce `max_new_tokens`
4. Close other applications
5. Test smaller model first

### Slow Inference (Disk-Bound)

**Problem**: Tokens/sec very low despite GPU usage
**Solutions**:
1. First model load is slower (reading from disk)
2. Ensure models are on SSD, not HDD
3. Check for disk usage bottleneck
4. GPU should show 80-95% utilization during inference

## 📈 Recommended Testing Plan for Your 24GB GPU

```
Day 1: TinyLlama Testing
├── Load model
├── Test with different prompts
└── Baseline performance

Day 2: Phi-2 Testing
├── Compare to TinyLlama
├── Test quality vs speed
└── Note memory usage

Day 3: Mistral-7B Testing
├── Full-size model performance
├── Benchmark production readiness
└── Compare quality improvements

Day 4: Llama-2-7B Testing
├── Alternative 7B model
├── Compare with Mistral
└── Final performance report

Day 5: Analysis
├── Create performance graphs
├── Identify best model for use case
└── Optimize top performer
```

## 🎯 Bottom Line for Your Setup

✅ **You are well-equipped!**
- 24GB GPU is ideal for testing 4-7B models
- You can run everything we provide
- FP16 precision recommended for balance
- Expect 15-60 tokens/sec depending on model
- GPU makes 10-30x difference vs CPU
- Plan ~1.5-2 hours for complete testing suite

**No further GPU investment needed** - your current setup is excellent for local LLM inference and fine-tuning!
