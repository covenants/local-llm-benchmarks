#!/usr/bin/env python3
"""
HumanEval Pro benchmark for any Ollama model.

Generalized from scripts/qwen3_coder_humaneval_pro.py — the prompt construction,
execution harness and scoring are byte-identical to that script so results are
directly comparable to the qwen3-coder-30b-iq4xs baseline (60.4%).

Usage:
    python scripts/humaneval_pro_ollama.py --model qwen3.6:35b-a3b-coding
    python scripts/humaneval_pro_ollama.py --model qwen3-coder-next:q4_K_M --out results/foo.json
"""

import argparse
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

import ollama

REPO_ROOT     = Path(__file__).resolve().parent.parent
DATASET_PATH  = REPO_ROOT / "humaneval_pro" / "dataset" / "humaneval_pro.json"
MAX_PROBLEMS  = 164
MAX_TOKENS    = 2048
EXEC_TIMEOUT  = 10   # seconds per test execution

SYSTEM_PROMPT = (
    "You are an expert Python programmer. "
    "Implement the requested Python function completely. "
    "Output ONLY a raw Python code block — the complete function with signature and body. "
    "No markdown fences, no explanation, no extra text. "
    "Include any necessary imports at the top."
)

def build_prompt(new_problem: str) -> str:
    lines = new_problem.strip().splitlines()
    description_lines = [l for l in lines if l.startswith("#")]
    sig_lines = [l for l in lines if not l.startswith("#")]
    description = "\n".join(description_lines).strip()
    signature   = "\n".join(sig_lines).strip()
    return (
        f"Task: {description}\n\n"
        f"Implement this function:\n{signature}\n\n"
        f"Output the complete function (signature + body). /no_think"
    )

THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)

# Some models reject the `think` option entirely; remember that per-model so we
# only pay for the failed call once.
_THINK_UNSUPPORTED: set[str] = set()

def generate(model: str, problem_prompt: str, think: bool | None,
             max_tokens: int = MAX_TOKENS) -> tuple[str, float, int]:
    """Generate one solution.

    `think` is passed through to Ollama's API-level thinking switch. Reasoning
    models (Qwen 3.6/3.8) return their chain of thought in a separate
    `thinking` field and leave `content` EMPTY, so without think=False every
    problem scores as a generation failure while burning the whole token
    budget. Prompt-level "/no_think" does not work on these builds.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": problem_prompt},
    ]
    options = {"temperature": 0.0, "num_predict": max_tokens}

    t0 = time.time()
    try:
        if think is None or model in _THINK_UNSUPPORTED:
            resp = ollama.chat(model=model, messages=messages, options=options)
        else:
            try:
                resp = ollama.chat(model=model, messages=messages, think=think, options=options)
            except Exception:
                # Model has no thinking support — retry without the flag.
                _THINK_UNSUPPORTED.add(model)
                resp = ollama.chat(model=model, messages=messages, options=options)

        message = resp["message"]
        code = (message["content"] or "").strip()
        # Older/other builds inline the reasoning in the content instead.
        code = THINK_RE.sub("", code).strip()
        # Strip markdown fences if the model adds them anyway
        if code.startswith("```"):
            lines = code.splitlines()
            code = "\n".join(
                l for l in lines
                if not l.strip().startswith("```")
            ).strip()
        tokens = resp.get("eval_count", 0) or 0
        return code, time.time() - t0, tokens
    except Exception:
        return "", time.time() - t0, 0

TYPING_HEADER = "from typing import List, Dict, Tuple, Optional, Any, Set, Union\n"

def execute_code(new_problem: str, generated_code: str, test_code: str) -> tuple[bool, str]:
    """Execute generated code against test assertions."""
    full_code = TYPING_HEADER + generated_code + "\n\n" + test_code
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(full_code)
            tmp = f.name
        result = subprocess.run(
            ["python", tmp],
            capture_output=True, text=True, timeout=EXEC_TIMEOUT
        )
        os.unlink(tmp)
        return result.returncode == 0, result.stderr[:200] if result.stderr else ""
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    except Exception as e:
        return False, str(e)[:200]

def slugify(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", model)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="Ollama model tag")
    ap.add_argument("--out", default=None, help="Results JSON path")
    ap.add_argument("--limit", type=int, default=MAX_PROBLEMS)
    ap.add_argument("--max-tokens", type=int, default=MAX_TOKENS,
                    help="num_predict budget. Reasoning models need a much "
                         "larger budget than 2048 or they cap out mid-thought "
                         "and return empty content.")
    ap.add_argument("--think", action="store_true",
                    help="Allow model-side reasoning (default: disabled, "
                         "matching the non-thinking qwen3-coder-30b baseline)")
    args = ap.parse_args()

    model = args.model
    results_path = Path(args.out) if args.out else (
        REPO_ROOT / "results" / f"humaneval_pro_{slugify(model)}.json"
    )

    print("=" * 65)
    print(f"HumanEval Pro — {model} ({args.limit} problems)")
    print("=" * 65)

    try:
        listed = ollama.list()
        model_names = {m.model for m in listed.models} if hasattr(listed, "models") else set()
    except Exception:
        model_names = set()
    if model not in model_names and f"{model}:latest" not in model_names:
        print(f"ERROR: '{model}' not found in Ollama. Pull it first.")
        return 1

    with open(DATASET_PATH, encoding="utf-8") as f:
        dataset = json.load(f)[:args.limit]

    results = {
        "model": model,
        "thinking_enabled": args.think,
        "max_tokens": args.max_tokens,
        "total": len(dataset),
        "passed": 0,
        "failed": 0,
        "error": 0,
        "timeout": 0,
        "pass_rate": 0.0,
        "avg_gen_time": 0.0,
        "total_tokens": 0,
        "problems": [],
    }

    gen_times = []
    start_wall = time.time()

    for idx, problem in enumerate(dataset):
        pid       = problem["id"]
        new_prob  = problem["new_problem"]
        test_code = problem.get("test_code", "")

        prompt = build_prompt(new_prob)
        code, gen_time, tokens = generate(model, prompt, args.think, args.max_tokens)
        gen_times.append(gen_time)
        results["total_tokens"] += tokens

        if not code:
            passed, err = False, "generation_failed"
            results["error"] += 1
        else:
            passed, err = execute_code(new_prob, code, test_code)
            if err == "TIMEOUT":
                results["timeout"] += 1
            elif passed:
                results["passed"] += 1
            else:
                results["failed"] += 1

        results["problems"].append({
            "id":       pid,
            "passed":   passed,
            "gen_time": round(gen_time, 2),
            "tokens":   tokens,
            "error":    err,
        })

        elapsed = time.time() - start_wall
        rate = (idx + 1) / elapsed * 60  # problems/min
        eta  = (len(dataset) - idx - 1) / (rate / 60) / 60 if rate > 0 else 0
        status = "PASS" if passed else "FAIL"
        print(
            f"  [{idx+1:>3}/{len(dataset)}] #{pid:<4} {status}  "
            f"{gen_time:>5.1f}s  |  "
            f"total {elapsed/60:>4.1f}m  ETA {eta:>4.1f}m",
            flush=True
        )

    total_time = time.time() - start_wall
    results["pass_rate"]    = results["passed"] / results["total"] * 100
    results["avg_gen_time"] = sum(gen_times) / len(gen_times)
    results["total_time_s"] = round(total_time, 1)
    results["tokens_per_sec"] = round(results["total_tokens"] / sum(gen_times), 1) if sum(gen_times) else 0.0

    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 65)
    print("FINAL RESULTS")
    print("=" * 65)
    print(f"Model:           {model}")
    print(f"Problems:        {results['total']}")
    print(f"Passed:          {results['passed']}  ({results['pass_rate']:.1f}%)")
    print(f"Failed:          {results['failed']}")
    print(f"Errors:          {results['error']}")
    print(f"Timeouts:        {results['timeout']}")
    print(f"Avg gen time:    {results['avg_gen_time']:.1f}s/problem")
    print(f"Throughput:      {results['tokens_per_sec']} tok/s")
    print(f"Total wall time: {total_time/60:.1f} min")
    print(f"\nResults saved: {results_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
