#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def run_command(cmd: list[str]) -> None:
    print("\n[RUN]", " ".join(cmd))
    subprocess.check_call(cmd, cwd=str(ROOT))


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Expected output not found: {path}")
    return pd.read_csv(path)


def method_row(final_metrics: pd.DataFrame, method: str) -> dict[str, Any]:
    rows = final_metrics[final_metrics["method"] == method]
    if rows.empty:
        return {}
    return rows.iloc[0].to_dict()


def summarize(out_dir: Path, target_coverage: float) -> dict[str, Any]:
    final_metrics = read_csv(out_dir / "final_aqf_metrics.csv")
    dataset_summary = read_csv(out_dir / "dataset_summary.csv")
    category = read_csv(out_dir / "coverage_by_query_category.csv")

    aqf = method_row(final_metrics, "aqf_full")
    no_pruning = method_row(final_metrics, "no_pruning")
    frequency = method_row(final_metrics, "frequency_only")
    flattened = method_row(final_metrics, "flattened_topk")
    no_operator = method_row(final_metrics, "no_operator_awareness")

    strict = float(aqf.get("strict_coverage", 0.0) or 0.0)
    partial = float(aqf.get("partial_coverage", 0.0) or 0.0)
    passed = strict >= target_coverage

    random_rows = final_metrics[final_metrics["method"].astype(str).str.startswith("random_topk_")]
    random_summary = {}
    if not random_rows.empty:
        random_summary = {
            "mean_strict_coverage": float(random_rows["strict_coverage"].mean()),
            "max_strict_coverage": float(random_rows["strict_coverage"].max()),
            "min_strict_coverage": float(random_rows["strict_coverage"].min()),
            "trial_count": int(len(random_rows)),
        }

    values = {
        "status": "PASS" if passed else "BELOW_TARGET",
        "target_strict_coverage": target_coverage,
        "aqf_full": aqf,
        "no_pruning": no_pruning,
        "frequency_only": frequency,
        "flattened_topk": flattened,
        "no_operator_awareness": no_operator,
        "random_topk": random_summary,
        "dataset_summary": dataset_summary.to_dict(orient="records"),
        "coverage_by_query_category": category.to_dict(orient="records"),
    }
    with (out_dir / "manuscript_values.json").open("w", encoding="utf-8") as f:
        json.dump(values, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 100)
    print("AQF JOURNAL PIPELINE SUMMARY")
    print("=" * 100)
    print(f"Output directory       : {out_dir}")
    print(f"Target strict coverage : {target_coverage:.2%}")
    print(f"AQF strict coverage    : {strict:.2%}")
    print(f"AQF partial coverage   : {partial:.2%}")
    print(f"AQF fields/operators   : {aqf.get('field_count')} fields / {aqf.get('operator_count')} operators")
    print(f"AQF complexity         : {aqf.get('final_complexity')}")
    if no_pruning:
        print(f"No-pruning coverage    : {float(no_pruning.get('strict_coverage', 0.0)):.2%}")
    if random_summary:
        print(f"Random mean/max        : {random_summary['mean_strict_coverage']:.2%} / {random_summary['max_strict_coverage']:.2%}")
    print(f"Status                 : {'PASS' if passed else 'BELOW TARGET'}")
    print("=" * 100 + "\n")
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the locked AQF journal evaluation pipeline.")
    parser.add_argument("--data-dir", default="dataset/mixed")
    parser.add_argument("--out-dir", default="results/journal_locked/main_run")
    parser.add_argument("--complexity-budget", type=float, default=50.0)
    parser.add_argument("--theta", type=float, default=0.0)
    parser.add_argument("--lambda-sc", type=float, default=0.0)
    parser.add_argument("--mu", type=float, default=0.1)
    parser.add_argument("--eta", type=float, default=1.0)
    parser.add_argument("--random-trials", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--target-coverage", type=float, default=0.90)
    parser.add_argument("--include-cross", action="store_true")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--skip-enhanced-metrics", action="store_true")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    eval_cmd = [
        sys.executable,
        "-B",
        str(ROOT / "evaluation" / "run_evaluation_final.py"),
        "--data-dir",
        args.data_dir,
        "--out-dir",
        str(out_dir),
        "--complexity-budget",
        str(args.complexity_budget),
        "--theta",
        str(args.theta),
        "--lambda-sc",
        str(args.lambda_sc),
        "--mu",
        str(args.mu),
        "--eta",
        str(args.eta),
        "--random-trials",
        str(args.random_trials),
        "--seed",
        str(args.seed),
    ]
    if not args.no_cache:
        eval_cmd.append("--use-cache")
    if args.include_cross:
        eval_cmd.append("--include-cross")

    run_command(eval_cmd)

    if not args.skip_enhanced_metrics:
        run_command([
            sys.executable,
            "-B",
            str(ROOT / "evaluation" / "aqf_metrics_report.py"),
            "--results-dir",
            str(out_dir),
            "--eta",
            str(args.eta),
        ])

    summarize(out_dir, args.target_coverage)


if __name__ == "__main__":
    main()
