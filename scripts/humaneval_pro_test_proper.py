"""
Proper HumanEval Pro benchmark test with correct verification
Follows official evaluation rubric: Pass@1 based on test assertions
"""

import json
import time
import torch
import subprocess
import tempfile
import os
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import Dict, Tuple

MODELS = [
    "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    "deepseek-ai/deepseek-coder-1.3b-instruct",
    "bigcode/starcoder2-3b",
    "Qwen/CodeQwen1.5-7B-Chat",
    "mistralai/Mistral-7B-Instruct-v0.1",
    "meta-llama/Llama-2-7b-chat-hf",
    "Intel/neural-chat-7b-v3-1",
    "Phi-2",
]

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DATASET_PATH = "humaneval_pro/dataset/humaneval_pro.json"
MAX_PROBLEMS = 164
TIMEOUT = 15  # seconds per test execution

class HumanEvalProTester:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.device = DEVICE
        self.model = None
        self.tokenizer = None
        self.results = {
            "model": model_name,
            "load_time": 0,
            "total_problems": 0,
            "passed": 0,
            "failed": 0,
            "timeout": 0,
            "error": 0,
            "pass_rate": 0.0,
            "avg_generation_time": 0.0,
        }

    def load_model(self):
        """Load model and tokenizer"""
        print(f"\n[{self.model_name}] Loading model...")
        start = time.time()
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                timeout=60
            )
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True
            )
            self.model.eval()
            self.results["load_time"] = time.time() - start
            print(f"  Load time: {self.results['load_time']:.2f}s")
            return True
        except Exception as e:
            print(f"  ERROR loading model: {e}")
            self.results["error"] = 1
            return False

    def generate_code_for_new_problem(self, problem: Dict) -> Tuple[str, float]:
        """Generate code for the new_problem (harder version)"""
        start = time.time()
        try:
            # Use the new_problem (harder version)
            prompt = problem["new_problem"]

            inputs = self.tokenizer.encode(prompt, return_tensors="pt").to(self.device)

            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_new_tokens=512,
                    temperature=0.7,
                    top_p=0.95,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )

            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            gen_time = time.time() - start

            # Extract the generated code (remove prompt)
            code = generated_text[len(prompt):].strip()
            return code, gen_time
        except Exception as e:
            gen_time = time.time() - start
            print(f"    ERROR in problem {problem.get('id', 'unknown')}: {str(e)[:100]}")
            return "", gen_time

    def verify_solution(self, problem: Dict, generated_code: str) -> bool:
        """
        Verify solution using HumanEval Pro rubric:
        1. Must include the raw_problem (base function)
        2. Must include the generated code for new_problem
        3. Must pass all test_code assertions
        """
        try:
            # Build complete test code:
            # 1. Raw problem (defines base functions needed)
            # 2. Generated code for new problem
            # 3. Test assertions

            full_code = (
                problem["raw_problem"] + "\n" +
                problem["raw_solution"] + "\n\n" +
                problem["new_problem"] + "\n" +
                generated_code + "\n\n" +
                problem["test_code"]
            )

            # Write to temp file and execute
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(full_code)
                temp_file = f.name

            try:
                # Execute with timeout
                result = subprocess.run(
                    ["python", temp_file],
                    capture_output=True,
                    timeout=TIMEOUT,
                    text=True
                )

                # Check if all assertions passed (return code 0)
                passed = result.returncode == 0

                if not passed and result.stderr:
                    # Log first error for debugging
                    error = result.stderr.split('\n')[0][:100]
                    # print(f"    Test error: {error}")

                return passed
            finally:
                os.unlink(temp_file)

        except subprocess.TimeoutExpired:
            return False
        except Exception as e:
            return False

    def run_benchmark(self):
        """Run benchmark on all problems"""
        if not self.load_model():
            return self.results

        print(f"\n[{self.model_name}] Running {MAX_PROBLEMS} problems...")

        # Load dataset
        with open(DATASET_PATH, 'r') as f:
            dataset = json.load(f)[:MAX_PROBLEMS]

        self.results["total_problems"] = len(dataset)
        generation_times = []

        for idx, problem in enumerate(dataset):
            if idx % 20 == 0:
                print(f"  Progress: {idx}/{len(dataset)}")

            # Generate code for new_problem
            code, gen_time = self.generate_code_for_new_problem(problem)
            generation_times.append(gen_time)

            # Verify using HumanEval Pro rubric
            # Include: raw_problem + raw_solution + generated code + test_code
            passed = self.verify_solution(problem, code) if code else False

            # Track result
            if passed:
                self.results["passed"] += 1
            elif not code:
                self.results["error"] += 1
            else:
                self.results["failed"] += 1

        # Calculate statistics
        self.results["pass_rate"] = (self.results["passed"] / self.results["total_problems"] * 100) if self.results["total_problems"] > 0 else 0
        self.results["avg_generation_time"] = sum(generation_times) / len(generation_times) if generation_times else 0

        # Cleanup
        del self.model
        del self.tokenizer
        torch.cuda.empty_cache()

        return self.results


def run_all_models():
    """Test all models on HumanEval Pro"""
    all_results = []

    print("=" * 80)
    print("HumanEval Pro Benchmark - Proper Verification with Self-Invoking")
    print("=" * 80)
    print("\nVerification Rubric:")
    print("1. Raw problem (base function) is included")
    print("2. Raw solution (reference implementation) is provided")
    print("3. Model generates code for new_problem (harder version)")
    print("4. Test code assertions must all pass")
    print("Metric: Pass@1 (first solution must be correct)")
    print("-" * 80)

    for model_name in MODELS:
        tester = HumanEvalProTester(model_name)
        result = tester.run_benchmark()
        all_results.append(result)

        # Print summary
        print(f"\n[SUMMARY] {model_name}")
        print(f"  Load Time: {result['load_time']:.2f}s")
        print(f"  Passed: {result['passed']}/{result['total_problems']} ({result['pass_rate']:.1f}%)")
        print(f"  Failed: {result['failed']}")
        print(f"  Errors: {result['error']}")
        print(f"  Avg Gen Time: {result['avg_generation_time']:.2f}s")

    # Save results
    output_file = "results/humaneval_pro_results_proper.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {output_file}")

    # Print final comparison
    print("\n" + "=" * 80)
    print("FINAL COMPARISON - Pass@1 Scores")
    print("=" * 80)
    print(f"{'Model':<40} {'Pass Rate':<15} {'Load (s)':<12} {'Gen Time':<12}")
    print("-" * 80)
    for result in sorted(all_results, key=lambda x: x['pass_rate'], reverse=True):
        print(f"{result['model']:<40} {result['pass_rate']:>6.1f}%{'':<8} {result['load_time']:>7.2f}{'':<4} {result['avg_generation_time']:>7.2f}")


if __name__ == "__main__":
    run_all_models()
