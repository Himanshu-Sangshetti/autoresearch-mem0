#!/usr/bin/env python3
"""
Add an experiment result to mem0.
Agent runs this after each experiment to store config, result, and insight.

Usage:
    uv run python scripts/mem0_add.py --config "LR 0.04, depth 8" --val-bpb 0.993 --status keep --insight "LR 0.04 improved val_bpb"
    uv run python scripts/mem0_add.py --config "double width" --val-bpb 0 --status crash --insight "OOM on 24GB GPU"

Requires MEM0_API_KEY environment variable (or mem0 Platform API key).
"""

import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(description="Add experiment to mem0 memory")
    parser.add_argument("--config", type=str, required=True, help="Short description of the change (e.g., 'LR 0.04, depth 8')")
    parser.add_argument("--val-bpb", type=float, required=True, help="val_bpb achieved (use 0.0 for crashes)")
    parser.add_argument("--status", type=str, required=True, choices=["keep", "discard", "crash"], help="Experiment status")
    parser.add_argument("--insight", type=str, default="", help="One-line takeaway (e.g., 'LR 0.04 improved; avoid GeLU')")
    parser.add_argument("--memory-gb", type=float, default=0, help="Peak memory in GB (optional)")
    parser.add_argument("--user-id", type=str, default=None, help="mem0 user_id (default: autoresearch from env or 'autoresearch')")
    args = parser.parse_args()

    api_key = (os.environ.get("MEM0_API_KEY") or "").strip()
    if not api_key:
        print("Error: MEM0_API_KEY environment variable not set. Sign up at https://app.mem0.ai", file=sys.stderr)
        sys.exit(1)

    user_id = args.user_id or os.environ.get("AUTORESEARCH_RUN_ID", "autoresearch")

    # Build a structured message for mem0 to store
    content_parts = [
        f"Experiment: {args.config}",
        f"val_bpb: {args.val_bpb:.6f}",
        f"status: {args.status}",
    ]
    if args.memory_gb > 0:
        content_parts.append(f"memory_gb: {args.memory_gb:.1f}")
    if args.insight:
        content_parts.append(f"insight: {args.insight}")

    content = ". ".join(content_parts)

    try:
        from mem0 import MemoryClient

        client = MemoryClient(api_key=api_key)
        messages = [
            {"role": "user", "content": content},
            {"role": "assistant", "content": f"Stored experiment: {args.config} -> val_bpb={args.val_bpb}, status={args.status}"},
        ]
        client.add(messages, user_id=user_id)
        print(f"Added to mem0: {args.config} (val_bpb={args.val_bpb}, status={args.status})")
    except ImportError:
        print("Error: mem0ai not installed. Run: uv sync (or pip install mem0ai)", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error adding to mem0: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
