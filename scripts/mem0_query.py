#!/usr/bin/env python3
"""
Query mem0 for relevant experiment memories.
Agent runs this before each experiment to retrieve past experiments, failures, and best configs.

Usage:
    uv run python scripts/mem0_query.py "past experiments and failures"
    uv run python scripts/mem0_query.py "best val_bpb configs" --limit 5

Requires MEM0_API_KEY environment variable (or mem0 Platform API key).
"""

import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(description="Query mem0 for experiment memories")
    parser.add_argument("query", type=str, help="Search query (e.g., 'past experiments, failures, best configs')")
    parser.add_argument("--limit", type=int, default=10, help="Max memories to return (default: 10)")
    parser.add_argument("--user-id", type=str, default=None, help="mem0 user_id (default: autoresearch from env or 'autoresearch')")
    args = parser.parse_args()

    api_key = (os.environ.get("MEM0_API_KEY") or "").strip()
    if not api_key:
        print("Error: MEM0_API_KEY environment variable not set. Sign up at https://app.mem0.ai", file=sys.stderr)
        sys.exit(1)

    user_id = args.user_id or os.environ.get("AUTORESEARCH_RUN_ID", "autoresearch")

    try:
        from mem0 import MemoryClient

        client = MemoryClient(api_key=api_key)
        results = client.search(
            query=args.query,
            limit=args.limit,
            filters={"user_id": user_id} if user_id else None,
        )
    except ImportError:
        print("Error: mem0ai not installed. Run: uv sync (or pip install mem0ai)", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error querying mem0: {e}", file=sys.stderr)
        sys.exit(1)

    # Output memories in a format the agent can easily read
    entries = results.get("results", []) if isinstance(results, dict) else []
    if not entries:
        print("(No relevant memories found)")
        return

    for i, entry in enumerate(entries, 1):
        if isinstance(entry, dict):
            memory = entry.get("memory", entry.get("message", str(entry)))
            score = entry.get("score", "")
        else:
            memory = str(entry)
            score = ""
        print(f"{i}. {memory}")
        if score:
            print(f"   [score: {score}]")
    print()


if __name__ == "__main__":
    main()
