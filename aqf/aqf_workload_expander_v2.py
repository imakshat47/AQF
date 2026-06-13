#!/usr/bin/env python3
"""
aqf_workload_expander_v2.py

Generate expanded AQF workloads.
Default semi-curated count is now 154.
"""
from __future__ import annotations
import argparse, csv, json, random
from pathlib import Path
from typing import Any, Dict, List

FIELD_CATALOG = {
    "demographic": [
        {"field":"gender", "operator":"equals", "values":["Male","Female"]},
        {"field":"birth date", "operator":"date_range", "values":[{"operator":"before","value":"1970-01-01"},{"operator":"after","value":"1980-01-01"},{"operator":"between","from":"1960-01-01","to":"1990-12-31"}]},
        {"field":"nationality", "operator":"equals", "values":["Brazilian","Portuguese","Other"]},
        {"field":"educational level", "operator":"equals", "values":["Higher education","Primary education","Secondary education"]},
    ],
    "diagnosis": [
        {"field":"Problem", "operator":"equals", "values":["breast cancer","lung cancer","colon cancer","prostate cancer"]},
        {"field":"Secondary Diagnosis", "operator":"equals", "values":["hypertension","diabetes","anemia"]},
        {"field":"topography", "operator":"equals", "values":["colon","breast","lung","prostate"]},
        {"field":"Clinical staging", "operator":"equals", "values":["Stage I","Stage II","Stage III","Stage IV"]},
    ],
    "treatment_procedure": [
        {"field":"Procedure", "operator":"equals", "values":["biopsy","surgery","radiotherapy","chemotherapy"]},
        {"field":"schema", "operator":"contains", "values":["FOLFOX","FOLFIRI","AC-T","cisplatin"]},
        {"field":"duration of treatment", "operator":"range", "values":[{"operator":">","value":30,"unit":"days"},{"operator":">","value":60,"unit":"days"},{"operator":">","value":90,"unit":"days"}]},
        {"field":"fields/insertions 1", "operator":"range", "values":[{"operator":">","value":0}]},
        {"field":"fields/insertions 2", "operator":"range", "values":[{"operator":">","value":0}]},
        {"field":"irradiated area 1", "operator":"equals", "values":["pelvis","thorax","abdomen"]},
    ],
    "temporal": [
        {"field":"issue date", "operator":"date_range", "values":[{"operator":"after","value":"2022-01-01"},{"operator":"between","from":"2021-01-01","to":"2022-12-31"}]},
        {"field":"date of discharge", "operator":"date_range", "values":[{"operator":"between","from":"2023-01-01","to":"2023-01-31"},{"operator":"after","value":"2022-06-01"}]},
        {"field":"date of beginning of chemotherapy", "operator":"date_range", "values":[{"operator":"after","value":"2021-06-01"},{"operator":"after","value":"2022-01-01"}]},
        {"field":"date of pathological identification", "operator":"date_range", "values":[{"operator":"between","from":"2020-01-01","to":"2020-12-31"},{"operator":"after","value":"2019-01-01"}]},
    ],
    "administrative": [
        {"field":"State", "operator":"equals", "values":["São Paulo","Rio de Janeiro","Minas Gerais"]},
        {"field":"healthcare unit", "operator":"equals", "values":["Unit A","Unit B","Unit C"]},
        {"field":"reason for encounter", "operator":"equals", "values":["treatment","diagnosis","follow-up"]},
    ]
}
CATEGORY_CONTEXTS = {
    "demographic":["Demographic data"], "diagnosis":["Problem/Diagnosis"],
    "treatment_procedure":["Procedure undertaken","chemotherapy"], "temporal":["HCPA"],
    "administrative":["General data"],
    "cross_context":["Demographic data","Problem/Diagnosis","Procedure undertaken","chemotherapy","HCPA"],
}
COMPLEXITY_BY_FIELD_COUNT={1:"easy",2:"medium",3:"hard",4:"hard"}

def load_base(path: str|Path) -> List[Dict[str,Any]]:
    payload=json.loads(Path(path).read_text(encoding='utf-8'))
    return payload if isinstance(payload,list) else payload.get('queries',[])

def constraint_for(item: Dict[str,Any]) -> Any:
    return random.choice(item['values'])

def make_query(qid, name, fields, category, description_prefix):
    required=[f['field'] for f in fields]
    req_ops={f['field']:[f['operator']] for f in fields}
    constraints={f['field']:constraint_for(f) for f in fields}
    return {"query_id":qid,"query_name":name,"query_complexity":COMPLEXITY_BY_FIELD_COUNT.get(min(len(fields),4),'hard'),"category":category,"description":f"{description_prefix}: filter records by "+", ".join(required)+".","required_fields":required,"required_operators":req_ops,"required_contexts":CATEGORY_CONTEXTS.get(category,[]),"constraints":constraints}

def add_alternative_groups(q):
    fields=set(q.get('required_fields',[]))
    if {'birth date','patient age','Problem'}.issubset(fields):
        q['alternative_required_field_groups']=[
            {"fields":["patient age","Problem"],"required_operators":{"patient age":["range"],"Problem":["equals"]}},
            {"fields":["birth date","Problem"],"required_operators":{"birth date":["date_range"],"Problem":["equals"]}}
        ]
    if {'fields/insertions 1','fields/insertions 2'}.issubset(fields):
        q['alternative_required_field_groups']=[
            {"fields":["fields/insertions 1"],"required_operators":{"fields/insertions 1":["range"]}},
            {"fields":["fields/insertions 2"],"required_operators":{"fields/insertions 2":["range"]}},
            {"fields":["irradiated area 1"],"required_operators":{"irradiated area 1":["equals"]}}
        ]
    return q

def generate_curated(base, target):
    out=[add_alternative_groups(dict(q)) for q in base]
    i=len(out)+1
    # Balanced expansion: category singles, pairs, then cross-context.
    for cat, fs in FIELD_CATALOG.items():
        for f in fs:
            if len(out)>=target: return out[:target]
            out.append(make_query(f"J{str(i).zfill(3)}",f"{cat} query by {f['field']}",[f],cat,"Single-field semi-curated query")); i+=1
        for a_idx,a in enumerate(fs):
            for b in fs[a_idx+1:]:
                if len(out)>=target: return out[:target]
                out.append(make_query(f"J{str(i).zfill(3)}",f"{cat} query by {a['field']} and {b['field']}",[a,b],cat,"Two-field semi-curated query")); i+=1
    groups=list(FIELD_CATALOG.values())
    while len(out)<target:
        chosen=[random.choice(g) for g in random.sample(groups,k=random.choice([2,3,4]))]
        out.append(add_alternative_groups(make_query(f"J{str(i).zfill(3)}","Cross-context semi-curated query",chosen,"cross_context","Cross-context semi-curated query"))); i+=1
    return out[:target]

def generate_synthetic(count):
    out=[]; cats=list(FIELD_CATALOG.keys())
    for i in range(1,count+1):
        if random.random()<0.45:
            groups=random.sample(list(FIELD_CATALOG.values()),k=random.choice([2,3,4]))
            fields=[random.choice(g) for g in groups]; cat='cross_context'
        else:
            cat=random.choice(cats); fields=random.sample(FIELD_CATALOG[cat],k=min(random.choice([1,1,2,2,3]),len(FIELD_CATALOG[cat])))
        out.append(add_alternative_groups(make_query(f"SYN{str(i).zfill(5)}","Synthetic user-like AQF query",fields,cat,"Synthetic user-like EHR search")))
    return out

def save(path, name, queries, synthetic):
    path.write_text(json.dumps({"metadata":{"name":name,"version":"2.0","query_count":len(queries),"synthetic":synthetic},"queries":queries},indent=2,ensure_ascii=False),encoding='utf-8')

def summarize(outdir, curated, synthetic):
    rows=[]
    for label,qs in [('curated',curated),('synthetic',synthetic)]:
        cats={}; comps={}
        for q in qs:
            cats[q['category']]=cats.get(q['category'],0)+1
            comps[q['query_complexity']]=comps.get(q['query_complexity'],0)+1
        rows.append({'workload':label,'query_count':len(qs),'category_distribution':json.dumps(cats,ensure_ascii=False),'complexity_distribution':json.dumps(comps,ensure_ascii=False)})
    with open(outdir/'workload_generation_summary.csv','w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['workload','query_count','category_distribution','complexity_distribution']); w.writeheader(); w.writerows(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--base_workload_json',required=True); ap.add_argument('--output_dir',required=True)
    ap.add_argument('--curated_count',type=int,default=154); ap.add_argument('--synthetic_count',type=int,default=10000); ap.add_argument('--seed',type=int,default=42)
    args=ap.parse_args(); random.seed(args.seed)
    out=Path(args.output_dir); out.mkdir(parents=True,exist_ok=True)
    base=load_base(args.base_workload_json)
    curated=generate_curated(base,args.curated_count); synthetic=generate_synthetic(args.synthetic_count)
    save(out/'benchmark_workload_154.json','AQF 154 semi-curated benchmark workload',curated,False)
    save(out/'synthetic_workload_10000.json','AQF 10,000 synthetic user-like workload',synthetic,True)
    summarize(out,curated,synthetic)
    print('AQF workload expansion v2 complete.')
    print(f'Curated workload: {len(curated)} queries')
    print(f'Synthetic workload: {len(synthetic)} queries')
    print(f'Output: {out}')
if __name__=='__main__': main()
