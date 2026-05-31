#!/usr/bin/env python3
"""
HumanEval Pro benchmark for Qwen3-Coder-30B-A3B via Ollama.
Tests all 164 problems, executes generated code against assert test cases.

Results saved to results/qwen3_coder_humaneval_pro_results.json
"""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import ollama

OLLAMA_MODEL  = "qwen3-coder-30b-iq4xs"
DATASET_PATH  = Path(r"D:\Data\Local_LLM_Testing\humaneval_pro\dataset\humaneval_pro.json")
RESULTS_PATH  = Path(r"D:\Data\Local_LLM_Testing\results\qwen3_coder_humaneval_pro_results.json")
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
    # Extract description (comment lines) and signature separately so the model
    # gets a clean task description without the truncated stub confusing it.
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

def generate(problem_prompt: str) -> tuple[str, float]:
    t0 = time.time()
    try:
        resp = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": problem_prompt},
            ],
            options={
                "temperature": 0.0,
                "num_predict": MAX_TOKENS,
            },
        )
        code = resp["message"]["content"].strip()
        # Strip markdown fences if the model adds them anyway
        if code.startswith("```"):
            lines = code.splitlines()
            code = "\n".join(
                l for l in lines
                if not l.strip().startswith("```")
            ).strip()
        return code, time.time() - t0
    except Exception as e:
        return "", time.time() - t0

TYPING_HEADER = "from typing import List, Dict, Tuple, Optional, Any, Set, Union\n"

def execute_code(new_problem: str, generated_code: str, test_code: str) -> tuple[bool, str]:
    """Execute generated code against test assertions."""
    # Always include typing imports — many stubs use List/Dict/Tuple without importing them
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

def main():
    print("=" * 65)
    print("HumanEval Pro — Qwen3-Coder-30B-A3B IQ4_XS (164 problems)")
    print("=" * 65)

    # Verify model is registered
    try:
        listed = ollama.list()
        model_names = {m.model for m in listed.models} if hasattr(listed, "models") else set()
    except Exception:
        model_names = set()
    if OLLAMA_MODEL not in model_names and f"{OLLAMA_MODEL}:latest" not in model_names:
        print(f"ERROR: '{OLLAMA_MODEL}' not found in Ollama. Run the smoke test first.")
        return

    with open(DATASET_PATH, encoding="utf-8") as f:
        dataset = json.load(f)[:MAX_PROBLEMS]

    results = {
        "model": OLLAMA_MODEL,
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
        code, gen_time = generate(prompt)
        gen_times.append(gen_time)

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
            "error":    err,
        })

        elapsed = time.time() - start_wall
        rate = (idx + 1) / elapsed * 60  # problems/min
        eta  = (len(dataset) - idx - 1) / (rate / 60) / 60 if rate > 0 else 0
        status = "PASS" if passed else "FAIL"
        print(
            f"  [{idx+1:>3}/{len(dataset)}] #{pid:<4} {status}  "
            f"{gen_time:>5.1f}s  |  "
            f"total {elapsed/60:>4.1f}m  ETA {eta:>4.1f}m"
        )

    total_time = time.time() - start_wall
    results["pass_rate"]    = results["passed"] / results["total"] * 100
    results["avg_gen_time"] = sum(gen_times) / len(gen_times)
    results["total_time_s"] = round(total_time, 1)

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 65)
    print("FINAL RESULTS")
    print("=" * 65)
    print(f"Model:           {OLLAMA_MODEL}")
    print(f"Problems:        {results['total']}")
    print(f"Passed:          {results['passed']}  ({results['pass_rate']:.1f}%)")
    print(f"Failed:          {results['failed']}")
    print(f"Errors:          {results['error']}")
    print(f"Timeouts:        {results['timeout']}")
    print(f"Avg gen time:    {results['avg_gen_time']:.1f}s/problem")
    print(f"Total wall time: {total_time/60:.1f} min")
    print(f"\nResults saved: {RESULTS_PATH}")

if __name__ == "__main__":
    main()
