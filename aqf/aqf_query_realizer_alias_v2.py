#!/usr/bin/env python3
"""
aqf_query_realizer_alias_v2.py

Alias-aware AQF query realization v2.

Fixes/extends earlier realizer:
  1. Prefer FILTER candidates over OUTPUT candidates for workload predicates.
  2. Prefer operator-compatible candidates before highest score.
  3. Relax text equality: required equals can be satisfied by contains for DV_TEXT.
  4. Supports alternative_required_field_groups for OR-style benchmark semantics.
  5. Supports demographic/external fields inserted by demographic_form_augmenter.py.
"""
from __future__ import annotations

import argparse, csv, json, re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

OPERATOR_ALIASES = {
    "equals": {"equals", "multi_select"},
    "multi_select": {"multi_select", "equals"},
    "range": {"range", "greater_than_less_than", "date_range"},
    "date_range": {"date_range", "date_equals", "range"},
    "date_equals": {"date_equals", "date_range"},
    "contains": {"contains", "starts_with", "equals"},
    "is_present": {"is_present", "equals", "contains", "date_range", "range"},
}

def norm(x: Any) -> str:
    if x is None: return ""
    s=str(x).strip().lower()
    s=re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())

def sid(x: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", norm(x).replace(" ", "_")) or "field"

def load_json(path: str|Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))

def load_aliases(path: Optional[str|Path]) -> Dict[str, List[str]]:
    if not path or not Path(path).exists(): return {}
    return load_json(path).get('field_aliases', {})

def alias_terms(term: str, aliases: Dict[str, List[str]]) -> set[str]:
    out={norm(term)}; nt=norm(term)
    for k, vals in aliases.items():
        group=[k]+list(vals or [])
        ng={norm(v) for v in group}
        if nt in ng: out.update(ng)
    return {x for x in out if x}

def alias_match(required: str, candidate: str, aliases: Dict[str, List[str]]) -> bool:
    c=norm(candidate)
    return any(a==c or a in c or c in a for a in alias_terms(required, aliases))

def operator_match(req: str, cand: str, datatype: Optional[str]=None) -> bool:
    r=norm(req).replace(' ','_'); c=norm(cand).replace(' ','_')
    if c in OPERATOR_ALIASES.get(r,{r}): return True
    # Important clinical-text relaxation: equality intent can be realized as text contains.
    if r == 'equals' and c == 'contains' and str(datatype or '').upper() in {'DV_TEXT','DV_CODED_TEXT'}:
        return True
    # Presence is weak but acceptable only for partial query drafts; not full support unless no explicit operator exists.
    return False

def collect_form_fields(form: Dict[str,Any]) -> List[Dict[str,Any]]:
    out=[]
    for role_key, role in [('filters','filter'),('outputs','output')]:
        for f in form.get(role_key,[]):
            x=dict(f); x['aqf_role']=role; out.append(x)
    return out

class AQFQueryRealizerV2:
    def __init__(self, aliases_json: Optional[str|Path]=None, strict_context: bool=False):
        self.aliases=load_aliases(aliases_json)
        self.strict_context=strict_context
        self.forms=[]; self.queries=[]; self.realized=[]

    def load_inputs(self, aqf_forms_json: str|Path, workload_json: str|Path):
        self.forms=load_json(aqf_forms_json).get('aqf_forms', [])
        payload=load_json(workload_json)
        self.queries=payload if isinstance(payload,list) else payload.get('queries', [])
        if not self.forms: raise ValueError('No AQF forms found')
        if not self.queries: raise ValueError('No workload queries found')

    def realize_all(self):
        self.realized=[self.realize_query(q) for q in self.queries]
        return self.realized

    def query_groups(self, q: Dict[str,Any]) -> List[Dict[str,Any]]:
        # If workload defines explicit OR groups, use them. Otherwise use current required_fields as one AND group.
        groups=q.get('alternative_required_field_groups') or q.get('alternative_field_groups')
        if groups:
            normalized=[]
            for g in groups:
                if isinstance(g, list):
                    normalized.append({'required_fields': g, 'required_operators': q.get('required_operators', {})})
                else:
                    normalized.append({'required_fields': g.get('fields', g.get('required_fields', [])), 'required_operators': g.get('required_operators', q.get('required_operators', {}))})
            return normalized
        return [{'required_fields': q.get('required_fields', []), 'required_operators': q.get('required_operators', {})}]

    def realize_query(self, q: Dict[str,Any]) -> Dict[str,Any]:
        scored=[]
        for form in self.forms:
            for group in self.query_groups(q):
                res=self.evaluate_group(q, group, form)
                score=(1 if res['query_realizable'] else 0, res['field_recall'], res['operator_support'], res['context_support'], float(form.get('utility') or 0))
                scored.append((score, form, group, res))
        scored.sort(key=lambda x:x[0], reverse=True)
        _, form, group, res=scored[0]
        select_clause=self.build_select_clause(res['field_mappings'])
        where_clause=self.build_where_clause(q, res['field_mappings'])
        aql=self.build_aql(select_clause, where_clause)
        return {
            'query_id': q.get('query_id'), 'query_name': q.get('query_name'), 'query_complexity': q.get('query_complexity'), 'category': q.get('category'),
            'selected_form_id': form.get('form_id'), 'selected_form_group': form.get('form_group'),
            'field_recall': res['field_recall'], 'operator_support': res['operator_support'], 'context_support': res['context_support'],
            'query_realizable': res['query_realizable'], 'missing_fields': '; '.join(res['missing_fields']), 'unsupported_fields': '; '.join(res['unsupported_fields']),
            'selected_required_fields': '; '.join(group.get('required_fields', [])), 'aql': aql
        }

    def evaluate_group(self, q: Dict[str,Any], group: Dict[str,Any], form: Dict[str,Any]) -> Dict[str,Any]:
        fields=collect_form_fields(form)
        req_fields=group.get('required_fields', [])
        req_ops=group.get('required_operators', {})
        mappings=[]; missing=[]; unsupported=[]; matched=0; op_ok=0; op_total=0
        for rf in req_fields:
            ops=req_ops.get(rf, [])
            if isinstance(ops,str): ops=[ops]
            op_total += len(ops)
            candidates=[f for f in fields if alias_match(rf, f.get('name',''), self.aliases)]
            def cand_key(f):
                compatible = 1 if (not ops or any(operator_match(o, f.get('operator',''), f.get('datatype')) for o in ops)) else 0
                filter_pref = 1 if f.get('aqf_role')=='filter' else 0
                return (compatible, filter_pref, float(f.get('score') or 0))
            candidates=sorted(candidates, key=cand_key, reverse=True)
            if not candidates:
                missing.append(rf); mappings.append({'required_field':rf,'matched':False}); continue
            best=candidates[0]; matched += 1
            compatible = True if not ops else any(operator_match(o, best.get('operator',''), best.get('datatype')) for o in ops)
            if compatible: op_ok += len(ops)
            else: unsupported.append(rf)
            mappings.append({'required_field':rf,'matched':True,'name':best.get('name'),'operator':best.get('operator'),'datatype':best.get('datatype'),'path':best.get('path'),'role':best.get('aqf_role'),'operator_supported':compatible})
        fr=matched/len(req_fields) if req_fields else 1.0
        os=op_ok/op_total if op_total else 1.0
        cs=self.context_support(q, form)
        realizable = fr>=1.0 and os>=1.0 and (cs>=1.0 or not self.strict_context)
        return {'field_recall':fr,'operator_support':os,'context_support':cs,'query_realizable':realizable,'missing_fields':missing,'unsupported_fields':unsupported,'field_mappings':mappings}

    def context_support(self, q: Dict[str,Any], form: Dict[str,Any]) -> float:
        ctx=q.get('required_contexts', [])
        if not ctx: return 1.0
        blob=' '.join([str(form.get('form_group',''))]+[str(f.get('ui_group',''))+' '+str(f.get('path','')) for f in collect_form_fields(form)])
        # relaxed context: if required field matched, context is mostly informational; still report ratio.
        m=sum(1 for c in ctx if norm(c) in norm(blob) or any(t in norm(blob) for t in alias_terms(c, self.aliases)))
        return m/len(ctx)

    def path_expr(self, m: Dict[str,Any]) -> str:
        p=m.get('path') or f"DEMOGRAPHIC::{sid(m.get('required_field'))}"
        if p.startswith('DEMOGRAPHIC::'): return p
        return 'c' + ''.join('/'+seg.split('|')[0]+'['+(seg.split('|')[2] if len(seg.split('|'))>2 else '*')+']' for seg in p.split('/') if seg)

    def build_select_clause(self, maps):
        cols=['e/ehr_id/value AS ehr_id']
        for m in maps:
            if m.get('matched'):
                cols.append(f"{self.path_expr(m)}/value AS {sid(m.get('required_field'))}")
        return ',\n  '.join(cols)

    def build_where_clause(self, q, maps):
        cons=q.get('constraints', {}) or {}; preds=[]
        for m in maps:
            if not m.get('matched'): continue
            c=cons.get(m.get('required_field'))
            path=self.path_expr(m)+'/value'
            if isinstance(c, dict):
                op=c.get('operator')
                if op in {'after','>'}: preds.append(f"{path} > '{c.get('value')}'")
                elif op in {'before','<'}: preds.append(f"{path} < '{c.get('value')}'")
                elif op in {'between','range'}: preds.append(f"{path} >= '{c.get('from')}' AND {path} <= '{c.get('to')}'")
                elif 'value' in c: preds.append(f"{path} = '{c.get('value')}'")
            elif c is not None:
                if m.get('operator')=='contains': preds.append(f"LOWER({path}) MATCHES '.*{str(c).lower()}.*'")
                else: preds.append(f"{path} = '{c}'")
            else:
                preds.append(f"{path} IS NOT NULL")
        return '\n  AND '.join(preds) if preds else '1 = 1'

    def build_aql(self, select, where):
        return f"SELECT\n  {select}\nFROM EHR e\nCONTAINS COMPOSITION c\nWHERE\n  {where}\n"

    def save_outputs(self, outdir: str|Path):
        out=Path(outdir); out.mkdir(parents=True, exist_ok=True); (out/'aql').mkdir(exist_ok=True)
        summary=self.summary()
        (out/'realized_queries.json').write_text(json.dumps({'metadata':summary,'realized_queries':self.realized}, indent=2, ensure_ascii=False), encoding='utf-8')
        cols=['query_id','query_name','query_complexity','category','selected_form_id','selected_form_group','field_recall','operator_support','context_support','query_realizable','missing_fields','unsupported_fields','selected_required_fields']
        with open(out/'realized_queries.csv','w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows([{k:r.get(k) for k in cols} for r in self.realized])
        with open(out/'query_realization_summary.csv','w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f, fieldnames=list(summary.keys())); w.writeheader(); w.writerow(summary)
        for r in self.realized:
            (out/'aql'/f"{sid(r.get('query_id'))}.aql").write_text(r.get('aql',''), encoding='utf-8')

    def summary(self):
        n=len(self.realized); cats={}; comps={}
        for r in self.realized:
            val=1 if r.get('query_realizable') else 0
            cats.setdefault(r.get('category'), []).append(val); comps.setdefault(r.get('query_complexity'), []).append(val)
        return {'query_count':n,'realizable_queries':sum(1 for r in self.realized if r.get('query_realizable')),'query_realization_rate':sum(1 for r in self.realized if r.get('query_realizable'))/max(n,1),'avg_field_recall':sum(float(r.get('field_recall') or 0) for r in self.realized)/max(n,1),'avg_operator_support':sum(float(r.get('operator_support') or 0) for r in self.realized)/max(n,1),'avg_context_support':sum(float(r.get('context_support') or 0) for r in self.realized)/max(n,1),'category_realization':json.dumps({k:sum(v)/len(v) for k,v in cats.items()}, ensure_ascii=False),'complexity_realization':json.dumps({k:sum(v)/len(v) for k,v in comps.items()}, ensure_ascii=False)}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--aqf_forms_json', required=True); ap.add_argument('--workload_json', required=True); ap.add_argument('--output_dir', required=True)
    ap.add_argument('--aliases_json', default=None); ap.add_argument('--strict_context', action='store_true')
    args=ap.parse_args()
    r=AQFQueryRealizerV2(args.aliases_json, args.strict_context); r.load_inputs(args.aqf_forms_json,args.workload_json); r.realize_all(); r.save_outputs(args.output_dir)
    s=r.summary(); print('AQF query realization v2 complete.'); print(f"Queries: {s['query_count']}"); print(f"Realizable: {s['realizable_queries']}"); print(f"Realization rate: {s['query_realization_rate']:.3f}")

if __name__=='__main__': main()
