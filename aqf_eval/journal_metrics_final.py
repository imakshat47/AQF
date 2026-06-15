from __future__ import annotations

import ast, json, math, re
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd

OPERATOR_WEIGHTS = {"is_known":0.5,"is_unknown":0.5,"equals":1.0,"not_equals":1.0,"contains":1.25,"in":1.25,">":1.25,"<":1.25,"before":1.25,"after":1.25,"between":1.5,"join":3.0}
GENERIC_CONTEXT_GROUPS={"Flat Fields","All Fields","Composition","Top-level fields"}

def parse_jsonish(value, default=None):
    if default is None: default=[]
    if isinstance(value,(list,dict)): return value
    if value is None: return default
    try:
        if isinstance(value,float) and math.isnan(value): return default
    except Exception: pass
    s=str(value).strip()
    if not s: return default
    try: return json.loads(s)
    except Exception:
        try: return ast.literal_eval(s)
        except Exception: return default

def norm(s):
    s=str(s or '').lower().replace('lymph','linphonodes')
    s=re.sub(r'[^a-z0-9]+',' ',s)
    return ' '.join(s.split())

def depth(f):
    parts=[p.strip() for p in str(f.get('canonical_path') or '').split('/') if p.strip()]
    if parts: return len(parts)
    return 1+len([p for p in str(f.get('nested_subgroup') or '').split('/') if p.strip()])

def valid_ops(f):
    d=set(f.get('observed_dv_types') or [])
    if f.get('dv_type'): d.add(f.get('dv_type'))
    if f.get('primary_dv_type'): d.add(f.get('primary_dv_type'))
    ops={'is_known','is_unknown'}
    if 'DV_CODED_TEXT' in d: ops|={'equals','not_equals','in','contains'}
    if 'DV_TEXT' in d: ops|={'equals','contains'}
    if 'DV_BOOLEAN' in d: ops|={'equals'}
    if 'DV_DATE' in d or 'DV_DATE_TIME' in d: ops|={'equals','before','after','between'}
    if 'DV_COUNT' in d or 'DV_QUANTITY' in d or 'DV_PROPORTION' in d: ops|={'equals','>','<','between'}
    return ops

def op_weight(op): return OPERATOR_WEIGHTS.get(str(op),1.0)

def complexity_row(form, eta=1.0):
    fields=form.get('fields',[])
    groups=form.get('groups',{}) or {}
    ops=0; valid=0; invalid=0; burden=0.0
    for f in fields:
        v=valid_ops(f)
        for op in f.get('operators',[]) or []:
            ops+=1; burden+=op_weight(op)
            if op in v: valid+=1
            else: invalid+=1
    return {'method':form.get('method'),'field_count':len(fields),'group_count':len(groups),'subgroup_count':sum(len(v or {}) for v in groups.values()) if isinstance(groups,dict) else 0,'max_depth':max([depth(f) for f in fields] or [0]),'eta':eta,'final_complexity':len(fields)+eta*max([depth(f) for f in fields] or [0]),'operator_count':ops,'valid_operator_count':valid,'invalid_or_unwanted_operator_count':invalid,'weighted_operator_burden':burden,'form_utility':sum(float(f.get('score') or 0) for f in fields)}

def operator_rows(form):
    rows=[]
    for i,f in enumerate(form.get('fields',[]),1):
        ops=f.get('operators',[]) or []; v=valid_ops(f); inv=[o for o in ops if o not in v]
        rows.append({'method':form.get('method'),'rank':i,'field_id':f.get('field_id'),'label':f.get('label'),'canonical_path':f.get('canonical_path'),'dv_type':f.get('dv_type'),'operator_count':len(ops),'operators_exposed':';'.join(map(str,ops)),'valid_operator_count':len([o for o in ops if o in v]),'invalid_or_unwanted_operator_count':len(inv),'invalid_or_unwanted_operators':';'.join(map(str,inv)),'weighted_operator_burden':sum(op_weight(o) for o in ops),'score':f.get('score')})
    return rows

def canonical_row(form):
    fields=form.get('fields',[]); groups=form.get('groups',{}) or {}; labels=[norm(f.get('label')) for f in fields]
    context=sum(1 for f in fields if f.get('form_group') not in GENERIC_CONTEXT_GROUPS and f.get('nested_subgroup') not in GENERIC_CONTEXT_GROUPS)
    lineage=sum(1 for f in fields if f.get('canonical_path'))
    dup=len(labels)-len(set(labels))
    return {'method':form.get('method'),'field_count':len(fields),'form_group_count':len(groups),'subgroup_count':sum(len(v or {}) for v in groups.values()) if isinstance(groups,dict) else 0,'max_depth':max([depth(f) for f in fields] or [0]),'avg_depth':sum(depth(f) for f in fields)/len(fields) if fields else 0,'context_preservation_rate':context/len(fields) if fields else 0,'lineage_preservation_rate':lineage/len(fields) if fields else 0,'ambiguous_label_count':dup,'ambiguous_label_resolution_rate':1.0 if dup==0 else max(0,1-dup/max(len(fields),1))}

def categorize(row):
    text=(' '.join([str(row.get('query_id','')),str(row.get('missing_fields','')),str(row.get('match_audit',''))])).lower()
    if any(t in text for t in ['gender','birth date','nationality','race','ethnic','educational']): return 'demographic'
    if any(t in text for t in ['admission','hospital','icu','patient class','claim reason','death indicator','universal id','state/province']): return 'hospitalisation'
    if any(t in text for t in ['diagnosis','problem','staging','topography','histopathological','linphonodes','lymph']): return 'diagnosis_oriented'
    if any(t in text for t in ['procedure','therapy','radiotherapy','chemotherapy','transplant','dialysis','ultrasonography','treatment']): return 'treatment_procedure'
    if any(t in text for t in ['date','duration','follow','age','before','after','between']): return 'temporal'
    return 'general_clinical'

def coverage_by_category(detail):
    d=detail.copy(); d['query_category']=d.apply(categorize,axis=1); rows=[]
    for (m,c),g in d.groupby(['method','query_category']):
        fail=g.loc[~g['strict_supported'],'failure_type'].value_counts()
        rows.append({'method':m,'category':c,'query_count':len(g),'strict_coverage':float(g['strict_supported'].mean()),'partial_coverage':float(g['partial_score'].mean()),'failure_count':int((~g['strict_supported']).sum()),'dominant_failure_reason':fail.index[0] if len(fail) else 'SUPPORTED'})
    return pd.DataFrame(rows)

def query_realization(detail):
    rows=[]
    for _,r in detail.iterrows():
        audit=parse_jsonish(r.get('match_audit'),[]); strict=bool(r.get('strict_supported'))
        paths=bool(audit) and all(a.get('matched_field') for a in audit)
        rows.append({'query_id':r.get('query_id'),'method':r.get('method'),'strict_supported':strict,'aql_generated':strict,'syntax_valid':strict,'paths_resolved':paths,'operator_valid':len(parse_jsonish(r.get('missing_operators'),[]))==0,'execution_success':None,'result_count':None,'realization_failure_type':'SUPPORTED' if strict else r.get('failure_type')})
    return pd.DataFrame(rows)

def relative_ablation(summary, complexity):
    s=summary[(summary.workload=='ALL')&(summary.difficulty=='ALL')] if {'workload','difficulty'}.issubset(summary.columns) else summary
    by={r.method:r for _,r in s.iterrows()}; cx={r.method:r for _,r in complexity.iterrows()}; rows=[]
    aqf=by.get('aqf_full'); aqfc=cx.get('aqf_full')
    if aqf is None or aqfc is None: return pd.DataFrame(rows)
    claims={'no_pruning':'compactness relative to full canonical schema','no_operator_awareness':'operator awareness reduces unnecessary controls','frequency_only':'AQF ranking vs frequency-only ranking','flattened_topk':'canonical structure/context preservation'}
    for b,claim in claims.items():
        br=by.get(b); bc=cx.get(b)
        for metric in ['strict_coverage','partial_coverage']:
            if br is not None:
                av=float(aqf.get(metric)); bv=float(br.get(metric)); rows.append({'comparison':f'aqf_full_vs_{b}','primary_claim':claim,'metric':metric,'aqf_value':av,'baseline_value':bv,'absolute_delta':av-bv,'relative_delta_percent':(av-bv)/bv*100 if bv else None})
        if bc is not None:
            for metric in ['field_count','operator_count','final_complexity','weighted_operator_burden','invalid_or_unwanted_operator_count']:
                av=float(aqfc.get(metric)); bv=float(bc.get(metric)); rows.append({'comparison':f'aqf_full_vs_{b}','primary_claim':claim,'metric':metric,'aqf_value':av,'baseline_value':bv,'absolute_delta':av-bv,'relative_delta_percent':(av-bv)/bv*100 if bv else None})
    return pd.DataFrame(rows)

def pareto(df):
    rows=[]
    for _,r in df.iterrows():
        dom=False
        for _,q in df.iterrows():
            if q.name==r.name: continue
            if q.strict_coverage>=r.strict_coverage and q.final_complexity<=r.final_complexity and (q.strict_coverage>r.strict_coverage or q.final_complexity<r.final_complexity): dom=True; break
        x=r.to_dict(); x['pareto_optimal']=not dom; rows.append(x)
    return pd.DataFrame(rows)
