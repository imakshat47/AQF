#!/usr/bin/env python3
"""
aqf_operator_repair.py

Repair/generated AQF form operators using an ORBDA/openEHR datatype-aware operator map.

Main fixes:
  - infer missing datatypes from field names/paths;
  - replace weak is_present operators with datatype-compatible primary operators;
  - attach compatible_operators to each field for downstream query realization;
  - produce repair report for auditability.
"""
from __future__ import annotations
import argparse, csv, json, re
from pathlib import Path
from typing import Any, Dict

def norm(x):
    return re.sub(r'[^a-z0-9]+',' ',str(x or '').lower()).strip()

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

def field_key(name): return norm(name)

def infer_datatype(field: Dict[str,Any], mapping: Dict[str,Any]) -> str:
    name=field_key(field.get('name'))
    if name in mapping.get('field_overrides',{}):
        return mapping['field_overrides'][name].get('datatype') or field.get('datatype') or ''
    dtype=field.get('datatype')
    if dtype: return dtype
    blob=norm(str(field.get('name',''))+' '+str(field.get('path','')))
    if 'date' in blob or 'birth' in blob: return 'DV_DATE'
    if 'duration' in blob or 'count' in blob or 'fields insertions' in blob or 'age' in blob: return 'DV_COUNT'
    if 'indicator' in blob or 'death' in blob or 'boolean' in blob: return 'DV_BOOLEAN'
    if 'schema' in blob or 'staging' in blob: return 'DV_TEXT'
    return 'DV_CODED_TEXT'

def preferred_filter(name, dtype, mapping):
    nk=field_key(name)
    if nk in mapping.get('field_overrides',{}):
        return mapping['field_overrides'][nk].get('preferred_filter') or mapping['datatype_operators'].get(dtype,{}).get('preferred_filter','equals')
    return mapping['datatype_operators'].get(dtype,{}).get('preferred_filter','equals')

def repair_field(field, role, mapping):
    before_dtype=field.get('datatype')
    before_op=field.get('operator')
    dtype=infer_datatype(field,mapping)
    ops=mapping.get('datatype_operators',{}).get(dtype,{})
    compatible=ops.get('filter' if role=='filter' else 'output', [])
    field['datatype']=dtype
    field['compatible_operators']=compatible
    changed=False; reason=[]
    if not before_dtype:
        changed=True; reason.append('inferred_datatype')
    if role=='filter':
        pref=preferred_filter(field.get('name'), dtype, mapping)
        if not before_op or before_op=='is_present' or before_op not in compatible:
            field['operator']=pref
            changed=True; reason.append(f'operator_repaired_to_{pref}')
    else:
        if not before_op or before_op not in compatible:
            field['operator']='project'
            changed=True; reason.append('output_operator_repaired_to_project')
    return changed, ';'.join(reason), before_dtype, before_op, field.get('datatype'), field.get('operator')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--aqf_forms_json', required=True)
    ap.add_argument('--operator_mapping_json', required=True)
    ap.add_argument('--output_dir', required=True)
    args=ap.parse_args()
    payload=load(args.aqf_forms_json); mapping=load(args.operator_mapping_json)
    report=[]
    for form in payload.get('aqf_forms',[]):
        for role_key, role in [('filters','filter'),('outputs','output')]:
            for f in form.get(role_key,[]):
                changed, reason, bd, bo, ad, ao=repair_field(f,role,mapping)
                if changed:
                    report.append({'form_id':form.get('form_id'),'form_group':form.get('form_group'),'field':f.get('name'),'role':role,'before_datatype':bd,'after_datatype':ad,'before_operator':bo,'after_operator':ao,'reason':reason})
    payload.setdefault('metadata',{})['operator_repaired']=True
    payload['metadata']['operator_repair_count']=len(report)
    out=Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    (out/'aqf_forms.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
    with open(out/'operator_repair_report.csv','w',newline='',encoding='utf-8') as fp:
        cols=['form_id','form_group','field','role','before_datatype','after_datatype','before_operator','after_operator','reason']
        w=csv.DictWriter(fp,fieldnames=cols); w.writeheader(); w.writerows(report)
    print('AQF operator repair complete.')
    print(f'Repaired fields: {len(report)}')
    print(f'Output: {out}')
if __name__=='__main__': main()
