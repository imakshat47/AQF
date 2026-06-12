#!/usr/bin/env python3
"""
demographic_form_augmenter.py

Add an explicit demographic AQF form to generated AQF forms.

This is a bridge module: it does NOT claim demographics were extracted from the current
COMPOSITION graph. It adds declared external demographic fields so benchmark evaluation
can represent the planned demographic integration stage.

Later, replace the placeholder DEMOGRAPHIC::* paths with paths from your demographic
source, MPI, PERSON service, or source-specific patient table.
"""
from __future__ import annotations
import argparse, json, csv, re
from pathlib import Path
from typing import Any, Dict

def sid(x):
    s=re.sub(r'[^a-z0-9]+','_',str(x).lower()).strip('_')
    return s or 'field'

def demographic_fields():
    return [
        {'name':'gender','datatype':'DV_CODED_TEXT','operator':'equals','control_type':'dropdown','path':'DEMOGRAPHIC::gender'},
        {'name':'birth date','datatype':'DV_DATE','operator':'date_range','control_type':'date_range_picker','path':'DEMOGRAPHIC::birth_date'},
        {'name':'nationality','datatype':'DV_CODED_TEXT','operator':'equals','control_type':'dropdown','path':'DEMOGRAPHIC::nationality'},
        {'name':'educational level','datatype':'DV_CODED_TEXT','operator':'equals','control_type':'dropdown','path':'DEMOGRAPHIC::educational_level'},
    ]

def make_field(f: Dict[str,Any], role='filter'):
    return {'field_id':f'{role}_{sid(f["name"])}_demographic','canonical_id':f'demographic_{sid(f["name"])}','name':f['name'],'role':role,'datatype':f['datatype'],'operator':f['operator'] if role=='filter' else 'project','operator_class':'filter' if role=='filter' else 'projection','control_type':f['control_type'] if role=='filter' else 'result_column','score':1.0,'queriability':1.0,'path':f['path'],'archetype_node_id':None,'archetype_id':'EXTERNAL-DEMOGRAPHIC','template_id':'external-demographic','required':False,'ui_group':'Demographic Data','external_source':True}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--aqf_forms_json', required=True); ap.add_argument('--output_dir', required=True); ap.add_argument('--include_outputs', action='store_true')
    args=ap.parse_args()
    payload=json.loads(Path(args.aqf_forms_json).read_text(encoding='utf-8'))
    forms=payload.get('aqf_forms', [])
    filters=[make_field(f,'filter') for f in demographic_fields()]
    outputs=[make_field(f,'output') for f in demographic_fields()] if args.include_outputs else []
    form={'form_id':'aqf_demographic_data_external','source_operator_aware_form_id':'external_demographic','canonical_form_id':'external_demographic','form_group':'Demographic data','title':'AQF Query Form - Demographic data','description':'External demographic AQF form declared for benchmark and future demographic-source integration.','filters':filters,'outputs':outputs,'relationships':[],'utility':sum(f['score'] for f in filters+outputs),'complexity':len(filters)+len(outputs),'max_depth':0,'selected_field_count':len(filters)+len(outputs),'relationship_count':0,'external_demographic_form':True}
    forms=[f for f in forms if f.get('form_id')!='aqf_demographic_data_external']+[form]
    payload['aqf_forms']=forms; payload.setdefault('metadata',{})['demographic_augmented']=True; payload['metadata']['form_count']=len(forms)
    out=Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    (out/'aqf_forms.json').write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    with open(out/'aqf_forms_summary.csv','w',newline='',encoding='utf-8') as f:
        cols=['form_id','form_group','utility','complexity','max_depth','selected_field_count','filter_count','output_count','relationship_count','external_demographic_form']
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader()
        for fm in forms:
            w.writerow({'form_id':fm.get('form_id'),'form_group':fm.get('form_group'),'utility':fm.get('utility'),'complexity':fm.get('complexity'),'max_depth':fm.get('max_depth'),'selected_field_count':fm.get('selected_field_count'),'filter_count':len(fm.get('filters',[])),'output_count':len(fm.get('outputs',[])),'relationship_count':fm.get('relationship_count',0),'external_demographic_form':fm.get('external_demographic_form',False)})
    print(f'Demographic form added. Forms: {len(forms)}. Output: {out}')

if __name__=='__main__': main()
