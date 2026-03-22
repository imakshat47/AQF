# render_heatmap.py

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="white", context="talk")

INPUT_CSV = Path("results_package/derived_metrics/queriability_fields.csv")
OUTPUT_PNG = Path("results_package/figures/fig_queriability_heatmap.png")

TOP_N = 25  # adjust if you want more/less rows

def main():
    df = pd.read_csv(INPUT_CSV)

    # Build readable row labels
    df["row_label"] = (
        df["entry_name"].astype(str)
        + " → "
        + df["subgroup_key"].astype(str)
        + " → "
        + df["element_name"].astype(str)
    )

    # Keep top N fields by max role score
    top_df = df.sort_values("max_role_score", ascending=False).head(TOP_N).copy()

    heatmap_df = top_df[
        ["row_label", "selection_score", "projection_score", "ordering_score"]
    ].set_index("row_label")

    plt.figure(figsize=(12, max(8, TOP_N * 0.4)))
    ax = sns.heatmap(
        heatmap_df,
        cmap="YlGnBu",
        annot=True,
        fmt=".2f",
        linewidths=0.5,
        cbar_kws={"label": "Normalized queriability score"}
    )

    ax.set_title("Operator-specific queriability heatmap")
    ax.set_xlabel("Query role")
    ax.set_ylabel("Fields (top ranked)")

    plt.tight_layout()
    OUTPUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_PNG, dpi=300, bbox_inches="tight")
    print(f"[OK] Saved: {OUTPUT_PNG}")

if __name__ == "__main__":
    main()