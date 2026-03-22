# generate_results.py

from __future__ import annotations

import argparse
from pathlib import Path
import json

from aqf_results import generate_results_package, save_csv, run_execution_benchmark


def main():
    parser = argparse.ArgumentParser(description="Generate AQF results package.")
    parser.add_argument("--cache_dir", type=str, default=".cache", help="Directory containing schema_union.json and fields.json")
    parser.add_argument("--out_dir", type=str, default="results_package", help="Directory to write results")
    parser.add_argument("--thresholds", type=int, nargs="*", default=[2, 4, 6, 8, 10, 12], help="Visible field budget sweep")
    parser.add_argument("--max_groups", type=int, default=None, help="Optional max number of visible groups")
    parser.add_argument("--dataset_folder", type=str, default=None, help="Dataset folder path (optional, for execution benchmarks)")
    parser.add_argument("--query_cases", type=str, default=None, help="JSON file containing query benchmark cases (optional)")
    parser.add_argument("--composition_archetype", type=str, default=None, help="Composition archetype for execution benchmark")
    args = parser.parse_args()

    results = generate_results_package(
        cache_dir=args.cache_dir,
        out_dir=args.out_dir,
        thresholds=args.thresholds,
        max_groups=args.max_groups
    )

    print(f"[OK] Core results written under: {args.out_dir}")

    # Optional execution benchmark
    if args.dataset_folder and args.query_cases and args.composition_archetype:
        # Delayed imports so the script still works if you only want structural metrics
        import query_executor
        import query_compiler

        with open(args.query_cases, "r", encoding="utf-8") as f:
            query_cases = json.load(f)

        exec_df = run_execution_benchmark(
            query_executor_module=query_executor,
            query_compiler_module=query_compiler,
            dataset_folder=args.dataset_folder,
            composition_archetype=args.composition_archetype,
            query_cases=query_cases
        )

        save_csv(exec_df, Path(args.out_dir) / "derived_metrics" / "execution_metrics.csv")
        print(f"[OK] Execution benchmark written to: {Path(args.out_dir) / 'derived_metrics' / 'execution_metrics.csv'}")


if __name__ == "__main__":
    main()