#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from aqf_eval.journal_metrics import (
    safe_json_load,
    complexity_breakdown_for_form,
    operator_burden_rows,
    canonical_structure_metrics_for_form,
    coverage_by_category,
    query_realization_results,
    build_candidate_pruning_audit,
    relative_ablation_summary,
    pareto_frontier,
)


def load_forms(run_dir: Path):
    forms = []
    for p in sorted((run_dir / "generated_forms").glob("*/forms.json")):
        form = safe_json_load(p, default={})
        if form:
            if not form.get("method"):
                form["method"] = p.parent.name
            forms.append(form)
    return forms


def find_artifact(run_dir: Path, name: str):
    candidates = [run_dir / name, run_dir / "artifacts" / name]
    for c in candidates:
        if c.exists():
            return c
    return None


def process_run_dir(run_dir: Path, eta: float, theta: float, out_dir: Path | None = None):
    out_dir = out_dir or run_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    forms = load_forms(run_dir)
    if not forms:
        print(f"[WARN] No generated_forms found in {run_dir}")
        return None

    complexity_rows = [complexity_breakdown_for_form(f, eta=eta) for f in forms]
    complexity = pd.DataFrame(complexity_rows)

    legacy_path = run_dir / "form_complexity.csv"
    if legacy_path.exists():
        legacy = pd.read_csv(legacy_path)
        if "complexity_score" in legacy.columns:
            complexity = complexity.merge(legacy[["method", "complexity_score"]], on="method", how="left")
            complexity["legacy_complexity_score"] = complexity["complexity_score"]
            complexity = complexity.drop(columns=["complexity_score"])

    op_rows = []
    for f in forms:
        op_rows.extend(operator_burden_rows(f))
    operator_burden = pd.DataFrame(op_rows)
    canonical_metrics = pd.DataFrame([canonical_structure_metrics_for_form(f) for f in forms])

    summary_path = run_dir / "benchmark_coverage_summary.csv"
    detail_path = run_dir / "benchmark_coverage_detail.csv"
    summary = pd.read_csv(summary_path) if summary_path.exists() else pd.DataFrame()
    detail = pd.read_csv(detail_path) if detail_path.exists() else pd.DataFrame()

    # Final method-level journal metrics.
    final_rows = []
    if not summary.empty:
        overall = summary[(summary["workload"] == "ALL") & (summary["difficulty"] == "ALL")].copy()
    else:
        overall = pd.DataFrame()
    for _, c in complexity.iterrows():
        method = c["method"]
        cov = overall[overall["method"] == method]
        row = c.to_dict()
        if len(cov):
            row.update({
                "query_count": int(cov.iloc[0].get("query_count")),
                "strict_coverage": float(cov.iloc[0].get("strict_coverage")),
                "partial_coverage": float(cov.iloc[0].get("partial_coverage")),
            })
        final_rows.append(row)
    final_metrics = pd.DataFrame(final_rows)

    final_metrics.to_csv(out_dir / "final_aqf_metrics.csv", index=False)
    complexity.to_csv(out_dir / "complexity_breakdown.csv", index=False)
    operator_burden.to_csv(out_dir / "operator_burden.csv", index=False)
    operator_burden.groupby("method", as_index=False).agg(
        field_count=("field_id", "count"),
        operator_count=("operator_count", "sum"),
        valid_operator_count=("valid_operator_count", "sum"),
        invalid_or_unwanted_operator_count=("invalid_or_unwanted_operator_count", "sum"),
        weighted_operator_burden=("weighted_operator_burden", "sum"),
    ).to_csv(out_dir / "operator_burden_summary.csv", index=False)
    canonical_metrics.to_csv(out_dir / "canonical_structure_metrics.csv", index=False)

    if not detail.empty:
        coverage_by_category(detail).to_csv(out_dir / "coverage_by_query_category.csv", index=False)
        query_realization_results(detail).to_csv(out_dir / "query_realization_results.csv", index=False)

    if not summary.empty:
        relative_ablation_summary(summary, complexity).to_csv(out_dir / "relative_ablation_summary.csv", index=False)

    forest_path = find_artifact(run_dir, "canonical_forest.json")
    scores_path = find_artifact(run_dir, "queriability_scores.json")
    if forest_path and scores_path:
        forest = safe_json_load(forest_path, default={})
        scores = safe_json_load(scores_path, default={})
        build_candidate_pruning_audit(forest, scores, theta=theta).to_csv(out_dir / "candidate_pruning_audit.csv", index=False)

    if "strict_coverage" in final_metrics.columns:
        pareto_frontier(final_metrics.dropna(subset=["strict_coverage", "final_complexity"])).to_csv(out_dir / "pareto_frontier.csv", index=False)

    make_plots(out_dir, final_metrics, detail)
    print(f"[OK] Journal metrics written to {out_dir}")
    return final_metrics


def make_plots(out_dir: Path, final_metrics: pd.DataFrame, detail: pd.DataFrame):
    plots = out_dir / "journal_plots"
    plots.mkdir(exist_ok=True)
    if not final_metrics.empty and {"final_complexity", "strict_coverage", "method"}.issubset(final_metrics.columns):
        plt.figure(figsize=(9, 6))
        for method, g in final_metrics.groupby("method"):
            plt.scatter(g["final_complexity"], g["strict_coverage"] * 100, label=method)
        plt.xlabel("Final AQF complexity C(F)=|E_F|+η·depth(F)")
        plt.ylabel("Strict coverage (%)")
        plt.title("Coverage vs final AQF complexity")
        plt.legend(fontsize=8)
        plt.tight_layout()
        plt.savefig(plots / "coverage_vs_final_complexity.png", dpi=200)
        plt.close()

    if not final_metrics.empty and {"method", "operator_count"}.issubset(final_metrics.columns):
        plt.figure(figsize=(10, 5))
        x = final_metrics.sort_values("operator_count", ascending=False)
        plt.bar(x["method"], x["operator_count"])
        plt.xticks(rotation=45, ha="right")
        plt.ylabel("Operator count")
        plt.title("Operator burden by method")
        plt.tight_layout()
        plt.savefig(plots / "operator_burden_by_method.png", dpi=200)
        plt.close()

    cat_path = out_dir / "coverage_by_query_category.csv"
    if cat_path.exists():
        cat = pd.read_csv(cat_path)
        if not cat.empty:
            pivot = cat.pivot_table(index="category", columns="method", values="strict_coverage", aggfunc="first") * 100
            pivot.plot(kind="bar", figsize=(11, 6))
            plt.ylabel("Strict coverage (%)")
            plt.title("Coverage by query category")
            plt.tight_layout()
            plt.savefig(plots / "coverage_by_query_category.png", dpi=200)
            plt.close()

    cand_path = out_dir / "candidate_pruning_audit.csv"
    if cand_path.exists():
        cand = pd.read_csv(cand_path)
        if not cand.empty and "selected_by_theta" in cand.columns:
            counts = [len(cand), int(cand["selected_by_theta"].sum())]
            plt.figure(figsize=(6, 4))
            plt.bar(["before θ", "after θ"], counts)
            plt.ylabel("Candidate fields")
            plt.title("Candidate pruning funnel")
            plt.tight_layout()
            plt.savefig(plots / "candidate_pruning_funnel.png", dpi=200)
            plt.close()


def process_sweep_root(root: Path, eta: float, theta: float):
    combo_dirs = sorted((root / "combos").glob("combo_*"))
    if not combo_dirs:
        return process_run_dir(root, eta=eta, theta=theta)
    all_rows = []
    for combo in combo_dirs:
        metrics = process_run_dir(combo, eta=eta, theta=theta, out_dir=combo / "journal_metrics")
        if metrics is not None:
            params = safe_json_load(combo / "params.json", default={})
            metrics = metrics.copy()
            metrics["combo_id"] = combo.name
            for k, v in params.items():
                metrics[k] = v
            all_rows.append(metrics)
    if all_rows:
        combined = pd.concat(all_rows, ignore_index=True)
        combined.to_csv(root / "journal_all_results.csv", index=False)
        pareto_frontier(combined.dropna(subset=["strict_coverage", "final_complexity"])).to_csv(root / "journal_pareto_frontier.csv", index=False)
        make_plots(root, combined, pd.DataFrame())
        print(f"[OK] Combined journal sweep outputs written to {root}")
    return None


def main():
    p = argparse.ArgumentParser(description="Generate journal-grade AQF evaluation metrics from existing AQF result folders.")
    p.add_argument("--results-dir", required=True, help="A single run directory or sweep root containing combos/combo_* folders.")
    p.add_argument("--eta", type=float, default=1.0, help="Depth penalty for C(F)=|E_F|+eta*depth(F).")
    p.add_argument("--theta", type=float, default=0.10, help="Candidate pruning threshold used for audit reporting.")
    args = p.parse_args()
    process_sweep_root(Path(args.results_dir), eta=args.eta, theta=args.theta)


if __name__ == "__main__":
    main()
