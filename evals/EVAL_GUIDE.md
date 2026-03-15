# Autoresearch Eval: How It Works

This guide explains how the eval runs **with vs without Mem0**, what gets trained, and how evaluation works.

---

## The Big Picture

**Autoresearch** is an experiment where an AI agent (Cursor/Claude) autonomously researches how to improve a small language model. The agent:

1. Edits `train.py` with an idea (e.g., change learning rate, add a layer)
2. Runs training for a fixed time budget
3. Gets a **val_bpb** (validation bits-per-byte) score — lower is better
4. Keeps the change if it improved, reverts if not
5. Repeats indefinitely

**The eval** compares two conditions:

| Condition | Program | Memory | What the agent has |
|-----------|---------|--------|--------------------|
| **baseline** | `program.md` | None | Only git + `results.tsv` (current session) |
| **memory** | `program_mem0.md` | mem0 | Git + results.tsv + **persistent mem0** (past experiments, failures, insights) |

The hypothesis: **memory** should outperform **baseline** because the agent can avoid repeating failed experiments and build on what worked.

---

## What Gets Trained?

The same thing in both conditions: a **small GPT-style language model** on **ClimbMix** (Karpathy’s 400B-token web text dataset).

- **Model**: GPT with configurable depth, width, window attention
- **Data**: ClimbMix shards (parquet) + BPE tokenizer
- **Metric**: **val_bpb** (validation bits-per-byte) — lower = better language modeling
- **Time budget**: 5 min default, 2 min on laptop (`--laptop`)

The agent only edits `train.py`. It cannot change `prepare.py` (data, tokenizer, eval harness). So the **evaluation is fixed** — same data, same metric, same time budget. The only variable is the agent’s ability to find better hyperparameters/architecture.

---

## How the Eval Runs

### 1. Setup a run

```bash
# Baseline (no memory)
uv run python evals/run_experiment.py --condition baseline --run-id 1

# Memory (with mem0)
uv run python evals/run_experiment.py --condition memory --run-id 1
```

This prints instructions: which program to use, how to record results.

### 2. Point the agent

- **Baseline**: Point Cursor/Claude to `program.md`
- **Memory**: Point to `program_mem0.md`, set `MEM0_API_KEY`, optionally `AUTORESEARCH_RUN_ID`

### 3. Agent runs the loop

**Baseline loop** (`program.md`):

1. Edit `train.py`
2. `git commit`
3. Run `uv run train.py > run.log 2>&1`
4. Parse `val_bpb` from log
5. Append to `results.tsv`
6. Keep or revert based on improvement

**Memory loop** (`program_mem0.md`):

1. **Query mem0** — "past experiments, failures, best configs"
2. Edit `train.py` (using that context)
3. `git commit`
4. Run `uv run train.py > run.log 2>&1`
5. Parse `val_bpb` from log
6. Append to `results.tsv`
7. **Add to mem0** — config, val_bpb, status, insight
8. Keep or revert based on improvement

### 4. Record results

After the agent finishes N experiments:

```bash
uv run python evals/run_experiment.py --record --condition baseline --run-id 1 --source results.tsv
uv run python evals/run_experiment.py --record --condition memory --run-id 1 --source results.tsv
```

This copies `results.tsv` → `evals/results/{condition}_{run_id}.tsv`.

### 5. View the dashboard

```bash
uv run streamlit run evals/dashboard.py
```

Open the URL (e.g. http://localhost:8501). The dashboard shows:

- Table: condition, run_id, experiments, best val_bpb, status
- Chart: val_bpb over experiment index
- Aggregate metrics per condition

---

## Laptop Mode (4GB VRAM)

On a laptop with 4GB VRAM:

1. **Prepare** (once): `uv run python prepare.py --laptop`
2. **Train**: `uv run python train.py --laptop`

Laptop profile: smaller model (depth 4), shorter sequences (256), 2 min budget. Cursor runs in the cloud; only `train.py` uses your GPU.

---

## 40-Experiment Protocol

- 2 sessions × 5 experiments × 4 runs = 40 experiments
- 2 runs baseline, 2 runs memory
- ~2 min per experiment on laptop → ~80 min GPU total

---

## Metrics

| Metric | Definition |
|--------|------------|
| **Best val_bpb** | Lowest val_bpb in a run |
| **Mean ± std** | Across runs per condition |
| **Time to target** | Experiments to reach val_bpb ≤ X |
| **Redundancy** | Near-duplicate experiments (memory should reduce this) |

---

## Summary

| Question | Answer |
|----------|--------|
| What is trained? | Small GPT on ClimbMix |
| What is the metric? | val_bpb (lower = better) |
| Baseline vs memory? | Same training; memory adds mem0 for past experiments |
| How to run? | `run_experiment.py` setup → agent → record → dashboard |
| Laptop? | `--laptop` on prepare + train |
