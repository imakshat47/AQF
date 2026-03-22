# generate_execution_metrics.py

from __future__ import annotations

import json
import time
import argparse
from pathlib import Path
import pandas as pd

from composition_loader import group_docs_by_composition_archetype
import query_compiler
import query_executor


def save_csv(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def main():
    parser = argparse.ArgumentParser(description="Generate execution_metrics.csv for AQF")
    parser.add_argument("--dataset_folder", required=True, help="Path to dataset folder")
    parser.add_argument("--composition_archetype", required=True, help="Composition archetype to benchmark")
    parser.add_argument("--query_cases", required=True, help="Path to query_cases.json")
    parser.add_argument("--out_csv", default="results_package/derived_metrics/execution_metrics.csv", help="Output CSV path")
    args = parser.parse_args()

    dataset_folder = Path(args.dataset_folder)
    out_csv = Path(args.out_csv)

    # Resolve files lazily from current dataset
    valid_groups, skipped = group_docs_by_composition_archetype(dataset_folder)
    files = [p for p, _ in valid_groups.get(args.composition_archetype, [])]

    if not files:
        raise RuntimeError(
            f"No files found for composition archetype: {args.composition_archetype}"
        )

    with open(args.query_cases, "r", encoding="utf-8") as f:
        query_cases = json.load(f)

    rows = []
    for case in query_cases:
        name = case["name"]
        form_state = case["form_state"]

        # count a simple interaction proxy:
        # number of criteria + outputs + sort(if any) + run button
        interaction_count = (
            len(form_state.get("criteria", []))
            + len(form_state.get("output_fields", []))
            + (1 if form_state.get("sort") else 0)
            + 1
        )

        # compile
        t0 = time.perf_counter()
        plan = query_compiler.compile_query(form_state)
        compile_sec = time.perf_counter() - t0

        # execute
        t1 = time.perf_counter()
        out = query_executor.run_query(
            files[: int(form_state.get("advanced", {}).get("slice_size", 200))],
            plan,
            occurrence_semantics=form_state.get("advanced", {}).get("occurrence_semantics", "ALL"),
            limit=int(form_state.get("advanced", {}).get("result_limit", 100))
        )
        execution_sec = time.perf_counter() - t1

        rows.append({
            "query_name": name,
            "compile_sec": compile_sec,
            "execution_sec": execution_sec,
            "scanned": out.get("scanned", 0),
            "matched": out.get("matched", 0),
            "sec_per_doc": out.get("sec_per_doc", 0.0),
            "interaction_count": interaction_count
        })

    df = pd.DataFrame(rows)
    save_csv(df, out_csv)
    print(f"[OK] Saved execution metrics to: {out_csv}")


if __name__ == "__main__":
    main()