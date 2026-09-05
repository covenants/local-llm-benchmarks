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

| Model | Solved | Tool calls | Listed first | Read before write | Verified after fix | Time |
|---|---|---:|---|---|---|---:|
| `qwen3-coder-30b-iq4xs` (run 1) | ✅ | 6 | ✅ | ✅ | ✅ | 19.4s |
| `qwen3-coder-30b-iq4xs` (run 2) | ✅ | 6 | ✅ | ✅ | ✅ | ~19s |
| `qwen3-coder-30b-iq4xs` (run 3) | ✅ | 6 | ✅ | ✅ | ✅ | ~19s |
| `qwen3.6:35b-a3b-coding` | not completed | — | — | — | — | — |
| `qwen3-coder-next:q4_K_M` | not completed | — | — | — | — | — |
| `llama3.2` | not completed | — | — | — | — | — |

The three unfinished rows were queued but did not complete in the session that
produced this file. `qwen3.6:35b-a3b-coding` in particular ran for an extended
period without emitting a result. They are listed as not completed rather than
omitted, so the gap is visible.

## `qwen3-coder-30b-iq4xs`: competent, and consistent

All three runs produced the identical call sequence:

```
list_files -> read_file(test_billing.py) -> read_file(billing.py)
           -> write_file(billing.py) -> run_tests -> run_tests -> "DONE"
```

Every behavioural check passed:

- **Listed before acting.** It discovered the filenames rather than guessing
  them, as instructed.
- **Read the tests first, then the source.** It went looking for the contract
  before the implementation -- the correct order for a bug fix.
- **Verified after writing.** It ran the tests rather than declaring success,
  and only said DONE once they passed.
- **Stopped cleanly.** No flailing, no redundant edits.

The duplicate `run_tests` is mild redundancy, not an error.

## This corrects an earlier inference

The app-build task ([`../app_build_eval/RESULTS.md`](../app_build_eval/RESULTS.md))
found this model plateauing at 24/39 across three repair rounds, fixing nothing
when handed failing pytest output and asked to regenerate the whole file. The
natural inference was that it would be weak as an agent.

That inference was wrong. The two tasks differ in a way that matters:

| | Repair loop (failed) | Agent loop (succeeded) |
|---|---|---|
| Unit of work | regenerate an entire 300-line file | one small tool call |
| State access | a wall of text in the prompt | inspect on demand |
| Fault localisation | must infer from a symptom list | can read the actual file |

The model is good at **small focused steps with tools to inspect state** and bad
at **whole-file regeneration from a text dump**. Only the first resembles what
agent harnesses actually ask of a model, so the agentic result is the more
relevant one for day-to-day use.

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

Use **`qwen3-coder-30b-iq4xs`** for local agent work. It is free, private,
fully GPU-resident, and demonstrably runs a clean tool loop.

## Limits of this test

One task, one bug, three files. It shows a clean short loop, not durability
over long multi-file sessions -- and the app-build result suggests quality does
degrade as scope grows. Treat this as a floor, not a ceiling.
