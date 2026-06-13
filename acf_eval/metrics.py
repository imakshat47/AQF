from __future__ import annotations

import ast, json, math, re
from typing import Any, Dict, List
import pandas as pd

OP_WEIGHTS={"is_known":0.5,"is_unknown":0.5,"equals":1.0,"not_equals":1.0,"contains":1.25,"in":1.25,">":1.25,"<":1.25,"before":1.25,"after":1.25,"between":1.5}

def parse_jsonish(x, default=None):
    if default is None: default=[]
    if isinstance(x,(list,dict)): return x
    if x is None: return default
    try:
        if isinstance(x,float) and math.isnan(x): return default
    except Exception: pass
    s=str(x).strip()
    if not s: return default
    try: return json.loads(s)
    except Exception:
        try: return ast.literal_eval(s)
        except Exception: return default

def norm(s):
    s=str(s or '').lower().replace('lymph','linphonodes')
    s=re.sub(r'[^a-z0-9]+',' ',s)
    return ' '.join(s.split())

def depth(f): return max(1,len([p for p in str(f.get('canonical_path') or '').split('/') if p.strip()]))

def complexity_row(form):
    fields=form.get('fields',[]); groups=form.get('groups',{}) or {}
    ops=sum(len(f.get('operators',[]) or []) for f in fields)
    burden=sum(OP_WEIGHTS.get(op,1.0) for f in fields for op in (f.get('operators',[]) or []))
    return {'method':form.get('method'),'field_count':len(fields),'group_count':len(groups),'subgroup_count':sum(len(v or {}) for v in groups.values()) if isinstance(groups,dict) else 0,'max_depth':max([depth(f) for f in fields] or [0]),'form_complexity_elements':len(fields),'operator_count':ops,'weighted_operator_burden':burden,'form_utility':sum(float(f.get('score') or 0) for f in fields)}

def operator_rows(form):
    rows=[]
    for i,f in enumerate(form.get('fields',[]),1):
        ops=f.get('operators',[]) or []
        rows.append({'method':form.get('method'),'rank':i,'field_id':f.get('field_id'),'label':f.get('label'),'canonical_path':f.get('canonical_path'),'operator_count':len(ops),'operators_exposed':';'.join(ops),'weighted_operator_burden':sum(OP_WEIGHTS.get(op,1.0) for op in ops),'score':f.get('score'),'necessity':f.get('necessity'),'q_selection':f.get('q_selection'),'q_projection':f.get('q_projection'),'q_sort':f.get('q_sort'),'q_aggregation':f.get('q_aggregation')})
    return rows

def canonical_row(form):
    fields=form.get('fields',[]); groups=form.get('groups',{}) or {}; labels=[norm(f.get('label')) for f in fields]
    generic={'Flat Fields','All Fields','Composition','Top-level fields'}
    context=sum(1 for f in fields if f.get('form_group') not in generic and f.get('nested_subgroup') not in generic)
    dup=len(labels)-len(set(labels))
    return {'method':form.get('method'),'field_count':len(fields),'form_group_count':len(groups),'subgroup_count':sum(len(v or {}) for v in groups.values()) if isinstance(groups,dict) else 0,'max_depth':max([depth(f) for f in fields] or [0]),'context_preservation_rate':context/len(fields) if fields else 0,'ambiguous_label_count':dup}

def category(row):
    text=' '.join([str(row.get('query_id','')),str(row.get('missing_fields','')),str(row.get('match_audit',''))]).lower()
    if any(t in text for t in ['gender','birth date','nationality','race','ethnic','educational']): return 'demographic'
    if any(t in text for t in ['diagnosis','problem','staging','topography','histopathological','linphonodes','lymph']): return 'diagnosis_oriented'
    if any(t in text for t in ['procedure','therapy','radiotherapy','chemotherapy','transplant','dialysis','ultrasonography','treatment']): return 'treatment_procedure'
    if any(t in text for t in ['date','duration','follow','age','before','after','between']): return 'temporal'
    return 'general_clinical'

def coverage_by_category(detail):
    d=detail.copy(); d['query_category']=d.apply(category,axis=1); rows=[]
    for (m,c),g in d.groupby(['method','query_category']):
        fail=g.loc[~g['strict_supported'],'failure_type'].value_counts()
        rows.append({'method':m,'category':c,'query_count':len(g),'strict_coverage':float(g['strict_supported'].mean()),'partial_coverage':float(g['partial_score'].mean()),'failure_count':int((~g['strict_supported']).sum()),'dominant_failure_reason':fail.index[0] if len(fail) else 'SUPPORTED'})
    return pd.DataFrame(rows)

def relative_summary(summary, complexity):
    s=summary[(summary.workload=='ALL')&(summary.difficulty=='ALL')]
    by={r.method:r for _,r in s.iterrows()}; cx={r.method:r for _,r in complexity.iterrows()}; rows=[]
    base=by.get('acf_full'); basec=cx.get('acf_full')
    if base is None or basec is None: return pd.DataFrame(rows)
    claims={'no_pruning':'full-schema upper bound','no_operator_awareness':'operator-specific formula benefit','frequency_only':'paper formulas vs frequency only','necessity_only':'operator-specific formulas vs Formula 4 only','selection_only':'full operator model vs selection-only','flattened_acf':'context-preserving composition vs flattened fields','random_entities':'paper entity ranking vs random entity choice'}
    for m,claim in claims.items():
        if m not in by: continue
        for metric in ['strict_coverage','partial_coverage']:
            av=float(base[metric]); bv=float(by[m][metric]); rows.append({'comparison':f'acf_full_vs_{m}','claim':claim,'metric':metric,'acf_value':av,'baseline_value':bv,'absolute_delta':av-bv,'relative_delta_percent':(av-bv)/bv*100 if bv else None})
        if m in cx:
            for metric in ['field_count','operator_count','weighted_operator_burden','form_complexity_elements']:
                av=float(basec[metric]); bv=float(cx[m][metric]); rows.append({'comparison':f'acf_full_vs_{m}','claim':claim,'metric':metric,'acf_value':av,'baseline_value':bv,'absolute_delta':av-bv,'relative_delta_percent':(av-bv)/bv*100 if bv else None})
    return pd.DataFrame(rows)
