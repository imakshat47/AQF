#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


METHOD_LABELS = {
    "aqf_full": "AQF full pipeline",
    "aqf_topk_no_threshold": "AQF without threshold",
    "frequency_only": "Frequency-only ranking",
    "flattened_topk": "Flattened top-k",
    "no_operator_awareness": "No operator awareness",
    "no_pruning": "No pruning upper bound",
}


RQ_ROWS = [
    {
        "research_question": "RQ1. Does AQF preserve query expressivity?",
        "claim": "Automatically generated forms should realize benchmark queries without manual query-log training.",
        "metric": "Strict coverage and partial coverage",
        "primary_artifact": "benchmark_coverage_summary.csv; final_aqf_metrics.csv",
        "reviewer_reading": "Higher coverage supports expressivity.",
    },
    {
        "research_question": "RQ2. Does AQF reduce interface complexity?",
        "claim": "AQF should expose fewer form elements than an unpruned form while retaining high coverage.",
        "metric": "Field count and final complexity C(F)",
        "primary_artifact": "final_aqf_metrics.csv; complexity_breakdown.csv",
        "reviewer_reading": "Lower field count and complexity support bounded form generation.",
    },
    {
        "research_question": "RQ3. Does operator awareness help?",
        "claim": "Operator-aware classification should reduce invalid or unnecessary controls without reducing coverage.",
        "metric": "Operator count, invalid operator count, weighted operator burden, coverage delta",
        "primary_artifact": "operator_burden_summary.csv; relative_ablation_summary.csv",
        "reviewer_reading": "Same coverage with lower operator burden supports operator awareness.",
    },
    {
        "research_question": "RQ4. Does pruning help?",
        "claim": "Candidate pruning should trade a small amount of expressivity for a simpler form.",
        "metric": "Coverage delta versus no-pruning, field reduction, complexity reduction",
        "primary_artifact": "relative_ablation_summary.csv; final_aqf_metrics.csv",
        "reviewer_reading": "A small coverage loss with large complexity reduction supports pruning.",
    },
    {
        "research_question": "RQ5. Does AQF generalize across ORBDA workloads?",
        "claim": "The same AQF pipeline should support multiple composition families and workload categories.",
        "metric": "Coverage by workload or query category",
        "primary_artifact": "coverage_by_query_category.csv; benchmark_coverage_summary.csv",
        "reviewer_reading": "Stable category coverage supports generalization.",
    },
]


FORMULA_MOTIVATION = """# Formula Motivation For Methodology Validation

AQF uses local utility `LU(v) = cov(v) * div(v)` because a useful query-form field must satisfy two conditions at the same time: it must be present often enough to be practically queryable, and it must vary enough to support meaningful filtering or projection. Multiplication makes this conjunction explicit. A field with high coverage but almost no diversity is unlikely to separate records, while a highly diverse field that is rarely present is unreliable as a general form element. A weighted sum would allow one factor to compensate for the near absence of the other; the product penalizes such one-sided fields and is therefore better aligned with query-form usefulness.

The neighborhood term in `Q(v) = LU(v) + mu * sum SC(u,v) * LU(u)` reflects the fact that form fields are not useful in isolation inside hierarchical EHR data. A field gains practical value when it appears in a structurally coherent neighborhood with other useful fields, because users commonly combine nearby clinical concepts in predicates, projections, and sorting. The structural-connectivity term `SC(u,v)` therefore rewards fields embedded in meaningful containment or co-occurrence contexts. The parameter `mu` keeps this contextual reinforcement bounded so that local evidence remains primary while related clinical context can improve ranking.

AQF uses a bounded complexity objective because the goal is not maximum schema exposure. Exposing every repository field can increase expressivity but also increases cognitive and interaction cost. The complexity model `C(F) = |E_F| + eta * depth(F)` captures both the number of exposed form elements and the structural depth users must navigate. This makes the evaluation directly test the central AQF tradeoff: preserving query expressivity while keeping generated forms manageable.
"""


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    return pd.read_csv(path)


def pct(value: Any) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except Exception:
        return ""


def num(value: Any) -> str:
    try:
        f = float(value)
        if f.is_integer():
            return str(int(f))
        return f"{f:.2f}"
    except Exception:
        return ""


def method(final: pd.DataFrame, name: str) -> dict[str, Any]:
    rows = final[final["method"] == name]
    return rows.iloc[0].to_dict() if len(rows) else {}


def random_summary(final: pd.DataFrame) -> dict[str, Any]:
    random_rows = final[final["method"].astype(str).str.startswith("random_topk_")]
    if random_rows.empty:
        return {}
    return {
        "method": "random_topk_mean",
        "query_count": int(random_rows["query_count"].max()),
        "strict_coverage": float(random_rows["strict_coverage"].mean()),
        "partial_coverage": float(random_rows["partial_coverage"].mean()),
        "field_count": float(random_rows["field_count"].mean()),
        "operator_count": float(random_rows["operator_count"].mean()),
        "final_complexity": float(random_rows["final_complexity"].mean()),
        "strict_coverage_min": float(random_rows["strict_coverage"].min()),
        "strict_coverage_max": float(random_rows["strict_coverage"].max()),
        "trial_count": int(len(random_rows)),
    }


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.iterrows():
        out.append("| " + " | ".join(str(row.get(c, "")) for c in cols) + " |")
    return "\n".join(out) + "\n"


def save_table(df: pd.DataFrame, out_dir: Path, stem: str) -> None:
    df.to_csv(out_dir / f"{stem}.csv", index=False)
    (out_dir / f"{stem}.md").write_text(markdown_table(df), encoding="utf-8")


def build_rq_mapping() -> pd.DataFrame:
    return pd.DataFrame(RQ_ROWS)


def build_claim_evidence(final: pd.DataFrame, category: pd.DataFrame) -> pd.DataFrame:
    aqf = method(final, "aqf_full")
    no_pruning = method(final, "no_pruning")
    no_operator = method(final, "no_operator_awareness")
    frequency = method(final, "frequency_only")
    flattened = method(final, "flattened_topk")
    random = random_summary(final)

    rows = []
    rows.append({
        "claim": "Expressivity",
        "evidence": "AQF strict coverage",
        "aqf_result": pct(aqf.get("strict_coverage")),
        "comparison": f"{int(aqf.get('query_count', 0))} benchmark queries",
        "interpretation": "Shows how many benchmark requests the generated form realizes exactly.",
    })
    rows.append({
        "claim": "Complexity reduction",
        "evidence": "AQF versus no-pruning",
        "aqf_result": f"{num(aqf.get('field_count'))} fields, C={num(aqf.get('final_complexity'))}",
        "comparison": f"no-pruning: {num(no_pruning.get('field_count'))} fields, C={num(no_pruning.get('final_complexity'))}",
        "interpretation": "Shows the expressivity-complexity tradeoff imposed by candidate selection.",
    })
    rows.append({
        "claim": "Operator awareness",
        "evidence": "Operator burden ablation",
        "aqf_result": f"{num(aqf.get('operator_count'))} operators, {num(aqf.get('invalid_or_unwanted_operator_count'))} invalid",
        "comparison": f"no-operator-awareness: {num(no_operator.get('operator_count'))} operators, {num(no_operator.get('invalid_or_unwanted_operator_count'))} invalid",
        "interpretation": "Shows that operator awareness reduces interaction burden without changing coverage.",
    })
    rows.append({
        "claim": "Ranking quality",
        "evidence": "AQF versus frequency-only",
        "aqf_result": pct(aqf.get("strict_coverage")),
        "comparison": f"frequency-only: {pct(frequency.get('strict_coverage'))}",
        "interpretation": "Shows whether structural queriability improves over simple prevalence ranking.",
    })
    rows.append({
        "claim": "Canonical structure",
        "evidence": "AQF versus flattened form",
        "aqf_result": f"{num(aqf.get('group_count'))} groups, {num(aqf.get('subgroup_count'))} subgroups",
        "comparison": f"flattened: {num(flattened.get('group_count'))} group, {num(flattened.get('subgroup_count'))} subgroup",
        "interpretation": "Shows that AQF preserves form context rather than only selecting fields.",
    })
    if random:
        rows.append({
            "claim": "Workload-independent selection",
            "evidence": "AQF versus random top-k trials",
            "aqf_result": pct(aqf.get("strict_coverage")),
            "comparison": f"random mean: {pct(random.get('strict_coverage'))}; max: {pct(random.get('strict_coverage_max'))}",
            "interpretation": "Shows generated ranking is stronger than arbitrary compact field selection.",
        })

    if not category.empty and "method" in category.columns:
        aqf_cat = category[category["method"] == "aqf_full"].copy()
        if not aqf_cat.empty:
            weak = aqf_cat.sort_values("strict_coverage").iloc[0]
            strong_count = int((aqf_cat["strict_coverage"] >= 0.90).sum())
            rows.append({
                "claim": "Generalization across ORBDA categories",
                "evidence": "Category coverage",
                "aqf_result": f"{strong_count}/{len(aqf_cat)} categories at or above 90%",
                "comparison": f"weakest: {weak['category']} at {pct(weak['strict_coverage'])}",
                "interpretation": "Shows where AQF generalizes and where limitations remain visible.",
            })
    return pd.DataFrame(rows)


def build_ablation_table(final: pd.DataFrame) -> pd.DataFrame:
    aqf = method(final, "aqf_full")
    rows = []
    for baseline, label, test in [
        ("no_pruning", "Candidate pruning", "Does pruning reduce fields and complexity?"),
        ("no_operator_awareness", "Operator-aware classification", "Does operator awareness reduce unnecessary controls?"),
        ("frequency_only", "Structural queriability ranking", "Does AQF improve over prevalence-only ranking?"),
        ("flattened_topk", "Canonical grouping", "Does AQF preserve structured form context?"),
    ]:
        b = method(final, baseline)
        if not b:
            continue
        rows.append({
            "component_tested": label,
            "comparison": f"aqf_full vs {baseline}",
            "reviewer_question": test,
            "strict_coverage_delta": pct(float(aqf.get("strict_coverage", 0)) - float(b.get("strict_coverage", 0))),
            "field_delta": int(float(aqf.get("field_count", 0)) - float(b.get("field_count", 0))),
            "complexity_delta": num(float(aqf.get("final_complexity", 0)) - float(b.get("final_complexity", 0))),
            "operator_burden_delta": num(float(aqf.get("weighted_operator_burden", 0)) - float(b.get("weighted_operator_burden", 0))),
            "main_interpretation": interpret_ablation(baseline, aqf, b),
        })
    return pd.DataFrame(rows)


def interpret_ablation(baseline: str, aqf: dict[str, Any], b: dict[str, Any]) -> str:
    if baseline == "no_pruning":
        return "No-pruning is the expressivity upper bound; AQF is judged by how much complexity it saves for its coverage loss."
    if baseline == "no_operator_awareness":
        return "Coverage should remain similar while operator count and invalid operators fall sharply."
    if baseline == "frequency_only":
        return "Tests whether structural and diversity-aware scoring adds value over field prevalence."
    if baseline == "flattened_topk":
        return "Tests whether context preservation is maintained beyond raw coverage."
    return ""


def build_formula_table() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "formula": "LU(v) = cov(v) * div(v)",
            "design_intuition": "A field is useful only when it is both present and discriminative.",
            "why_not_simpler": "A weighted sum can let high coverage compensate for near-zero diversity, or vice versa.",
            "evaluation_link": "Supports field ranking and compact form selection.",
        },
        {
            "formula": "SC(u,v) = lambda*CC(u,v) + (1-lambda)*CO(u,v)",
            "design_intuition": "Query usefulness depends on both containment context and empirical co-occurrence.",
            "why_not_simpler": "Structure-only ignores data support; co-occurrence-only can miss clinically meaningful hierarchy.",
            "evaluation_link": "Supports category-level generalization and canonical context preservation.",
        },
        {
            "formula": "Q(v) = LU(v) + mu*sum SC(u,v)*LU(u)",
            "design_intuition": "Fields embedded near other useful fields are stronger form candidates.",
            "why_not_simpler": "Local scoring alone cannot capture clinically coherent query neighborhoods.",
            "evaluation_link": "Supports AQF versus frequency-only and random top-k comparisons.",
        },
        {
            "formula": "C(F) = |E_F| + eta*depth(F)",
            "design_intuition": "Usability cost grows with both number of fields and navigational depth.",
            "why_not_simpler": "Field count alone misses the cost of deeply nested form structures.",
            "evaluation_link": "Supports complexity reduction and pruning ablations.",
        },
    ])


def build_evaluation_narrative(final: pd.DataFrame, category: pd.DataFrame) -> str:
    aqf = method(final, "aqf_full")
    no_pruning = method(final, "no_pruning")
    no_operator = method(final, "no_operator_awareness")
    random = random_summary(final)
    category_count = ""
    if not category.empty and "method" in category.columns:
        aqf_cat = category[category["method"] == "aqf_full"]
        if not aqf_cat.empty:
            category_count = f"{int((aqf_cat['strict_coverage'] >= 0.90).sum())} of {len(aqf_cat)} query categories"
    return f"""# Evaluation Framing For Manuscript

The evaluation is organized around explicit research questions rather than a list of raw experiments. RQ1 evaluates expressivity using strict and partial benchmark coverage. RQ2 evaluates complexity reduction using field count and final form complexity. RQ3 evaluates operator-aware form design through an ablation that disables operator compatibility. RQ4 evaluates pruning through the no-pruning upper bound. RQ5 evaluates generalization across ORBDA workload categories.

At the current operating point, AQF realizes {pct(aqf.get('strict_coverage'))} of {int(aqf.get('query_count', 0))} benchmark queries with {num(aqf.get('field_count'))} exposed fields and final complexity {num(aqf.get('final_complexity'))}. The no-pruning upper bound realizes {pct(no_pruning.get('strict_coverage'))}, but exposes {num(no_pruning.get('field_count'))} fields with final complexity {num(no_pruning.get('final_complexity'))}. This directly frames AQF as an expressivity-complexity tradeoff rather than a maximum-coverage system.

Operator awareness should be interpreted as a usability mechanism, not an expressivity mechanism. In the current results, disabling operator awareness preserves strict coverage at {pct(no_operator.get('strict_coverage'))} but increases operator count from {num(aqf.get('operator_count'))} to {num(no_operator.get('operator_count'))} and invalid or unwanted operators from {num(aqf.get('invalid_or_unwanted_operator_count'))} to {num(no_operator.get('invalid_or_unwanted_operator_count'))}. This supports the claim that operator-aware classification reduces interaction burden without sacrificing query realization.

Random compact selections provide an important reviewer-facing sanity check. Across {random.get('trial_count', 0)} random top-k trials, mean strict coverage is {pct(random.get('strict_coverage'))}, compared with AQF at {pct(aqf.get('strict_coverage'))}. This helps show that AQF's compact coverage is not simply due to selecting any similarly sized set of fields.

Category-level coverage should be used to show both generalization and limitations. AQF reaches at least 90% strict coverage in {category_count or 'the high-performing categories'}, while weaker treatment/procedure coverage should be discussed as the main remaining limitation of the current benchmark and candidate-selection setting.
"""


def make_claim_plot(final: pd.DataFrame, out_dir: Path) -> None:
    wanted = [
        "aqf_full",
        "frequency_only",
        "no_operator_awareness",
        "no_pruning",
    ]
    rows = final[final["method"].isin(wanted)].copy()
    random = random_summary(final)
    if random:
        rows = pd.concat([rows, pd.DataFrame([random])], ignore_index=True)
    rows["label"] = rows["method"].map(METHOD_LABELS).fillna("Random top-k mean")
    rows = rows.sort_values("strict_coverage", ascending=False)

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.8))
    colors = ["#2f6f9f" if m == "aqf_full" else "#8a8f98" for m in rows["method"]]

    axes[0].barh(rows["label"], rows["strict_coverage"] * 100, color=colors)
    axes[0].set_xlabel("Strict coverage (%)")
    axes[0].set_title("Expressivity")
    axes[0].invert_yaxis()

    axes[1].barh(rows["label"], rows["field_count"], color=colors)
    axes[1].set_xlabel("Exposed fields")
    axes[1].set_title("Complexity")
    axes[1].invert_yaxis()

    axes[2].barh(rows["label"], rows["weighted_operator_burden"], color=colors)
    axes[2].set_xlabel("Weighted operator burden")
    axes[2].set_title("Operator burden")
    axes[2].invert_yaxis()

    for ax in axes:
        ax.grid(axis="x", alpha=0.25)
    fig.suptitle("Reviewer-facing AQF evidence: expressivity, complexity, and operator awareness")
    fig.tight_layout()
    fig.savefig(out_dir / "reviewer_evidence_summary.png", dpi=220)
    fig.savefig(out_dir / "reviewer_evidence_summary.pdf")
    plt.close(fig)


def export(results_dir: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    final = read_csv(results_dir / "final_aqf_metrics.csv")
    category_path = results_dir / "coverage_by_query_category.csv"
    category = pd.read_csv(category_path) if category_path.exists() else pd.DataFrame()

    save_table(build_rq_mapping(), out_dir, "table_rq_metric_mapping")
    save_table(build_claim_evidence(final, category), out_dir, "table_claim_evidence")
    save_table(build_ablation_table(final), out_dir, "table_ablation_framing")
    save_table(build_formula_table(), out_dir, "table_formula_motivation")

    (out_dir / "formula_motivation.md").write_text(FORMULA_MOTIVATION, encoding="utf-8")
    (out_dir / "evaluation_framing.md").write_text(build_evaluation_narrative(final, category), encoding="utf-8")
    make_claim_plot(final, out_dir)

    manifest = {
        "source_results_dir": str(results_dir),
        "outputs": [
            "table_rq_metric_mapping.csv",
            "table_claim_evidence.csv",
            "table_ablation_framing.csv",
            "table_formula_motivation.csv",
            "formula_motivation.md",
            "evaluation_framing.md",
            "reviewer_evidence_summary.png",
            "reviewer_evidence_summary.pdf",
        ],
    }
    (out_dir / "reviewer_evidence_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[OK] reviewer evidence package written to {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export reviewer-facing AQF evaluation evidence tables and plots.")
    parser.add_argument("--results-dir", required=True, help="Result directory containing final_aqf_metrics.csv.")
    parser.add_argument("--out-dir", default=None, help="Output directory. Defaults to <results-dir>/reviewer_evidence.")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    out_dir = Path(args.out_dir) if args.out_dir else results_dir / "reviewer_evidence"
    export(results_dir, out_dir)


if __name__ == "__main__":
    main()
