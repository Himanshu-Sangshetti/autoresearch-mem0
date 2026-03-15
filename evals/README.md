# Autoresearch Eval Protocol

This directory contains the evaluation framework for comparing autoresearch **with** vs **without** mem0 memory.

## Metrics

| Metric | Definition |
|--------|-------------|
| **Best val_bpb in N experiments** | Lowest val_bpb achieved after N runs |
| **Time to target** | Number of experiments to reach val_bpb <= X (e.g. 0.98) |
| **Redundancy** | Count of near-duplicate experiments (same config class) |
| **Multi-session recovery** | Session 2+ benefits from mem0; baseline loses context |

## Conditions

- **baseline**: Use `program.md`. No mem0. Agent has only git + results.tsv.
- **memory**: Use `program_mem0.md`. mem0 enabled. Agent queries and stores experiments in mem0.

## Single-Session Protocol

1. **Runs**: 5 runs per condition (baseline_1..5, memory_1..5).
2. **Experiments per run**: 20 (or until human stops).
3. **Setup each run**:
   ```bash
   uv run python evals/run_experiment.py --condition baseline --run-id 1
   # Follow printed instructions: point agent to program.md
   ```
4. **Record when done**:
   ```bash
   uv run python evals/run_experiment.py --record --condition baseline --run-id 1 --source results.tsv
   ```
5. **Analyze** (requires `uv run` for pandas and other deps):
   ```bash
   uv run python evals/analyze.py
   uv run python evals/analyze.py --target 0.98  # custom target
   ```

## Multi-Session Protocol

Tests cross-session memory. Memory condition should outperform baseline when the agent is restarted.

1. **Session 1**: Run 10 experiments with `program_mem0.md`. Agent stores to mem0.
2. **Stop**: End the agent session (new chat, or restart).
3. **Session 2**: Start fresh agent. Point to `program_mem0.md`. Agent queries mem0 at start — should see prior experiments. Run 10 more experiments.
4. **Session 3** (optional): Repeat.
5. **Baseline**: For comparison, run 3 sessions of 10 experiments with `program.md`. Agent has no memory across sessions (only results.tsv file if it persists).

## Reproducibility

- Use same hardware (GPU) for all runs.
- Use same agent (e.g. Claude in Cursor) for both conditions.
- For memory runs: set `AUTORESEARCH_RUN_ID` to a unique value per run (e.g. `eval_memory_1_20250315`) so memories don't leak between runs.

## Output

Results are stored in `evals/results/{condition}_{run_id}.tsv`. The analyze script aggregates and reports mean ± std for best val_bpb, time to target, and redundancy.
