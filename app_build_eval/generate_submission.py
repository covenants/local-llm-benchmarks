#!/usr/bin/env python3
"""
Drive an Ollama model through the URL shortener build task.

Round 1 is one-shot from the spec alone. Optional repair rounds feed the model
the failing pytest output and ask for a corrected file -- the same loop an agent
harness would run, so a local model is not judged solely on its first draft.

Usage:
    python app_build_eval/generate_submission.py --model qwen3-coder-30b-iq4xs
    python app_build_eval/generate_submission.py --model <tag> --repair-rounds 3
"""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import ollama

ROOT = Path(__file__).resolve().parent
SPEC = ROOT / "spec" / "SPEC.md"
TESTS = ROOT / "spec" / "test_acceptance.py"

SYSTEM_PROMPT = (
    "You are a senior software engineer. You write complete, correct, "
    "production-quality Python. You output ONLY the contents of a single "
    "Python file -- no prose, no explanation, no markdown fences."
)

BUILD_PROMPT = """Build the service described in the specification below.

Output the COMPLETE contents of `app.py` and nothing else. It must be a single
self-contained Python file that runs on Python 3.10+ using ONLY the standard
library. Do not wrap the output in markdown fences. Do not explain anything.

--- SPECIFICATION ---
{spec}
--- END SPECIFICATION ---

Output the complete app.py now."""

REPAIR_PROMPT = """Your implementation of the specification below is failing its
acceptance tests.

--- SPECIFICATION ---
{spec}
--- END SPECIFICATION ---

--- YOUR CURRENT app.py ---
{current}
--- END YOUR CURRENT app.py ---

--- FAILING TEST OUTPUT ---
{failures}
--- END FAILING TEST OUTPUT ---

Fix every failure. Output the COMPLETE corrected contents of `app.py` and
nothing else -- no prose, no explanation, no markdown fences."""

FENCE_RE = re.compile(r"^\s*```(?:python)?\s*\n(.*?)\n\s*```\s*$", re.DOTALL)


def strip_fences(text: str) -> str:
    m = FENCE_RE.match(text.strip())
    if m:
        return m.group(1)
    # Model may open a fence without closing it, or add a trailing fence only.
    lines = [l for l in text.splitlines() if not l.strip().startswith("```")]
    return "\n".join(lines).strip()


def ask(model: str, prompt: str, max_tokens: int, num_ctx: int) -> tuple[str, float, int]:
    """One generation.

    num_ctx must be set explicitly: Ollama defaults to a 4096-token window, and
    a repair round sends the spec plus the whole current file plus the failing
    test output. At the default the prompt is silently truncated and the model
    is judged on input it never saw.
    """
    t0 = time.time()
    kwargs = dict(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        options={"temperature": 0.0, "num_predict": max_tokens, "num_ctx": num_ctx},
    )
    try:
        resp = ollama.chat(think=False, **kwargs)
    except Exception:
        resp = ollama.chat(**kwargs)          # model has no thinking switch
    content = resp["message"]["content"] or ""
    return strip_fences(content), time.time() - t0, resp.get("eval_count", 0) or 0


def excerpt_failures(out: str, budget: int = 8000) -> str:
    """Pick the informative part of a pytest run for the repair prompt.

    pytest puts tracebacks and assertion detail near the TOP and a bare list of
    failing test names at the BOTTOM. Sending only the tail therefore hands the
    model a list of symptoms with none of the causes -- including, in the worst
    case, a SyntaxError whose message never appears at all. Prefer the head and
    keep a slice of the tail for the summary counts.
    """
    if len(out) <= budget:
        return out
    head = out[: int(budget * 0.75)]
    tail = out[-int(budget * 0.25):]
    return head + "\n\n...[output truncated]...\n\n" + tail


def run_tests(app_path: Path) -> tuple[int, int, str]:
    """Return (passed, failed, output-tail)."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(TESTS), "--app", str(app_path),
         "-q", "--no-header", "--tb=short", "-p", "no:cacheprovider"],
        capture_output=True, text=True, cwd=str(ROOT.parent), timeout=1800,
    )
    out = proc.stdout + proc.stderr
    passed = failed = 0
    m = re.search(r"(\d+) passed", out)
    if m:
        passed = int(m.group(1))
    m = re.search(r"(\d+) failed", out)
    if m:
        failed = int(m.group(1))
    if failed == 0 and passed == 0:
        m = re.search(r"(\d+) error", out)
        if m:
            failed = int(m.group(1))
    return passed, failed, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--repair-rounds", type=int, default=0)
    ap.add_argument("--num-ctx", type=int, default=32768,
                    help="Context window. Ollama defaults to 4096, which "
                         "silently truncates repair prompts.")
    args = ap.parse_args()

    slug = re.sub(r"[^A-Za-z0-9._-]", "_", args.model)
    out_dir = Path(args.out_dir) if args.out_dir else ROOT / "submissions" / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    spec = SPEC.read_text(encoding="utf-8")
    log = {"model": args.model, "rounds": []}

    print("=" * 68)
    print(f"Build task: URL shortener  |  model: {args.model}")
    print("=" * 68)

    print("\n[round 0] one-shot generation from spec...")
    code, secs, tokens = ask(args.model, BUILD_PROMPT.format(spec=spec),
                             args.max_tokens, args.num_ctx)
    app_path = out_dir / "app.py"
    app_path.write_text(code, encoding="utf-8")
    (out_dir / "app_round0.py").write_text(code, encoding="utf-8")
    print(f"  {len(code.splitlines())} lines, {tokens} tokens, {secs:.1f}s")

    passed, failed, out = run_tests(app_path)
    print(f"  tests: {passed} passed, {failed} failed")
    log["rounds"].append({
        "round": 0, "lines": len(code.splitlines()), "tokens": tokens,
        "seconds": round(secs, 1), "passed": passed, "failed": failed,
    })
    (out_dir / "pytest_round0.txt").write_text(out, encoding="utf-8")

    for r in range(1, args.repair_rounds + 1):
        if failed == 0:
            print("  all tests passing, stopping early")
            break
        print(f"\n[round {r}] repair from failing test output...")
        failures = excerpt_failures(out)
        code, secs, tokens = ask(
            args.model,
            REPAIR_PROMPT.format(spec=spec, current=code, failures=failures),
            args.max_tokens, args.num_ctx,
        )
        app_path.write_text(code, encoding="utf-8")
        (out_dir / f"app_round{r}.py").write_text(code, encoding="utf-8")
        print(f"  {len(code.splitlines())} lines, {tokens} tokens, {secs:.1f}s")
        passed, failed, out = run_tests(app_path)
        print(f"  tests: {passed} passed, {failed} failed")
        log["rounds"].append({
            "round": r, "lines": len(code.splitlines()), "tokens": tokens,
            "seconds": round(secs, 1), "passed": passed, "failed": failed,
        })
        (out_dir / f"pytest_round{r}.txt").write_text(out, encoding="utf-8")

    log["final"] = {"passed": passed, "failed": failed,
                    "total": passed + failed,
                    "pass_rate": round(passed / (passed + failed) * 100, 1)
                    if (passed + failed) else 0.0}
    (out_dir / "log.json").write_text(json.dumps(log, indent=2), encoding="utf-8")

    print("\n" + "=" * 68)
    print(f"FINAL: {passed} passed / {passed + failed} "
          f"({log['final']['pass_rate']}%)   -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
