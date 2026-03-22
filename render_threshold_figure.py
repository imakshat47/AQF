# render_threshold_figure.py

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid", context="talk")

INPUT_CSV = Path("results_package/derived_metrics/threshold_sweep.csv")
OUTPUT_PNG = Path("results_package/figures/fig_threshold_sweep.png")

def main():
    df = pd.read_csv(INPUT_CSV)

    fig, axes = plt.subplots(1, 3, figsize=(20, 6))

    # Panel 1: form-set size
    sns.lineplot(
        data=df,
        x="threshold",
        y="form_set_size",
        marker="o",
        linewidth=2.5,
        ax=axes[0],
        color="#1f77b4"
    )
    axes[0].set_title("Form-set size vs threshold")
    axes[0].set_xlabel("Visible field threshold")
    axes[0].set_ylabel("Form-set size")

    # Panel 2: structural expressivity
    sns.lineplot(
        data=df,
        x="threshold",
        y="structural_expressivity",
        marker="o",
        linewidth=2.5,
        ax=axes[1],
        color="#d62728"
    )
    axes[1].set_title("Structural expressivity vs threshold")
    axes[1].set_xlabel("Visible field threshold")
    axes[1].set_ylabel("Structural expressivity")

    # Panel 3: coverage
    sns.lineplot(
        data=df,
        x="threshold",
        y="section_coverage",
        marker="o",
        linewidth=2.5,
        ax=axes[2],
        label="Section coverage",
        color="#2ca02c"
    )
    sns.lineplot(
        data=df,
        x="threshold",
        y="subgroup_coverage",
        marker="o",
        linewidth=2.5,
        ax=axes[2],
        label="Subgroup coverage",
        color="#9467bd"
    )
    sns.lineplot(
        data=df,
        x="threshold",
        y="field_coverage",
        marker="o",
        linewidth=2.5,
        ax=axes[2],
        label="Field coverage",
        color="#ff7f0e"
    )
    axes[2].set_title("Coverage vs threshold")
    axes[2].set_xlabel("Visible field threshold")
    axes[2].set_ylabel("Coverage")
    axes[2].legend(loc="lower right")

    plt.tight_layout()
    OUTPUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_PNG, dpi=300, bbox_inches="tight")
    print(f"[OK] Saved: {OUTPUT_PNG}")

if __name__ == "__main__":
    main()