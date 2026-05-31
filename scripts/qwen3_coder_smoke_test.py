#!/usr/bin/env python3
"""
Smoke test for Qwen3-Coder-30B-A3B-Instruct (iq4_xs GGUF via Ollama).

Downloads the GGUF directly via huggingface_hub, registers it with Ollama,
then runs one coding prompt and reports throughput + VRAM.

Model: Mungert/Qwen3-Coder-30B-A3B-Instruct-GGUF (iq4_xs, 15.3GB)
Full-precision ref: Qwen/Qwen3-Coder-30B-A3B-Instruct
Architecture: MoE, 30B total / 3B active params, 256K native context
"""

import subprocess
import sys
import time
from pathlib import Path

REPO_ID   = "Mungert/Qwen3-Coder-30B-A3B-Instruct-GGUF"
FILENAME  = "Qwen3-Coder-30B-A3B-Instruct-iq4_xs.gguf"
MODEL_DIR = Path(r"D:\Data\Local_LLM_Testing\models\gguf")
OLLAMA_NAME = "qwen3-coder-30b-iq4xs"

# /no_think skips chain-of-thought for direct, fast coding output
PROMPT = """\
Write a Python function that merges two sorted arrays into one sorted array in O(n) time.
Include type hints, a docstring, and 3 test cases. /no_think"""

def run(cmd, **kwargs):
    return subprocess.run(cmd, check=True, **kwargs)

def download_gguf() -> Path:
    local = MODEL_DIR / FILENAME
    if local.exists():
        size_gb = local.stat().st_size / 1024**3
        print(f"GGUF already on disk: {local} ({size_gb:.1f} GB)")
        return local

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {FILENAME} (15.3 GB) from HuggingFace...")
    print("This is a one-time download — subsequent runs skip this step.\n")

    from huggingface_hub import hf_hub_download
    path = hf_hub_download(
        repo_id=REPO_ID,
        filename=FILENAME,
        local_dir=str(MODEL_DIR),
    )
    size_gb = Path(path).stat().st_size / 1024**3
    print(f"Downloaded: {path} ({size_gb:.1f} GB)")
    return Path(path)

def register_with_ollama(gguf_path: Path):
    """Create an Ollama model from the local GGUF if not already registered."""
    result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    if OLLAMA_NAME in result.stdout:
        print(f"Ollama model '{OLLAMA_NAME}' already registered.")
        return

    modelfile = MODEL_DIR / "Modelfile"
    # Qwen3 uses ChatML format; /no_think is injected in the prompt directly
    modelfile.write_text(
        f'FROM "{gguf_path.as_posix()}"\n'
        'PARAMETER num_ctx 4096\n'
        'PARAMETER num_gpu 99\n'
        'TEMPLATE """{{ if .System }}<|im_start|>system\n{{ .System }}<|im_end|>\n{{ end }}'
        '<|im_start|>user\n{{ .Prompt }}<|im_end|>\n<|im_start|>assistant\n"""\n'
        'PARAMETER stop "<|im_end|>"\n'
        'PARAMETER stop "<|im_start|>"\n',
        encoding="utf-8"
    )
    print(f"Registering '{OLLAMA_NAME}' with Ollama...")
    run(["ollama", "create", OLLAMA_NAME, "-f", str(modelfile)])
    print("Registered.")

def main():
    print("=" * 60)
    print("Qwen3-Coder-30B-A3B IQ4_XS Smoke Test (Ollama)")
    print("=" * 60)

    try:
        import ollama as ollama_pkg
    except ImportError:
        run([sys.executable, "-m", "pip", "install", "ollama", "-q"])
        import ollama as ollama_pkg

    # Verify Ollama daemon is reachable
    try:
        ollama_pkg.list()
    except Exception:
        print("ERROR: Ollama daemon not reachable. Start it from the system tray or run: ollama serve")
        sys.exit(1)

    gguf_path = download_gguf()
    register_with_ollama(gguf_path)

    print(f"\nPrompt: {PROMPT}")
    print("-" * 60)
    print("Generating...\n")

    t0 = time.time()
    first_token_time = None
    chunks = []
    last_chunk = {}

    for chunk in ollama_pkg.generate(model=OLLAMA_NAME, prompt=PROMPT, stream=True):
        if first_token_time is None and chunk.get("response"):
            first_token_time = time.time()
        text = chunk.get("response", "")
        chunks.append(text)
        print(text, end="", flush=True)
        last_chunk = chunk

    gen_time = time.time() - t0
    ttft = (first_token_time - t0) if first_token_time else 0

    output_tokens   = last_chunk.get("eval_count", len("".join(chunks).split()))
    eval_duration_s = last_chunk.get("eval_duration", gen_time * 1e9) / 1e9
    tokens_per_sec  = output_tokens / eval_duration_s if eval_duration_s > 0 else 0

    print("\n\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    print(f"Time to first token: {ttft:.1f}s")
    print(f"Total gen time:      {gen_time:.1f}s")
    print(f"Output tokens:       {output_tokens}")
    print(f"Throughput:          {tokens_per_sec:.1f} tokens/sec")

    if tokens_per_sec >= 15:
        print("\nVerdict: PASS — usable for interactive coding (>=15 tok/s)")
    elif tokens_per_sec >= 8:
        print("\nVerdict: MARGINAL — workable for batch tasks, slow for interactive use")
    else:
        print("\nVerdict: SLOW — run `ollama ps` to confirm GPU is being used")

if __name__ == "__main__":
    main()
