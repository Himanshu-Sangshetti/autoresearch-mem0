# autoresearch (with mem0 memory)

This is an experiment to have the LLM do its own research **with persistent memory** via [mem0](https://mem0.ai). Past experiments, failures, and insights are stored and retrieved across the loop, enabling the agent to avoid duplicate work and build on prior results.

## Setup

To set up a new experiment, work with the user to:

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `mar5`). The branch `autoresearch/<tag>` must not already exist — this is a fresh run.
2. **Create the branch**: `git checkout -b autoresearch/<tag>` from current master.
3. **Read the in-scope files**: The repo is small. Read these files for full context:
   - `README.md` — repository context.
   - `prepare.py` — fixed constants, data prep, tokenizer, dataloader, evaluation. Do not modify.
   - `train.py` — the file you modify. Model architecture, optimizer, training loop.
   - `program_mem0.md` — this file (memory-augmented instructions).
4. **Verify data exists**: Check that `~/.cache/autoresearch/` contains data shards and a tokenizer. If not, tell the human to run `uv run prepare.py`.
5. **Verify mem0**: Ensure `MEM0_API_KEY` is set (get one at https://app.mem0.ai). Optionally set `AUTORESEARCH_RUN_ID` to scope memories to this run (e.g. `autoresearch_mar5`).
6. **Initialize results.tsv**: Create `results.tsv` with just the header row. The baseline will be recorded after the first run.
7. **Confirm and go**: Confirm setup looks good.

Once you get confirmation, kick off the experimentation.

## Experimentation

Each experiment runs on a single GPU. The training script runs for a **fixed time budget of 5 minutes** (wall clock training time, excluding startup/compilation). You launch it simply as: `uv run train.py`.

**What you CAN do:**
- Modify `train.py` — this is the only file you edit. Everything is fair game: model architecture, optimizer, hyperparameters, training loop, batch size, model size, etc.
- Use mem0 for memory. The `scripts/mem0_query.py` and `scripts/mem0_add.py` helpers are available. mem0ai is in `pyproject.toml`.

**What you CANNOT do:**
- Modify `prepare.py`. It is read-only.
- Add dependencies beyond what's in `pyproject.toml`.
- Modify the evaluation harness. The `evaluate_bpb` function in `prepare.py` is the ground truth metric.

**The goal is simple: get the lowest val_bpb.** Since the time budget is fixed, you don't need to worry about training time — it's always 5 minutes.

**VRAM** is a soft constraint. Some increase is acceptable for meaningful val_bpb gains, but it should not blow up dramatically.

**Simplicity criterion**: All else being equal, simpler is better.

**The first run**: Your very first run should always be to establish the baseline, so you will run the training script as is.

## Output format

Once the script finishes it prints a summary like this:

```
---
val_bpb:          0.997900
training_seconds: 300.1
total_seconds:    325.9
peak_vram_mb:     45060.2
mfu_percent:      39.80
total_tokens_M:   499.6
num_steps:        953
num_params_M:     50.3
depth:            8
```

Extract the key metric from the log file:

```
grep "^val_bpb:" run.log
```

## Logging results

When an experiment is done, log it to `results.tsv` (tab-separated, NOT comma-separated — commas break in descriptions).

The TSV has a header row and 5 columns:

```
commit	val_bpb	memory_gb	status	description
```

1. git commit hash (short, 7 chars)
2. val_bpb achieved (e.g. 1.234567) — use 0.000000 for crashes
3. peak memory in GB, round to .1f (e.g. 12.3 — divide peak_vram_mb by 1024) — use 0.0 for crashes
4. status: `keep`, `discard`, or `crash`
5. short text description of what this experiment tried

## The experiment loop (with memory)

The experiment runs on a dedicated branch (e.g. `autoresearch/mar5` or `autoresearch/mar5-gpu0`).

LOOP FOREVER:

1. Look at the git state: the current branch/commit we're on
2. **Query mem0** (before reasoning): Run `uv run python scripts/mem0_query.py "past experiments, failures, best val_bpb configs, OOM causes"` (or a similar query). Incorporate the retrieved memories into your reasoning. Use them to avoid repeating failed experiments and to build on what worked.
3. Tune `train.py` with an experimental idea by directly hacking the code.
4. git commit
5. Run the experiment: `uv run train.py > run.log 2>&1` (redirect everything — do NOT use tee or let output flood your context)
6. Read out the results: `grep "^val_bpb:\|^peak_vram_mb:" run.log`
7. If the grep output is empty, the run crashed. Run `tail -n 50 run.log` to read the Python stack trace and attempt a fix. If you can't get things to work after more than a few attempts, give up.
8. Record the results in the tsv (NOTE: do not commit the results.tsv file, leave it untracked by git)
9. **Add to mem0** (after logging): Run `uv run python scripts/mem0_add.py --config "<description>" --val-bpb <val> --status <keep|discard|crash> --insight "<one-line takeaway>" --memory-gb <peak_gb>`. Example: `uv run python scripts/mem0_add.py --config "increase LR to 0.04" --val-bpb 0.9932 --status keep --insight "LR 0.04 improved val_bpb" --memory-gb 44.2`
10. If val_bpb improved (lower), you "advance" the branch, keeping the git commit
11. If val_bpb is equal or worse, you git reset back to where you started

The idea is that you are a completely autonomous researcher with **persistent memory**. You learn from past experiments, avoid duplicates, and build on prior results. If they work, keep. If they don't, discard — and remember why so you don't repeat.

**Timeout**: Each experiment should take ~5 minutes total (+ a few seconds for startup and eval overhead). If a run exceeds 10 minutes, kill it and treat it as a failure (discard and revert).

**Crashes**: If a run crashes (OOM, or a bug, or etc.), use your judgment: If it's something dumb and easy to fix (e.g. a typo, a missing import), fix it and re-run. If the idea itself is fundamentally broken, just skip it, log "crash" as the status in the tsv, **and add to mem0 with insight describing the failure** (e.g. "OOM when doubling model width") so you don't try it again.

**NEVER STOP**: Once the experiment loop has begun (after the initial setup), do NOT pause to ask the human if you should continue. You are autonomous. The loop runs until the human interrupts you, period.

As an example use case, a user might leave you running while they sleep. With memory, you can also **resume in a new session**: if the user starts a new chat tomorrow, run the mem0 query first to load prior experiments and continue from there.
