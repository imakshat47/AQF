#!/usr/bin/env python3
"""
aqf_query_realizer_v3_multiform.py

Production-level query realizer with:
  - datatype-aware operator compatibility;
  - multi-form/cross-form query realization;
  - alternative required field groups;
  - better failure diagnostics.

This fixes cross-context queries where demographic fields live in a demographic form
and clinical fields live in a clinical COMPOSITION form.
"""
from __future__ import annotations
import argparse, csv, json, re
from pathlib import Path
from typing import Any, Dict, List, Optional

def norm(x): return re.sub(r'[^a-z0-9]+',' ',str(x or '').lower()).strip()
def sid(x): return re.sub(r'[^a-zA-Z0-9_]','_',norm(x).replace(' ','_')) or 'field'
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

def load_aliases(p):
    if not p or not Path(p).exists(): return {}
    return load(p).get('field_aliases',{})

def alias_terms(term, aliases):
    out={norm(term)}; nt=norm(term)
    for k, vals in aliases.items():
        group=[k]+list(vals or [])
        if nt in {norm(x) for x in group}: out.update(norm(x) for x in group)
    return {x for x in out if x}

def alias_match(req,cand,aliases):
    c=norm(cand)
    return any(a==c or a in c or c in a for a in alias_terms(req,aliases))

class RealizerV3:
    def __init__(self, aliases_json=None, operator_mapping_json=None, strict_context=False):
        self.aliases=load_aliases(aliases_json)
        self.mapping=load(operator_mapping_json) if operator_mapping_json else {'operator_aliases':{},'datatype_operators':{},'field_overrides':{}}
        self.strict_context=strict_context
        self.forms=[]; self.queries=[]; self.results=[]

    def load_inputs(self, forms_json, workload_json):
        self.forms=load(forms_json).get('aqf_forms',[])
        payload=load(workload_json); self.queries=payload if isinstance(payload,list) else payload.get('queries',[])
        if not self.forms: raise ValueError('No AQF forms found')
        if not self.queries: raise ValueError('No workload queries found')

    def operator_match(self, req, cand, dtype=None):
        r=norm(req).replace(' ','_'); c=norm(cand).replace(' ','_')
        if r==c: return True
        aliases=self.mapping.get('operator_aliases',{})
        if c in aliases.get(r,[]): return True
        if r=='equals' and c=='contains' and str(dtype).upper() in {'DV_TEXT','DV_CODED_TEXT'}: return True
        if r in {'greater_than','less_than','greater_or_equal','less_or_equal'} and c=='range': return True
        if r in {'before','after','on_or_before','on_or_after'} and c in {'date_range','datetime_range'}: return True
        return False

    def all_fields(self):
        rows=[]
        for form in self.forms:
            for role_key, role in [('filters','filter'),('outputs','output')]:
                for f in form.get(role_key,[]):
                    x=dict(f); x['form_id']=form.get('form_id'); x['form_group']=form.get('form_group'); x['aqf_role']=role; rows.append(x)
        return rows

    def query_groups(self,q):
        groups=q.get('alternative_required_field_groups') or q.get('alternative_field_groups')
        if groups:
            out=[]
            for g in groups:
                if isinstance(g,list): out.append({'required_fields':g,'required_operators':q.get('required_operators',{})})
                else: out.append({'required_fields':g.get('fields',g.get('required_fields',[])),'required_operators':g.get('required_operators',q.get('required_operators',{}))})
            return out
        return [{'required_fields':q.get('required_fields',[]),'required_operators':q.get('required_operators',{})}]

    def realize_all(self):
        self.results=[self.realize_query(q) for q in self.queries]
        return self.results

    def realize_query(self,q):
        candidates=[]
        for g in self.query_groups(q):
            res=self.evaluate_group(q,g)
            score=(1 if res['query_realizable'] else 0,res['field_recall'],res['operator_support'],res['context_support'],-len(res['selected_forms']))
            candidates.append((score,g,res))
        candidates.sort(key=lambda x:x[0], reverse=True)
        _, group, res=candidates[0]
        return {'query_id':q.get('query_id'),'query_name':q.get('query_name'),'query_complexity':q.get('query_complexity'),'category':q.get('category'),'selected_forms':'; '.join(res['selected_forms']),'field_recall':res['field_recall'],'operator_support':res['operator_support'],'context_support':res['context_support'],'query_realizable':res['query_realizable'],'missing_fields':'; '.join(res['missing_fields']),'unsupported_fields':'; '.join(res['unsupported_fields']),'selected_required_fields':'; '.join(group.get('required_fields',[])),'failure_reason':res['failure_reason']}

    def evaluate_group(self,q,g):
        allf=self.all_fields(); maps=[]; missing=[]; unsupported=[]; forms=set(); matched=0; opok=0; optotal=0
        for rf in g.get('required_fields',[]):
            ops=g.get('required_operators',{}).get(rf,[])
            if isinstance(ops,str): ops=[ops]
            optotal+=len(ops)
            cands=[f for f in allf if alias_match(rf,f.get('name',''),self.aliases)]
            def key(f):
                comp=1 if (not ops or any(self.operator_match(o,f.get('operator',''),f.get('datatype')) for o in ops)) else 0
                filter_pref=1 if f.get('aqf_role')=='filter' else 0
                return (comp, filter_pref, float(f.get('score') or 0))
            cands=sorted(cands,key=key,reverse=True)
            if not cands:
                missing.append(rf); continue
            best=cands[0]; matched+=1; forms.add(best.get('form_id'))
            comp=True if not ops else any(self.operator_match(o,best.get('operator',''),best.get('datatype')) for o in ops)
            if comp: opok+=len(ops)
            else: unsupported.append(rf)
        fr=matched/len(g.get('required_fields',[])) if g.get('required_fields') else 1.0
        os=opok/optotal if optotal else 1.0
        cs=self.context_support(q, forms)
        ok=fr>=1.0 and os>=1.0 and (cs>=1.0 or not self.strict_context)
        reasons=[]
        if missing: reasons.append('missing_fields')
        if unsupported: reasons.append('unsupported_operators')
        if self.strict_context and cs<1.0: reasons.append('context_mismatch')
        return {'field_recall':fr,'operator_support':os,'context_support':cs,'query_realizable':ok,'missing_fields':missing,'unsupported_fields':unsupported,'selected_forms':sorted(forms),'failure_reason':';'.join(reasons)}

    def context_support(self,q, selected_forms):
        ctx=q.get('required_contexts',[])
        if not ctx: return 1.0
        blob=' '.join([str(f.get('form_group',''))+' '+ ' '.join(str(x.get('ui_group',''))+' '+str(x.get('path','')) for x in f.get('filters',[])+f.get('outputs',[])) for f in self.forms if f.get('form_id') in selected_forms])
        hits=sum(1 for c in ctx if norm(c) in norm(blob) or any(t in norm(blob) for t in alias_terms(c,self.aliases)))
        return hits/len(ctx)

    def summary(self):
        n=len(self.results); cats={}; comps={}
        for r in self.results:
            v=1 if r['query_realizable'] else 0
            cats.setdefault(r.get('category'),[]).append(v); comps.setdefault(r.get('query_complexity'),[]).append(v)
        return {'query_count':n,'realizable_queries':sum(1 for r in self.results if r['query_realizable']),'query_realization_rate':sum(1 for r in self.results if r['query_realizable'])/max(n,1),'avg_field_recall':sum(float(r['field_recall']) for r in self.results)/max(n,1),'avg_operator_support':sum(float(r['operator_support']) for r in self.results)/max(n,1),'avg_context_support':sum(float(r['context_support']) for r in self.results)/max(n,1),'category_realization':json.dumps({k:sum(v)/len(v) for k,v in cats.items()},ensure_ascii=False),'complexity_realization':json.dumps({k:sum(v)/len(v) for k,v in comps.items()},ensure_ascii=False)}

    def save(self,outdir):
        out=Path(outdir); out.mkdir(parents=True,exist_ok=True)
        cols=['query_id','query_name','query_complexity','category','selected_forms','field_recall','operator_support','context_support','query_realizable','missing_fields','unsupported_fields','selected_required_fields','failure_reason']
        with open(out/'realized_queries.csv','w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows([{k:r.get(k) for k in cols} for r in self.results])
        s=self.summary()
        with open(out/'query_realization_summary.csv','w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(s.keys())); w.writeheader(); w.writerow(s)
        (out/'realized_queries.json').write_text(json.dumps({'metadata':s,'realized_queries':self.results},indent=2,ensure_ascii=False),encoding='utf-8')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--aqf_forms_json',required=True); ap.add_argument('--workload_json',required=True); ap.add_argument('--aliases_json',default=None); ap.add_argument('--operator_mapping_json',default=None); ap.add_argument('--output_dir',required=True); ap.add_argument('--strict_context',action='store_true')
    args=ap.parse_args()
    r=RealizerV3(args.aliases_json,args.operator_mapping_json,args.strict_context); r.load_inputs(args.aqf_forms_json,args.workload_json); r.realize_all(); r.save(args.output_dir)
    s=r.summary(); print('AQF query realization v3 complete.'); print(f"Queries: {s['query_count']}"); print(f"Realizable: {s['realizable_queries']}"); print(f"Realization rate: {s['query_realization_rate']:.3f}")
if __name__=='__main__': main()
