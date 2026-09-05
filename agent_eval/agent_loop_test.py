#!/usr/bin/env python3
"""
Agentic tool-use test for local Ollama models.

Declared `tools` capability only means the model can emit a tool call. This
measures whether it can actually run an agent loop: choose the right tool,
chain calls whose inputs depend on earlier results, act on what it finds, and
stop when done.

The task is a small bug hunt in a sandboxed directory:
  1. list the files              (must discover, not guess, the filename)
  2. read the buggy one          (input depends on step 1)
  3. write a fix                 (input depends on step 2)
  4. run the tests to verify     (must confirm rather than assume)

Scoring is on observed behaviour, not on self-report.

Usage:
    python agent_eval/agent_loop_test.py --model qwen3-coder-30b-iq4xs
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import ollama

MAX_STEPS = 14

BUGGY_SOURCE = '''\
def calculate_total(items):
    """Return the sum of the 'price' field across items."""
    total = items[0]["price"]
    for item in items[1:]:
        total += item["price"]
    return total


def apply_discount(total, percent):
    return total - (total * percent / 100)
'''

TEST_SOURCE = '''\
from billing import calculate_total, apply_discount


def test_sums_prices():
    assert calculate_total([{"price": 10}, {"price": 5}]) == 15


def test_empty_list_returns_zero():
    assert calculate_total([]) == 0


def test_discount():
    assert apply_discount(200, 10) == 180
'''

README_SOURCE = """\
Billing helpers.

Run the tests with: python -m pytest test_billing.py
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List the files in the project directory.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the full contents of a file.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string",
                                        "description": "File name, e.g. billing.py"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Overwrite a file with new contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string",
                                "description": "The complete new file contents"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": "Run the project's test suite and return the output.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

TASK = (
    "The test suite in this project is failing. Find the bug, fix it, and run "
    "the tests to confirm they all pass. Use the tools available to you. "
    "Do not guess file names -- list the directory first. When the tests pass, "
    "reply with the single word DONE."
)


class Sandbox:
    def __init__(self):
        self.dir = Path(tempfile.mkdtemp(prefix="agent_eval_"))
        (self.dir / "billing.py").write_text(BUGGY_SOURCE, encoding="utf-8")
        (self.dir / "test_billing.py").write_text(TEST_SOURCE, encoding="utf-8")
        (self.dir / "README.txt").write_text(README_SOURCE, encoding="utf-8")
        self.calls = []

    def cleanup(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _safe(self, name):
        """Confine access to the sandbox; reject traversal."""
        p = (self.dir / name).resolve()
        if not str(p).startswith(str(self.dir.resolve())):
            raise ValueError("path outside sandbox")
        return p

    def dispatch(self, name, args):
        self.calls.append(name)
        try:
            if name == "list_files":
                return "\n".join(sorted(p.name for p in self.dir.iterdir()))
            if name == "read_file":
                return self._safe(args["path"]).read_text(encoding="utf-8")
            if name == "write_file":
                self._safe(args["path"]).write_text(args["content"], encoding="utf-8")
                return "written"
            if name == "run_tests":
                proc = subprocess.run(
                    [sys.executable, "-m", "pytest", "test_billing.py", "-q",
                     "--no-header", "-p", "no:cacheprovider"],
                    cwd=str(self.dir), capture_output=True, text=True, timeout=120,
                )
                return (proc.stdout + proc.stderr)[-2500:]
            return f"unknown tool: {name}"
        except Exception as exc:
            return f"error: {exc}"

    def tests_pass(self):
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "test_billing.py", "-q",
             "--no-header", "-p", "no:cacheprovider"],
            cwd=str(self.dir), capture_output=True, text=True, timeout=120,
        )
        return proc.returncode == 0, (proc.stdout + proc.stderr)[-800:]


def run(model, num_ctx, verbose=True):
    box = Sandbox()
    messages = [
        {"role": "system", "content":
         "You are a software engineering agent. Use the provided tools to "
         "inspect and modify the project. Take one action at a time."},
        {"role": "user", "content": TASK},
    ]
    transcript = []
    t0 = time.time()
    finished_cleanly = False

    try:
        for step in range(MAX_STEPS):
            kwargs = dict(model=model, messages=messages, tools=TOOLS,
                          options={"temperature": 0.0, "num_ctx": num_ctx})
            try:
                resp = ollama.chat(think=False, **kwargs)
            except Exception:
                resp = ollama.chat(**kwargs)

            msg = resp["message"]
            calls = msg.get("tool_calls") or []
            content = (msg.get("content") or "").strip()
            messages.append({
                "role": "assistant",
                "content": content,
                "tool_calls": calls,
            })

            if not calls:
                transcript.append({"step": step, "tool": None,
                                   "text": content[:300]})
                if verbose:
                    print(f"  [{step}] (no tool call) {content[:120]!r}")
                if "DONE" in content.upper():
                    finished_cleanly = True
                break

            for call in calls:
                fn = call["function"]["name"]
                raw = call["function"].get("arguments") or {}
                args = json.loads(raw) if isinstance(raw, str) else raw
                result = box.dispatch(fn, args)
                if verbose:
                    detail = args.get("path", "") if isinstance(args, dict) else ""
                    print(f"  [{step}] {fn}({detail}) -> {str(result)[:70]!r}")
                transcript.append({"step": step, "tool": fn,
                                   "args": {k: str(v)[:120] for k, v in args.items()}
                                   if isinstance(args, dict) else {},
                                   "result": str(result)[:300]})
                messages.append({"role": "tool", "content": str(result),
                                 "tool_name": fn})

        passed, detail = box.tests_pass()
        seq = box.calls
        return {
            "model": model,
            "solved": passed,
            "said_done": finished_cleanly,
            "steps": len(transcript),
            "tool_calls": len(seq),
            "call_sequence": seq,
            "listed_first": bool(seq) and seq[0] == "list_files",
            "read_before_write": ("read_file" in seq and "write_file" in seq
                                  and seq.index("read_file") < seq.index("write_file")),
            "verified_after_write": ("write_file" in seq and "run_tests" in seq
                                     and seq.index("run_tests") > seq.index("write_file")),
            "seconds": round(time.time() - t0, 1),
            "final_test_output": detail,
            "transcript": transcript,
        }
    finally:
        box.cleanup()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--num-ctx", type=int, default=32768)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    print("=" * 64)
    print(f"Agent loop test: {args.model}")
    print("=" * 64)
    result = run(args.model, args.num_ctx)

    print("\n" + "-" * 64)
    print(f"  solved (tests pass) : {result['solved']}")
    print(f"  tool calls          : {result['tool_calls']}  {result['call_sequence']}")
    print(f"  listed before acting: {result['listed_first']}")
    print(f"  read before writing : {result['read_before_write']}")
    print(f"  verified after fix  : {result['verified_after_write']}")
    print(f"  wall time           : {result['seconds']}s")

    out = Path(args.out) if args.out else (
        Path(__file__).resolve().parent / "results" /
        f"{re.sub(r'[^A-Za-z0-9._-]', '_', args.model)}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\n  saved: {out}")


if __name__ == "__main__":
    main()
