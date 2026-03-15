#!/usr/bin/env python3
"""
Streamlit dashboard for autoresearch eval results.

Reads evals/results/*.tsv and displays:
- Summary table (condition, run_id, experiments, best val_bpb, status)
- Line chart: val_bpb over experiment index per run
- Aggregate metrics (mean ± std per condition)

Usage:
  uv run streamlit run evals/dashboard.py
  uv run streamlit run evals/dashboard.py --server.port 8502
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

RESULTS_DIR = Path(__file__).resolve().parent / "results"


@st.cache_data(ttl=30)
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

        status = "complete"
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
            "data": df,
        })
    return runs


def main():
    st.set_page_config(
        page_title="Autoresearch Eval Dashboard",
        page_icon="📊",
        layout="wide",
    )

    st.title("📊 Autoresearch Eval Dashboard")
    st.caption("Compares baseline (no memory) vs memory (mem0) conditions")

    if st.button("🔄 Refresh", help="Reload results from evals/results/*.tsv"):
        load_runs.clear()
        st.rerun()

    runs = load_runs()

    if not runs:
        st.info("No results yet. Run experiments and record them with `evals/run_experiment.py --record`.")
        st.code("uv run python evals/run_experiment.py --record --condition baseline --run-id 1 --source results.tsv")
        return

    # Summary table
    st.subheader("Runs summary")
    table_data = [
        {
            "Condition": r["condition"],
            "Run ID": r["run_id"],
            "Experiments": r["experiments"],
            "Best val_bpb": f"{r['best_val_bpb']:.6f}" if r["best_val_bpb"] is not None else "—",
            "Status": r["status"],
        }
        for r in runs
    ]
    st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

    # Aggregate metrics per condition
    st.subheader("Aggregate by condition")
    by_cond = {}
    for r in runs:
        c = r["condition"]
        if c not in by_cond:
            by_cond[c] = []
        if r["best_val_bpb"] is not None:
            by_cond[c].append(r["best_val_bpb"])

    cols = st.columns(len(by_cond) or 1)
    for i, (cond, vals) in enumerate(sorted(by_cond.items())):
        with cols[i]:
            if vals:
                mean = sum(vals) / len(vals)
                var = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1) if len(vals) > 1 else 0
                std = var ** 0.5
                st.metric(
                    label=f"**{cond}** (n={len(vals)})",
                    value=f"{mean:.6f}",
                    delta=f"± {std:.6f}" if std > 0 else None,
                )
            else:
                st.metric(label=f"**{cond}**", value="—", delta=None)

    # Line chart: val_bpb over experiments
    st.subheader("val_bpb over experiments")
    fig = go.Figure()
    colors = ["#6ee7b7", "#93c5fd", "#fbbf24", "#f472b6", "#a78bfa"]
    for i, r in enumerate(runs):
        df = r["data"]
        val_bpb = pd.to_numeric(df["val_bpb"], errors="coerce")
        valid_mask = val_bpb > 0
        if not valid_mask.any():
            continue
        exp_idx = [j + 1 for j in range(len(df)) if valid_mask.iloc[j]]
        vals = val_bpb[valid_mask].tolist()
        fig.add_trace(
            go.Scatter(
                x=exp_idx,
                y=vals,
                mode="lines+markers",
                name=f"{r['condition']}_{r['run_id']}",
                line=dict(color=colors[i % len(colors)], width=2),
                marker=dict(size=6),
            )
        )
    fig.update_layout(
        xaxis_title="Experiment",
        yaxis_title="val_bpb",
        hovermode="x unified",
        height=400,
        margin=dict(l=60, r=20, t=20, b=60),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Raw data expander
    with st.expander("View raw TSV files"):
        for r in runs:
            st.markdown(f"**{r['condition']}_{r['run_id']}**")
            st.dataframe(r["data"], use_container_width=True, hide_index=True)

    st.caption("Results from evals/results/*.tsv · Data refreshes every 30s or on Refresh click")


if __name__ == "__main__":
    main()
