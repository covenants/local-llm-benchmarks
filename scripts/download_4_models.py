#!/usr/bin/env python3
"""
Download only the 4 models needed for detailed testing.
"""

from huggingface_hub import snapshot_download
from pathlib import Path
import sys

MODELS = [
    {
        "model_id": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        "name": "TinyLlama-1.1B",
        "size": "~2.2GB",
    },
    {
        "model_id": "deepseek-ai/deepseek-coder-1.3b-instruct",
        "name": "DeepSeek-Coder-1.3B",
        "size": "~2.6GB",
    },
    {
        "model_id": "microsoft/phi-2",
        "name": "Phi-2-2.7B",
        "size": "~5.5GB",
    },
    {
        "model_id": "bigcode/starcoder2-3b",
        "name": "StarCoder2-3B",
        "size": "~6GB",
    },
]

def main():
    print("\n" + "="*80)
    print("DOWNLOADING 4 MODELS FOR DETAILED TESTING")
    print("="*80 + "\n")

    for i, model in enumerate(MODELS, 1):
        print(f"\n[{i}/{len(MODELS)}] {model['name']}")
        print(f"Size: {model['size']}")
        print(f"Downloading from: {model['model_id']}\n")

        models_dir = Path("d:\\Data\\Local_LLM_Testing\\models\\hf_models")
        save_dir = models_dir / model['name']

        try:
            snapshot_download(
                repo_id=model['model_id'],
                cache_dir=str(save_dir),
                resume_download=True,
                local_files_only=False
            )
            print(f"[OK] Successfully downloaded {model['name']}")
        except Exception as e:
            print(f"✗ Failed to download {model['name']}: {e}")
            return 1

    print("\n" + "="*80)
    print("DOWNLOAD COMPLETE")
    print("="*80)
    print("\nNext: Run 'python scripts/detailed_inference_test.py' to test these models")
    return 0

if __name__ == "__main__":
    sys.exit(main())
