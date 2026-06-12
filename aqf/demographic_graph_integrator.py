#!/usr/bin/env python3
"""
demographic_graph_integrator.py

Create a true merged AQF model:
  clinical COMPOSITION graph + demographic schema graph -> merged AQF graph

This replaces the temporary DEMOGRAPHIC::* bridge with a first-class demographic
integration stage. It can ingest demographic metadata from:
  1. a supplied demographic CSV, or
  2. a declared default demographic schema if no CSV exists yet.

Outputs:
  demographic_schema_graph.json
  merged_schema_graph.json
  merged_demographic_summary.csv
  demographic_mapping.json

The merged graph can be used by canonical_structure_generator.py.
"""
from __future__ import annotations

import argparse, csv, json, re
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_DEMOGRAPHIC_FIELDS = [
    {"name":"gender", "datatype":"DV_CODED_TEXT", "operator_hint":"equals", "source_path":"DEMOGRAPHIC::gender"},
    {"name":"birth date", "datatype":"DV_DATE", "operator_hint":"date_range", "source_path":"DEMOGRAPHIC::birth_date"},
    {"name":"nationality", "datatype":"DV_CODED_TEXT", "operator_hint":"equals", "source_path":"DEMOGRAPHIC::nationality"},
    {"name":"educational level", "datatype":"DV_CODED_TEXT", "operator_hint":"equals", "source_path":"DEMOGRAPHIC::educational_level"},
]

def slug(x: Any) -> str:
    s=re.sub(r'[^a-z0-9]+','_',str(x).lower()).strip('_')
    return s or 'field'

def load_json(path: str|Path) -> Dict[str,Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))

def infer_datatype(series_values: List[str], field_name: str) -> str:
    n=field_name.lower()
    if 'date' in n or 'birth' in n: return 'DV_DATE'
    if 'age' in n or 'count' in n: return 'DV_COUNT'
    return 'DV_CODED_TEXT'

def fields_from_csv(path: str|Path) -> List[Dict[str,Any]]:
    p=Path(path)
    with p.open('r', encoding='utf-8-sig', newline='') as f:
        reader=csv.DictReader(f)
        rows=list(reader)
        headers=reader.fieldnames or []
    fields=[]
    for h in headers:
        if h.lower() in {'patient_id','subject_id','ehr_id','id'}:
            continue
        vals=[str(r.get(h,'')) for r in rows[:200] if r.get(h,'') not in (None,'')]
        dtype=infer_datatype(vals,h)
        op='date_range' if dtype=='DV_DATE' else ('range' if dtype=='DV_COUNT' else 'equals')
        fields.append({"name":h.replace('_',' '), "datatype":dtype, "operator_hint":op, "source_path":f"DEMOGRAPHIC::{slug(h)}"})
    return fields

def demographic_graph(fields: List[Dict[str,Any]]) -> Dict[str,Any]:
    nodes=[]; edges=[]
    root_id='demographic_root::demographic_data'
    nodes.append({"node_id":root_id,"name":"Demographic data","rm_type":"DEMOGRAPHIC_ROOT","aqf_type":"root","archetype_node_id":None,"archetype_id":"EXTERNAL-DEMOGRAPHIC","template_id":"external-demographic","path":"DEMOGRAPHIC::root","datatype":None,"records_present":[],"weight":1.0,"queriability":1.0})
    for f in fields:
        nid=f"demographic::{slug(f['name'])}"
        nodes.append({"node_id":nid,"name":f['name'],"rm_type":"DEMOGRAPHIC_FIELD","aqf_type":"leaf","archetype_node_id":None,"archetype_id":"EXTERNAL-DEMOGRAPHIC","template_id":"external-demographic","path":f.get('source_path') or f"DEMOGRAPHIC::{slug(f['name'])}","datatype":f.get('datatype'),"records_present":[],"weight":1.0,"queriability":1.0,"operator_hint":f.get('operator_hint')})
        edges.append({"source":root_id,"target":nid,"edge_type":"containment","weight":1.0,"structural_connectivity":1.0,"containment_connectivity":1.0,"cooccurrence_connectivity":0.0})
    # Add demographic co-occurrence edges so fields stay connected as a form group.
    leaf_ids=[n['node_id'] for n in nodes if n.get('aqf_type')=='leaf']
    for i,a in enumerate(leaf_ids):
        for b in leaf_ids[i+1:]:
            edges.append({"source":a,"target":b,"edge_type":"cooccurrence","weight":0.75,"structural_connectivity":0.75,"containment_connectivity":0.5,"cooccurrence_connectivity":1.0})
            edges.append({"source":b,"target":a,"edge_type":"cooccurrence","weight":0.75,"structural_connectivity":0.75,"containment_connectivity":0.5,"cooccurrence_connectivity":1.0})
    return {"metadata":{"graph_type":"demographic_schema_graph","node_count":len(nodes),"edge_count":len(edges)},"nodes":nodes,"edges":edges}

def merge_graphs(clinical: Dict[str,Any], demo: Dict[str,Any]) -> Dict[str,Any]:
    nodes=list(clinical.get('nodes',[]))+list(demo.get('nodes',[]))
    edges=list(clinical.get('edges',[]))+list(demo.get('edges',[]))
    # weak bridge from demographic root to each clinical composition root
    demo_root='demographic_root::demographic_data'
    clinical_roots=[n['node_id'] for n in clinical.get('nodes',[]) if n.get('aqf_type')=='root' or n.get('rm_type')=='COMPOSITION']
    for cr in clinical_roots:
        edges.append({"source":demo_root,"target":cr,"edge_type":"demographic_clinical_bridge","weight":0.3,"structural_connectivity":0.3,"containment_connectivity":0.0,"cooccurrence_connectivity":0.3})
        edges.append({"source":cr,"target":demo_root,"edge_type":"demographic_clinical_bridge","weight":0.3,"structural_connectivity":0.3,"containment_connectivity":0.0,"cooccurrence_connectivity":0.3})
    meta=dict(clinical.get('metadata',{}))
    meta.update({"merged_demographic":True,"node_count":len(nodes),"edge_count":len(edges),"demographic_nodes":len(demo.get('nodes',[])),"demographic_edges":len(demo.get('edges',[]))})
    return {"metadata":meta,"nodes":nodes,"edges":edges}

def main():
    ap=argparse.ArgumentParser(description='Merge demographic schema fields into AQF schema graph.')
    ap.add_argument('--clinical_graph_json', required=True)
    ap.add_argument('--output_dir', required=True)
    ap.add_argument('--demographic_csv', default=None)
    ap.add_argument('--demographic_mapping_json', default=None)
    args=ap.parse_args()
    out=Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    if args.demographic_csv:
        fields=fields_from_csv(args.demographic_csv)
    elif args.demographic_mapping_json and Path(args.demographic_mapping_json).exists():
        fields=load_json(args.demographic_mapping_json).get('fields', DEFAULT_DEMOGRAPHIC_FIELDS)
    else:
        fields=DEFAULT_DEMOGRAPHIC_FIELDS
    demo=demographic_graph(fields)
    clinical=load_json(args.clinical_graph_json)
    merged=merge_graphs(clinical,demo)
    (out/'demographic_schema_graph.json').write_text(json.dumps(demo,indent=2,ensure_ascii=False),encoding='utf-8')
    (out/'merged_schema_graph.json').write_text(json.dumps(merged,indent=2,ensure_ascii=False),encoding='utf-8')
    (out/'demographic_mapping.json').write_text(json.dumps({"fields":fields},indent=2,ensure_ascii=False),encoding='utf-8')
    with open(out/'merged_demographic_summary.csv','w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['name','datatype','operator_hint','source_path']); w.writeheader(); w.writerows(fields)
    print('Demographic graph integration complete.')
    print(f'Demographic fields: {len(fields)}')
    print(f'Merged nodes: {len(merged["nodes"])}')
    print(f'Merged edges: {len(merged["edges"])}')
    print(f'Output: {out}')
if __name__=='__main__': main()
