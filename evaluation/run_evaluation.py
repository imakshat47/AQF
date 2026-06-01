#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys, time, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from aqf_eval.openehr_utils import scan_json_folder, stable_hash
from aqf_eval.canonical import build_canonical_forest
from aqf_eval.queriability import compute_scores
from aqf_eval.form_generation import generate_form
from aqf_eval.query_eval import evaluate_form, useful_field_labels
from aqf_eval.metrics import summarize_coverage, precision_at_k, recall_at_k, form_complexity, canonical_metrics
from aqf_eval.reporting import write_json, write_csv, append_csv, append_jsonl

PARSER_VERSION = "orbda_parser_v2_correctness"
BENCHMARK_VERSION = "expert_curated_v1"

def load_json(path):
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

def load_benchmarks(paths, include_cross=False):
    qs=[]
    for p in paths:
        p=Path(p)
        if not include_cross and "cross" in p.name.lower(): continue
        if p.exists(): qs.extend(load_json(p))
    return qs

def fingerprint_dir(data_dir: Path):
    meta=[]
    for p in sorted(data_dir.rglob("*.json")):
        if ".cache" in p.parts or "results" in p.parts: continue
        try: st=p.stat(); meta.append((str(p.relative_to(data_dir)), st.st_size, int(st.st_mtime)))
        except Exception: pass
    return stable_hash({"parser_version": PARSER_VERSION, "files": meta})

def dataset_summary(record_units, forest):
    fields=[f for t in forest.get("trees",{}).values() for f in t.get("fields", [])]
    return [{"json_record_units": len(record_units), "composition_families": len(forest.get("trees",{})), "canonical_trees": len(forest.get("trees",{})), "form_groups": len({(f.get("record_family"), f.get("form_group")) for f in fields}), "nested_subgroups": len({(f.get("record_family"), f.get("form_group"), f.get("nested_subgroup")) for f in fields}), "leaf_elements": len(fields), "null_flavour_fields": sum(1 for f in fields if f.get("has_null_flavour")), "coded_fields": sum(1 for f in fields if f.get("kind")=="coded"), "temporal_fields": sum(1 for f in fields if f.get("kind")=="temporal"), "numeric_fields": sum(1 for f in fields if f.get("kind")=="numeric")}]

def run(args):
    out_dir=Path(args.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir=Path(args.cache_dir) if args.cache_dir else out_dir/".cache"; cache_dir.mkdir(parents=True, exist_ok=True)
    fp=fingerprint_dir(Path(args.data_dir)); cache_meta=cache_dir/"dataset_fingerprint.json"; cache_ok=False
    if args.use_cache and cache_meta.exists() and (cache_dir/"canonical_forest.json").exists() and (cache_dir/"queriability_scores.json").exists():
        try: cache_ok = load_json(cache_meta).get("fingerprint") == fp
        except Exception: cache_ok = False
    t={}; record_units=[]
    if cache_ok:
        t["scan_seconds"]=0.0; t["canonical_build_seconds"]=0.0; t["queriability_seconds"]=0.0
        forest=load_json(cache_dir/"canonical_forest.json"); scores=load_json(cache_dir/"queriability_scores.json")
        record_count=forest.get("record_count", 0)
    else:
        t0=time.perf_counter(); record_units=scan_json_folder(Path(args.data_dir)); t["scan_seconds"]=time.perf_counter()-t0
        t0=time.perf_counter(); forest=build_canonical_forest(record_units); t["canonical_build_seconds"]=time.perf_counter()-t0
        t0=time.perf_counter(); scores=compute_scores(forest, alpha=args.alpha, beta=args.beta, lamb=args.lamb); t["queriability_seconds"]=time.perf_counter()-t0
        write_json({"fingerprint": fp, "parser_version": PARSER_VERSION, "data_dir": args.data_dir}, cache_meta)
        write_json(forest, cache_dir/"canonical_forest.json"); write_json(scores, cache_dir/"queriability_scores.json")
        record_count=len(record_units)
    queries=load_benchmarks(args.benchmarks, include_cross=args.include_cross); useful=useful_field_labels(queries)
    methods=[("aqf_full", True, args.theta), ("flattened_topk", True, args.theta), ("frequency_only", True, args.theta), ("no_pruning", True, 0.0), ("no_operator_awareness", False, args.theta)]
    forms=[]; t0=time.perf_counter()
    for method, op_aware, theta in methods:
        actual="aqf_full" if method=="no_operator_awareness" else method
        form=generate_form(forest, scores, method=actual, kappa=args.kappa, theta=theta, operator_aware=op_aware, seed=args.seed); form["method"]=method; forms.append(form)
    for i in range(args.random_trials): forms.append(generate_form(forest, scores, method=f"random_topk_{i+1}", kappa=args.kappa, theta=args.theta, operator_aware=True, seed=args.seed+i))
    t["form_generation_seconds"]=time.perf_counter()-t0
    coverage_detail=[]; ranking_rows=[]; complexity_rows=[]; canonical_rows=[]; audits=[]; t0=time.perf_counter()
    for form in forms:
        rows=evaluate_form(form, queries); coverage_detail.extend(rows)
        for r in rows:
            for a in r.get("match_audit", []): audits.append({"method": form.get("method"), "query_id": r.get("query_id"), **a})
        ranking_rows.append({"method": form.get("method"), "precision_at_10": precision_at_k(form, useful, 10), "precision_at_20": precision_at_k(form, useful, 20), "recall_at_20": recall_at_k(form, useful, 20)})
        complexity_rows.append(form_complexity(form)); canonical_rows.append(canonical_metrics(form)); write_json(form, out_dir/"generated_forms"/form.get("method")/"forms.json")
    t["query_evaluation_seconds"]=time.perf_counter()-t0
    coverage_summary=summarize_coverage(coverage_detail); runtime_rows=[{"metric": k, "seconds": v} for k,v in t.items()]; runtime_rows.append({"metric":"total_seconds","seconds":sum(t.values())})
    write_json(forest, out_dir/"artifacts"/"canonical_forest.json"); write_json(scores, out_dir/"artifacts"/"queriability_scores.json")
    write_csv(dataset_summary(record_units if record_units else [{}]*record_count, forest), out_dir/"dataset_summary.csv")
    write_csv(coverage_detail, out_dir/"benchmark_coverage_detail.csv"); write_csv(coverage_summary, out_dir/"benchmark_coverage_summary.csv")
    write_csv(ranking_rows, out_dir/"queriability_ranking.csv"); write_csv(complexity_rows, out_dir/"form_complexity.csv"); write_csv(canonical_rows, out_dir/"canonical_metrics.csv"); write_csv(runtime_rows, out_dir/"runtime.csv")
    append_jsonl(audits, out_dir/"field_match_audit.jsonl")
    run_id=stable_hash({"time": time.time(), "args": vars(args)})[:12]
    for row in coverage_summary:
        if row.get("workload")=="ALL" and row.get("difficulty")=="ALL":
            append_csv({"run_id": run_id, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "parser_version": PARSER_VERSION, "benchmark_version": BENCHMARK_VERSION, "data_dir": args.data_dir, "cache_used": cache_ok, "method": row["method"], "kappa": args.kappa, "theta": args.theta, "alpha": args.alpha, "beta": args.beta, "lambda": args.lamb, "include_cross": args.include_cross, "query_count": row["query_count"], "strict_coverage": row["strict_coverage"], "partial_coverage": row["partial_coverage"], "total_seconds": sum(t.values())}, out_dir/"evaluation_run_log.csv")
    print(f"AQF correctness evaluation complete. Results: {out_dir}")
    print(f"Cache used: {cache_ok} | Canonical fields: {dataset_summary([], forest)[0]['leaf_elements']} | Queries: {len(queries)}")

def main():
    p=argparse.ArgumentParser(); p.add_argument("--data-dir", required=True); p.add_argument("--out-dir", default="results/aqf_eval_corrected"); p.add_argument("--cache-dir", default=None); p.add_argument("--use-cache", action="store_true")
    p.add_argument("--benchmarks", nargs="+", default=[str(ROOT/"evaluation"/"benchmarks"/"benchmark_queries_hcpa.json"), str(ROOT/"evaluation"/"benchmarks"/"benchmark_queries_demographic.json"), str(ROOT/"evaluation"/"benchmarks"/"benchmark_queries_cross_composition.json")])
    p.add_argument("--include-cross", action="store_true"); p.add_argument("--kappa", type=int, default=25); p.add_argument("--theta", type=float, default=0.10); p.add_argument("--alpha", type=float, default=0.70); p.add_argument("--beta", type=float, default=0.30); p.add_argument("--lamb", type=float, default=0.25); p.add_argument("--random-trials", type=int, default=30); p.add_argument("--seed", type=int, default=42); run(p.parse_args())
if __name__ == "__main__": main()
