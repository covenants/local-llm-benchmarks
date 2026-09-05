# Agentic Tool-Use Evaluation

Declared `tools` support only means a model can emit a tool call. This test
measures whether it can run an actual agent loop: pick the right tool, chain
calls whose inputs depend on earlier results, act on what it finds, and verify
before stopping.

Task: a sandboxed 3-file project with a failing test suite (`calculate_total`
crashes on an empty list). Tools: `list_files`, `read_file`, `write_file`,
`run_tests`. Scored on observed behaviour, not self-report.

Harness: [`agent_loop_test.py`](agent_loop_test.py)

## Results

| Model | Solved | Calls | Listed first | Read before write | Verified fix | Ran tests first | Time |
|---|:--:|--:|:--:|:--:|:--:|:--:|--:|
| `qwen3-coder-30b-iq4xs` (run 1, cold) | ✅ | 6 | ✅ | ✅ | ✅ | — | 19.4s |
| `qwen3-coder-30b-iq4xs` (run 2) | ✅ | 6 | ✅ | ✅ | ✅ | — | **6.1s** |
| `qwen3-coder-30b-iq4xs` (run 3) | ✅ | 6 | ✅ | ✅ | ✅ | — | **6.3s** |
| `qwen3-coder-next:q4_K_M` | ✅ | 6 | ✅ | ✅ | ✅ | ✅ | 173.5s |
| `qwen3.6:35b-a3b-coding` | ✅ | 6 | ✅ | ✅ | ✅ | ✅ | 282.8s |
| `llama3.2` | ❌ | 3 | ✅ | ❌ | ❌ | — | 48.5s |

Every model except `llama3.2` solved the task in six tool calls. The separation
is entirely in **latency**, and it is enormous: `qwen3-coder-30b` finishes in
~6s warm, against 174s and 283s. That is a 28x gap for an identical outcome.

`llama3.2` listed and read files but never attempted a fix, stopping after
three calls. Tool-calling capability alone is clearly not sufficient.

## Two valid strategies appeared

```
qwen3-coder-30b:  list -> read -> read -> write_file -> run_tests -> run_tests
coder-next/3.6:   list -> read -> read -> run_tests  -> write_file -> run_tests
```

The second group ran the suite *before* fixing, to observe the failure
first-hand rather than inferring it from the source. That is arguably the
better habit. Both groups verified after writing.

### A metric bug this exposed

The first version of `verified_after_write` compared `seq.index("run_tests")`
against `seq.index("write_file")` -- **first** occurrences. For the
observe-first sequence that yields `3 > 4 == False`, scoring a model that did
verify its fix as though it had not, and penalising the better strategy.

The check now compares **last** occurrences, and `ran_tests_before_fixing` was
added to record the strategy rather than silently punish it. The initial run of
this file reported `verified after fix: False` for `qwen3.6` and
`qwen3-coder-next`; that was a harness defect, not model behaviour.

## This corrects an earlier inference

The app-build task ([`../app_build_eval/RESULTS.md`](../app_build_eval/RESULTS.md))
found `qwen3-coder-30b` plateauing at 24/39 across three repair rounds, fixing
nothing when handed failing pytest output and asked to regenerate a whole file.
The natural inference was that it would be weak as an agent.

That inference was wrong. The tasks differ in a way that matters:

| | Repair loop (failed) | Agent loop (succeeded) |
|---|---|---|
| Unit of work | regenerate an entire 300-line file | one small tool call |
| State access | a wall of text in the prompt | inspect on demand |
| Fault localisation | infer from a symptom list | read the actual file |

The model is good at **small focused steps with tools to inspect state** and bad
at **whole-file regeneration from a text dump**. Only the former is what agent
harnesses actually ask of a model, so the agentic result is the more relevant
one for daily use.

## Ollama Cloud availability (tested, not assumed)

| Model | Result on this account |
|---|---|
| `gemma4:31b-cloud` | works on the free tier |
| `glm-5.3:cloud` | 402 Payment Required |
| `glm-5.3-flash:cloud` | 402 Payment Required |
| `deepseek-v4-flash:cloud` | 402 Payment Required |
| `glm-4.6:cloud` | retired upstream (2026-06-16) |

The strongest open-weights cloud coder (GLM-5.3) requires a paid Ollama
subscription. `gemma4:31b-cloud` is the only free cloud option confirmed
working.

Note: `gpt-oss:120b` no longer loads after the Ollama 0.33.3 upgrade --
`tensor "blk.0.ffn_down_exps.weight" size overflow`. It needs re-pulling.

## Recommendation

Use **`qwen3-coder-30b-iq4xs`** for local agent work. It matches every other
local model on outcome and beats them by 28x on latency, which is the dimension
that actually decides whether an agent loop is usable interactively.

## Limits of this test

One task, one bug, three files. It shows a clean short loop, not durability
over long multi-file sessions -- and the app-build result suggests quality
degrades as scope grows. Treat this as a floor, not a ceiling.
