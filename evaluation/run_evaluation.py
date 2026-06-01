#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Allow running from repository root or from evaluation folder.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aqf_eval.openehr_utils import scan_json_folder, stable_hash
from aqf_eval.canonical import build_canonical_forest
from aqf_eval.queriability import compute_scores
from aqf_eval.form_generation import generate_form
from aqf_eval.query_eval import evaluate_form, useful_field_labels
from aqf_eval.metrics import summarize_coverage, precision_at_k, recall_at_k, form_complexity, canonical_metrics
from aqf_eval.reporting import write_json, write_csv, try_write_plots


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_benchmarks(paths: list[Path], include_cross: bool = False) -> list[dict]:
    queries = []
    for p in paths:
        if not include_cross and "cross" in p.name.lower():
            continue
        if p.exists():
            queries.extend(load_json(p))
    return queries


def dataset_summary(record_units, forest):
    trees = forest.get("trees", {})
    fields = [f for t in trees.values() for f in t.get("fields", [])]
    return [{
        "json_record_units": len(record_units),
        "composition_families": len(trees),
        "canonical_trees": len(trees),
        "form_groups": len({(f.get("record_family"), f.get("form_group")) for f in fields}),
        "nested_subgroups": len({(f.get("record_family"), f.get("form_group"), f.get("nested_subgroup")) for f in fields}),
        "leaf_elements": len(fields),
        "null_flavour_fields": sum(1 for f in fields if f.get("has_null_flavour")),
        "coded_fields": sum(1 for f in fields if f.get("kind") == "coded"),
        "temporal_fields": sum(1 for f in fields if f.get("kind") == "temporal"),
        "numeric_fields": sum(1 for f in fields if f.get("kind") == "numeric"),
    }]


def run(args):
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    t = {}
    t0 = time.perf_counter()
    record_units = scan_json_folder(Path(args.data_dir))
    t["scan_seconds"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    forest = build_canonical_forest(record_units)
    t["canonical_build_seconds"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    scores = compute_scores(forest, alpha=args.alpha, beta=args.beta, lamb=args.lamb)
    t["queriability_seconds"] = time.perf_counter() - t0

    benchmark_paths = [Path(p) for p in args.benchmarks]
    queries = load_benchmarks(benchmark_paths, include_cross=args.include_cross)
    useful = useful_field_labels(queries)

    methods = [
        ("aqf_full", True, args.theta),
        ("flattened_topk", True, args.theta),
        ("frequency_only", True, args.theta),
        ("no_pruning", True, 0.0),
        ("no_operator_awareness", False, args.theta),
    ]
    forms = []
    t0 = time.perf_counter()
    for method, op_aware, theta in methods:
        actual_method = "aqf_full" if method == "no_operator_awareness" else method
        form = generate_form(forest, scores, method=actual_method, kappa=args.kappa, theta=theta, operator_aware=op_aware, seed=args.seed)
        form["method"] = method
        forms.append(form)
    for i in range(args.random_trials):
        forms.append(generate_form(forest, scores, method=f"random_topk_{i+1}", kappa=args.kappa, theta=args.theta, operator_aware=True, seed=args.seed + i))
    t["form_generation_seconds"] = time.perf_counter() - t0

    coverage_detail = []
    ranking_rows = []
    complexity_rows = []
    canonical_rows = []
    t0 = time.perf_counter()
    for form in forms:
        coverage_detail.extend(evaluate_form(form, queries))
        ranking_rows.append({
            "method": form.get("method"),
            "precision_at_10": precision_at_k(form, useful, 10),
            "precision_at_20": precision_at_k(form, useful, 20),
            "recall_at_20": recall_at_k(form, useful, 20),
        })
        complexity_rows.append(form_complexity(form))
        canonical_rows.append(canonical_metrics(form))
        write_json(form, out_dir / "generated_forms" / form.get("method", "unknown") / "forms.json")
    t["query_evaluation_seconds"] = time.perf_counter() - t0

    coverage_summary = summarize_coverage(coverage_detail)
    runtime_rows = [{"metric": k, "seconds": v} for k, v in t.items()]
    runtime_rows.append({"metric": "total_seconds", "seconds": sum(t.values())})

    write_json({"record_units": record_units}, out_dir / "artifacts" / "record_units.json")
    write_json(forest, out_dir / "artifacts" / "canonical_forest.json")
    write_json(scores, out_dir / "artifacts" / "queriability_scores.json")
    write_csv(dataset_summary(record_units, forest), out_dir / "dataset_summary.csv")
    write_csv(coverage_detail, out_dir / "benchmark_coverage_detail.csv")
    write_csv(coverage_summary, out_dir / "benchmark_coverage_summary.csv")
    write_csv(ranking_rows, out_dir / "queriability_ranking.csv")
    write_csv(complexity_rows, out_dir / "form_complexity.csv")
    write_csv(canonical_rows, out_dir / "canonical_metrics.csv")
    write_csv(runtime_rows, out_dir / "runtime.csv")
    try_write_plots(coverage_summary, out_dir / "figures")

    print(f"AQF evaluation complete. Results written to: {out_dir}")
    print(f"Record units: {len(record_units)} | Canonical trees: {forest.get('tree_count')} | Queries: {len(queries)}")


def main():
    parser = argparse.ArgumentParser(description="Run AQF evaluation engine over a folder of openEHR JSON compositions.")
    parser.add_argument("--data-dir", required=True, help="Folder containing JSON compositions/EHR exports.")
    parser.add_argument("--out-dir", default="results/aqf_eval", help="Output directory for CSV/JSON/figures.")
    parser.add_argument("--benchmarks", nargs="+", default=[
        str(ROOT / "evaluation" / "benchmarks" / "benchmark_queries_hcpa.json"),
        str(ROOT / "evaluation" / "benchmarks" / "benchmark_queries_demographic.json"),
        str(ROOT / "evaluation" / "benchmarks" / "benchmark_queries_cross_composition.json"),
    ])
    parser.add_argument("--include-cross", action="store_true", help="Include cross-composition challenge queries in main evaluation.")
    parser.add_argument("--kappa", type=int, default=60, help="Complexity budget: maximum visible fields in generated form.")
    parser.add_argument("--theta", type=float, default=0.10, help="Pruning threshold as fraction of max score.")
    parser.add_argument("--alpha", type=float, default=0.70, help="Containment weight.")
    parser.add_argument("--beta", type=float, default=0.30, help="Co-occurrence weight.")
    parser.add_argument("--lamb", type=float, default=0.25, help="Propagation/reinforcement weight.")
    parser.add_argument("--random-trials", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    run(parser.parse_args())

if __name__ == "__main__":
    main()
