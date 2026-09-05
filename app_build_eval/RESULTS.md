# App Build Head-to-Head: Claude Opus 5 vs qwen3-coder-30b

Task: build a single-file, stdlib-only URL shortener from `spec/SPEC.md`.
Judged by 39 black-box HTTP acceptance tests written and committed **before**
either implementation existed.

## Scores

| | Claude Opus 5 | `qwen3-coder-30b-iq4xs` |
|---|---:|---:|
| Round 0 (one-shot, no feedback) | **39/39 (100%)** | 24/39 (61.5%) |
| After 3 repair rounds with failing test output | n/a | **24/39 (61.5%)** |
| Lines produced | 317 | 336 |
| Wall time | single pass | 15.8s + 3 x ~18s |

A separate sample from the same model at the same temperature produced a file
that **did not compile at all** (`SyntaxError: name 'DB_PATH' is used prior to
global declaration`, line 268 of 277) and scored 0/39. Both samples are kept:
`submissions/qwen3-coder-30b-iq4xs/` and `submissions/_qwen_run1_bad_feedback/`.

## What the local model got wrong

**1. Routing: the `/api/links/<code>` handler is unreachable dead code.**

```python
# Handle redirect
if self.path.startswith('/'):        # matches EVERY path
    code = self.path[1:]
    ...
    return                            # always returns

# Handle API endpoints
if self.path.startswith('/api/links/'):   # never reached
```

`GET /api/links/<code>` is treated as a short-code lookup for the literal code
`api/links/<code>`, returns 404, and the test sees `KeyError: 'clicks'`. The
spec states explicitly: *"Reserved prefix: `/api/...` is never a short code."*
The model wrote the correct handler and then made it unreachable.

**2. Single-threaded server, despite an explicit instruction.**

```python
server = HTTPServer(('', PORT), Handler)     # spec required ThreadingHTTPServer
```

The spec says *"The server must handle concurrent requests (use
`ThreadingHTTPServer`)"*. With 25 concurrent clients the server serialises,
requests time out, and the failure cascades through every later test in the
suite -- which is why 15 tests fail rather than the 2 or 3 the underlying bugs
would suggest.

**3. A new SQLite connection per operation**, opened and discarded inside
`increment_clicks` and friends, with no locking around read-modify-write.

## The finding that matters most

**Three repair rounds produced zero improvement: 24/39, 24/39, 24/39, 24/39.**

The model regenerated the file each round (contents changed; rounds 2 and 3 were
byte-identical to each other) but never fixed a single failing test, despite
being handed the failing pytest output, the full spec, and its own current
source. It could not localise "this handler is unreachable" from "KeyError:
'clicks'".

That is a sharper limitation than any pass-rate gap. A model that scores lower
but converges under feedback is usable in an agent loop; a model that plateaus
immediately is not.

## Reliability

At `temperature=0.0` two runs of the same prompt produced materially different
programs -- 277 lines that did not compile, and 336 lines that scored 61.5%.
Determinism is not guaranteed for this MoE model under Ollama, so a single
sample is not a reliable measurement of it.

## Why this task and not HumanEval Pro

On HumanEval Pro this model scores 60.4%, close to models that cost far more to
run. That benchmark presents one self-contained function per problem. It cannot
observe:

- whole-file coherence (the `global` scoping error, the unreachable branch)
- following explicit non-functional requirements (`ThreadingHTTPServer`)
- correctness under concurrency
- recovery from test feedback

All four are what "shipping a production app" actually consists of, and the
model's HumanEval Pro score is not predictive of any of them. The 60.4% vs
64.0% spread between local models measured previously is far less consequential
than the gap this task exposes.

## Fairness notes

- The 39 tests were written from the spec alone and committed before any
  implementation existed, so the contract could not be retrofitted.
- The tests are pure black-box HTTP against a spawned subprocess and never
  import the submission.
- **The same author wrote the tests and one of the submissions.** Opus 5's
  39/39 should be read as "the spec author also implemented the spec". The
  local model received the identical spec, which is precise about status codes,
  JSON shapes and the alias regex, but this asymmetry cannot be fully removed.
- Two harness bugs were found and fixed before scoring, both of which had
  handicapped the local model:
  - Ollama's default 4096-token context truncated the prompt; raised to 32768.
  - Repair rounds were fed the *tail* of pytest output (a list of test names)
    rather than the head (tracebacks and error messages), so the model never
    saw the actual `SyntaxError`. Fixed to prefer the head.
  The pre-fix run is retained under `submissions/_qwen_run1_bad_feedback/`.

## Reproducing

```bash
python app_build_eval/generate_submission.py --model <ollama-tag> --repair-rounds 3
python -m pytest app_build_eval/spec/test_acceptance.py --app <path/to/app.py>
```
