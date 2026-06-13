#!/usr/bin/env python3
"""
aqf_reverse_evaluation_sweep.py

Reverse AQF parameter sweep:
  - start from a high-capability configuration;
  - progressively tune DOWN field budget / complexity / top-k;
  - stop when realization falls into a desired compact target band, e.g. 0.92–0.94;
  - then save the first/best compact configuration for plotting and journal reporting.

This is faster than full grid sweep because it searches from known-good settings downwards.

Required sibling scripts:
  - operator_aware_field_selector.py
  - adaptive_form_generator_coverage_v2.py
  - demographic_graph_integrator.py
  - operator_aware_demographic_patch.py
  - aqf_operator_repair.py
  - aqf_query_realizer_v3_multiform.py
"""
from __future__ import annotations

import argparse, csv, json, shutil, subprocess, sys
from pathlib import Path
from typing import Any, Dict, List


def run(cmd: List[str], log_file: Path) -> int:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open('a', encoding='utf-8') as log:
        log.write('\n$ ' + ' '.join(cmd) + '\n')
        p=subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        log.write(p.stdout)
        return p.returncode


def read_one_row_csv(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    rows=list(csv.DictReader(path.open(encoding='utf-8')))
    if not rows:
        return {}
    out={}
    for k,v in rows[0].items():
        try: out[k]=float(v)
        except Exception: out[k]=v
    return out


def read_forms_summary(path: Path) -> Dict[str, Any]:
    if not path.exists(): return {}
    rows=list(csv.DictReader(path.open(encoding='utf-8')))
    vals=lambda col: [float(r.get(col) or 0) for r in rows]
    return {
        'form_count': len(rows),
        'total_selected_fields': sum(vals('selected_field_count')),
        'total_filters': sum(vals('filter_count')),
        'total_outputs': sum(vals('output_count')),
        'max_complexity': max(vals('complexity') or [0]),
        'total_complexity': sum(vals('complexity')),
    }


def compactness_score(rate: float, complexity: float, fields: float, target_min: float, target_max: float) -> float:
    """Prefer target-band rates and compactness. Penalize 100% or above target_max."""
    if target_min <= rate <= target_max:
        # closer to middle of band + lower fields/complexity
        mid=(target_min+target_max)/2
        return 10000 - abs(rate-mid)*1000 - complexity*1.0 - fields*0.5
    if rate > target_max:
        return 1000 - (rate-target_max)*5000 - complexity*1.0 - fields*0.5
    return rate*1000 - complexity*1.0 - fields*0.5


def copytree_clean(src: Path, dst: Path):
    if dst.exists(): shutil.rmtree(dst)
    shutil.copytree(src, dst)


def parse_ints(s: str) -> List[int]:
    return [int(x) for x in s.split(',') if x.strip()]

def parse_floats(s: str) -> List[float]:
    return [float(x) for x in s.split(',') if x.strip()]


def main():
    ap=argparse.ArgumentParser(description='Reverse AQF sweep: tune down from high-capability configs to compact 92–94% target band.')
    ap.add_argument('--canonical_forms_json', required=True)
    ap.add_argument('--clinical_graph_json', required=True)
    ap.add_argument('--workload_json', required=True)
    ap.add_argument('--aliases_json', required=True)
    ap.add_argument('--operator_mapping_json', required=True)
    ap.add_argument('--output_root', required=True)
    ap.add_argument('--target_min', type=float, default=0.92)
    ap.add_argument('--target_max', type=float, default=0.94)
    ap.add_argument('--stop_on_first_hit', action='store_true')
    ap.add_argument('--python_exe', default=sys.executable)
    # Defaults are descending/reverse order.
    ap.add_argument('--top_k_values', default='30,25,22,20,18,16,14,12,10,8')
    ap.add_argument('--target_total_fields_values', default='35,32,30,28,26,24,22,20,18,16,14,12')
    ap.add_argument('--kappa_values', default='40,36,34,32,30,28,26,24,22,20,18,16')
    ap.add_argument('--max_filters_values', default='25,22,20,18,16,14,12,10,8')
    ap.add_argument('--max_outputs_values', default='15,12,10,8,6,4')
    # Fast mode tries aligned compact configurations first, then local refinement.
    ap.add_argument('--fast_mode', action='store_true')
    args=ap.parse_args()

    py=args.python_exe
    outroot=Path(args.output_root); outroot.mkdir(parents=True, exist_ok=True)
    log_file=outroot/'reverse_sweep.log'

    top_ks=parse_ints(args.top_k_values)
    targets=parse_ints(args.target_total_fields_values)
    kappas=parse_floats(args.kappa_values)
    max_filters=parse_ints(args.max_filters_values)
    max_outputs=parse_ints(args.max_outputs_values)

    demo_dir=outroot/'00_demographic_integration'
    if not (demo_dir/'demographic_schema_graph.json').exists():
        rc=run([py,'demographic_graph_integrator.py','--clinical_graph_json',args.clinical_graph_json,'--output_dir',str(demo_dir)], log_file)
        if rc!=0: raise RuntimeError('demographic_graph_integrator.py failed')

    # Build configurations in reverse order. Fast mode uses reasonable paired values first.
    configs=[]
    if args.fast_mode:
        for topk in top_ks:
            for tf in targets:
                # choose nearest kappa >= tf + max depth allowance-ish
                k_candidates=[k for k in kappas if k>=tf]
                kappa=k_candidates[-1] if k_candidates else kappas[-1]
                mf_candidates=[m for m in max_filters if m<=tf and m>=max(4,int(tf*0.55))]
                mo_candidates=[m for m in max_outputs if m<=tf and m>=max(2,tf-(mf_candidates[0] if mf_candidates else int(tf*0.65)))]
                mf=mf_candidates[0] if mf_candidates else min(max_filters)
                mo=mo_candidates[0] if mo_candidates else min(max_outputs)
                if mf+mo>=tf:
                    configs.append((topk,tf,kappa,mf,mo))
    else:
        for topk in top_ks:
          for tf in targets:
           for kappa in kappas:
            for mf in max_filters:
             for mo in max_outputs:
                if mf+mo>=tf and kappa>=min(tf, max(kappas)):
                    configs.append((topk,tf,kappa,mf,mo))

    rows=[]; best=None; best_dir=None; hit=None
    op_cache={}
    for iteration,(topk,tf,kappa,mf,mo) in enumerate(configs, start=1):
        # Operator-aware can be cached per topk.
        if topk not in op_cache:
            op_dir=outroot/f'op_topk_{topk}'
            rc=run([py,'operator_aware_field_selector.py','--canonical_forms_json',args.canonical_forms_json,'--output_dir',str(op_dir),'--top_k_input_per_form',str(topk),'--top_k_output_per_form',str(topk),'--best_operator_only'], log_file)
            if rc!=0: continue
            op_demo_dir=outroot/f'op_demo_topk_{topk}'
            rc=run([py,'operator_aware_demographic_patch.py','--operator_aware_forms_json',str(op_dir/'operator_aware_forms.json'),'--demographic_schema_graph_json',str(demo_dir/'demographic_schema_graph.json'),'--output_dir',str(op_demo_dir)], log_file)
            if rc!=0: continue
            op_cache[topk]=op_demo_dir/'operator_aware_forms.json'

        run_dir=outroot/f'run_{iteration:04d}_tk{topk}_tf{tf}_k{kappa:g}_mf{mf}_mo{mo}'
        forms_dir=run_dir/'aqf_forms'
        repaired_dir=run_dir/'aqf_forms_repaired'
        real_dir=run_dir/'realization'

        rc=run([py,'adaptive_form_generator_coverage_v2.py','--operator_aware_forms_json',str(op_cache[topk]),'--output_dir',str(forms_dir),'--workload_json',args.workload_json,'--aliases_json',args.aliases_json,'--target_total_fields',str(tf),'--kappa',str(kappa),'--max_filters',str(mf),'--max_outputs',str(mo),'--preserve_all_forms'], log_file)
        if rc!=0: continue
        rc=run([py,'aqf_operator_repair.py','--aqf_forms_json',str(forms_dir/'aqf_forms.json'),'--operator_mapping_json',args.operator_mapping_json,'--output_dir',str(repaired_dir)], log_file)
        if rc!=0: continue
        rc=run([py,'aqf_query_realizer_v3_multiform.py','--aqf_forms_json',str(repaired_dir/'aqf_forms.json'),'--workload_json',args.workload_json,'--aliases_json',args.aliases_json,'--operator_mapping_json',args.operator_mapping_json,'--output_dir',str(real_dir)], log_file)
        if rc!=0: continue

        summary=read_one_row_csv(real_dir/'query_realization_summary.csv')
        fsum=read_forms_summary(forms_dir/'aqf_forms_summary.csv')
        rate=float(summary.get('query_realization_rate') or 0)
        complexity=float(fsum.get('total_complexity') or 0)
        fields=float(fsum.get('total_selected_fields') or 0)
        score=compactness_score(rate, complexity, fields, args.target_min, args.target_max)
        row={'iteration':iteration,'top_k':topk,'target_total_fields':tf,'kappa':kappa,'max_filters':mf,'max_outputs':mo,'realization_rate':rate,'compactness_score':score,**summary,**fsum,'run_dir':str(run_dir)}
        rows.append(row)
        if best is None or score>best['compactness_score']:
            best=row; best_dir=run_dir
        if args.target_min <= rate <= args.target_max and hit is None:
            hit=row; best=row; best_dir=run_dir
            print(f'First target-band hit: iteration={iteration}, rate={rate:.4f}, run={run_dir}')
            if args.stop_on_first_hit:
                break

    if not rows:
        raise RuntimeError('No successful reverse sweep iterations')

    fields_out=sorted({k for r in rows for k in r.keys()})
    with (outroot/'reverse_sweep_results.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=fields_out); w.writeheader(); w.writerows(rows)
    chosen=hit or best
    (outroot/'best_result.json').write_text(json.dumps(chosen,indent=2,ensure_ascii=False),encoding='utf-8')
    if best_dir:
        copytree_clean(best_dir, outroot/'best_run')

    print('Reverse AQF evaluation sweep complete.')
    print(f'Successful iterations: {len(rows)}')
    print(f"Chosen rate: {chosen['realization_rate']:.4f}")
    print(f"Chosen run: {chosen['run_dir']}")
    print(f'Output root: {outroot}')

if __name__=='__main__': main()
