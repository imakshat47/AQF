#!/usr/bin/env python3
"""aqf_realization_failure_analyzer.py: summarize realization failures."""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path
from collections import Counter, defaultdict

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--realized_queries_csv',required=True); ap.add_argument('--output_dir',required=True); args=ap.parse_args()
    rows=list(csv.DictReader(open(args.realized_queries_csv,encoding='utf-8')))
    missing=Counter(); unsupported=Counter(); category=defaultdict(lambda:Counter())
    for r in rows:
        ok=str(r.get('query_realizable')).lower()=='true'
        category[r.get('category')]['total']+=1; category[r.get('category')]['realizable']+=1 if ok else 0
        if not ok:
            for f in (r.get('missing_fields') or '').split(';'):
                f=f.strip()
                if f: missing[f]+=1
            for f in (r.get('unsupported_fields') or '').split(';'):
                f=f.strip()
                if f: unsupported[f]+=1
    out=Path(args.output_dir); out.mkdir(parents=True,exist_ok=True)
    with open(out/'failure_missing_fields.csv','w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['field','count']); w.writerows(missing.most_common())
    with open(out/'failure_unsupported_fields.csv','w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['field','count']); w.writerows(unsupported.most_common())
    with open(out/'failure_category_summary.csv','w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['category','total','realizable','rate'])
        for k,c in category.items(): w.writerow([k,c['total'],c['realizable'],c['realizable']/c['total'] if c['total'] else 0])
    print('Failure analysis complete:', out)
if __name__=='__main__': main()
