#!/usr/bin/env python3
"""
Simple inference testing - downloads models directly from HuggingFace
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

MODELS = [
    ("TinyLlama/TinyLlama-1.1B-Chat-v1.0", "TinyLlama-1.1B", "Tier 1: Tiny"),
    ("deepseek-ai/deepseek-coder-1.3b-instruct", "DeepSeek-Coder-1.3B", "Tier 2: Small Coding"),
    ("microsoft/phi-2", "Phi-2-2.7B", "Tier 2: Small General"),
    ("bigcode/starcoder2-3b", "StarCoder2-3B", "Tier 2: Small Coding"),
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

def test_model(model_id, model_name, category):
    """Test a single model."""
    device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"\n{'='*100}")
    print(f"Testing: {model_name} ({category})")
    print(f"Model ID: {model_id}")
    print(f"Device: {device}")
    print(f"{'='*100}\n")

    result = {
        "model_id": model_id,
        "model_name": model_name,
        "category": category,
        "device": device,
        "timestamp": datetime.now().isoformat(),
    }

    try:
        # Load model
        print(f"Loading model...")
        start_load = time.time()

        tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            device_map="auto",
            trust_remote_code=True
        )

        load_time = time.time() - start_load
        print(f"[OK] Model loaded in {load_time:.2f}s\n")
        result["load_time_seconds"] = load_time

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

    except Exception as e:
        print(f"[FAIL] Error: {str(e)}\n")
        result["error"] = str(e)
        torch.cuda.empty_cache()
        return result

def create_report(results, output_path):
    """Create markdown report."""
    with open(output_path, 'w') as f:
        f.write("# Detailed Inference Testing Report\n\n")
        f.write(f"**Test Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Problem
        f.write("## Problem Statement\n\n")
        f.write("```\n")
        f.write(HARD_PROBLEM)
        f.write("\n```\n\n")

        # Summary table
        f.write("## Performance Summary\n\n")
        f.write("| Model | Category | Load (s) | Gen (s) | Tokens/s | Quality |\n")
        f.write("|-------|----------|----------|---------|----------|----------|\n")

        for result in results:
            if "error" in result:
                f.write(f"| {result['model_name']} | {result.get('category', 'N/A')} | ERROR | - | - | - |\n")
            else:
                load_t = result.get('load_time_seconds', 0)
                gen_t = result.get('generation_time_seconds', 0)
                tps = result.get('tokens_per_second', 0)
                qual = result.get('quality_metrics', {}).get('quality_score', 0)
                f.write(f"| {result['model_name']} | {result['category']} | {load_t:.2f} | {gen_t:.2f} | {tps:.2f} | {qual:.1f}/10 |\n")

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

        # Detailed results
        f.write("\n## Detailed Results by Model\n\n")

        for result in results:
            f.write(f"### {result['model_name']}\n\n")

            if "error" in result:
                f.write(f"**Status**: ERROR\n\n")
                f.write(f"**Error**: {result['error']}\n\n")
                continue

            f.write(f"**Category**: {result['category']}\n")
            f.write(f"**Device**: {result['device']}\n\n")

            f.write("#### Performance Metrics\n\n")
            f.write(f"- Load Time: {result.get('load_time_seconds', 0):.2f}s\n")
            f.write(f"- Generation Time: {result.get('generation_time_seconds', 0):.2f}s\n")
            f.write(f"- Input Tokens: {result.get('input_tokens', 0)}\n")
            f.write(f"- Output Tokens: {result.get('output_tokens', 0)}\n")
            f.write(f"- **Throughput: {result.get('tokens_per_second', 0):.2f} tokens/second**\n")
            f.write(f"- Total Response Length: {result.get('response_length', 0)} characters\n\n")

            qm = result.get('quality_metrics', {})
            f.write("#### Code Quality Analysis\n\n")
            f.write(f"- **Quality Score: {qm.get('quality_score', 0):.1f}/10**\n")
            f.write(f"- Has Function Definition: {'Yes' if qm.get('has_function_def') else 'No'}\n")
            f.write(f"- Has Comments: {'Yes' if qm.get('has_comments') else 'No'}\n")
            f.write(f"- Has Docstring: {'Yes' if qm.get('has_docstring') else 'No'}\n")
            f.write(f"- Has Examples: {'Yes' if qm.get('has_examples') else 'No'}\n")
            f.write(f"- Has Error Handling: {'Yes' if qm.get('has_error_handling') else 'No'}\n")
            f.write(f"- Code Blocks Count: {qm.get('code_blocks', 0)}\n\n")

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
            f.write("### Fastest Models (Tokens/Second)\n\n")
            for i, result in enumerate(speed_sorted, 1):
                f.write(f"{i}. **{result['model_name']}**: {result.get('tokens_per_second', 0):.2f} tokens/sec\n")

            quality_sorted = sorted(valid_results, key=lambda x: x.get('quality_metrics', {}).get('quality_score', 0), reverse=True)
            f.write("\n### Best Code Quality\n\n")
            for i, result in enumerate(quality_sorted, 1):
                score = result.get('quality_metrics', {}).get('quality_score', 0)
                f.write(f"{i}. **{result['model_name']}**: {score:.1f}/10\n")

        # Recommendations
        f.write("\n## Recommendations\n\n")

        if valid_results:
            fastest = speed_sorted[0] if speed_sorted else None
            best_quality = quality_sorted[0] if quality_sorted else None

            if fastest:
                f.write(f"**Fastest Model**: {fastest['model_name']} ({fastest.get('tokens_per_second', 0):.2f} tokens/sec)\n")
                f.write(f"- Best for: Real-time applications, speed-critical systems\n")
                f.write(f"- Use when: Response time is more important than quality\n\n")

            if best_quality:
                f.write(f"**Best Code Quality**: {best_quality['model_name']} ({best_quality.get('quality_metrics', {}).get('quality_score', 0):.1f}/10)\n")
                f.write(f"- Best for: Production code generation, complex problems\n")
                f.write(f"- Use when: Code quality is critical\n\n")

            # Find best balance
            balanced_scores = [(r['model_name'],
                              r.get('tokens_per_second', 0)/100,  # normalize speed
                              r.get('quality_metrics', {}).get('quality_score', 0)/10)
                             for r in valid_results]
            balanced = max(balanced_scores, key=lambda x: x[1] * x[2], default=None)
            if balanced:
                f.write(f"**Best Overall Balance**: {balanced[0]}\n")
                f.write(f"- Best for: General-purpose use, good balance of speed and quality\n\n")

def main():
    print("\n" + "="*100)
    print("DETAILED INFERENCE TESTING - HARD CODING PROBLEM")
    print("="*100 + "\n")

    results = []

    for model_id, model_name, category in MODELS:
        result = test_model(model_id, model_name, category)
        results.append(result)

    # Save results
    results_dir = Path("d:\\Data\\Local_LLM_Testing\\results")
    results_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON
    json_path = results_dir / f"detailed_results_{timestamp}.json"
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)

    # Latest JSON
    with open(results_dir / "latest_detailed_results.json", 'w') as f:
        json.dump(results, f, indent=2)

    # Markdown report
    md_path = results_dir / f"DETAILED_INFERENCE_REPORT_{timestamp}.md"
    create_report(results, md_path)

    # Latest markdown
    create_report(results, results_dir / "LATEST_DETAILED_REPORT.md")

    print("\n" + "="*100)
    print("TESTING COMPLETE")
    print("="*100)
    print(f"\nResults saved to: {results_dir}")
    print(f"View report: {results_dir / 'LATEST_DETAILED_REPORT.md'}")

if __name__ == "__main__":
    main()
