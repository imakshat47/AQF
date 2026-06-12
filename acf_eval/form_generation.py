from __future__ import annotations
from collections import defaultdict
import random

def _dv(a): return " ".join([str(a.get("dv_type") or ""), str(a.get("primary_dv_type") or ""), " ".join(map(str, a.get("observed_dv_types") or []))])
def _is_numeric(a): return any(t in _dv(a) for t in ["DV_COUNT","DV_QUANTITY","DV_PROPORTION"])
def _is_temporal(a): return "DV_DATE" in _dv(a) or "DV_DATE_TIME" in _dv(a)
def _is_text(a): return "DV_TEXT" in _dv(a)
def _is_coded(a): return "DV_CODED_TEXT" in _dv(a)
def _is_boolean(a): return "DV_BOOLEAN" in _dv(a)
def _selection_ops(a):
    if _is_temporal(a): return ["equals","before","after","between"]
    if _is_numeric(a): return ["equals",">","<","between"]
    if _is_boolean(a): return ["equals"]
    if _is_coded(a): return ["equals","not_equals","in","contains"]
    if _is_text(a): return ["equals","contains"]
    return ["equals","contains"]
def _type_ops(a): return list(dict.fromkeys(_selection_ops(a)+["is_known","is_unknown"]))

def operators_for_attribute(a, op_score, operator_specific=True, no_operator_awareness=False):
    all_ops=["equals","not_equals","in","contains",">","<","before","after","between","is_known","is_unknown"]
    if no_operator_awareness: return all_ops
    if not operator_specific: return _type_ops(a)
    ops=[]
    if op_score.get("q_selection",0.0)>0: ops+=_selection_ops(a)
    if op_score.get("q_sort",0.0)>0:
        if _is_temporal(a): ops += ["before","after","between"]
        elif _is_numeric(a): ops += [">","<","between"]
        else: ops += ["equals"]
    ops += ["is_known","is_unknown"]
    return [o for o in all_ops if o in set(ops)]

def _groups(fields):
    groups=defaultdict(lambda: defaultdict(list))
    for f in fields: groups[f.get("form_group") or "Composition"][f.get("nested_subgroup") or "Top-level fields"].append(f["field_id"])
    return {g:dict(sg) for g,sg in groups.items()}

def _related_items(rel):
    # Supports v1 tuple keys and v1.1 string keys.
    for key,rs in rel.items():
        if isinstance(key, (tuple,list)) and len(key)==2: yield key[0],key[1],rs
        elif isinstance(key,str) and '|||' in key:
            a,b=key.split('|||',1); yield a,b,rs

def _decorate(attr_rows, acf, method, operator_specific=True, no_operator_awareness=False, flattened=False):
    graph=acf["graph"]; op_scores=acf["operator_scores"]; fields=[]
    for rank,r in enumerate(attr_rows,1):
        aid=r["attribute_id"]; a=graph["attributes"][aid]
        fields.append({"field_id":a.get("field_id"),"label":a.get("label"),"canonical_path":a.get("canonical_path"),"record_family":a.get("record_family"),"form_group":"Flat Fields" if flattened else a.get("form_group"),"nested_subgroup":"All Fields" if flattened else a.get("nested_subgroup"),"kind":a.get("kind"),"dv_type":a.get("dv_type"),"primary_dv_type":a.get("primary_dv_type",a.get("dv_type")),"observed_dv_types":a.get("observed_dv_types") or ([a.get("dv_type")] if a.get("dv_type") else []),"supports_null_flavour":a.get("supports_null_flavour"),"operators":operators_for_attribute(a,op_scores.get(aid,{}),operator_specific,no_operator_awareness),"score":r.get("acf_field_score",r.get("q_operator_total",0.0)),"necessity":r.get("necessity"),"q_selection":r.get("q_selection"),"q_projection":r.get("q_projection"),"q_sort":r.get("q_sort"),"q_aggregation":r.get("q_aggregation"),"entity_id":a.get("entity_id"),"entity_queriability":acf["entity_scores"].get(a.get("entity_id"),{}).get("entity_queriability"),"rank":rank})
    return fields

def generate_acf_interface(acf, method="acf_full", k_e=5,k_a=10,k_r=1,k_sigma=6,k_pi=6,k_tau=3,k_gamma=2,field_complexity=30,seed=42):
    graph=acf["graph"]; entity_scores=acf["entity_scores"]; op_scores=acf["operator_scores"]
    e_rank=sorted(entity_scores.values(),key=lambda x:x.get("entity_queriability",0.0),reverse=True); selected=[e["entity_id"] for e in e_rank[:k_e]]
    if method.startswith("random_entities"):
        rng=random.Random(seed); eids=list(graph["entities"]); rng.shuffle(eids); selected=eids[:k_e]
    related=set(selected)
    for e in selected:
        pairs=[]
        for a,b,rs in _related_items(acf.get("related_entity_scores",{})):
            if a==e or b==e: pairs.append((rs.get("related_queriability",0.0), b if a==e else a))
        pairs.sort(reverse=True)
        for _,other in pairs[:k_r]: related.add(other)
    selected=list(dict.fromkeys(selected+list(related)))
    attr_rows=[]
    for eid in selected:
        attrs=[]
        for aid,a in graph["attributes"].items():
            if a["entity_id"]!=eid: continue
            os=op_scores[aid]
            if method=="frequency_only": score=a.get("coverage",0.0)
            elif method=="necessity_only": score=os.get("necessity",0.0)
            elif method=="selection_only": score=os.get("q_selection",0.0)
            elif method=="projection_only": score=os.get("q_projection",0.0)
            elif method=="no_pruning": score=1e12 + os.get("q_operator_total",0.0)
            else:
                score=(os.get("q_selection",0.0)*max(k_sigma,1)+os.get("q_projection",0.0)*max(k_pi,1)+os.get("q_sort",0.0)*max(k_tau,1)+os.get("q_aggregation",0.0)*max(k_gamma,1))*max(entity_scores.get(eid,{}).get("entity_queriability",0.0),1e-12)
            r=dict(os); r["acf_field_score"]=score; attrs.append(r)
        attrs.sort(key=lambda x:x.get("acf_field_score",0.0), reverse=True)
        attr_rows.extend(attrs if method=="no_pruning" else attrs[:k_a])
    if method=="no_pruning":
        # all attributes, not only selected entities, as true upper bound
        attr_rows=[]
        for aid,a in graph["attributes"].items():
            r=dict(op_scores[aid]); r["acf_field_score"]=r.get("q_operator_total",0.0); attr_rows.append(r)
    elif method not in ["frequency_only","necessity_only","selection_only","projection_only"] and not method.startswith("random_entities"):
        selected_ids=set()
        for key,k in [("q_selection",k_sigma),("q_projection",k_pi),("q_sort",k_tau),("q_aggregation",k_gamma)]:
            for r in sorted(attr_rows,key=lambda x:x.get(key,0.0),reverse=True)[:k]:
                if r.get(key,0.0)>0: selected_ids.add(r["attribute_id"])
        selected_rows=[r for r in attr_rows if r["attribute_id"] in selected_ids]
        remaining=[r for r in sorted(attr_rows,key=lambda x:x.get("acf_field_score",0.0),reverse=True) if r["attribute_id"] not in selected_ids]
        for r in remaining:
            if len(selected_rows)>=field_complexity: break
            selected_rows.append(r)
        attr_rows=sorted(selected_rows,key=lambda x:x.get("acf_field_score",0.0),reverse=True)
    else:
        attr_rows=sorted(attr_rows,key=lambda x:x.get("acf_field_score",0.0),reverse=True)
    if method!="no_pruning": attr_rows=attr_rows[:field_complexity]
    fields=_decorate(attr_rows,acf,method,operator_specific=(method!="no_operator_specific"),no_operator_awareness=(method=="no_operator_awareness"),flattened=(method=="flattened_acf"))
    return {"method":method,"k_e":k_e,"k_a":k_a,"k_r":k_r,"k_sigma":k_sigma,"k_pi":k_pi,"k_tau":k_tau,"k_gamma":k_gamma,"field_complexity":field_complexity,"field_count":len(fields),"fields":fields,"groups":_groups(fields)}
