#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys,traceback
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from aqf_eval.openehr_utils import scan_json_folder, stable_hash
from aqf_eval.canonical import build_canonical_forest
from aqf_eval.query_eval import evaluate_form, useful_field_labels
from aqf_eval.metrics import summarize_coverage, precision_at_k, recall_at_k
from aqf_eval.reporting import write_json, write_csv, append_jsonl
from acf_eval.paper_formulas import compute_acf_scores, scores_rows
from acf_eval.form_generation import generate_acf_interface
from acf_eval.metrics import complexity_row, operator_rows, canonical_row, coverage_by_category, relative_summary
PARSER_VERSION='acf_paper_formula_v1_1_fix'

def load_json(p):
    with open(p,'r',encoding='utf-8') as f: return json.load(f)
def load_benchmarks(paths,include_cross=False):
    qs=[]
    for p in paths:
        p=Path(p)
        if not include_cross and 'cross' in p.name.lower(): continue
        if p.exists(): qs.extend(load_json(p))
    return qs
def fingerprint_dir(data_dir):
    meta=[]
    for p in sorted(Path(data_dir).rglob('*.json')):
        if '.cache' in p.parts or 'results' in p.parts: continue
        try: st=p.stat(); meta.append((str(p.relative_to(data_dir)),st.st_size,int(st.st_mtime)))
        except Exception: pass
    return stable_hash({'parser_version':PARSER_VERSION,'files':meta})
def ensure_forest(args,out_dir):
    cache=Path(args.cache_dir) if args.cache_dir else out_dir/'.cache'; cache.mkdir(parents=True,exist_ok=True)
    fp=fingerprint_dir(Path(args.data_dir)); meta=cache/'dataset_fingerprint.json'; forest_p=cache/'canonical_forest.json'
    if args.use_cache and meta.exists() and forest_p.exists():
        try:
            if load_json(meta).get('fingerprint')==fp: return load_json(forest_p),True,cache
        except Exception: pass
    units=scan_json_folder(Path(args.data_dir)); forest=build_canonical_forest(units); write_json(forest,forest_p); write_json({'fingerprint':fp,'parser_version':PARSER_VERSION},meta); return forest,False,cache
def acf_cache_path(cache,args):
    flags=f"v1_1_p{args.p:g}_level{args.entity_level}_p1{int(args.use_p1)}p2{int(args.use_p2)}p3{int(args.use_p3)}p4{int(args.use_p4)}p5{int(args.use_p5)}p6{int(args.use_p6)}p7{int(args.use_p7)}p8{int(args.use_p8)}p9{int(args.use_p9)}".replace('.','p')
    return cache/'acf_scores'/f'{flags}.json'
def ensure_acf(forest,args,cache):
    p=acf_cache_path(cache,args); p.parent.mkdir(parents=True,exist_ok=True)
    if args.use_cache and p.exists(): return load_json(p), True
    acf=compute_acf_scores(forest,p=args.p,entity_level=args.entity_level,use_p1=args.use_p1,use_p2=args.use_p2,use_p3=args.use_p3,use_p4=args.use_p4,use_p5=args.use_p5,use_p6=args.use_p6,use_p7=args.use_p7,use_p8=args.use_p8,use_p9=args.use_p9)
    write_json(acf,p); return acf, False

def main():
    ap=argparse.ArgumentParser(description='ACF evaluation v1.1 fixed')
    ap.add_argument('--data-dir',required=True); ap.add_argument('--out-dir',default='results/acf_eval')
    ap.add_argument('--cache-dir',default=None); ap.add_argument('--use-cache',action='store_true'); ap.add_argument('--p',type=float,default=0.15)
    ap.add_argument('--entity-level',choices=['family','group','subgroup'],default='subgroup'); ap.add_argument('--k-e',type=int,default=5); ap.add_argument('--k-a',type=int,default=10); ap.add_argument('--k-r',type=int,default=1)
    ap.add_argument('--k-sigma',type=int,default=6); ap.add_argument('--k-pi',type=int,default=6); ap.add_argument('--k-tau',type=int,default=3); ap.add_argument('--k-gamma',type=int,default=2); ap.add_argument('--field-complexity',type=int,default=30)
    ap.add_argument('--random-trials',type=int,default=30); ap.add_argument('--seed',type=int,default=42); ap.add_argument('--include-cross',action='store_true')
    for flag in ['p1','p2','p3','p4','p5','p6','p7','p8','p9']:
        ap.add_argument(f'--no-{flag}',dest=f'use_{flag}',action='store_false'); ap.set_defaults(**{f'use_{flag}':True})
    ap.add_argument('--benchmarks',nargs='+',default=[str(ROOT/'evaluation'/'benchmarks'/'benchmark_queries_hcpa.json'),str(ROOT/'evaluation'/'benchmarks'/'benchmark_queries_demographic.json'),str(ROOT/'evaluation'/'benchmarks'/'benchmark_queries_cross_composition.json')])
    args=ap.parse_args(); out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)
    try:
        forest,forest_cached,cache=ensure_forest(args,out); acf,acf_cached=ensure_acf(forest,args,cache)
        queries=load_benchmarks(args.benchmarks,args.include_cross); useful=useful_field_labels(queries)
        methods=['acf_full','frequency_only','necessity_only','selection_only','projection_only','no_operator_specific','flattened_acf','no_operator_awareness','no_pruning','random_entities']
        forms=[generate_acf_interface(acf,method=m,k_e=args.k_e,k_a=args.k_a,k_r=args.k_r,k_sigma=args.k_sigma,k_pi=args.k_pi,k_tau=args.k_tau,k_gamma=args.k_gamma,field_complexity=args.field_complexity,seed=args.seed) for m in methods]
        for i in range(args.random_trials): forms.append(generate_acf_interface(acf,method=f'random_entities_{i+1}',k_e=args.k_e,k_a=args.k_a,k_r=args.k_r,k_sigma=args.k_sigma,k_pi=args.k_pi,k_tau=args.k_tau,k_gamma=args.k_gamma,field_complexity=args.field_complexity,seed=args.seed+i))
        detail=[]; audits=[]; ranking=[]; complexity=[]; canon=[]; op_rows=[]
        for form in forms:
            rows=evaluate_form(form,queries); detail.extend(rows)
            for r in rows:
                for a in r.get('match_audit',[]): audits.append({'method':form['method'],'query_id':r.get('query_id'),**a})
            ranking.append({'method':form['method'],'precision_at_10':precision_at_k(form,useful,10),'precision_at_20':precision_at_k(form,useful,20),'recall_at_20':recall_at_k(form,useful,20)})
            complexity.append(complexity_row(form)); canon.append(canonical_row(form)); op_rows.extend(operator_rows(form)); write_json(form,out/'generated_forms'/form['method']/'forms.json')
        summary=summarize_coverage(detail); rows=scores_rows(acf)
        write_csv(rows['entity_scores'],out/'acf_entity_scores.csv'); write_csv(rows['attribute_operator_scores'],out/'acf_attribute_operator_scores.csv'); write_csv(rows['related_entity_scores'],out/'acf_related_entity_scores.csv')
        write_json({'params':acf.get('params'),'forest_cache_used':forest_cached,'acf_cache_used':acf_cached},out/'run_metadata.json')
        write_csv(detail,out/'benchmark_coverage_detail.csv'); write_csv(summary,out/'benchmark_coverage_summary.csv'); write_csv(ranking,out/'queriability_ranking.csv'); write_csv(complexity,out/'complexity_breakdown.csv'); write_csv(canon,out/'canonical_structure_metrics.csv'); write_csv(op_rows,out/'operator_burden.csv')
        pd.DataFrame(op_rows).groupby('method',as_index=False).agg(field_count=('field_id','count'),operator_count=('operator_count','sum'),weighted_operator_burden=('weighted_operator_burden','sum')).to_csv(out/'operator_burden_summary.csv',index=False)
        detail_df=pd.DataFrame(detail); summ_df=pd.DataFrame(summary); comp_df=pd.DataFrame(complexity); coverage_by_category(detail_df).to_csv(out/'coverage_by_query_category.csv',index=False); relative_summary(summ_df,comp_df).to_csv(out/'relative_ablation_summary.csv',index=False)
        final=comp_df.merge(summ_df[(summ_df.workload=='ALL')&(summ_df.difficulty=='ALL')][['method','query_count','strict_coverage','partial_coverage']],on='method',how='left'); final.to_csv(out/'final_acf_metrics.csv',index=False); append_jsonl(audits,out/'field_match_audit.jsonl')
        print('[OK] ACF evaluation complete:',out); print(final[final.method.isin(methods)][['method','query_count','strict_coverage','partial_coverage','field_count','form_complexity_elements','operator_count','weighted_operator_burden']].to_string(index=False))
    except Exception:
        traceback.print_exc(); raise
if __name__=='__main__': main()
