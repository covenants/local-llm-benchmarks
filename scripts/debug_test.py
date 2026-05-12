"""Debug script to test problem generation with detailed error output"""

import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import traceback

DATASET_PATH = "humaneval_pro/dataset/humaneval_pro.json"
MODEL_NAME = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Using device: {DEVICE}")
print(f"Loading model: {MODEL_NAME}")

try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True, timeout=60)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    print("[OK] Tokenizer loaded")

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True
    )
    model.eval()
    print("[OK] Model loaded")

    # Load dataset
    with open(DATASET_PATH, 'r') as f:
        dataset = json.load(f)

    # Test first 3 problems
    for idx in range(min(3, len(dataset))):
        problem = dataset[idx]
        print(f"\n{'='*60}")
        print(f"Testing Problem {idx}")
        print(f"{'='*60}")

        try:
            prompt = problem["new_problem"]
            print(f"Prompt length: {len(prompt)} chars")
            print(f"First 100 chars: {prompt[:100]}")

            inputs = tokenizer.encode(prompt, return_tensors="pt").to(DEVICE)
            print(f"Tokenized input shape: {inputs.shape}")

            with torch.no_grad():
                outputs = model.generate(
                    inputs,
                    max_new_tokens=512,
                    temperature=0.7,
                    top_p=0.95,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id,
                )

            generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            code = generated_text[len(prompt):].strip()
            print(f"[OK] Generated {len(code)} chars of code")
            print(f"First 100 chars of generated code: {code[:100]}")

        except Exception as e:
            print(f"[ERROR] {e}")
            traceback.print_exc()

except Exception as e:
    print(f"[ERROR] Setup failed: {e}")
    traceback.print_exc()
