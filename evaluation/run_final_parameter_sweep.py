#!/usr/bin/env python3
from __future__ import annotations
import argparse, itertools, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def vals(s,typ=float): return [typ(x.strip()) for x in s.split(',') if x.strip()]

def main():
    p=argparse.ArgumentParser(description='AQF final-draft aligned parameter sweep')
    p.add_argument('--data-dir',required=True); p.add_argument('--out-dir',required=True); p.add_argument('--cache-dir',default=None); p.add_argument('--use-cache',action='store_true')
    p.add_argument('--complexity-budgets',default='30,32,35,39,42,45,53')
    p.add_argument('--thetas',default='0.00,0.02,0.05,0.08,0.10,0.12,0.15,0.20')
    p.add_argument('--lambda-scs',default='0.00,0.25,0.50,0.75,1.00')
    p.add_argument('--mus',default='0.00,0.10,0.25,0.50,0.75,1.00')
    p.add_argument('--etas',default='0.0,0.5,1.0,1.5,2.0')
    p.add_argument('--random-trials',type=int,default=30); p.add_argument('--seed',type=int,default=42); p.add_argument('--max-combos',type=int,default=0)
    args=p.parse_args(); out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)
    combos=list(itertools.product(vals(args.complexity_budgets,float), vals(args.thetas,float), vals(args.lambda_scs,float), vals(args.mus,float), vals(args.etas,float)))
    if args.max_combos: combos=combos[:args.max_combos]
    all_rows=[]
    for i,(cb,theta,lam,mu,eta) in enumerate(combos,1):
        combo_dir=out/'combos'/f'combo_{i:04d}_c{cb:g}_t{theta:g}_l{lam:g}_mu{mu:g}_e{eta:g}'.replace('.','p')
        cmd=[sys.executable,str(ROOT/'evaluation'/'run_evaluation_final.py'),'--data-dir',args.data_dir,'--out-dir',str(combo_dir),'--complexity-budget',str(cb),'--theta',str(theta),'--lambda-sc',str(lam),'--mu',str(mu),'--eta',str(eta),'--random-trials',str(args.random_trials),'--seed',str(args.seed)]
        if args.cache_dir: cmd+=['--cache-dir',args.cache_dir]
        if args.use_cache: cmd+=['--use-cache']
        print('\n[SWEEP]',i,'/',len(combos),' '.join(cmd)); subprocess.check_call(cmd)
        import pandas as pd
        df=pd.read_csv(combo_dir/'final_aqf_metrics.csv'); df['combo_id']=combo_dir.name; df['complexity_budget']=cb; df['theta']=theta; df['lambda_sc']=lam; df['mu']=mu; df['eta']=eta; all_rows.append(df)
    if all_rows:
        import pandas as pd
        all_df=pd.concat(all_rows,ignore_index=True); all_df.to_csv(out/'journal_all_results.csv',index=False)
        # Lightweight best/average summaries.
        all_df[~all_df.method.str.startswith('random')].sort_values(['method','strict_coverage','partial_coverage','final_complexity'],ascending=[True,False,False,True]).groupby('method').head(1).to_csv(out/'journal_best_by_method.csv',index=False)
        all_df.groupby('method',as_index=False).agg(avg_strict_coverage=('strict_coverage','mean'),avg_partial_coverage=('partial_coverage','mean'),avg_final_complexity=('final_complexity','mean'),avg_operator_count=('operator_count','mean')).to_csv(out/'journal_average_by_method.csv',index=False)
    print('[OK] final AQF sweep complete',out)
if __name__=='__main__': main()
