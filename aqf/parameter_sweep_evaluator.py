#!/usr/bin/env python3
"""
parameter_sweep_evaluator.py

Run AQF parameter sweeps and evaluate generated AQF forms.

This script orchestrates the existing AQF pipeline:
  1. aqf_schema_graph.py
  2. canonical_structure_generator.py
  3. operator_aware_field_selector.py
  4. adaptive_form_generator.py

Then evaluates generated forms against a workload JSON using:
  - query support rate
  - field recall
  - operator support
  - path/context support
  - form utility and complexity
  - graph complexity statistics
  - runtime

Outputs:
  parameter_sweep_results.csv
  best_configuration.json
  evaluation_plots/*.png   if matplotlib is available and --no_plots is not used

Example:
  python parameter_sweep_evaluator.py \
    --data_dir data \
    --workload_json evaluation/workload.json \
    --output_dir output/experiments \
    --scripts_dir . \
    --mode pilot
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


# ============================================================
# Experiment configuration
# ============================================================

@dataclass
class ExperimentConfig:
    experiment_id: str
    lambda_cc: float
    mu: float
    theta: float
    edge_threshold: float
    cooccurrence_scope: str
    input_weight_threshold: float
    output_weight_threshold: float
    min_input_aq: float
    min_output_aq: float
    top_k_input_per_form: int
    top_k_output_per_form: int
    kappa: float
    eta: float
    max_filters: int
    max_outputs: int
    relationship_top_k: int


@dataclass
class ExperimentResult:
    experiment_id: str
    status: str
    error: str

    lambda_cc: float
    mu: float
    theta: float
    edge_threshold: float
    cooccurrence_scope: str
    input_weight_threshold: float
    output_weight_threshold: float
    min_input_aq: float
    min_output_aq: float
    top_k_input_per_form: int
    top_k_output_per_form: int
    kappa: float
    eta: float
    max_filters: int
    max_outputs: int
    relationship_top_k: int

    schema_nodes: int = 0
    schema_edges: int = 0
    weighted_nodes: int = 0
    weighted_edges: int = 0
    reduced_nodes: int = 0
    reduced_edges: int = 0
    containment_edges: int = 0
    cooccurrence_edges: int = 0
    graph_density: float = 0.0

    canonical_forms: int = 0
    operator_aware_forms: int = 0
    aqf_forms: int = 0
    avg_form_complexity: float = 0.0
    avg_form_utility: float = 0.0
    avg_filter_count: float = 0.0
    avg_output_count: float = 0.0

    workload_queries: int = 0
    query_support_rate: float = 0.0
    avg_field_recall: float = 0.0
    avg_operator_support: float = 0.0
    avg_context_support: float = 0.0
    category_support_json: str = "{}"

    combined_score: float = 0.0
    runtime_seconds: float = 0.0


# ============================================================
# Workload evaluation
# ============================================================

OPERATOR_ALIASES = {
    "equals": {"equals", "multi_select"},
    "multi_select": {"multi_select", "equals"},
    "range": {"range", "greater_than_less_than", "date_range"},
    "date_range": {"date_range", "date_equals", "range"},
    "date_equals": {"date_equals", "date_range"},
    "contains": {"contains", "starts_with", "equals"},
    "project": {"project"},
    "sort": {"sort"},
    "group_by": {"group_by"},
    "aggregate": {"aggregate"},
    "is_present": {"is_present", "equals"},
}


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    chars = []
    for ch in text:
        if ch.isalnum():
            chars.append(ch)
        else:
            chars.append(" ")
    return " ".join("".join(chars).split())


def name_match(required: str, candidate: str) -> bool:
    r = normalize_text(required)
    c = normalize_text(candidate)
    if not r or not c:
        return False
    return r == c or r in c or c in r


def operator_match(required_operator: str, candidate_operator: str) -> bool:
    req = normalize_text(required_operator).replace(" ", "_")
    cand = normalize_text(candidate_operator).replace(" ", "_")
    allowed = OPERATOR_ALIASES.get(req, {req})
    return cand in allowed


def load_workload(workload_json: Optional[str | Path]) -> List[Dict[str, Any]]:
    if not workload_json:
        return []
    path = Path(workload_json)
    if not path.exists():
        raise FileNotFoundError(f"Workload file not found: {workload_json}")
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    if isinstance(payload, list):
        return payload
    return payload.get("queries", [])


def load_aqf_forms(forms_json: str | Path) -> List[Dict[str, Any]]:
    path = Path(forms_json)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload.get("aqf_forms", [])


def evaluate_workload(forms: List[Dict[str, Any]], workload: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not workload:
        return {
            "workload_queries": 0,
            "query_support_rate": 0.0,
            "avg_field_recall": 0.0,
            "avg_operator_support": 0.0,
            "avg_context_support": 0.0,
            "category_support": {},
        }

    query_results = []
    by_category: Dict[str, List[int]] = {}

    for query in workload:
        category = query.get("category", "uncategorized")
        best = evaluate_single_query_against_forms(query, forms)
        query_results.append(best)
        by_category.setdefault(category, []).append(1 if best["query_supported"] else 0)

    supported = sum(1 for x in query_results if x["query_supported"])
    category_support = {
        cat: (sum(vals) / len(vals) if vals else 0.0)
        for cat, vals in by_category.items()
    }

    return {
        "workload_queries": len(workload),
        "query_support_rate": supported / len(workload),
        "avg_field_recall": avg([x["field_recall"] for x in query_results]),
        "avg_operator_support": avg([x["operator_support"] for x in query_results]),
        "avg_context_support": avg([x["context_support"] for x in query_results]),
        "category_support": category_support,
    }


def evaluate_single_query_against_forms(query: Dict[str, Any], forms: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not forms:
        return {"query_supported": False, "field_recall": 0.0, "operator_support": 0.0, "context_support": 0.0}

    best = {"query_supported": False, "field_recall": 0.0, "operator_support": 0.0, "context_support": 0.0}
    for form in forms:
        score = evaluate_single_query_against_form(query, form)
        # Rank by support, then field recall, operator support, context support.
        if tuple_score(score) > tuple_score(best):
            best = score
    return best


def tuple_score(score: Dict[str, Any]) -> Tuple[int, float, float, float]:
    return (
        1 if score.get("query_supported") else 0,
        float(score.get("field_recall") or 0.0),
        float(score.get("operator_support") or 0.0),
        float(score.get("context_support") or 0.0),
    )


def evaluate_single_query_against_form(query: Dict[str, Any], form: Dict[str, Any]) -> Dict[str, Any]:
    required_fields = query.get("required_fields", [])
    required_ops = query.get("required_operators", {})
    required_contexts = query.get("required_contexts", [])

    form_fields = []
    for f in form.get("filters", []):
        f2 = dict(f)
        f2["aqf_role"] = "filter"
        form_fields.append(f2)
    for f in form.get("outputs", []):
        f2 = dict(f)
        f2["aqf_role"] = "output"
        form_fields.append(f2)

    matched_fields = 0
    matched_operators = 0
    total_operator_requirements = 0

    for req_field in required_fields:
        candidates = [f for f in form_fields if name_match(req_field, f.get("name", ""))]
        if candidates:
            matched_fields += 1

        ops = required_ops.get(req_field, [])
        if isinstance(ops, str):
            ops = [ops]
        total_operator_requirements += len(ops)
        for req_op in ops:
            if any(operator_match(req_op, f.get("operator", "")) for f in candidates):
                matched_operators += 1

    field_recall = matched_fields / len(required_fields) if required_fields else 1.0
    operator_support = matched_operators / total_operator_requirements if total_operator_requirements else 1.0

    context_support = 1.0
    if required_contexts:
        contexts_found = 0
        text_blob = " ".join([
            str(form.get("form_group", "")),
            " ".join(str(f.get("ui_group", "")) for f in form_fields),
            " ".join(str(f.get("path", "")) for f in form_fields),
        ])
        for ctx in required_contexts:
            if name_match(ctx, text_blob):
                contexts_found += 1
        context_support = contexts_found / len(required_contexts)

    query_supported = field_recall >= 1.0 and operator_support >= 1.0 and context_support >= 1.0
    return {
        "query_supported": query_supported,
        "field_recall": field_recall,
        "operator_support": operator_support,
        "context_support": context_support,
    }


# ============================================================
# Parameter grid
# ============================================================


def values_for_mode(mode: str) -> Dict[str, List[Any]]:
    if mode == "pilot":
        return {
            "lambda_cc": [0.5, 0.7, 0.85],
            "mu": [0.25, 0.5],
            "theta": [0.15, 0.25, 0.35],
            "edge_threshold": [0.2, 0.3],
            "cooccurrence_scope": ["leaf"],
            "input_weight_threshold": [0.0],
            "output_weight_threshold": [0.0],
            "min_input_aq": [0.0],
            "min_output_aq": [0.0],
            "top_k_input_per_form": [12],
            "top_k_output_per_form": [12],
            "kappa": [20, 24],
            "eta": [1.0],
            "max_filters": [12],
            "max_outputs": [8],
            "relationship_top_k": [40],
        }
    if mode == "mini":
        return {
            "lambda_cc": [0.7],
            "mu": [0.5],
            "theta": [0.25, 0.35],
            "edge_threshold": [0.3],
            "cooccurrence_scope": ["leaf"],
            "input_weight_threshold": [0.0],
            "output_weight_threshold": [0.0],
            "min_input_aq": [0.0],
            "min_output_aq": [0.0],
            "top_k_input_per_form": [12],
            "top_k_output_per_form": [12],
            "kappa": [20, 24],
            "eta": [1.0],
            "max_filters": [12],
            "max_outputs": [8],
            "relationship_top_k": [40],
        }
    if mode == "full":
        return {
            "lambda_cc": [0.5, 0.7, 0.85],
            "mu": [0.25, 0.5, 0.75],
            "theta": [0.1, 0.2, 0.25, 0.3, 0.4],
            "edge_threshold": [0.2, 0.3, 0.4],
            "cooccurrence_scope": ["leaf"],
            "input_weight_threshold": [0.0, 0.2],
            "output_weight_threshold": [0.0, 0.2],
            "min_input_aq": [0.0, 0.1],
            "min_output_aq": [0.0, 0.1],
            "top_k_input_per_form": [10, 12],
            "top_k_output_per_form": [8, 12],
            "kappa": [16, 20, 24, 30],
            "eta": [0.5, 1.0, 1.5],
            "max_filters": [8, 12],
            "max_outputs": [6, 8],
            "relationship_top_k": [20, 40],
        }
    raise ValueError(f"Unknown mode: {mode}")


def build_configs(mode: str, limit: Optional[int] = None) -> List[ExperimentConfig]:
    grid = values_for_mode(mode)
    keys = list(grid.keys())
    configs = []
    for idx, combo in enumerate(itertools.product(*(grid[k] for k in keys)), start=1):
        data = dict(zip(keys, combo))
        eid = f"exp_{idx:05d}"
        configs.append(ExperimentConfig(experiment_id=eid, **data))
        if limit is not None and len(configs) >= limit:
            break
    return configs


# ============================================================
# Pipeline runner
# ============================================================

class AQFParameterSweepEvaluator:
    def __init__(
        self,
        data_dir: str | Path,
        workload_json: Optional[str | Path],
        output_dir: str | Path,
        scripts_dir: str | Path,
        python_executable: str = sys.executable,
        keep_intermediate: bool = False,
        no_plots: bool = False,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.workload_json = Path(workload_json) if workload_json else None
        self.output_dir = Path(output_dir)
        self.scripts_dir = Path(scripts_dir)
        self.python = python_executable
        self.keep_intermediate = keep_intermediate
        self.no_plots = no_plots
        self.workload = load_workload(self.workload_json) if self.workload_json else []
        self.results: List[ExperimentResult] = []

    def run(self, configs: List[ExperimentConfig]) -> List[ExperimentResult]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        experiments_dir = self.output_dir / "runs"
        experiments_dir.mkdir(parents=True, exist_ok=True)

        for i, config in enumerate(configs, start=1):
            print(f"[{i}/{len(configs)}] Running {config.experiment_id} ...")
            result = self.run_single(config, experiments_dir / config.experiment_id)
            self.results.append(result)
            self.write_results_csv(self.output_dir / "parameter_sweep_results.csv")
            self.write_best_configuration(self.output_dir / "best_configuration.json")

        if not self.no_plots:
            self.create_plots(self.output_dir / "evaluation_plots")
        return self.results

    def run_single(self, config: ExperimentConfig, run_dir: Path) -> ExperimentResult:
        start = time.time()
        run_dir.mkdir(parents=True, exist_ok=True)
        result = ExperimentResult(status="success", error="", **asdict(config))

        try:
            graph_out = run_dir / "graph"
            canonical_out = run_dir / "canonical"
            operator_out = run_dir / "operator_aware"
            forms_out = run_dir / "aqf_forms"

            self.run_command([
                self.python, str(self.scripts_dir / "aqf_schema_graph.py"),
                "--input", str(self.data_dir),
                "--output", str(graph_out),
                "--lambda_cc", str(config.lambda_cc),
                "--mu", str(config.mu),
                "--theta", str(config.theta),
                "--edge_threshold", str(config.edge_threshold),
                "--cooccurrence_scope", str(config.cooccurrence_scope),
            ])

            self.run_command([
                self.python, str(self.scripts_dir / "canonical_structure_generator.py"),
                "--graph_json", str(graph_out / "reduced_schema_graph.json"),
                "--output_dir", str(canonical_out),
                "--input_weight_threshold", str(config.input_weight_threshold),
                "--output_weight_threshold", str(config.output_weight_threshold),
            ])

            self.run_command([
                self.python, str(self.scripts_dir / "operator_aware_field_selector.py"),
                "--canonical_forms_json", str(canonical_out / "canonical_forms.json"),
                "--output_dir", str(operator_out),
                "--min_input_aq", str(config.min_input_aq),
                "--min_output_aq", str(config.min_output_aq),
                "--top_k_input_per_form", str(config.top_k_input_per_form),
                "--top_k_output_per_form", str(config.top_k_output_per_form),
                "--best_operator_only",
            ])

            self.run_command([
                self.python, str(self.scripts_dir / "adaptive_form_generator.py"),
                "--operator_aware_forms_json", str(operator_out / "operator_aware_forms.json"),
                "--output_dir", str(forms_out),
                "--kappa", str(config.kappa),
                "--eta", str(config.eta),
                "--max_filters", str(config.max_filters),
                "--max_outputs", str(config.max_outputs),
                "--relationship_top_k", str(config.relationship_top_k),
                "--no_html",
            ])

            self.collect_metrics(result, graph_out, canonical_out, operator_out, forms_out)
            forms = load_aqf_forms(forms_out / "aqf_forms.json")
            eval_metrics = evaluate_workload(forms, self.workload)
            result.workload_queries = eval_metrics["workload_queries"]
            result.query_support_rate = eval_metrics["query_support_rate"]
            result.avg_field_recall = eval_metrics["avg_field_recall"]
            result.avg_operator_support = eval_metrics["avg_operator_support"]
            result.avg_context_support = eval_metrics["avg_context_support"]
            result.category_support_json = json.dumps(eval_metrics["category_support"], ensure_ascii=False)
            result.combined_score = self.combined_score(result)

            if not self.keep_intermediate:
                self.clean_intermediate(run_dir)

        except Exception as exc:
            result.status = "failed"
            result.error = str(exc)
            print(f"[ERROR] {config.experiment_id}: {exc}")

        result.runtime_seconds = time.time() - start
        return result

    def run_command(self, cmd: List[str]) -> None:
        completed = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if completed.returncode != 0:
            raise RuntimeError(f"Command failed: {' '.join(cmd)}\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}")

    def collect_metrics(self, result: ExperimentResult, graph_out: Path, canonical_out: Path, operator_out: Path, forms_out: Path) -> None:
        schema = load_json_safe(graph_out / "schema_graph.json")
        weighted = load_json_safe(graph_out / "weighted_schema_graph.json")
        reduced = load_json_safe(graph_out / "reduced_schema_graph.json")

        result.schema_nodes = len(schema.get("nodes", []))
        result.schema_edges = len(schema.get("edges", []))
        result.weighted_nodes = len(weighted.get("nodes", []))
        result.weighted_edges = len(weighted.get("edges", []))
        result.reduced_nodes = len(reduced.get("nodes", []))
        result.reduced_edges = len(reduced.get("edges", []))
        result.containment_edges = sum(1 for e in reduced.get("edges", []) if e.get("edge_type") == "containment")
        result.cooccurrence_edges = sum(1 for e in reduced.get("edges", []) if e.get("edge_type") == "cooccurrence")
        result.graph_density = result.reduced_edges / max(result.reduced_nodes * (result.reduced_nodes - 1), 1)

        canonical = load_json_safe(canonical_out / "canonical_forms.json")
        operator = load_json_safe(operator_out / "operator_aware_forms.json")
        forms_payload = load_json_safe(forms_out / "aqf_forms.json")
        forms = forms_payload.get("aqf_forms", [])

        result.canonical_forms = len(canonical.get("canonical_forms", []))
        result.operator_aware_forms = len(operator.get("operator_aware_forms", []))
        result.aqf_forms = len(forms)
        result.avg_form_complexity = avg([float(f.get("complexity") or 0.0) for f in forms])
        result.avg_form_utility = avg([float(f.get("utility") or 0.0) for f in forms])
        result.avg_filter_count = avg([len(f.get("filters", [])) for f in forms])
        result.avg_output_count = avg([len(f.get("outputs", [])) for f in forms])

    def combined_score(self, result: ExperimentResult) -> float:
        # Multi-objective score. If no workload is supplied, query metrics remain zero
        # and utility/complexity still rank configurations.
        support = result.query_support_rate
        field = result.avg_field_recall
        operator = result.avg_operator_support
        utility = normalize_positive(result.avg_form_utility, 0.0, 50.0)
        complexity_penalty = normalize_positive(result.avg_form_complexity, 0.0, max(result.kappa, 1.0))
        runtime_penalty = normalize_positive(result.runtime_seconds, 0.0, 300.0)
        graph_penalty = normalize_positive(result.reduced_edges, 0.0, max(result.weighted_edges, 1))
        return (
            0.35 * support
            + 0.20 * field
            + 0.15 * operator
            + 0.15 * utility
            - 0.08 * complexity_penalty
            - 0.04 * runtime_penalty
            - 0.03 * graph_penalty
        )

    def clean_intermediate(self, run_dir: Path) -> None:
        # Keep compact outputs for inspection, remove large JSON folders if desired.
        # Currently keep everything because JSON outputs are useful for debugging.
        return

    def write_results_csv(self, path: Path) -> None:
        if not self.results:
            return
        cols = list(asdict(self.results[0]).keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=cols)
            writer.writeheader()
            for r in self.results:
                writer.writerow(asdict(r))

    def write_best_configuration(self, path: Path) -> None:
        successful = [r for r in self.results if r.status == "success"]
        if not successful:
            return
        best = sorted(successful, key=lambda r: r.combined_score, reverse=True)[0]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(best), f, indent=2, ensure_ascii=False)

    def create_plots(self, plot_dir: Path) -> None:
        try:
            import matplotlib.pyplot as plt
        except Exception:
            print("[WARN] matplotlib not available; skipping plots.")
            return

        plot_dir.mkdir(parents=True, exist_ok=True)
        successful = [r for r in self.results if r.status == "success"]
        if not successful:
            return

        # Query support vs complexity
        plt.figure(figsize=(8, 6))
        plt.scatter([r.avg_form_complexity for r in successful], [r.query_support_rate for r in successful], c=[r.theta for r in successful])
        plt.xlabel("Average form complexity")
        plt.ylabel("Query support rate")
        plt.title("AQF Query Support vs Form Complexity")
        plt.colorbar(label="theta")
        plt.tight_layout()
        plt.savefig(plot_dir / "query_support_vs_complexity.png", dpi=300)
        plt.close()

        # Theta sensitivity
        grouped: Dict[float, List[ExperimentResult]] = {}
        for r in successful:
            grouped.setdefault(r.theta, []).append(r)
        xs = sorted(grouped)
        ys_support = [avg([r.query_support_rate for r in grouped[x]]) for x in xs]
        ys_edges = [avg([r.reduced_edges for r in grouped[x]]) for x in xs]
        fig, ax1 = plt.subplots(figsize=(8, 6))
        ax1.plot(xs, ys_support, marker="o")
        ax1.set_xlabel("theta")
        ax1.set_ylabel("Avg query support")
        ax2 = ax1.twinx()
        ax2.plot(xs, ys_edges, marker="s")
        ax2.set_ylabel("Avg reduced edges")
        plt.title("Theta Sensitivity")
        fig.tight_layout()
        plt.savefig(plot_dir / "theta_sensitivity.png", dpi=300)
        plt.close()

        # Pareto-like plot
        plt.figure(figsize=(8, 6))
        sizes = [max(20, r.reduced_edges / 3) for r in successful]
        plt.scatter([r.avg_form_complexity for r in successful], [r.query_support_rate for r in successful], s=sizes, c=[r.combined_score for r in successful])
        plt.xlabel("Average form complexity")
        plt.ylabel("Query support rate")
        plt.title("AQF Pareto View: Complexity vs Support")
        plt.colorbar(label="combined score")
        plt.tight_layout()
        plt.savefig(plot_dir / "pareto_front.png", dpi=300)
        plt.close()


def load_json_safe(path: str | Path) -> Dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def avg(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def normalize_positive(value: float, min_value: float, max_value: float) -> float:
    if max_value <= min_value:
        return 0.0
    return max(0.0, min(1.0, (value - min_value) / (max_value - min_value)))


# ============================================================
# CLI
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="Run AQF parameter sweep evaluation.")
    parser.add_argument("--data_dir", required=True, help="Folder containing openEHR JSON composition files")
    parser.add_argument("--workload_json", default=None, help="Evaluation workload JSON")
    parser.add_argument("--output_dir", required=True, help="Output folder for experiment results")
    parser.add_argument("--scripts_dir", default=".", help="Folder containing AQF pipeline scripts")
    parser.add_argument("--mode", choices=["mini", "pilot", "full"], default="pilot", help="Parameter grid size")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of configurations")
    parser.add_argument("--python", default=sys.executable, help="Python executable")
    parser.add_argument("--keep_intermediate", action="store_true", help="Keep all intermediate run outputs")
    parser.add_argument("--no_plots", action="store_true", help="Do not generate matplotlib plots")

    args = parser.parse_args()

    configs = build_configs(args.mode, limit=args.limit)
    print(f"Prepared {len(configs)} configurations for mode={args.mode}")

    evaluator = AQFParameterSweepEvaluator(
        data_dir=args.data_dir,
        workload_json=args.workload_json,
        output_dir=args.output_dir,
        scripts_dir=args.scripts_dir,
        python_executable=args.python,
        keep_intermediate=args.keep_intermediate,
        no_plots=args.no_plots,
    )
    evaluator.run(configs)
    print(f"Done. Results saved to {Path(args.output_dir) / 'parameter_sweep_results.csv'}")
    print(f"Best configuration saved to {Path(args.output_dir) / 'best_configuration.json'}")


if __name__ == "__main__":
    main()
