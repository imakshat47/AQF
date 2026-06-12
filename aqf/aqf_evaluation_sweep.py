#!/usr/bin/env python3
"""
aqf_evaluation_sweep.py

End-to-end AQF evaluation sweep for journal-grade reporting.

Goal:
  - tune AQF generation parameters to reach a target realization band, e.g. 0.9467–0.98;
  - avoid reporting suspicious 100% coverage as the primary result;
  - balance expressivity and compactness;
  - save the first acceptable/best run and generate plots.

This script expects the previously created pipeline scripts to be available in the same
working directory or on PATH:
  - operator_aware_field_selector.py
  - adaptive_form_generator_coverage_v2.py
  - demographic_graph_integrator.py
  - operator_aware_demographic_patch.py
  - aqf_operator_repair.py
  - aqf_query_realizer_v3_multiform.py
  - aqf_realization_failure_analyzer.py

It does not modify the original input files.
"""
from __future__ import annotations

import argparse, csv, json, os, shutil, subprocess, sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def run(cmd: List[str], log_file: Path) -> int:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open('a', encoding='utf-8') as log:
        log.write('\n$ ' + ' '.join(cmd) + '\n')
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        log.write(p.stdout)
        return p.returncode


def read_summary(path: Path) -> Dict[str, Any]:
    with path.open('r', encoding='utf-8') as f:
        rows=list(csv.DictReader(f))
    if not rows: return {}
    out={}
    for k,v in rows[0].items():
        try: out[k]=float(v)
        except Exception: out[k]=v
    return out


def read_forms_summary(path: Path) -> Dict[str, Any]:
    if not path.exists(): return {}
    rows=list(csv.DictReader(path.open(encoding='utf-8')))
    return {
        'form_count': len(rows),
        'total_selected_fields': sum(float(r.get('selected_field_count') or 0) for r in rows),
        'total_filters': sum(float(r.get('filter_count') or 0) for r in rows),
        'total_outputs': sum(float(r.get('output_count') or 0) for r in rows),
        'max_complexity': max([float(r.get('complexity') or 0) for r in rows] or [0]),
        'total_complexity': sum(float(r.get('complexity') or 0) for r in rows),
    }


def score_run(rate: float, complexity: float, target: float, ceiling: float) -> float:
    # Prefer rates inside target band, then lower complexity. Penalize 100-ish coverage.
    if target <= rate <= ceiling:
        return 1000 + (ceiling-rate)*10 - complexity*0.01
    if rate > ceiling:
        return 500 - (rate-ceiling)*200 - complexity*0.01
    return rate*100 - complexity*0.01


def copytree_clean(src: Path, dst: Path):
    if dst.exists(): shutil.rmtree(dst)
    shutil.copytree(src, dst)


def main():
    ap=argparse.ArgumentParser(description='Run AQF parameter sweep and stop near target coverage.')
    ap.add_argument('--canonical_forms_json', required=True)
    ap.add_argument('--clinical_graph_json', required=True)
    ap.add_argument('--base_operator_aware_json', default=None, help='Optional precomputed operator-aware forms. If omitted, operator-aware selection is run each iteration.')
    ap.add_argument('--workload_json', required=True)
    ap.add_argument('--aliases_json', required=True)
    ap.add_argument('--operator_mapping_json', required=True)
    ap.add_argument('--output_root', required=True)
    ap.add_argument('--target_min', type=float, default=0.9467)
    ap.add_argument('--target_max', type=float, default=0.98)
    ap.add_argument('--stop_on_first_hit', action='store_true')
    ap.add_argument('--top_k_values', default='12,16,20,25,30')
    ap.add_argument('--target_total_fields_values', default='18,22,26,30,35')
    ap.add_argument('--kappa_values', default='24,28,32,36,40')
    ap.add_argument('--max_filters_values', default='12,16,20,25')
    ap.add_argument('--max_outputs_values', default='8,10,12,15')
    ap.add_argument('--python_exe', default=sys.executable)
    args=ap.parse_args()

    outroot=Path(args.output_root); outroot.mkdir(parents=True, exist_ok=True)
    log_file=outroot/'sweep.log'
    py=args.python_exe

    top_ks=[int(x) for x in args.top_k_values.split(',') if x.strip()]
    targets=[int(x) for x in args.target_total_fields_values.split(',') if x.strip()]
    kappas=[float(x) for x in args.kappa_values.split(',') if x.strip()]
    max_filters=[int(x) for x in args.max_filters_values.split(',') if x.strip()]
    max_outputs=[int(x) for x in args.max_outputs_values.split(',') if x.strip()]

    # Build demographic graph once.
    demo_dir=outroot/'00_demographic_integration'
    if not (demo_dir/'demographic_schema_graph.json').exists():
        rc=run([py,'demographic_graph_integrator.py','--clinical_graph_json',args.clinical_graph_json,'--output_dir',str(demo_dir)], log_file)
        if rc!=0: raise RuntimeError('demographic_graph_integrator.py failed')

    rows=[]; best=None; best_dir=None; iteration=0
    for topk in top_ks:
        # operator-aware full/partial
        op_dir=outroot/f'op_topk_{topk}'
        if args.base_operator_aware_json:
            op_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(args.base_operator_aware_json, op_dir/'operator_aware_forms.json')
        else:
            rc=run([py,'operator_aware_field_selector.py','--canonical_forms_json',args.canonical_forms_json,'--output_dir',str(op_dir),'--top_k_input_per_form',str(topk),'--top_k_output_per_form',str(topk),'--best_operator_only'], log_file)
            if rc!=0: continue
        op_demo_dir=outroot/f'op_demo_topk_{topk}'
        rc=run([py,'operator_aware_demographic_patch.py','--operator_aware_forms_json',str(op_dir/'operator_aware_forms.json'),'--demographic_schema_graph_json',str(demo_dir/'demographic_schema_graph.json'),'--output_dir',str(op_demo_dir)], log_file)
        if rc!=0: continue

        for kappa in kappas:
          for target_fields in targets:
           for mf in max_filters:
            for mo in max_outputs:
                if mf+mo < target_fields: continue
                iteration+=1
                run_dir=outroot/f'run_{iteration:04d}_tk{topk}_tf{target_fields}_k{kappa:g}_mf{mf}_mo{mo}'
                forms_dir=run_dir/'aqf_forms'
                repaired_dir=run_dir/'aqf_forms_repaired'
                real_dir=run_dir/'realization'
                rc=run([py,'adaptive_form_generator_coverage_v2.py','--operator_aware_forms_json',str(op_demo_dir/'operator_aware_forms.json'),'--output_dir',str(forms_dir),'--workload_json',args.workload_json,'--aliases_json',args.aliases_json,'--target_total_fields',str(target_fields),'--kappa',str(kappa),'--max_filters',str(mf),'--max_outputs',str(mo),'--preserve_all_forms'], log_file)
                if rc!=0: continue
                rc=run([py,'aqf_operator_repair.py','--aqf_forms_json',str(forms_dir/'aqf_forms.json'),'--operator_mapping_json',args.operator_mapping_json,'--output_dir',str(repaired_dir)], log_file)
                if rc!=0: continue
                rc=run([py,'aqf_query_realizer_v3_multiform.py','--aqf_forms_json',str(repaired_dir/'aqf_forms.json'),'--workload_json',args.workload_json,'--aliases_json',args.aliases_json,'--operator_mapping_json',args.operator_mapping_json,'--output_dir',str(real_dir)], log_file)
                if rc!=0: continue

                summary=read_summary(real_dir/'query_realization_summary.csv')
                fsum=read_forms_summary(forms_dir/'aqf_forms_summary.csv')
                rate=float(summary.get('query_realization_rate') or 0)
                complexity=float(fsum.get('total_complexity') or 0)
                sc=score_run(rate, complexity, args.target_min, args.target_max)
                row={'iteration':iteration,'top_k':topk,'target_total_fields':target_fields,'kappa':kappa,'max_filters':mf,'max_outputs':mo,'realization_rate':rate,'score':sc,**summary,**fsum,'run_dir':str(run_dir)}
                rows.append(row)
                if best is None or sc>best['score']:
                    best=row; best_dir=run_dir
                if args.target_min <= rate <= args.target_max and args.stop_on_first_hit:
                    print(f'First target-band hit at iteration {iteration}: rate={rate:.4f}, run={run_dir}')
                    break
            else: continue
            break
           else: continue
           break
          else: continue
          break
        if args.stop_on_first_hit and rows and args.target_min <= rows[-1]['realization_rate'] <= args.target_max:
            break

    if not rows: raise RuntimeError('No successful sweep iterations')
    fields=sorted({k for r in rows for k in r.keys()})
    with (outroot/'sweep_results.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    best=best or max(rows,key=lambda r:r['score'])
    (outroot/'best_result.json').write_text(json.dumps(best,indent=2,ensure_ascii=False),encoding='utf-8')
    if best_dir:
        copytree_clean(best_dir, outroot/'best_run')
    print('AQF evaluation sweep complete.')
    print(f'Iterations: {len(rows)}')
    print(f"Best rate: {best['realization_rate']:.4f}")
    print(f"Best run: {best['run_dir']}")
    print(f'Output root: {outroot}')

if __name__=='__main__': main()
