#!/usr/bin/env python3
"""
Complete tier testing: Tier 3 + Tier 4 models
Tests with the same hard problem for fair comparison across all tiers
"""

import time
import json
from pathlib import Path
from datetime import datetime
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

HARD_PROBLEM = """You are an expert Python developer. Solve this step by step:

Problem: Write a Python function that finds the longest substring without repeating characters in a given string. Return both the substring and its length.

Requirements:
1. Handle edge cases (empty string, single character, all repeating)
2. Optimize for O(n) time complexity
3. Include detailed comments explaining the algorithm
4. Add example usage and test cases

Provide the complete, production-ready solution with explanations."""

# Tier 3 & 4 Models to test
MODELS_TO_TEST = [
    # TIER 3: Balanced (6B-7B)
    {
        "model_id": "Qwen/CodeQwen1.5-7B-Chat",
        "name": "CodeQwen-7B",
        "tier": "Tier 3: Balanced (7B)",
        "expected_vram": "14-16GB",
        "specialization": "Coding",
    },
    {
        "model_id": "mistralai/Mistral-7B-Instruct-v0.1",
        "name": "Mistral-7B-Instruct",
        "tier": "Tier 3: Balanced (7B)",
        "expected_vram": "14-16GB",
        "specialization": "General",
    },
    # TIER 4: Large (13B+)
    {
        "model_id": "meta-llama/Llama-2-13b-chat-hf",
        "name": "Llama-2-13B-Chat",
        "tier": "Tier 4: Large (13B)",
        "expected_vram": "26GB",
        "specialization": "Chat/General",
    },
    {
        "model_id": "deepseek-ai/deepseek-coder-6.7b-instruct",
        "name": "DeepSeek-Coder-6.7B",
        "tier": "Tier 3.5: Large Small (6.7B)",
        "expected_vram": "13-16GB",
        "specialization": "Coding",
    },
]

def analyze_code_quality(response):
    """Analyze code quality."""
    metrics = {
        "has_function_def": "def " in response,
        "has_comments": "#" in response,
        "has_docstring": '"""' in response or "'''" in response,
        "has_examples": "example" in response.lower() or ">>>" in response,
        "has_error_handling": "try" in response or "except" in response,
        "code_blocks": response.count("```"),
    }

    score = 0
    score += 2 if metrics["has_function_def"] else 0
    score += 1.5 if metrics["has_comments"] else 0
    score += 1.5 if metrics["has_docstring"] else 0
    score += 1.5 if metrics["has_examples"] else 0
    score += 1.5 if metrics["has_error_handling"] else 0
    score += min(2, metrics["code_blocks"] * 0.5)

    metrics["quality_score"] = min(10, score)
    return metrics

def test_model(model_info):
    """Test a single model."""
    device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"\n{'='*100}")
    print(f"Testing: {model_info['name']}")
    print(f"Tier: {model_info['tier']}")
    print(f"Expected VRAM: {model_info['expected_vram']}")
    print(f"Specialization: {model_info['specialization']}")
    print(f"Device: {device}")
    print(f"{'='*100}\n")

    result = {
        "model_id": model_info["model_id"],
        "model_name": model_info["name"],
        "tier": model_info["tier"],
        "specialization": model_info["specialization"],
        "device": device,
        "timestamp": datetime.now().isoformat(),
    }

    try:
        # Check available VRAM before loading
        if torch.cuda.is_available():
            free_vram = torch.cuda.mem_get_info()[0] / 1e9
            print(f"Available VRAM before load: {free_vram:.2f}GB\n")
            result["vram_before_load_gb"] = free_vram

        # Load model
        print(f"Loading model...")
        start_load = time.time()

        tokenizer = AutoTokenizer.from_pretrained(model_info["model_id"], trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(
            model_info["model_id"],
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            device_map="auto",
            trust_remote_code=True
        )

        load_time = time.time() - start_load
        print(f"[OK] Model loaded in {load_time:.2f}s\n")
        result["load_time_seconds"] = load_time

        # Check VRAM after load
        if torch.cuda.is_available():
            allocated_vram = torch.cuda.memory_allocated() / 1e9
            print(f"VRAM after load: {allocated_vram:.2f}GB\n")
            result["vram_after_load_gb"] = allocated_vram

        # Run inference
        print(f"Running inference...")
        inputs = tokenizer.encode(HARD_PROBLEM, return_tensors="pt").to(device)
        input_tokens = inputs.shape[1]

        print(f"Input tokens: {input_tokens}")

        start_gen = time.time()
        outputs = model.generate(
            inputs,
            max_new_tokens=512,
            temperature=0.7,
            top_p=0.95,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )
        gen_time = time.time() - start_gen
        output_tokens = outputs.shape[1] - input_tokens

        # Decode
        full_response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        response_text = full_response[len(HARD_PROBLEM):].strip()

        tokens_per_second = output_tokens / gen_time if gen_time > 0 else 0
        quality = analyze_code_quality(response_text)

        print(f"[OK] Generation complete")
        print(f"  Time: {gen_time:.2f}s")
        print(f"  Tokens: {output_tokens}")
        print(f"  Speed: {tokens_per_second:.2f} tokens/sec")
        print(f"  Quality: {quality['quality_score']:.1f}/10")
        print(f"\nPreview:")
        print("-" * 80)
        print(response_text[:400] + "...")
        print("-" * 80 + "\n")

        result["generation_time_seconds"] = gen_time
        result["input_tokens"] = int(input_tokens)
        result["output_tokens"] = int(output_tokens)
        result["tokens_per_second"] = tokens_per_second
        result["response_length"] = len(response_text)
        result["response_preview"] = response_text[:500]
        result["full_response"] = response_text
        result["quality_metrics"] = quality

        # Cleanup
        del model
        del tokenizer
        torch.cuda.empty_cache()

        return result

    except RuntimeError as e:
        if "CUDA out of memory" in str(e):
            print(f"[OOM] Out of GPU memory!")
            result["error"] = "CUDA out of memory"
            result["oom_error"] = True
            torch.cuda.empty_cache()
            return result
        else:
            print(f"[FAIL] Error: {str(e)}\n")
            result["error"] = str(e)
            torch.cuda.empty_cache()
            return result

    except Exception as e:
        print(f"[FAIL] Error: {str(e)}\n")
        result["error"] = str(e)
        torch.cuda.empty_cache()
        return result

def create_report(results, output_path):
    """Create markdown report."""
    with open(output_path, 'w') as f:
        f.write("# Comprehensive Tier Testing Report (Tier 3 & 4)\n\n")
        f.write(f"**Test Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**GPU**: RTX 3090 (25.7GB VRAM)\n\n")

        # Problem
        f.write("## Problem Statement\n\n")
        f.write("```\n")
        f.write(HARD_PROBLEM)
        f.write("\n```\n\n")

        # Summary table
        f.write("## Performance Summary - Tier 3 & 4 Models\n\n")
        f.write("| Model | Tier | Load (s) | Gen (s) | Tokens/s | Quality | Status |\n")
        f.write("|-------|------|----------|---------|----------|---------|--------|\n")

        for result in results:
            if "error" in result:
                if result.get("oom_error"):
                    status = "OUT OF MEMORY"
                else:
                    status = "ERROR"
                f.write(f"| {result['model_name']} | {result['tier']} | - | - | - | - | {status} |\n")
            else:
                load_t = result.get('load_time_seconds', 0)
                gen_t = result.get('generation_time_seconds', 0)
                tps = result.get('tokens_per_second', 0)
                qual = result.get('quality_metrics', {}).get('quality_score', 0)
                f.write(f"| {result['model_name']} | {result['tier']} | {load_t:.2f} | {gen_t:.2f} | {tps:.2f} | {qual:.1f}/10 | OK |\n")

        # Quality table
        f.write("\n## Code Quality Metrics\n\n")
        f.write("| Model | Function | Comments | Docstring | Examples | Error Handle | Quality |\n")
        f.write("|-------|----------|----------|-----------|----------|--------------|----------|\n")

        for result in results:
            if "quality_metrics" in result:
                qm = result["quality_metrics"]
                f.write(f"| {result['model_name']} | ")
                f.write(f"{'Yes' if qm['has_function_def'] else 'No'} | ")
                f.write(f"{'Yes' if qm['has_comments'] else 'No'} | ")
                f.write(f"{'Yes' if qm['has_docstring'] else 'No'} | ")
                f.write(f"{'Yes' if qm['has_examples'] else 'No'} | ")
                f.write(f"{'Yes' if qm['has_error_handling'] else 'No'} | ")
                f.write(f"{qm['quality_score']:.1f}/10 |\n")

        # VRAM Analysis
        f.write("\n## VRAM Usage Analysis\n\n")
        f.write("| Model | Size | Before Load | After Load | Used |\n")
        f.write("|-------|------|-------------|-----------|------|\n")

        for result in results:
            if "vram_before_load_gb" in result and "vram_after_load_gb" in result:
                before = result.get('vram_before_load_gb', 0)
                after = result.get('vram_after_load_gb', 0)
                used = after
                f.write(f"| {result['model_name']} | ? | {before:.2f}GB | {after:.2f}GB | {used:.2f}GB |\n")

        # Detailed results
        f.write("\n## Detailed Results\n\n")

        for result in results:
            f.write(f"### {result['model_name']}\n\n")
            f.write(f"**Tier**: {result['tier']}\n")
            f.write(f"**Specialization**: {result['specialization']}\n\n")

            if "error" in result:
                if result.get("oom_error"):
                    f.write(f"**Status**: OUT OF GPU MEMORY\n\n")
                    f.write(f"This model requires more than 25.7GB VRAM to load in FP16 precision.\n")
                    f.write(f"**Solutions**:\n")
                    f.write(f"- Use INT8 quantization (75% memory reduction)\n")
                    f.write(f"- Use a larger GPU (40GB+)\n")
                    f.write(f"- Use CPU offloading\n")
                else:
                    f.write(f"**Status**: ERROR\n\n")
                    f.write(f"**Error**: {result['error']}\n")
                continue

            f.write("#### Performance Metrics\n\n")
            f.write(f"- Load Time: {result.get('load_time_seconds', 0):.2f}s\n")
            f.write(f"- Generation Time: {result.get('generation_time_seconds', 0):.2f}s\n")
            f.write(f"- Input Tokens: {result.get('input_tokens', 0)}\n")
            f.write(f"- Output Tokens: {result.get('output_tokens', 0)}\n")
            f.write(f"- **Throughput: {result.get('tokens_per_second', 0):.2f} tokens/second**\n")
            if "vram_after_load_gb" in result:
                f.write(f"- VRAM Used: {result.get('vram_after_load_gb', 0):.2f}GB\n")
            f.write(f"- Total Response Length: {result.get('response_length', 0)} characters\n\n")

            qm = result.get('quality_metrics', {})
            f.write("#### Code Quality\n\n")
            f.write(f"- **Quality Score: {qm.get('quality_score', 0):.1f}/10**\n")
            f.write(f"- Function: {'Yes' if qm.get('has_function_def') else 'No'}\n")
            f.write(f"- Comments: {'Yes' if qm.get('has_comments') else 'No'}\n")
            f.write(f"- Docstring: {'Yes' if qm.get('has_docstring') else 'No'}\n")
            f.write(f"- Examples: {'Yes' if qm.get('has_examples') else 'No'}\n")
            f.write(f"- Error Handling: {'Yes' if qm.get('has_error_handling') else 'No'}\n\n")

            f.write("#### Generated Solution Preview\n\n")
            f.write("```python\n")
            response = result.get('full_response', '')
            preview = response[:1500]
            if preview.count('\n') > 50:
                lines = preview.split('\n')[:50]
                preview = '\n'.join(lines)
            f.write(preview)
            f.write("\n```\n\n")

        # Rankings
        f.write("\n## Performance Rankings\n\n")

        valid_results = [r for r in results if "error" not in r]

        if valid_results:
            speed_sorted = sorted(valid_results, key=lambda x: x.get('tokens_per_second', 0), reverse=True)
            f.write("### Fastest Models\n\n")
            for i, result in enumerate(speed_sorted, 1):
                f.write(f"{i}. **{result['model_name']}** ({result['tier']}): {result.get('tokens_per_second', 0):.2f} tokens/sec\n")

            quality_sorted = sorted(valid_results, key=lambda x: x.get('quality_metrics', {}).get('quality_score', 0), reverse=True)
            f.write("\n### Best Code Quality\n\n")
            for i, result in enumerate(quality_sorted, 1):
                score = result.get('quality_metrics', {}).get('quality_score', 0)
                f.write(f"{i}. **{result['model_name']}** ({result['tier']}): {score:.1f}/10\n")

        # Recommendations
        f.write("\n## Recommendations\n\n")

        if valid_results:
            f.write("### For Production Code (Best Quality)\n")
            quality_sorted = sorted(valid_results, key=lambda x: x.get('quality_metrics', {}).get('quality_score', 0), reverse=True)
            if quality_sorted:
                best = quality_sorted[0]
                f.write(f"**{best['model_name']}** - {best.get('quality_metrics', {}).get('quality_score', 0):.1f}/10\n\n")

            f.write("### For Speed (Fastest Inference)\n")
            speed_sorted = sorted(valid_results, key=lambda x: x.get('tokens_per_second', 0), reverse=True)
            if speed_sorted:
                fastest = speed_sorted[0]
                f.write(f"**{fastest['model_name']}** - {fastest.get('tokens_per_second', 0):.2f} tokens/sec\n\n")

        # Summary
        f.write("## Summary\n\n")
        f.write(f"Successfully tested: {len(valid_results)} models\n")
        f.write(f"Failed/OOM: {len([r for r in results if 'error' in r])} models\n")
        f.write(f"GPU capacity: 25.7GB\n\n")

        f.write("### Key Findings\n\n")
        if valid_results:
            best_quality = max(valid_results, key=lambda x: x.get('quality_metrics', {}).get('quality_score', 0))
            fastest = max(valid_results, key=lambda x: x.get('tokens_per_second', 0))

            f.write(f"- Best Quality: {best_quality['model_name']} ({best_quality.get('quality_metrics', {}).get('quality_score', 0):.1f}/10)\n")
            f.write(f"- Fastest: {fastest['model_name']} ({fastest.get('tokens_per_second', 0):.2f} tokens/sec)\n")
            f.write(f"- Recommended for production: Larger models have better quality but slower inference\n")

def main():
    print("\n" + "="*100)
    print("COMPREHENSIVE TIER 3 & 4 TESTING")
    print("GPU: RTX 3090 (25.7GB VRAM)")
    print("="*100 + "\n")

    results = []

    print("WARNING: These are large models. Testing will use significant VRAM.\n")
    print("Expected loads:")
    for model in MODELS_TO_TEST:
        print(f"  - {model['name']}: {model['expected_vram']}")
    print()

    for model_info in MODELS_TO_TEST:
        result = test_model(model_info)
        results.append(result)

    # Save results
    results_dir = Path("d:\\Data\\Local_LLM_Testing\\results")
    results_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON
    json_path = results_dir / f"tier34_results_{timestamp}.json"
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)

    # Latest JSON
    with open(results_dir / "latest_tier34_results.json", 'w') as f:
        json.dump(results, f, indent=2)

    # Markdown report
    md_path = results_dir / f"TIER34_REPORT_{timestamp}.md"
    create_report(results, md_path)

    # Latest markdown
    create_report(results, results_dir / "LATEST_TIER34_REPORT.md")

    print("\n" + "="*100)
    print("TESTING COMPLETE")
    print("="*100)
    print(f"\nResults saved to: {results_dir}")
    print(f"View report: {results_dir / 'LATEST_TIER34_REPORT.md'}")

if __name__ == "__main__":
    main()
