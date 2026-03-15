#!/usr/bin/env python3
"""
Aggregate eval results and compute metrics.

Reads all evals/results/*.tsv files, computes:
- Best val_bpb per run
- Mean ± std across runs (per condition)
- Time to target (experiments to reach val_bpb <= X)
- Redundancy (optional: count similar descriptions)

Usage:
  uv run python evals/analyze.py
  uv run python evals/analyze.py --target 0.98
"""

import argparse
from pathlib import Path
from collections import defaultdict

import pandas as pd

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def load_results() -> dict[str, list[pd.DataFrame]]:
    """Load all TSV files, grouped by condition (baseline, memory)."""
    by_condition: dict[str, list[pd.DataFrame]] = defaultdict(list)

    if not RESULTS_DIR.exists():
        return dict(by_condition)

    for f in sorted(RESULTS_DIR.glob("*.tsv")):
        # Filename: {condition}_{run_id}.tsv
        parts = f.stem.split("_", 1)
        if len(parts) < 2:
            continue
        condition, run_id = parts[0], parts[1]
        try:
            df = pd.read_csv(f, sep="\t")
            if "val_bpb" in df.columns:
                by_condition[condition].append(df)
        except Exception as e:
            print(f"Warning: could not parse {f}: {e}")

    return dict(by_condition)


def best_val_bpb(df: pd.DataFrame) -> float:
    """Lowest val_bpb in the run (excluding crashes with 0)."""
    val_bpb = pd.to_numeric(df["val_bpb"], errors="coerce")
    valid = val_bpb[val_bpb > 0]
    return float(valid.min()) if len(valid) > 0 else float("nan")


def time_to_target(df: pd.DataFrame, target: float) -> int:
    """Number of experiments (rows) until first val_bpb <= target. -1 if never reached."""
    val_bpb = pd.to_numeric(df["val_bpb"], errors="coerce")
    for i in range(len(df)):
        v = val_bpb.iloc[i]
        if v > 0 and v <= target:
            return int(i) + 1  # 1-indexed experiment number
    return -1


def redundancy_estimate(df: pd.DataFrame) -> int:
    """Rough estimate: count rows with very similar description (first 20 chars)."""
    if "description" not in df.columns:
        return 0
    prefixes = df["description"].astype(str).str[:20]
    return int((prefixes.value_counts() > 1).sum())


def main():
    parser = argparse.ArgumentParser(description="Analyze eval results")
    parser.add_argument("--target", type=float, default=0.98, help="Target val_bpb for time-to-target metric")
    args = parser.parse_args()

    by_condition = load_results()

    if not by_condition:
        print("No results found in evals/results/. Run experiments first.")
        return

    print("=" * 60)
    print("EVAL RESULTS SUMMARY")
    print("=" * 60)
    print()

    for condition in sorted(by_condition.keys()):
        dfs = by_condition[condition]
        print(f"Condition: {condition} (n={len(dfs)} runs)")
        print("-" * 40)

        best_list = [best_val_bpb(df) for df in dfs]
        tt_list = [time_to_target(df, args.target) for df in dfs]
        red_list = [redundancy_estimate(df) for df in dfs]

        if best_list:
            valid_best = [b for b in best_list if b == b]  # filter nan
            if valid_best:
                mean_best = sum(valid_best) / len(valid_best)
                n = len(valid_best)
                var = sum((b - mean_best) ** 2 for b in valid_best) / (n - 1) if n > 1 else 0.0
                std_best = var ** 0.5
                print(f"  Best val_bpb:     {mean_best:.6f} ± {std_best:.6f}")
            else:
                print(f"  Best val_bpb:     (no valid runs)")
        print(f"  Time to {args.target}:  {tt_list} (experiments; -1 = not reached)")
        print(f"  Redundancy (est):  {red_list}")
        print()

    print("=" * 60)
    print("To add more runs: use evals/run_experiment.py --record")
    print("=" * 60)


if __name__ == "__main__":
    main()
