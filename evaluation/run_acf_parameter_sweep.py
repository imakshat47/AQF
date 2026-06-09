#!/usr/bin/env python3
from __future__ import annotations
import argparse, itertools, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def vals(s,typ=int): return [typ(x.strip()) for x in s.split(',') if x.strip()]

def main():
    p=argparse.ArgumentParser(description='ACF paper-formula parameter sweep')
    p.add_argument('--data-dir',required=True); p.add_argument('--out-dir',required=True); p.add_argument('--cache-dir',default=None); p.add_argument('--use-cache',action='store_true')
    p.add_argument('--k-es',default='3,5,8,10'); p.add_argument('--k-as',default='5,7,10,12'); p.add_argument('--k-rs',default='0,1,2')
    p.add_argument('--field-complexities',default='20,25,30,35,40')
    p.add_argument('--ps',default='0.15,0.30,0.50')
    p.add_argument('--random-trials',type=int,default=30); p.add_argument('--seed',type=int,default=42); p.add_argument('--max-combos',type=int,default=0)
    args=p.parse_args(); out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)
    combos=list(itertools.product(vals(args.k_es,int),vals(args.k_as,int),vals(args.k_rs,int),vals(args.field_complexities,int),vals(args.ps,float)))
    if args.max_combos: combos=combos[:args.max_combos]
    all_rows=[]
    for i,(ke,ka,kr,fc,pval) in enumerate(combos,1):
        combo=out/'combos'/f'combo_{i:04d}_ke{ke}_ka{ka}_kr{kr}_fc{fc}_p{pval:g}'.replace('.','p')
        cmd=[sys.executable,str(ROOT/'evaluation'/'run_acf_evaluation.py'),'--data-dir',args.data_dir,'--out-dir',str(combo),'--k-e',str(ke),'--k-a',str(ka),'--k-r',str(kr),'--field-complexity',str(fc),'--p',str(pval),'--random-trials',str(args.random_trials),'--seed',str(args.seed)]
        if args.cache_dir: cmd+=['--cache-dir',args.cache_dir]
        if args.use_cache: cmd+=['--use-cache']
        print('\n[ACF SWEEP]',i,'/',len(combos),' '.join(cmd)); subprocess.check_call(cmd)
        import pandas as pd
        df=pd.read_csv(combo/'final_acf_metrics.csv'); df['combo_id']=combo.name; df['k_e']=ke; df['k_a']=ka; df['k_r']=kr; df['field_complexity']=fc; df['p']=pval; all_rows.append(df)
    if all_rows:
        import pandas as pd
        all_df=pd.concat(all_rows,ignore_index=True); all_df.to_csv(out/'acf_all_results.csv',index=False)
        det=all_df[~all_df.method.str.startswith('random')]
        det.sort_values(['method','strict_coverage','partial_coverage','field_count'],ascending=[True,False,False,True]).groupby('method').head(1).to_csv(out/'acf_best_by_method.csv',index=False)
        det.groupby('method',as_index=False).agg(avg_strict_coverage=('strict_coverage','mean'),avg_partial_coverage=('partial_coverage','mean'),avg_field_count=('field_count','mean'),avg_operator_count=('operator_count','mean')).to_csv(out/'acf_average_by_method.csv',index=False)
    print('[OK] ACF sweep complete:',out)
if __name__=='__main__': main()
