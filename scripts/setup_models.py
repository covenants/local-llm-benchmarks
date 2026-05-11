#!/usr/bin/env python3
"""
Setup script to download open-source LLM models from Hugging Face.
Models are selected based on inference speed, quality, and variety.
"""

import os
import subprocess
import sys
from pathlib import Path

# Define models to download (model_id, file_name, description)
MODELS = [
    # Tier 1: Ultra-Small & Fast (CPU-friendly)
    {
        "model_id": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        "name": "TinyLlama-1.1B",
        "size": "~2.2GB",
        "description": "Smallest, fastest. General chat/coding baseline. ~60 tokens/sec on GPU"
    },

    # Tier 2: Small & Efficient (Coding-Optimized)
    {
        "model_id": "Qwen/CodeQwen1.5-7B-Chat",
        "name": "CodeQwen-7B",
        "size": "~14GB",
        "description": "Small coding expert by Alibaba. Excels at code generation and understanding"
    },
    {
        "model_id": "deepseek-ai/deepseek-coder-1.3b-instruct",
        "name": "DeepSeek-Coder-1.3B",
        "size": "~2.6GB",
        "description": "Tiny but powerful coding model. ~50 tokens/sec on GPU. Excellent code quality for size"
    },

    # Tier 3: Balanced General Purpose
    {
        "model_id": "microsoft/phi-2",
        "name": "Phi-2-2.7B",
        "size": "~5.5GB",
        "description": "Microsoft's efficient model - good all-rounder, decent coding ability"
    },

    # Tier 4: Best Coding Performance (Still Small)
    {
        "model_id": "bigcode/starcoder2-3b",
        "name": "StarCoder2-3B",
        "size": "~6GB",
        "description": "Updated coding model. Best coding for <4GB footprint. ~35 tokens/sec on GPU"
    },
]

def check_dependencies():
    """Check if required packages are installed."""
    required = ["torch", "transformers", "huggingface_hub"]

    for package in required:
        try:
            __import__(package)
            print(f"✓ {package} is installed")
        except ImportError:
            print(f"✗ {package} is NOT installed")
            print(f"  Install with: pip install {package}")
            return False
    return True

def print_model_list():
    """Print list of models to download."""
    print("\n" + "="*80)
    print("MODELS TO DOWNLOAD")
    print("="*80)

    total_size = 0
    for i, model in enumerate(MODELS, 1):
        print(f"\n{i}. {model['name']}")
        print(f"   Model ID: {model['model_id']}")
        print(f"   Description: {model['description']}")
        print(f"   Approximate Size: {model['size']}")

    print("\n" + "="*80)
    print("Note: These are approximate sizes. Actual sizes may vary.")
    print("="*80 + "\n")

def download_models(models_dir):
    """Download models from Hugging Face."""
    from huggingface_hub import snapshot_download

    print("\nStarting model downloads...")
    print("="*80 + "\n")

    downloaded = []
    failed = []

    for model_info in MODELS:
        model_id = model_info["model_id"]
        model_name = model_info["name"]
        save_dir = os.path.join(models_dir, "hf_models", model_name)

        print(f"Downloading {model_name}...")
        print(f"  From: {model_id}")
        print(f"  To: {save_dir}")

        try:
            snapshot_download(
                repo_id=model_id,
                cache_dir=save_dir,
                resume_download=True,
                local_files_only=False
            )
            print(f"✓ Successfully downloaded {model_name}\n")
            downloaded.append(model_name)
        except Exception as e:
            print(f"✗ Failed to download {model_name}: {str(e)}\n")
            failed.append((model_name, str(e)))

    return downloaded, failed

def create_summary(models_dir, downloaded, failed):
    """Create a summary file."""
    summary_path = os.path.join(models_dir, "..", "DOWNLOAD_SUMMARY.md")

    with open(summary_path, 'w') as f:
        f.write("# Model Download Summary\n\n")

        if downloaded:
            f.write("## Successfully Downloaded Models\n\n")
            for model in downloaded:
                f.write(f"- {model}\n")

        if failed:
            f.write("\n## Failed Downloads\n\n")
            for model, error in failed:
                f.write(f"- {model}: {error}\n")

        f.write("\n## Next Steps\n\n")
        f.write("1. Run inference tests using `inference_test.py`\n")
        f.write("2. Results will be saved in the `results/` directory\n")
        f.write("3. Check `INFERENCE_RESULTS.md` for timing comparisons\n")

def main():
    """Main setup function."""
    print("\n" + "="*80)
    print("LOCAL LLM TESTING ENVIRONMENT SETUP")
    print("="*80 + "\n")

    # Check dependencies
    print("Checking dependencies...")
    if not check_dependencies():
        print("\nPlease install missing packages and run again.")
        return 1

    print("\n✓ All dependencies installed\n")

    # Print model list
    print_model_list()

    # Create models directory
    models_dir = Path("d:\\Data\\Local_LLM_Testing\\models")
    models_dir.mkdir(parents=True, exist_ok=True)

    # Download models
    input("\nPress Enter to start downloading models (this may take a while)...")
    downloaded, failed = download_models(models_dir)

    # Create summary
    create_summary(models_dir, downloaded, failed)

    print("\n" + "="*80)
    print("SETUP COMPLETE")
    print("="*80)
    print(f"\nSuccessfully downloaded: {len(downloaded)} models")
    print(f"Failed downloads: {len(failed)} models")
    print("\nNext: Run 'python scripts/inference_test.py' to test inference")

    return 0

if __name__ == "__main__":
    sys.exit(main())
