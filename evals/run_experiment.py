#!/usr/bin/env python3
"""
Eval runner for autoresearch with/without memory.

Setup: Prepares environment for a run (condition A=baseline or B=memory).
Record: Copies results.tsv to evals/results/ after a run completes.

Usage:
  # Start a new run (prints instructions)
  uv run python evals/run_experiment.py --condition baseline --run-id 1
  uv run python evals/run_experiment.py --condition memory --run-id 1

  # After agent completes, record results
  uv run python evals/run_experiment.py --record --condition baseline --run-id 1 --source results.tsv
  uv run python evals/run_experiment.py --record --condition memory --run-id 1 --source results.tsv
"""

import argparse
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVALS_DIR.parent
RESULTS_DIR = EVALS_DIR / "results"


def setup_run(condition: str, run_id: str) -> None:
    """Print setup instructions and set env for the run."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if condition == "baseline":
        program = "program.md"
        mem_note = "No mem0. Agent uses only git + results.tsv."
    elif condition == "memory":
        program = "program_mem0.md"
        run_tag = f"eval_{condition}_{run_id}_{datetime.now().strftime('%Y%m%d')}"
        mem_note = f"mem0 enabled. Set AUTORESEARCH_RUN_ID={run_tag} to scope memories."
        if not os.environ.get("MEM0_API_KEY"):
            print("WARNING: MEM0_API_KEY not set. Get one at https://app.mem0.ai", file=sys.stderr)
    else:
        print(f"Error: unknown condition '{condition}'. Use 'baseline' or 'memory'.", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print(f"EVAL RUN: condition={condition}, run_id={run_id}")
    print("=" * 60)
    print()
    print(f"Program: {program}")
    print(f"Memory: {mem_note}")
    print()
    print("Steps:")
    print(f"  1. Point your agent (Cursor/Claude) to {program}")
    print(f"  2. Use run tag: eval_{condition}_{run_id}")
    print(f"  3. Let the agent run N experiments (e.g. 20)")
    print(f"  4. When done, run:")
    print(f"     uv run python evals/run_experiment.py --record --condition {condition} --run-id {run_id} --source results.tsv")
    print()
    if condition == "memory":
        run_tag = f"eval_{condition}_{run_id}_{datetime.now().strftime('%Y%m%d')}"
        print(f"  Export for this run: export AUTORESEARCH_RUN_ID={run_tag}")
    print("=" * 60)


def _sanitize_run_id(run_id: str) -> str:
    """Allow only alphanumeric, underscore, hyphen to prevent path traversal."""
    return re.sub(r"[^\w\-]", "_", run_id)


def record_run(condition: str, run_id: str, source: str) -> None:
    """Copy results.tsv to evals/results/{condition}_{run_id}.tsv"""
    source_path = Path(source)
    if not source_path.is_absolute():
        source_path = (REPO_ROOT / source_path).resolve()
    else:
        source_path = source_path.resolve()

    # Prevent path traversal: source must be under REPO_ROOT
    try:
        source_path.relative_to(REPO_ROOT.resolve())
    except ValueError:
        print(f"Error: source path must be inside the repo: {source_path}", file=sys.stderr)
        sys.exit(1)

    if not source_path.exists():
        print(f"Error: source file not found: {source_path}", file=sys.stderr)
        sys.exit(1)
    if not source_path.is_file():
        print(f"Error: source must be a file, not a directory: {source_path}", file=sys.stderr)
        sys.exit(1)

    safe_run_id = _sanitize_run_id(run_id)
    dest_path = RESULTS_DIR / f"{condition}_{safe_run_id}.tsv"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, dest_path)
    print(f"Recorded: {source_path} -> {dest_path}")


def main():
    parser = argparse.ArgumentParser(description="Eval runner for autoresearch with/without memory")
    parser.add_argument("--condition", type=str, required=True, choices=["baseline", "memory"], help="baseline (no mem0) or memory (with mem0)")
    parser.add_argument("--run-id", type=str, required=True, help="Unique run identifier (e.g. 1, 2, 3)")
    parser.add_argument("--record", action="store_true", help="Record results after run completes")
    parser.add_argument("--source", type=str, default="results.tsv", help="Path to results.tsv (default: results.tsv)")
    args = parser.parse_args()

    if args.record:
        record_run(args.condition, args.run_id, args.source)
    else:
        setup_run(args.condition, args.run_id)


if __name__ == "__main__":
    main()
