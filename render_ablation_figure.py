# render_ablation_figure.py

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid", context="talk")

INPUT_CSV = Path("results_package/derived_metrics/ablation_results.csv")
OUTPUT_PNG = Path("results_package/figures/fig_ablation.png")

VARIANT_LABELS = {
    "full": "Full AQF",
    "no_structure_awareness": "No structure\nawareness",
    "no_operator_specific_scoring": "No operator-\nspecific scoring",
    "no_missingness_handling": "No missingness\nhandling",
    "no_progressive_disclosure": "No progressive\ndisclosure"
}

def main():
    df = pd.read_csv(INPUT_CSV)
    df["variant_label"] = df["variant"].map(VARIANT_LABELS).fillna(df["variant"])

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    sns.barplot(
        data=df,
        x="variant_label",
        y="structural_expressivity",
        palette="Blues_d",
        ax=axes[0]
    )
    axes[0].set_title("Structural expressivity by ablation")
    axes[0].set_xlabel("")
    axes[0].set_ylabel("Structural expressivity")
    axes[0].tick_params(axis="x", rotation=20)

    sns.barplot(
        data=df,
        x="variant_label",
        y="utility_proxy",
        palette="Oranges_d",
        ax=axes[1]
    )
    axes[1].set_title("Utility proxy by ablation")
    axes[1].set_xlabel("")
    axes[1].set_ylabel("Utility proxy")
    axes[1].tick_params(axis="x", rotation=20)

    plt.tight_layout()
    OUTPUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_PNG, dpi=300, bbox_inches="tight")
    print(f"[OK] Saved: {OUTPUT_PNG}")

if __name__ == "__main__":
    main()