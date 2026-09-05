#!/usr/bin/env python3
"""
Build a markdown comparison table from HumanEval Pro result JSONs.

Usage:
    python scripts/compare_humaneval_pro.py results/*.json --out results/MODEL_COMPARISON.md
"""

import argparse
import itertools
import json
from math import comb
from pathlib import Path

def load(path: Path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    if not isinstance(d, dict) or "pass_rate" not in d:
        return None
    return d


def mcnemar_exact(pa: dict, pb: dict) -> tuple[int, int, float]:
    """Exact two-sided binomial McNemar test over paired per-problem outcomes.

    Only discordant pairs carry information: problems both models get right (or
    both get wrong) say nothing about which is better. With ~164 problems the
    discordant count is small, so differences of a few points are usually not
    distinguishable from noise -- which is the whole point of reporting this.
    """
    ids = sorted(set(pa) & set(pb))
    a_only = sum(1 for i in ids if pa[i] and not pb[i])
    b_only = sum(1 for i in ids if pb[i] and not pa[i])
    n = a_only + b_only
    if n == 0:
        return a_only, b_only, 1.0
    k = min(a_only, b_only)
    p = sum(comb(n, i) for i in range(k + 1)) / 2 ** n * 2
    return a_only, b_only, min(p, 1.0)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", nargs="+", help="Result JSON files")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    runs = []
    for p in args.results:
        d = load(Path(p))
        if d:
            runs.append(d)
    runs.sort(key=lambda d: d["pass_rate"], reverse=True)

    lines = [
        "# HumanEval Pro — Local Model Comparison",
        "",
        "All runs use the same harness (`scripts/humaneval_pro_ollama.py`): identical",
        "system prompt, temperature 0.0, 164 problems, generated code",
        "executed against the dataset's assert test cases with a 10s timeout.",
        "",
        "| Model | Pass | Fail | Pass rate | Avg gen | Throughput | Wall time |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for d in runs:
        tps = d.get("tokens_per_sec", 0) or 0
        tps_s = f"{tps:.1f} tok/s" if tps else "n/a"
        lines.append(
            f"| `{d['model']}` | {d['passed']} | {d['failed']} | "
            f"**{d['pass_rate']:.1f}%** | {d['avg_gen_time']:.1f}s | {tps_s} | "
            f"{d.get('total_time_s', 0)/60:.1f} min |"
        )

    by_model = {d["model"]: {p["id"]: p["passed"] for p in d["problems"]} for d in runs}

    # Pairwise significance. A few points of pass-rate difference on 164
    # problems is routinely within noise, so state it rather than imply a winner.
    if len(runs) > 1:
        lines += [
            "",
            "## Significance (exact McNemar, paired per-problem)",
            "",
            "| A | B | A only | B only | p |",
            "|---|---|---:|---:|---:|",
        ]
        for (ma, pa), (mb, pb) in itertools.combinations(by_model.items(), 2):
            a_only, b_only, pv = mcnemar_exact(pa, pb)
            sig = "" if pv < 0.05 else " (n.s.)"
            lines.append(f"| `{ma}` | `{mb}` | {a_only} | {b_only} | {pv:.3f}{sig} |")

        ids = sorted(set.intersection(*[set(v) for v in by_model.values()]))
        n_all  = sum(1 for i in ids if all(by_model[m][i] for m in by_model))
        n_any  = sum(1 for i in ids if any(by_model[m][i] for m in by_model))
        n_none = len(ids) - n_any
        lines += [
            "",
            f"Of {len(ids)} problems: **{n_all}** ({n_all/len(ids)*100:.1f}%) solved by every "
            f"model, **{n_any}** ({n_any/len(ids)*100:.1f}%) by at least one "
            f"(the oracle ceiling for routing between them), **{n_none}** "
            f"({n_none/len(ids)*100:.1f}%) by none.",
        ]

    # Per-problem agreement: which problems does each model uniquely fail?
    if len(runs) > 1:
        lines += ["", "## Divergence", ""]
        all_ids = sorted(set().union(*[set(v) for v in by_model.values()]))
        for model, probs in by_model.items():
            others = [m for m in by_model if m != model]
            uniq_pass = [i for i in all_ids
                         if probs.get(i) and not any(by_model[o].get(i) for o in others)]
            uniq_fail = [i for i in all_ids
                         if probs.get(i) is False and all(by_model[o].get(i) for o in others)]
            lines.append(f"- `{model}`: solved alone: {len(uniq_pass)} "
                         f"{uniq_pass[:12]}{'...' if len(uniq_pass) > 12 else ''}; "
                         f"failed alone: {len(uniq_fail)} "
                         f"{uniq_fail[:12]}{'...' if len(uniq_fail) > 12 else ''}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nWrote {out}")

if __name__ == "__main__":
    main()
