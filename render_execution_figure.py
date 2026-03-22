# render_execution_figure.py

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import json

sns.set_theme(style="whitegrid", context="talk")

INPUT_CSV = Path("results_package/derived_metrics/execution_metrics.csv")
OUTPUT_PNG = Path("results_package/figures/fig_execution_summary.png")
OUTPUT_MAPPING_CSV = Path("results_package/derived_metrics/query_index_mapping.csv")

# Optional: if available, use this to create a richer appendix mapping
QUERY_CASES_JSON = Path("query_cases_30.json")


def format_us(v: float) -> str:
    return f"{v:.1f} µs"


def format_ms(v: float) -> str:
    return f"{v:.2f} ms"


def format_sec_per_doc(v: float) -> str:
    if v < 1e-3:
        return f"{v * 1e6:.0f} µs/doc"
    elif v < 1:
        return f"{v * 1e3:.2f} ms/doc"
    return f"{v:.3f} s/doc"


def summarize_form_state(form_state: dict) -> str:
    """
    Build a short natural-language-like description from query_cases.json.
    This is intentionally compact for appendix mapping, not full prose.
    """
    criteria = form_state.get("criteria", [])
    outputs = form_state.get("output_fields", [])
    sort = form_state.get("sort")

    parts = []

    if criteria:
        crit_parts = []
        for c in criteria:
            field = c.get("element_name", "field")
            op = c.get("operator", "")
            value = c.get("value", "")
            if op in ("is_known", "is_unknown"):
                crit_parts.append(f"{field} {op}")
            else:
                crit_parts.append(f"{field} {op} {value}")
        parts.append("WHERE " + " AND ".join(crit_parts))

    if outputs:
        out_names = [o.get("element_name", "field") for o in outputs]
        parts.append("SHOW " + ", ".join(out_names))

    if sort:
        parts.append(f"SORT BY {sort.get('element_name', 'field')} {sort.get('direction', 'asc')}")

    return " | ".join(parts)


def build_query_mapping(exec_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build appendix-style query index mapping.
    If query_cases_30.json exists, enrich with NLP-style description.
    """
    mapping_df = exec_df.copy()
    mapping_df["query_index"] = [f"Q{i+1}" for i in range(len(mapping_df))]

    mapping_df["query_label_nlp"] = mapping_df["query_name"].astype(str).str.replace("_", " ", regex=False)

    if QUERY_CASES_JSON.exists():
        with QUERY_CASES_JSON.open("r", encoding="utf-8") as f:
            query_cases = json.load(f)

        case_map = {q["name"]: q for q in query_cases}

        nlp_texts = []
        criteria_counts = []
        output_counts = []

        for qn in mapping_df["query_name"]:
            if qn in case_map:
                form_state = case_map[qn]["form_state"]
                nlp_texts.append(summarize_form_state(form_state))
                criteria_counts.append(len(form_state.get("criteria", [])))
                output_counts.append(len(form_state.get("output_fields", [])))
            else:
                nlp_texts.append(qn.replace("_", " "))
                criteria_counts.append(None)
                output_counts.append(None)

        mapping_df["query_label_nlp"] = nlp_texts
        mapping_df["criteria_count"] = criteria_counts
        mapping_df["output_count"] = output_counts

    # Keep only appendix-relevant columns
    cols = ["query_index", "query_name", "query_label_nlp"]
    if "criteria_count" in mapping_df.columns:
        cols += ["criteria_count", "output_count"]

    return mapping_df[cols]


def main():
    df = pd.read_csv(INPUT_CSV)

    if df.empty:
        raise RuntimeError(f"No rows found in {INPUT_CSV}")

    # Sort by execution time descending for better visual comparison
    df = df.sort_values("execution_sec", ascending=False).reset_index(drop=True)

    # Add query index labels Q1..Qn
    df["query_index"] = [f"Q{i+1}" for i in range(len(df))]

    # Save appendix mapping
    mapping_df = build_query_mapping(df)
    OUTPUT_MAPPING_CSV.parent.mkdir(parents=True, exist_ok=True)
    mapping_df.to_csv(OUTPUT_MAPPING_CSV, index=False)

    # Convert units for readability
    df["compile_us"] = df["compile_sec"] * 1e6
    df["execution_ms"] = df["execution_sec"] * 1e3

    n = len(df)
    fig_height = max(8, 0.45 * n + 3)

    fig, axes = plt.subplots(2, 2, figsize=(16, fig_height), sharey=True)

    # ------------------------------------------
    # Panel 1: Compile time (µs)
    # ------------------------------------------
    sns.barplot(
        data=df,
        y="query_index",
        x="compile_us",
        color="#4C78A8",
        ax=axes[0, 0]
    )
    axes[0, 0].set_title("Query compilation latency")
    axes[0, 0].set_xlabel("Compile time (µs)")
    axes[0, 0].set_ylabel("Query index")

    for i, (_, row) in enumerate(df.iterrows()):
        axes[0, 0].text(
            row["compile_us"] + max(df["compile_us"].max() * 0.02, 0.05),
            i,
            format_us(row["compile_us"]),
            va="center",
            ha="left",
            fontsize=10
        )

    # ------------------------------------------
    # Panel 2: Execution time (ms)
    # ------------------------------------------
    sns.barplot(
        data=df,
        y="query_index",
        x="execution_ms",
        color="#F58518",
        ax=axes[0, 1]
    )
    axes[0, 1].set_title("Query execution latency")
    axes[0, 1].set_xlabel("Execution time (ms)")
    axes[0, 1].set_ylabel("")
    axes[0, 1].tick_params(axis="y", labelleft=False)

    for i, (_, row) in enumerate(df.iterrows()):
        axes[0, 1].text(
            row["execution_ms"] + max(df["execution_ms"].max() * 0.01, 0.05),
            i,
            format_ms(row["execution_ms"]),
            va="center",
            ha="left",
            fontsize=10
        )

    # ------------------------------------------
    # Panel 3: Scanned vs matched
    # ------------------------------------------
    vol_df = df.melt(
        id_vars=["query_index"],
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
        y="query_index",
        x="count",
        hue="metric",
        palette=["#54A24B", "#E45756"],
        ax=axes[1, 0]
    )
    axes[1, 0].set_title("Scanned vs matched records")
    axes[1, 0].set_xlabel("Count")
    axes[1, 0].set_ylabel("Query index")
    axes[1, 0].legend(title="Metric", loc="lower right")

    # ------------------------------------------
    # Panel 4: Interaction count + sec/doc text
    # ------------------------------------------
    sns.barplot(
        data=df,
        y="query_index",
        x="interaction_count",
        color="#B279A2",
        ax=axes[1, 1]
    )
    axes[1, 1].set_title("Interaction count (annotated with sec/doc)")
    axes[1, 1].set_xlabel("Interactions")
    axes[1, 1].set_ylabel("")
    axes[1, 1].tick_params(axis="y", labelleft=False)

    for i, (_, row) in enumerate(df.iterrows()):
        axes[1, 1].text(
            row["interaction_count"] + max(df["interaction_count"].max() * 0.03, 0.15),
            i,
            f"{int(row['interaction_count'])} • {format_sec_per_doc(row['sec_per_doc'])}",
            va="center",
            ha="left",
            fontsize=10
        )

    plt.tight_layout()
    OUTPUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_PNG, dpi=300, bbox_inches="tight")
    print(f"[OK] Saved figure: {OUTPUT_PNG}")
    print(f"[OK] Saved mapping: {OUTPUT_MAPPING_CSV}")


if __name__ == "__main__":
    main()