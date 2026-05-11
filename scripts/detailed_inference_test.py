#!/usr/bin/env python3
"""
Detailed inference testing with challenging problems.
Tests 4 representative models with a hard coding problem.
Records timing, output quality, and detailed metrics.
"""

import os
import time
import json
from pathlib import Path
from datetime import datetime
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Hard problem for testing - requires genuine understanding
HARD_PROBLEM = """You are an expert Python developer. Solve this step by step:

Problem: Write a Python function that finds the longest substring without repeating characters in a given string. Return both the substring and its length.

Requirements:
1. Handle edge cases (empty string, single character, all repeating)
2. Optimize for O(n) time complexity
3. Include detailed comments explaining the algorithm
4. Add example usage and test cases

Provide the complete, production-ready solution with explanations."""

# Models to test - one from each category
MODELS_TO_TEST = [
    {
        "model_id": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        "name": "TinyLlama-1.1B",
        "category": "Tier 1: Tiny",
        "description": "Smallest model - baseline performance",
        "expected_quality": "Basic",
    },
    {
        "model_id": "deepseek-ai/deepseek-coder-1.3b-instruct",
        "name": "DeepSeek-Coder-1.3B",
        "category": "Tier 2: Small Coding Specialist",
        "description": "Tiny but specialized for coding",
        "expected_quality": "Good",
    },
    {
        "model_id": "microsoft/phi-2",
        "name": "Phi-2-2.7B",
        "category": "Tier 2: Small General",
        "description": "Efficient general-purpose model",
        "expected_quality": "Good",
    },
    {
        "model_id": "bigcode/starcoder2-3b",
        "name": "StarCoder2-3B",
        "category": "Tier 2: Small Coding Specialist",
        "description": "Purpose-built for code generation",
        "expected_quality": "Very Good",
    },
]

class DetailedInferenceTester:
    def __init__(self, models_dir, results_dir):
        self.models_dir = Path(models_dir)
        self.results_dir = Path(results_dir)
        self.results = {}
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")

    def find_model_path(self, model_name):
        """Find downloaded model path."""
        hf_models_dir = self.models_dir / "hf_models"
        model_path = hf_models_dir / model_name

        if model_path.exists():
            return model_path
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
            "problem": HARD_PROBLEM,
        }

        # Try to find model locally first
        model_path = self.find_model_path(model_name)

        if not model_path:
            print(f"⚠️ Model not found locally. Downloading from Hugging Face...")
            model_path = model_name  # Use model_id for automatic download
            download_mode = True
        else:
            print(f"[OK] Found local model at {model_path}")
            download_mode = False

        try:
            # Load model
            print(f"Loading model: {model_name}...")
            start_load = time.time()

            tokenizer = AutoTokenizer.from_pretrained(
                str(model_path) if not download_mode else model_id,
                trust_remote_code=True
            )

            # Set padding token if not set
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token

            model = AutoModelForCausalLM.from_pretrained(
                str(model_path) if not download_mode else model_id,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto",
                trust_remote_code=True
            )

            load_time = time.time() - start_load
            print(f"[OK] Model loaded in {load_time:.2f}s\n")

            result["load_time_seconds"] = load_time

            # Run inference with hard problem
            print(f"Running inference with hard problem...")
            print(f"Problem: {HARD_PROBLEM[:100]}...\n")

            inference_result = self.run_hard_problem_inference(
                model, tokenizer, HARD_PROBLEM
            )

            result.update(inference_result)

            # Unload model to free VRAM
            del model
            del tokenizer
            torch.cuda.empty_cache()

            return result

        except Exception as e:
            print(f"✗ Error testing {model_name}: {str(e)}")
            result["error"] = str(e)
            torch.cuda.empty_cache()
            return result

    def run_hard_problem_inference(self, model, tokenizer, prompt):
        """Run inference on hard problem and measure everything."""
        try:
            # Tokenize input
            inputs = tokenizer.encode(prompt, return_tensors="pt").to(self.device)
            input_tokens = inputs.shape[1]

            print(f"Input tokens: {input_tokens}")
            print(f"Generating solution...")

            # Measure generation time
            start_time = time.time()

            outputs = model.generate(
                inputs,
                max_new_tokens=512,  # Allow more tokens for detailed solution
                temperature=0.7,
                top_p=0.95,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
            )

            generation_time = time.time() - start_time
            output_tokens = outputs.shape[1] - input_tokens

            # Decode output
            generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Extract just the generated part (remove input prompt)
            prompt_length = len(prompt)
            response_text = generated_text[prompt_length:].strip()

            # Calculate metrics
            tokens_per_second = output_tokens / generation_time if generation_time > 0 else 0

            # Analyze code quality
            quality_metrics = self.analyze_code_quality(response_text)

            print(f"[OK] Generation complete")
            print(f"  Time: {generation_time:.2f}s")
            print(f"  Tokens generated: {output_tokens}")
            print(f"  Throughput: {tokens_per_second:.2f} tokens/sec")
            print(f"  Output quality score: {quality_metrics['quality_score']}/10")
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
            print(f"✗ Inference error: {str(e)}")
            return {
                "error": str(e),
                "generation_time_seconds": 0,
                "tokens_per_second": 0,
            }

    def analyze_code_quality(self, response):
        """Analyze the quality of generated code."""
        metrics = {
            "has_function_def": False,
            "has_comments": False,
            "has_docstring": False,
            "has_examples": False,
            "has_error_handling": False,
            "code_blocks": 0,
            "quality_score": 0,
        }

        # Check for function definition
        if "def " in response:
            metrics["has_function_def"] = True

        # Check for comments
        if "#" in response:
            metrics["has_comments"] = True

        # Check for docstring
        if '"""' in response or "'''" in response:
            metrics["has_docstring"] = True

        # Check for examples
        if "example" in response.lower() or ">>>" in response:
            metrics["has_examples"] = True

        # Check for error handling
        if "try" in response or "except" in response:
            metrics["has_error_handling"] = True

        # Count code blocks (triple backticks)
        metrics["code_blocks"] = response.count("```")

        # Calculate quality score (0-10)
        score = 0
        score += 2 if metrics["has_function_def"] else 0
        score += 1.5 if metrics["has_comments"] else 0
        score += 1.5 if metrics["has_docstring"] else 0
        score += 1.5 if metrics["has_examples"] else 0
        score += 1.5 if metrics["has_error_handling"] else 0
        score += min(2, metrics["code_blocks"] * 0.5)

        metrics["quality_score"] = min(10, score)

        return metrics

    def save_detailed_results(self):
        """Save detailed results in multiple formats."""
        self.results_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save raw JSON
        json_path = self.results_dir / f"detailed_results_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"✓ Saved JSON results to: {json_path}")

        # Save markdown report
        md_path = self.results_dir / f"DETAILED_INFERENCE_REPORT_{timestamp}.md"
        self.create_detailed_markdown_report(md_path)
        print(f"✓ Saved markdown report to: {md_path}")

        # Also save as latest
        latest_json = self.results_dir / "latest_detailed_results.json"
        with open(latest_json, 'w') as f:
            json.dump(self.results, f, indent=2)

        latest_md = self.results_dir / "LATEST_DETAILED_REPORT.md"
        self.create_detailed_markdown_report(latest_md)

    def create_detailed_markdown_report(self, output_path):
        """Create comprehensive markdown report."""
        with open(output_path, 'w') as f:
            f.write("# Detailed Inference Testing Report\n\n")
            f.write(f"**Test Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Problem statement
            f.write("## Problem Statement\n\n")
            f.write("```\n")
            f.write(HARD_PROBLEM)
            f.write("\n```\n\n")

            # Performance summary table
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

            # Quality comparison
            f.write("\n## Quality Metrics Comparison\n\n")
            f.write("| Model | Function | Comments | Docstring | Examples | Error Handling | Code Blocks |\n")
            f.write("|-------|----------|----------|-----------|----------|----------------|-------------|\n")

            for model_name, results in sorted(self.results.items()):
                if "quality_metrics" in results:
                    qm = results["quality_metrics"]
                    f.write(f"| {model_name} | ")
                    f.write(f"{'✓' if qm['has_function_def'] else '✗'} | ")
                    f.write(f"{'✓' if qm['has_comments'] else '✗'} | ")
                    f.write(f"{'✓' if qm['has_docstring'] else '✗'} | ")
                    f.write(f"{'✓' if qm['has_examples'] else '✗'} | ")
                    f.write(f"{'✓' if qm['has_error_handling'] else '✗'} | ")
                    f.write(f"{qm['code_blocks']} |\n")

            # Detailed results for each model
            f.write("\n## Detailed Results by Model\n\n")

            for model_name, results in sorted(self.results.items()):
                f.write(f"### {model_name}\n\n")

                if "error" in results:
                    f.write(f"**Status**: ❌ ERROR\n")
                    f.write(f"**Error**: {results['error']}\n\n")
                    continue

                f.write(f"**Category**: {results['category']}\n\n")

                f.write("#### Performance Metrics\n\n")
                f.write(f"- **Model Load Time**: {results.get('load_time_seconds', 0):.2f}s\n")
                f.write(f"- **Generation Time**: {results.get('generation_time_seconds', 0):.2f}s\n")
                f.write(f"- **Input Tokens**: {results.get('input_tokens', 0)}\n")
                f.write(f"- **Output Tokens**: {results.get('output_tokens', 0)}\n")
                f.write(f"- **Throughput**: {results.get('tokens_per_second', 0):.2f} tokens/second\n")
                f.write(f"- **Response Length**: {results.get('total_response_length', 0)} characters\n\n")

                # Quality analysis
                qm = results.get('quality_metrics', {})
                f.write("#### Code Quality Analysis\n\n")
                f.write(f"- **Quality Score**: {qm.get('quality_score', 0):.1f}/10\n")
                f.write(f"- **Has Function Definition**: {'✓ Yes' if qm.get('has_function_def') else '✗ No'}\n")
                f.write(f"- **Has Comments**: {'✓ Yes' if qm.get('has_comments') else '✗ No'}\n")
                f.write(f"- **Has Docstring**: {'✓ Yes' if qm.get('has_docstring') else '✗ No'}\n")
                f.write(f"- **Has Examples**: {'✓ Yes' if qm.get('has_examples') else '✗ No'}\n")
                f.write(f"- **Has Error Handling**: {'✓ Yes' if qm.get('has_error_handling') else '✗ No'}\n")
                f.write(f"- **Code Blocks**: {qm.get('code_blocks', 0)}\n\n")

                # Generated response
                f.write("#### Generated Response\n\n")
                f.write("```python\n")
                response = results.get('full_response', '')
                # Try to extract just the code part
                if "```" in response:
                    parts = response.split("```")
                    if len(parts) >= 2:
                        code_content = parts[1].replace("python\n", "", 1)
                        f.write(code_content)
                    else:
                        f.write(response)
                else:
                    f.write(response)
                f.write("\n```\n\n")

            # Analysis and recommendations
            f.write("\n## Analysis & Recommendations\n\n")

            # Find best performers
            results_sorted = sorted(
                [(name, r) for name, r in self.results.items() if "error" not in r],
                key=lambda x: x[1].get('tokens_per_second', 0),
                reverse=True
            )

            if results_sorted:
                f.write("### Speed Rankings (Tokens/Second)\n\n")
                for i, (name, result) in enumerate(results_sorted, 1):
                    f.write(f"{i}. **{name}**: {result.get('tokens_per_second', 0):.2f} tokens/sec\n")

            # Quality rankings
            quality_sorted = sorted(
                [(name, r) for name, r in self.results.items() if "error" not in r],
                key=lambda x: x[1].get('quality_metrics', {}).get('quality_score', 0),
                reverse=True
            )

            if quality_sorted:
                f.write("\n### Code Quality Rankings\n\n")
                for i, (name, result) in enumerate(quality_sorted, 1):
                    score = result.get('quality_metrics', {}).get('quality_score', 0)
                    f.write(f"{i}. **{name}**: {score:.1f}/10\n")

            f.write("\n### Conclusions\n\n")
            if results_sorted:
                fastest = results_sorted[0]
                f.write(f"**Fastest Model**: {fastest[0]} ({fastest[1].get('tokens_per_second', 0):.2f} tokens/sec)\n\n")

            if quality_sorted:
                best_quality = quality_sorted[0]
                f.write(f"**Best Quality**: {best_quality[0]} ({best_quality[1].get('quality_metrics', {}).get('quality_score', 0):.1f}/10)\n\n")

            f.write("### Recommendations\n\n")
            f.write("- **For Speed**: Use the fastest model for real-time applications\n")
            f.write("- **For Quality**: Use highest quality-scoring model for production code\n")
            f.write("- **Best Balance**: Consider model with good speed-to-quality ratio\n")

def main():
    """Main testing function."""
    print("\n" + "="*100)
    print("DETAILED INFERENCE TESTING - HARD PROBLEM")
    print("="*100 + "\n")

    models_dir = Path("d:\\Data\\Local_LLM_Testing\\models")
    results_dir = Path("d:\\Data\\Local_LLM_Testing\\results")

    tester = DetailedInferenceTester(models_dir, results_dir)

    print(f"Testing {len(MODELS_TO_TEST)} models with hard problem...\n")

    # Test each model
    for model_info in MODELS_TO_TEST:
        result = tester.test_model(model_info)
        tester.results[model_info["name"]] = result

    # Save results
    tester.save_detailed_results()

    print("\n" + "="*100)
    print("TESTING COMPLETE")
    print("="*100)
    print("\nCheck results/ directory for detailed reports")
    print("View: results/LATEST_DETAILED_REPORT.md")

if __name__ == "__main__":
    import sys
    sys.exit(main())
