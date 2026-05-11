#!/usr/bin/env python3
"""
Inference testing script to measure inference speed of different models.
Tests various prompt lengths and measures tokens/second.
"""

import os
import time
import json
from pathlib import Path
from datetime import datetime
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

# Test prompts of varying lengths
TEST_PROMPTS = {
    "short": "What is machine learning?",
    "medium": "Explain how machine learning algorithms work, including the main types like supervised learning, unsupervised learning, and reinforcement learning. What are some real-world applications?",
    "long": "Provide a comprehensive overview of natural language processing (NLP). Include its history, main techniques used in modern NLP systems, applications in industry, challenges researchers face, and future directions. Also explain how neural networks have transformed the field."
}

GENERATION_CONFIG = {
    "max_new_tokens": 128,
    "temperature": 0.7,
    "top_p": 0.95,
}

class InferenceTestor:
    def __init__(self, models_dir, results_dir):
        self.models_dir = Path(models_dir)
        self.results_dir = Path(results_dir)
        self.results = {}

    def find_models(self):
        """Find downloaded models."""
        hf_models_dir = self.models_dir / "hf_models"
        if not hf_models_dir.exists():
            print(f"Models directory not found: {hf_models_dir}")
            return []

        models = sorted([d for d in hf_models_dir.iterdir() if d.is_dir()])
        return models

    def test_model(self, model_path):
        """Test a single model."""
        model_name = model_path.name
        print(f"\n{'='*80}")
        print(f"Testing: {model_name}")
        print(f"{'='*80}")

        results = {
            "model_name": model_name,
            "model_path": str(model_path),
            "timestamp": datetime.now().isoformat(),
            "tests": {}
        }

        try:
            # Load model and tokenizer
            print(f"Loading model: {model_name}...")
            start_load = time.time()

            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"Using device: {device}")

            tokenizer = AutoTokenizer.from_pretrained(str(model_path), trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(
                str(model_path),
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                device_map="auto",
                trust_remote_code=True
            )

            load_time = time.time() - start_load
            print(f"✓ Model loaded in {load_time:.2f}s\n")

            results["load_time_seconds"] = load_time
            results["device"] = device

            # Run inference tests
            for prompt_type, prompt in TEST_PROMPTS.items():
                print(f"\nTesting with {prompt_type} prompt...")
                test_results = self.run_inference_test(model, tokenizer, prompt, device)
                results["tests"][prompt_type] = test_results
                print(f"  Tokens/sec: {test_results['tokens_per_second']:.2f}")
                print(f"  Total time: {test_results['generation_time_seconds']:.2f}s")
                print(f"  Tokens generated: {test_results['tokens_generated']}")

            self.results[model_name] = results
            return results

        except Exception as e:
            print(f"✗ Error testing {model_name}: {str(e)}")
            results["error"] = str(e)
            self.results[model_name] = results
            return results

    def run_inference_test(self, model, tokenizer, prompt, device):
        """Run inference and measure performance."""
        try:
            inputs = tokenizer.encode(prompt, return_tensors="pt").to(device)

            start_time = time.time()
            outputs = model.generate(
                inputs,
                max_new_tokens=GENERATION_CONFIG["max_new_tokens"],
                temperature=GENERATION_CONFIG["temperature"],
                top_p=GENERATION_CONFIG["top_p"],
                do_sample=True,
            )
            generation_time = time.time() - start_time

            # Decode to get generated text
            generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            tokens_generated = outputs.shape[1] - inputs.shape[1]

            tokens_per_second = tokens_generated / generation_time if generation_time > 0 else 0

            return {
                "generation_time_seconds": generation_time,
                "tokens_generated": int(tokens_generated),
                "tokens_per_second": tokens_per_second,
                "generated_text": generated_text[:200] + "..." if len(generated_text) > 200 else generated_text
            }

        except Exception as e:
            print(f"  ✗ Error during inference: {str(e)}")
            return {
                "error": str(e),
                "generation_time_seconds": 0,
                "tokens_per_second": 0
            }

    def save_results(self):
        """Save results to files."""
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Save raw JSON results
        json_path = self.results_dir / "inference_results.json"
        with open(json_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n✓ Saved raw results to: {json_path}")

        # Save markdown report
        md_path = self.results_dir / "INFERENCE_RESULTS.md"
        self.create_markdown_report(md_path)
        print(f"✓ Saved markdown report to: {md_path}")

    def create_markdown_report(self, output_path):
        """Create a detailed markdown report."""
        with open(output_path, 'w') as f:
            f.write("# Inference Speed Testing Results\n\n")
            f.write(f"**Test Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Summary table
            f.write("## Performance Summary\n\n")
            f.write("| Model | Device | Load Time | Short Prompt (tokens/s) | Medium Prompt (tokens/s) | Long Prompt (tokens/s) |\n")
            f.write("|-------|--------|-----------|------------------------|--------------------------|------------------------|\n")

            for model_name, results in sorted(self.results.items()):
                if "error" in results:
                    f.write(f"| {model_name} | ERROR | - | - | - | - |\n")
                else:
                    device = results.get("device", "N/A")
                    load_time = f"{results.get('load_time_seconds', 0):.2f}s"

                    short_tps = results["tests"].get("short", {}).get("tokens_per_second", 0)
                    medium_tps = results["tests"].get("medium", {}).get("tokens_per_second", 0)
                    long_tps = results["tests"].get("long", {}).get("tokens_per_second", 0)

                    f.write(f"| {model_name} | {device} | {load_time} | {short_tps:.2f} | {medium_tps:.2f} | {long_tps:.2f} |\n")

            # Detailed results
            f.write("\n## Detailed Results\n\n")

            for model_name, results in sorted(self.results.items()):
                f.write(f"### {model_name}\n\n")

                if "error" in results:
                    f.write(f"**Error**: {results['error']}\n\n")
                    continue

                f.write(f"- **Device**: {results.get('device', 'N/A')}\n")
                f.write(f"- **Model Load Time**: {results.get('load_time_seconds', 0):.2f}s\n\n")

                for prompt_type, test_result in results["tests"].items():
                    f.write(f"#### {prompt_type.capitalize()} Prompt\n\n")
                    if "error" in test_result:
                        f.write(f"**Error**: {test_result['error']}\n\n")
                    else:
                        f.write(f"- **Generation Time**: {test_result.get('generation_time_seconds', 0):.2f}s\n")
                        f.write(f"- **Tokens Generated**: {test_result.get('tokens_generated', 0)}\n")
                        f.write(f"- **Throughput**: {test_result.get('tokens_per_second', 0):.2f} tokens/second\n")
                        f.write(f"- **Sample Output**: {test_result.get('generated_text', 'N/A')}\n\n")

            f.write("## Notes\n\n")
            f.write("- Tokens/second is a key metric for inference speed\n")
            f.write("- Load time is the time to load the model into memory\n")
            f.write("- Tests use generation_config: max_tokens=128, temperature=0.7, top_p=0.95\n")
            f.write("- All models tested with the same prompts for fair comparison\n")

def main():
    """Main testing function."""
    print("\n" + "="*80)
    print("LOCAL LLM INFERENCE SPEED TESTING")
    print("="*80 + "\n")

    models_dir = Path("d:\\Data\\Local_LLM_Testing\\models")
    results_dir = Path("d:\\Data\\Local_LLM_Testing\\results")

    testor = InferenceTestor(models_dir, results_dir)

    # Find models
    models = testor.find_models()
    if not models:
        print(f"No models found in {models_dir}/hf_models/")
        print("Please run setup_models.py first to download models.")
        return 1

    print(f"Found {len(models)} model(s) to test:")
    for model in models:
        print(f"  - {model.name}")

    # Test each model
    for model_path in models:
        testor.test_model(model_path)
        print("\n")

    # Save results
    testor.save_results()

    print("\n" + "="*80)
    print("TESTING COMPLETE")
    print("="*80)
    print("\nResults saved in:", results_dir)

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
