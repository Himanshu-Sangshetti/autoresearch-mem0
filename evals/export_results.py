#!/usr/bin/env python3
"""
Export eval results to JSON (optional, for scripting or external dashboards).

Reads evals/results/*.tsv and writes evals/results.json.
The Streamlit dashboard reads TSV directly; this script is for JSON export.

Usage:
  uv run python evals/export_results.py
  uv run python evals/export_results.py -o evals/results.json
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

RESULTS_DIR = Path(__file__).resolve().parent / "results"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "results.json"


def load_runs():
    """Load all TSV files into a list of run dicts."""
    runs = []

    if not RESULTS_DIR.exists():
        return runs

    for f in sorted(RESULTS_DIR.glob("*.tsv")):
        parts = f.stem.split("_", 1)
        if len(parts) < 2:
            continue
        condition, run_id = parts[0], parts[1]
        try:
            df = pd.read_csv(f, sep="\t")
        except Exception:
            continue

        if "val_bpb" not in df.columns:
            continue

        val_bpb = pd.to_numeric(df["val_bpb"], errors="coerce")
        valid = val_bpb[val_bpb > 0]
        best_val_bpb = float(valid.min()) if len(valid) > 0 else None

        # Series for chart: [[exp_idx, val_bpb], ...]
        data = []
        for i, row in df.iterrows():
            v = row.get("val_bpb")
            if v is not None:
                try:
                    vf = float(v)
                    if vf > 0:
                        data.append([int(i) + 1, vf])
                except (TypeError, ValueError):
                    pass

        status = "complete"  # could derive from last row if needed
        if "status" in df.columns:
            last = df["status"].iloc[-1] if len(df) > 0 else ""
            if str(last).lower() in ("fail", "crash", "error"):
                status = str(last).lower()

        runs.append({
            "condition": condition,
            "run_id": run_id,
            "experiments": len(df),
            "best_val_bpb": best_val_bpb,
            "status": status,
            "data": data,
        })

    return runs


def main():
    parser = argparse.ArgumentParser(description="Export eval results to JSON for dashboard")
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT, help="Output JSON path")
    args = parser.parse_args()

    runs = load_runs()
    out = {
        "runs": runs,
        "updated": datetime.now(timezone.utc).isoformat(),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(out, f, indent=2)

    print(f"Exported {len(runs)} runs to {args.output}")


if __name__ == "__main__":
    main()
