#!/usr/bin/env python3
"""
Fixed detailed inference testing with proper model path resolution.
"""

import os
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

MODELS_TO_TEST = [
    {
        "model_id": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        "name": "TinyLlama-1.1B",
        "category": "Tier 1: Tiny",
        "description": "Smallest model - baseline performance",
    },
    {
        "model_id": "deepseek-ai/deepseek-coder-1.3b-instruct",
        "name": "DeepSeek-Coder-1.3B",
        "category": "Tier 2: Small Coding Specialist",
        "description": "Tiny but specialized for coding",
    },
    {
        "model_id": "microsoft/phi-2",
        "name": "Phi-2-2.7B",
        "category": "Tier 2: Small General",
        "description": "Efficient general-purpose model",
    },
    {
        "model_id": "bigcode/starcoder2-3b",
        "name": "StarCoder2-3B",
        "category": "Tier 2: Small Coding Specialist",
        "description": "Purpose-built for code generation",
    },
]

class DetailedInferenceTester:
    def __init__(self, models_dir, results_dir):
        self.models_dir = Path(models_dir)
        self.results_dir = Path(results_dir)
        self.results = {}
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}\n")

    def find_model_snapshot(self, model_name):
        """Find the actual model in the huggingface cache structure."""
        model_folder = self.models_dir / "hf_models" / model_name

        if not model_folder.exists():
            return None

        # Look for snapshots directory
        for item in model_folder.rglob("snapshots"):
            if item.is_dir():
                snapshots = list(item.iterdir())
                if snapshots:
                    return snapshots[0]  # Return first snapshot

        # If no snapshots, check if it's the model directory itself
        if (model_folder / "config.json").exists():
            return model_folder

        return None

    def test_model(self, model_info):
        """Test a single model with hard problem."""
        model_name = model_info["name"]
        model_id = model_info["model_id"]

        print(f"\n{'='*100}")
        print(f"TESTING: {model_name}")
        print(f"Category: {model_info['category']}")
        print(f"{'='*100}\n")

        result = {
            "model_name": model_name,
            "model_id": model_id,
            "category": model_info["category"],
            "timestamp": datetime.now().isoformat(),
        }

        # Find model path
        model_path = self.find_model_snapshot(model_name)

        if not model_path:
            print(f"[FAIL] Model not found locally: {model_name}")
            print(f"Looking in: {self.models_dir / 'hf_models' / model_name}")
            result["error"] = "Model path not found"
            return result

        print(f"[OK] Found model at: {model_path}")

        try:
            # Load model
            print(f"Loading model: {model_name}...")
            start_load = time.time()

            tokenizer = AutoTokenizer.from_pretrained(str(model_path), trust_remote_code=True)

            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token

            model = AutoModelForCausalLM.from_pretrained(
                str(model_path),
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto",
                trust_remote_code=True
            )

            load_time = time.time() - start_load
            print(f"[OK] Model loaded in {load_time:.2f}s\n")

            result["load_time_seconds"] = load_time

            # Run inference
            print(f"Running inference with hard problem...")
            inference_result = self.run_hard_problem_inference(model, tokenizer)
            result.update(inference_result)

            # Cleanup
            del model
            del tokenizer
            torch.cuda.empty_cache()

            return result

        except Exception as e:
            print(f"[FAIL] Error testing {model_name}: {str(e)}")
            result["error"] = str(e)
            torch.cuda.empty_cache()
            return result

    def run_hard_problem_inference(self, model, tokenizer, prompt=None):
        """Run inference on hard problem."""
        if prompt is None:
            prompt = HARD_PROBLEM

        try:
            inputs = tokenizer.encode(prompt, return_tensors="pt").to(self.device)
            input_tokens = inputs.shape[1]

            print(f"Input tokens: {input_tokens}")
            print(f"Generating solution...")

            start_time = time.time()
            outputs = model.generate(
                inputs,
                max_new_tokens=512,
                temperature=0.7,
                top_p=0.95,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
            )
            generation_time = time.time() - start_time
            output_tokens = outputs.shape[1] - input_tokens

            # Decode
            generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            prompt_length = len(prompt)
            response_text = generated_text[prompt_length:].strip()

            tokens_per_second = output_tokens / generation_time if generation_time > 0 else 0
            quality_metrics = self.analyze_code_quality(response_text)

            print(f"[OK] Generation complete")
            print(f"  Time: {generation_time:.2f}s")
            print(f"  Tokens generated: {output_tokens}")
            print(f"  Throughput: {tokens_per_second:.2f} tokens/sec")
            print(f"  Quality score: {quality_metrics['quality_score']:.1f}/10")
            print(f"\nGenerated Response Preview:")
            print("-" * 80)
            print(response_text[:500] + ("..." if len(response_text) > 500 else ""))
            print("-" * 80 + "\n")

            return {
                "generation_time_seconds": generation_time,
                "input_tokens": int(input_tokens),
                "output_tokens": int(output_tokens),
                "tokens_per_second": tokens_per_second,
                "total_response_length": len(response_text),
                "response_preview": response_text[:500],
                "full_response": response_text,
                "quality_metrics": quality_metrics,
            }

        except Exception as e:
            print(f"[FAIL] Inference error: {str(e)}")
            return {"error": str(e)}

    def analyze_code_quality(self, response):
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

    def save_results(self):
        """Save results."""
        self.results_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save JSON
        json_path = self.results_dir / f"detailed_results_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"[OK] Saved results to: {json_path}")

        # Save markdown
        md_path = self.results_dir / f"DETAILED_INFERENCE_REPORT_{timestamp}.md"
        self.create_markdown_report(md_path)
        print(f"[OK] Saved report to: {md_path}")

        # Latest copies
        latest_json = self.results_dir / "latest_detailed_results.json"
        with open(latest_json, 'w') as f:
            json.dump(self.results, f, indent=2)

        latest_md = self.results_dir / "LATEST_DETAILED_REPORT.md"
        self.create_markdown_report(latest_md)

    def create_markdown_report(self, output_path):
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

            for model_name, results in sorted(self.results.items()):
                if "error" in results:
                    f.write(f"| {model_name} | {results.get('category', 'N/A')} | ERROR | - | - | - |\n")
                else:
                    load_time = results.get("load_time_seconds", 0)
                    gen_time = results.get("generation_time_seconds", 0)
                    tps = results.get("tokens_per_second", 0)
                    quality = results.get("quality_metrics", {}).get("quality_score", 0)
                    f.write(f"| {model_name} | {results['category']} | {load_time:.2f} | {gen_time:.2f} | {tps:.2f} | {quality:.1f}/10 |\n")

            # Quality metrics
            f.write("\n## Quality Metrics\n\n")
            f.write("| Model | Function | Comments | Docstring | Examples | Error Handling | Quality |\n")
            f.write("|-------|----------|----------|-----------|----------|----------------|----------|\n")

            for model_name, results in sorted(self.results.items()):
                if "quality_metrics" in results:
                    qm = results["quality_metrics"]
                    f.write(f"| {model_name} | ")
                    f.write(f"{'Yes' if qm['has_function_def'] else 'No'} | ")
                    f.write(f"{'Yes' if qm['has_comments'] else 'No'} | ")
                    f.write(f"{'Yes' if qm['has_docstring'] else 'No'} | ")
                    f.write(f"{'Yes' if qm['has_examples'] else 'No'} | ")
                    f.write(f"{'Yes' if qm['has_error_handling'] else 'No'} | ")
                    f.write(f"{qm['quality_score']:.1f}/10 |\n")

            # Detailed results
            f.write("\n## Detailed Results\n\n")

            for model_name, results in sorted(self.results.items()):
                f.write(f"### {model_name}\n\n")

                if "error" in results:
                    f.write(f"**Status**: ERROR\n")
                    f.write(f"**Error**: {results['error']}\n\n")
                    continue

                f.write(f"**Category**: {results['category']}\n\n")

                f.write("#### Performance\n\n")
                f.write(f"- Load Time: {results.get('load_time_seconds', 0):.2f}s\n")
                f.write(f"- Generation Time: {results.get('generation_time_seconds', 0):.2f}s\n")
                f.write(f"- Input Tokens: {results.get('input_tokens', 0)}\n")
                f.write(f"- Output Tokens: {results.get('output_tokens', 0)}\n")
                f.write(f"- **Throughput: {results.get('tokens_per_second', 0):.2f} tokens/second**\n\n")

                # Quality
                qm = results.get('quality_metrics', {})
                f.write("#### Code Quality\n\n")
                f.write(f"- **Quality Score: {qm.get('quality_score', 0):.1f}/10**\n")
                f.write(f"- Function Definition: {'Yes' if qm.get('has_function_def') else 'No'}\n")
                f.write(f"- Comments: {'Yes' if qm.get('has_comments') else 'No'}\n")
                f.write(f"- Docstring: {'Yes' if qm.get('has_docstring') else 'No'}\n")
                f.write(f"- Examples: {'Yes' if qm.get('has_examples') else 'No'}\n")
                f.write(f"- Error Handling: {'Yes' if qm.get('has_error_handling') else 'No'}\n\n")

                # Code
                f.write("#### Generated Solution\n\n")
                f.write("```python\n")
                response = results.get('full_response', '')
                if "```" in response:
                    parts = response.split("```")
                    if len(parts) >= 2:
                        code_content = parts[1].replace("python\n", "", 1)
                        f.write(code_content[:2000])  # Limit to 2000 chars
                    else:
                        f.write(response[:2000])
                else:
                    f.write(response[:2000])
                f.write("\n```\n\n")

            # Rankings
            f.write("\n## Rankings\n\n")

            results_sorted = sorted(
                [(name, r) for name, r in self.results.items() if "error" not in r],
                key=lambda x: x[1].get('tokens_per_second', 0),
                reverse=True
            )

            if results_sorted:
                f.write("### Speed (Tokens/Second)\n\n")
                for i, (name, result) in enumerate(results_sorted, 1):
                    f.write(f"{i}. **{name}**: {result.get('tokens_per_second', 0):.2f} tokens/sec\n")

            quality_sorted = sorted(
                [(name, r) for name, r in self.results.items() if "error" not in r],
                key=lambda x: x[1].get('quality_metrics', {}).get('quality_score', 0),
                reverse=True
            )

            if quality_sorted:
                f.write("\n### Code Quality (Score)\n\n")
                for i, (name, result) in enumerate(quality_sorted, 1):
                    score = result.get('quality_metrics', {}).get('quality_score', 0)
                    f.write(f"{i}. **{name}**: {score:.1f}/10\n")

            f.write("\n## Recommendations\n\n")
            if results_sorted:
                f.write(f"- **Fastest**: {results_sorted[0][0]} ({results_sorted[0][1].get('tokens_per_second', 0):.2f} tokens/sec)\n")
            if quality_sorted:
                f.write(f"- **Best Quality**: {quality_sorted[0][0]} ({quality_sorted[0][1].get('quality_metrics', {}).get('quality_score', 0):.1f}/10)\n")

def main():
    """Main testing function."""
    print("\n" + "="*100)
    print("DETAILED INFERENCE TESTING - HARD PROBLEM")
    print("="*100 + "\n")

    models_dir = Path("d:\\Data\\Local_LLM_Testing\\models")
    results_dir = Path("d:\\Data\\Local_LLM_Testing\\results")

    tester = DetailedInferenceTester(models_dir, results_dir)

    print(f"Testing {len(MODELS_TO_TEST)} models...\n")

    for model_info in MODELS_TO_TEST:
        result = tester.test_model(model_info)
        tester.results[model_info["name"]] = result

    tester.save_results()

    print("\n" + "="*100)
    print("TESTING COMPLETE")
    print("="*100)
    print("\nResults saved to: results/")
    print("View: results/LATEST_DETAILED_REPORT.md")

if __name__ == "__main__":
    import sys
    sys.exit(main())
