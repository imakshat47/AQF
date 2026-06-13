#!/usr/bin/env python3
"""
canonical_structure_generator_demographic_patch.py

Post-process canonical_forms.json to add a first-class Demographic data canonical form
from demographic_schema_graph.json created by demographic_graph_integrator.py.

This avoids changing your original canonical generator while allowing a complete AQF
pipeline with clinical + demographic forms.
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from typing import Any, Dict

def slug(x):
    return re.sub(r'[^a-z0-9]+','_',str(x).lower()).strip('_') or 'field'

def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))

def make_form(demo_graph: Dict[str,Any]) -> Dict[str,Any]:
    leaves=[n for n in demo_graph.get('nodes',[]) if n.get('aqf_type')=='leaf']
    nodes=[]; input_ids=[]; output_ids=[]
    root_id='form_group_demographic_data_external'
    nodes.append({"canonical_id":root_id,"name":"Demographic data","canonical_type":"form_group","path":"DEMOGRAPHIC::root","datatype":None,"queriability":1.0})
    for leaf in leaves:
        cid=f"form_element_{slug(leaf['name'])}_demographic"
        item={"canonical_id":cid,"name":leaf['name'],"canonical_type":"form_element","path":leaf.get('path'),"datatype":leaf.get('datatype'),"queriability":1.0,"archetype_node_id":None,"archetype_id":"EXTERNAL-DEMOGRAPHIC","template_id":"external-demographic"}
        nodes.append(item); input_ids.append(cid); output_ids.append(cid)
    rel=[]
    for cid in input_ids:
        rel.append({"source":root_id,"target":cid,"edge_type":"canonical_containment","source_schema_edge_type":"containment","weight":1.0,"structural_connectivity":1.0,"containment_connectivity":1.0,"cooccurrence_connectivity":0.0})
    return {"canonical_form_id":"cf_demographic_data_external","source_tree_id":"ct_demographic_data_external","form_group":"Demographic data","root_canonical_id":root_id,"input_tree":input_ids,"output_tree":output_ids,"relationship_tree":rel,"input_tree_nodes":nodes,"output_tree_nodes":nodes,"max_depth":1,"utility":len(input_ids)}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--canonical_forms_json', required=True)
    ap.add_argument('--demographic_schema_graph_json', required=True)
    ap.add_argument('--output_dir', required=True)
    args=ap.parse_args()
    payload=load(args.canonical_forms_json); demo=load(args.demographic_schema_graph_json)
    forms=payload.get('canonical_forms', [])
    forms=[f for f in forms if f.get('canonical_form_id')!='cf_demographic_data_external']+[make_form(demo)]
    payload['canonical_forms']=forms; payload.setdefault('metadata',{})['canonical_form_count']=len(forms); payload['metadata']['demographic_canonical_added']=True
    out=Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    (out/'canonical_forms.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
    print(f'Demographic canonical form added. Canonical forms: {len(forms)}. Output: {out}')
if __name__=='__main__': main()
