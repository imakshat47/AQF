# render_execution_figure.py

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

sns.set_theme(style="whitegrid", context="talk")

INPUT_CSV = Path("results_package/derived_metrics/execution_metrics.csv")
OUTPUT_PNG = Path("results_package/figures/fig_execution_summary.png")


def format_seconds(v: float) -> str:
    """
    Pretty formatting for very small or moderate time values.
    """
    if v < 1e-3:
        return f"{v*1e6:.1f} µs"
    if v < 1:
        return f"{v*1e3:.2f} ms"
    return f"{v:.2f} s"


def add_value_labels(ax, values, fmt_func=None, rotation=0):
    """
    Annotate bar tops with values.
    """
    fmt_func = fmt_func or (lambda x: f"{x:.2f}")
    for i, v in enumerate(values):
        ax.text(
            i,
            v,
            fmt_func(v),
            ha="center",
            va="bottom",
            fontsize=11,
            rotation=rotation
        )


def main():
    df = pd.read_csv(INPUT_CSV)

    if df.empty:
        raise RuntimeError(f"No rows found in {INPUT_CSV}")

    # For readability in case of many queries
    df["query_label"] = df["query_name"].astype(str).str.replace("_", "\n", regex=False)

    fig, axes = plt.subplots(2, 2, figsize=(18, 12))

    # -------------------------
    # Panel 1: Compile vs execution latency
    # -------------------------
    lat_df = df.melt(
        id_vars=["query_label"],
        value_vars=["compile_sec", "execution_sec"],
        var_name="metric",
        value_name="seconds"
    )
    metric_map = {
        "compile_sec": "Compile time",
        "execution_sec": "Execution time"
    }
    lat_df["metric"] = lat_df["metric"].map(metric_map)

    sns.barplot(
        data=lat_df,
        x="query_label",
        y="seconds",
        hue="metric",
        palette=["#4C78A8", "#F58518"],
        ax=axes[0, 0]
    )
    axes[0, 0].set_title("Query compilation and execution latency")
    axes[0, 0].set_xlabel("Query case")
    axes[0, 0].set_ylabel("Time (seconds)")
    axes[0, 0].legend(title="Metric")

    # Annotate bars
    for container in axes[0, 0].containers:
        axes[0, 0].bar_label(
            container,
            labels=[format_seconds(v) for v in container.datavalues],
            padding=3,
            fontsize=10
        )

    # -------------------------
    # Panel 2: Scanned vs matched
    # -------------------------
    vol_df = df.melt(
        id_vars=["query_label"],
        value_vars=["scanned", "matched"],
        var_name="metric",
        value_name="count"
    )
    vol_df["metric"] = vol_df["metric"].map({
        "scanned": "Scanned",
        "matched": "Matched"
    })

    sns.barplot(
        data=vol_df,
        x="query_label",
        y="count",
        hue="metric",
        palette=["#54A24B", "#E45756"],
        ax=axes[0, 1]
    )
    axes[0, 1].set_title("Scanned vs matched records")
    axes[0, 1].set_xlabel("Query case")
    axes[0, 1].set_ylabel("Count")
    axes[0, 1].legend(title="Metric")

    for container in axes[0, 1].containers:
        axes[0, 1].bar_label(
            container,
            labels=[f"{int(v)}" for v in container.datavalues],
            padding=3,
            fontsize=10
        )

    # -------------------------
    # Panel 3: Seconds per document
    # -------------------------
    sns.barplot(
        data=df,
        x="query_label",
        y="sec_per_doc",
        color="#72B7B2",
        ax=axes[1, 0]
    )
    axes[1, 0].set_title("Seconds per document")
    axes[1, 0].set_xlabel("Query case")
    axes[1, 0].set_ylabel("Seconds / doc")

    for container in axes[1, 0].containers:
        axes[1, 0].bar_label(
            container,
            labels=[f"{v:.6f}" for v in container.datavalues],
            padding=3,
            fontsize=10
        )

    # -------------------------
    # Panel 4: Interaction count
    # -------------------------
    sns.barplot(
        data=df,
        x="query_label",
        y="interaction_count",
        color="#B279A2",
        ax=axes[1, 1]
    )
    axes[1, 1].set_title("Interaction count")
    axes[1, 1].set_xlabel("Query case")
    axes[1, 1].set_ylabel("Interactions")

    for container in axes[1, 1].containers:
        axes[1, 1].bar_label(
            container,
            labels=[f"{int(v)}" for v in container.datavalues],
            padding=3,
            fontsize=10
        )

    plt.tight_layout()
    OUTPUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_PNG, dpi=300, bbox_inches="tight")
    print(f"[OK] Saved: {OUTPUT_PNG}")


if __name__ == "__main__":
    main()