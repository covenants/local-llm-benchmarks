"""
Verification script to test HumanEval Pro setup
Checks: dataset, model loading, code generation, and test execution
"""

import json
import time
import torch
import subprocess
import tempfile
import os
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM

DATASET_PATH = "humaneval_pro/dataset/humaneval_pro.json"
TEST_MODELS = [
    "TinyLlama/TinyLlama-1.1B-Chat-v1.0",  # Fastest to verify setup
    "deepseek-ai/deepseek-coder-1.3b-instruct",  # Coding specialist
]

def verify_dataset():
    """Check if HumanEval Pro dataset exists and is valid"""
    print("\n[VERIFICATION] Checking HumanEval Pro Dataset...")

    if not Path(DATASET_PATH).exists():
        print(f"  ERROR: Dataset not found at {DATASET_PATH}")
        return False

    try:
        with open(DATASET_PATH, 'r') as f:
            data = json.load(f)

        print(f"  OK: Dataset loaded ({len(data)} problems)")
        print(f"  Sample problem keys: {list(data[0].keys())}")
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def verify_model_load(model_name: str):
    """Check if a model can be loaded"""
    print(f"\n[VERIFICATION] Loading model: {model_name}")

    try:
        start = time.time()
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True, timeout=60)
        print(f"  OK: Tokenizer loaded ({time.time()-start:.1f}s)")

        start = time.time()
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True
        )
        print(f"  OK: Model loaded ({time.time()-start:.1f}s)")

        del model
        del tokenizer
        torch.cuda.empty_cache()
        return True
    except Exception as e:
        print(f"  ERROR: {str(e)[:100]}")
        return False


def verify_code_generation(model_name: str):
    """Check if a model can generate code"""
    print(f"\n[VERIFICATION] Testing code generation: {model_name}")

    try:
        # Load model and tokenizer
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True
        )
        model.eval()

        # Load one problem
        with open(DATASET_PATH, 'r') as f:
            dataset = json.load(f)
        problem = dataset[0]

        # Generate code
        prompt = problem["raw_problem"]
        inputs = tokenizer.encode(prompt, return_tensors="pt").to("cuda" if torch.cuda.is_available() else "cpu")

        start = time.time()
        with torch.no_grad():
            outputs = model.generate(
                inputs,
                max_new_tokens=128,
                temperature=0.7,
                pad_token_id=tokenizer.eos_token_id
            )
        gen_time = time.time() - start

        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        code = generated_text[len(prompt):].strip()

        print(f"  OK: Generated {len(code)} characters in {gen_time:.2f}s")
        print(f"  Sample output:\n{code[:200]}...")

        del model
        del tokenizer
        torch.cuda.empty_cache()
        return True
    except Exception as e:
        print(f"  ERROR: {str(e)[:100]}")
        return False


def verify_code_execution():
    """Check if code can be executed and tested"""
    print(f"\n[VERIFICATION] Testing code execution...")

    try:
        # Create a simple Python script
        test_code = """
def add(a, b):
    return a + b

print(add(2, 3))
assert add(2, 3) == 5
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_code)
            temp_file = f.name

        try:
            result = subprocess.run(
                ["python", temp_file],
                capture_output=True,
                timeout=5,
                text=True
            )

            if result.returncode == 0:
                print(f"  OK: Code executed successfully")
                return True
            else:
                print(f"  ERROR: {result.stderr[:100]}")
                return False
        finally:
            os.unlink(temp_file)
    except Exception as e:
        print(f"  ERROR: {str(e)[:100]}")
        return False


def verify_cuda():
    """Check GPU availability"""
    print(f"\n[VERIFICATION] Checking GPU...")

    if torch.cuda.is_available():
        print(f"  OK: CUDA available")
        print(f"  GPU: {torch.cuda.get_device_name(0)}")
        print(f"  VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB")
        return True
    else:
        print(f"  WARNING: CUDA not available, will use CPU (slow)")
        return True  # Not critical, just slow


def main():
    print("=" * 80)
    print("HumanEval Pro Setup Verification")
    print("=" * 80)

    checks = [
        ("CUDA/GPU", verify_cuda),
        ("Dataset", verify_dataset),
    ]

    all_pass = True
    for name, check_func in checks:
        try:
            if not check_func():
                all_pass = False
        except Exception as e:
            print(f"  ERROR: {e}")
            all_pass = False

    # Test model loading and generation
    for model in TEST_MODELS:
        try:
            if not verify_model_load(model):
                all_pass = False
            elif not verify_code_generation(model):
                all_pass = False
        except Exception as e:
            print(f"  ERROR: {e}")
            all_pass = False

    # Test code execution
    try:
        if not verify_code_execution():
            all_pass = False
    except Exception as e:
        print(f"  ERROR: {e}")
        all_pass = False

    print("\n" + "=" * 80)
    if all_pass:
        print("RESULT: All checks passed! Ready to run full benchmark.")
        print("Run: python scripts/humaneval_pro_test.py")
    else:
        print("RESULT: Some checks failed. See errors above.")
    print("=" * 80)


if __name__ == "__main__":
    main()
