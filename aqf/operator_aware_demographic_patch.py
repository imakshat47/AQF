#!/usr/bin/env python3
"""
operator_aware_demographic_patch.py

Post-process operator_aware_forms.json to add an operator-aware Demographic data form
from demographic_schema_graph.json.
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

def slug(x): return re.sub(r'[^a-z0-9]+','_',str(x).lower()).strip('_') or 'field'
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

def input_operator(dtype):
    if dtype=='DV_DATE': return {'operator':'date_range','operator_class':'filter','compatibility':1.0,'operator_adjusted_queriability':1.0,'control_type':'date_range_picker','reason':'Demographic date supports temporal filtering.'}
    if dtype=='DV_COUNT': return {'operator':'range','operator_class':'filter','compatibility':1.0,'operator_adjusted_queriability':1.0,'control_type':'range_slider','reason':'Demographic numeric field supports range filtering.'}
    return {'operator':'equals','operator_class':'filter','compatibility':1.0,'operator_adjusted_queriability':1.0,'control_type':'dropdown','reason':'Demographic coded/text field supports equality filtering.'}

def output_operator(dtype):
    return {'operator':'project','operator_class':'projection','compatibility':1.0,'operator_adjusted_queriability':1.0,'control_type':'result_column','reason':'Demographic field is useful as a result attribute.'}

def make_field(leaf, role):
    cid=f"form_element_{slug(leaf['name'])}_demographic"
    dtype=leaf.get('datatype')
    if role=='input':
        op=input_operator(dtype)
        return {"canonical_id":cid,"name":leaf['name'],"datatype":dtype,"queriability":1.0,"best_input_operator":op['operator'],"best_input_score":1.0,"input_operators":[op],"path":leaf.get('path'),"archetype_node_id":None,"archetype_id":"EXTERNAL-DEMOGRAPHIC","template_id":"external-demographic"}
    op=output_operator(dtype)
    return {"canonical_id":cid,"name":leaf['name'],"datatype":dtype,"queriability":1.0,"best_output_operator":op['operator'],"best_output_score":1.0,"output_operators":[op],"path":leaf.get('path'),"archetype_node_id":None,"archetype_id":"EXTERNAL-DEMOGRAPHIC","template_id":"external-demographic"}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--operator_aware_forms_json', required=True)
    ap.add_argument('--demographic_schema_graph_json', required=True)
    ap.add_argument('--output_dir', required=True)
    args=ap.parse_args()
    payload=load(args.operator_aware_forms_json); demo=load(args.demographic_schema_graph_json)
    leaves=[n for n in demo.get('nodes',[]) if n.get('aqf_type')=='leaf']
    form={"operator_aware_form_id":"oaf_demographic_data_external","canonical_form_id":"cf_demographic_data_external","source_tree_id":"ct_demographic_data_external","form_group":"Demographic data","root_canonical_id":"form_group_demographic_data_external","operator_input_tree":[make_field(x,'input') for x in leaves],"operator_output_tree":[make_field(x,'output') for x in leaves],"operator_relationship_tree":[],"input_field_count":len(leaves),"output_field_count":len(leaves),"operator_form_utility":len(leaves)*2,"max_depth":1}
    forms=payload.get('operator_aware_forms', [])
    forms=[f for f in forms if f.get('operator_aware_form_id')!='oaf_demographic_data_external']+[form]
    payload['operator_aware_forms']=forms; payload.setdefault('metadata',{})['operator_aware_form_count']=len(forms); payload['metadata']['demographic_operator_aware_added']=True
    out=Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    (out/'operator_aware_forms.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
    print(f'Demographic operator-aware form added. Forms: {len(forms)}. Output: {out}')
if __name__=='__main__': main()
