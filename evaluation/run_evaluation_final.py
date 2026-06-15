#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from aqf_eval.openehr_utils import scan_json_folder, stable_hash
from aqf_eval.canonical import build_canonical_forest
from aqf_eval.queriability_final import compute_scores_final, scores_to_rows
from aqf_eval.form_generation_final import generate_form_final
from aqf_eval.query_eval import evaluate_form, useful_field_labels
from aqf_eval.metrics import summarize_coverage, precision_at_k, recall_at_k, canonical_metrics
from aqf_eval.reporting import write_json, write_csv, append_jsonl
from aqf_eval.selection_audit import audit_field_selection
from aqf_eval.journal_metrics_final import complexity_row, operator_rows, canonical_row, coverage_by_category, query_realization, relative_ablation, pareto
import pandas as pd

PARSER_VERSION='aqf_final_v2_4_draft_aligned'
BENCHMARK_VERSION='expert_curated_v2_three_compositions'

def load_json(p):
    with open(p,'r',encoding='utf-8') as f: return json.load(f)

def load_benchmarks(paths, include_cross=False):
    qs=[]
    for p in paths:
        p=Path(p)
        if not include_cross and 'cross' in p.name.lower(): continue
        if p.exists(): qs.extend(load_json(p))
    return qs

def fingerprint_dir(data_dir: Path):
    meta=[]
    for p in sorted(data_dir.rglob('*.json')):
        if '.cache' in p.parts or 'results' in p.parts: continue
        try:
            st=p.stat(); meta.append((str(p.relative_to(data_dir)), st.st_size, int(st.st_mtime)))
        except Exception: pass
    return stable_hash({'parser_version':'aqf_final_v2_4', 'files':meta})

def ensure_forest(args, out_dir):
    cache_dir=Path(args.cache_dir) if args.cache_dir else out_dir/'.cache'; cache_dir.mkdir(parents=True,exist_ok=True)
    fp=fingerprint_dir(Path(args.data_dir)); meta=cache_dir/'dataset_fingerprint.json'; forest_p=cache_dir/'canonical_forest.json'
    if args.use_cache and meta.exists() and forest_p.exists():
        try:
            if load_json(meta).get('fingerprint')==fp:
                return load_json(forest_p), True, cache_dir
        except Exception: pass
    units=scan_json_folder(Path(args.data_dir)); forest=build_canonical_forest(units)
    write_json(forest, forest_p); write_json({'fingerprint':fp,'parser_version':PARSER_VERSION}, meta)
    return forest, False, cache_dir

def score_cache_path(cache_dir, lambda_sc, mu):
    return cache_dir/'scores'/f'final_scores_l{lambda_sc:g}_mu{mu:g}.json'.replace('.','p')

def ensure_scores(forest, cache_dir, lambda_sc, mu, use_cache):
    p=score_cache_path(cache_dir,lambda_sc,mu); p.parent.mkdir(parents=True,exist_ok=True)
    if use_cache and p.exists(): return load_json(p), True
    scores=compute_scores_final(forest, lambda_sc=lambda_sc, mu=mu)
    write_json(scores,p); return scores, False

def dataset_summary(forest):
    fields=[f for t in forest.get('trees',{}).values() for f in t.get('fields',[])]
    return [{'composition_families':len(forest.get('trees',{})),'canonical_fields':len(fields),'coded_fields':sum(1 for f in fields if f.get('kind')=='coded'),'temporal_fields':sum(1 for f in fields if f.get('kind')=='temporal'),'numeric_fields':sum(1 for f in fields if f.get('kind')=='numeric'),'boolean_fields':sum(1 for f in fields if f.get('kind')=='boolean')}]

def main():
    p=argparse.ArgumentParser(description='AQF final-draft aligned evaluation')
    p.add_argument('--data-dir',required=True); p.add_argument('--out-dir',default='results/aqf_final_v2_4')
    p.add_argument('--cache-dir',default=None); p.add_argument('--use-cache',action='store_true')
    p.add_argument('--complexity-budget',type=float,default=35.0)
    p.add_argument('--theta',type=float,default=0.10); p.add_argument('--lambda-sc',type=float,default=0.25); p.add_argument('--mu',type=float,default=0.25); p.add_argument('--eta',type=float,default=1.0)
    p.add_argument('--random-trials',type=int,default=30); p.add_argument('--seed',type=int,default=42); p.add_argument('--include-cross',action='store_true')
    p.add_argument('--benchmarks',nargs='+',default=[
        str(ROOT/'evaluation'/'benchmarks'/'benchmark_queries_hcpa.json'),
        str(ROOT/'evaluation'/'benchmarks'/'benchmark_queries_demographic.json'),
        str(ROOT/'evaluation'/'benchmarks'/'benchmark_queries_hospitalisation.json'),
        str(ROOT/'evaluation'/'benchmarks'/'benchmark_queries_cross_composition.json'),
    ])
    args=p.parse_args(); out_dir=Path(args.out_dir); out_dir.mkdir(parents=True,exist_ok=True)
    forest, forest_cached, cache_dir=ensure_forest(args,out_dir)
    scores, scores_cached=ensure_scores(forest,cache_dir,args.lambda_sc,args.mu,args.use_cache)
    queries=load_benchmarks(args.benchmarks,args.include_cross); useful=useful_field_labels(queries)
    methods=['aqf_full','aqf_topk_no_threshold','frequency_only','flattened_topk','no_operator_awareness','no_pruning']
    forms=[]
    for m in methods:
        forms.append(generate_form_final(forest,scores,method=m,complexity_budget=args.complexity_budget,theta=args.theta,eta=args.eta,seed=args.seed))
    for i in range(args.random_trials):
        forms.append(generate_form_final(forest,scores,method=f'random_topk_{i+1}',complexity_budget=args.complexity_budget,theta=args.theta,eta=args.eta,seed=args.seed+i))
    detail=[]; audits=[]; ranking=[]; complexity=[]; canon=[]; op_rows=[]
    for form in forms:
        rows=evaluate_form(form,queries); detail.extend(rows)
        for r in rows:
            for a in r.get('match_audit',[]): audits.append({'method':form['method'],'query_id':r.get('query_id'),**a})
        ranking.append({'method':form['method'],'precision_at_10':precision_at_k(form,useful,10),'precision_at_20':precision_at_k(form,useful,20),'recall_at_20':recall_at_k(form,useful,20)})
        c=complexity_row(form,args.eta); complexity.append(c); canon.append(canonical_row(form)); op_rows.extend(operator_rows(form))
        write_json(form,out_dir/'generated_forms'/form['method']/'forms.json')
    summary=summarize_coverage(detail)
    write_json(forest,out_dir/'artifacts'/'canonical_forest.json'); write_json(scores,out_dir/'artifacts'/'queriability_scores_final.json')
    write_csv(scores_to_rows(forest,scores), out_dir/'field_scores_final.csv')
    write_csv(dataset_summary(forest),out_dir/'dataset_summary.csv')
    write_csv(detail,out_dir/'benchmark_coverage_detail.csv'); write_csv(summary,out_dir/'benchmark_coverage_summary.csv')
    write_csv(ranking,out_dir/'queriability_ranking.csv'); write_csv(complexity,out_dir/'complexity_breakdown.csv'); write_csv(canon,out_dir/'canonical_structure_metrics.csv'); write_csv(op_rows,out_dir/'operator_burden.csv')
    append_jsonl(audits,out_dir/'field_match_audit.jsonl')
    try: write_csv(audit_field_selection(forest,scores,forms,queries),out_dir/'field_selection_audit.csv')
    except Exception as e: print('[WARN] field selection audit failed',e)
    comp_df=pd.DataFrame(complexity); summ_df=pd.DataFrame(summary); detail_df=pd.DataFrame(detail)
    final=comp_df.merge(summ_df[(summ_df.workload=='ALL')&(summ_df.difficulty=='ALL')][['method','query_count','strict_coverage','partial_coverage']],on='method',how='left')
    final.to_csv(out_dir/'final_aqf_metrics.csv',index=False)
    pd.DataFrame(op_rows).groupby('method',as_index=False).agg(field_count=('field_id','count'),operator_count=('operator_count','sum'),valid_operator_count=('valid_operator_count','sum'),invalid_or_unwanted_operator_count=('invalid_or_unwanted_operator_count','sum'),weighted_operator_burden=('weighted_operator_burden','sum')).to_csv(out_dir/'operator_burden_summary.csv',index=False)
    coverage_by_category(detail_df).to_csv(out_dir/'coverage_by_query_category.csv',index=False)
    query_realization(detail_df).to_csv(out_dir/'query_realization_results.csv',index=False)
    relative_ablation(summ_df,comp_df).to_csv(out_dir/'relative_ablation_summary.csv',index=False)
    pareto(final.dropna(subset=['strict_coverage','final_complexity'])).to_csv(out_dir/'pareto_frontier.csv',index=False)
    write_json({'parser_version':PARSER_VERSION,'benchmark_version':BENCHMARK_VERSION,'complexity_budget':args.complexity_budget,'theta':args.theta,'lambda_sc':args.lambda_sc,'mu':args.mu,'eta':args.eta,'forest_cache_used':forest_cached,'score_cache_used':scores_cached},out_dir/'run_metadata.json')
    print(f'[OK] AQF final evaluation complete: {out_dir}')
    print(final[final.method.isin(methods)][['method','query_count','strict_coverage','partial_coverage','field_count','max_depth','final_complexity','operator_count','weighted_operator_burden']].to_string(index=False))
if __name__=='__main__': main()
