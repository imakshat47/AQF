from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Dict, List, Tuple


def _safe_float(x, default=0.0) -> float:
    try:
        if x is None:
            return default
        v = float(x)
        if math.isnan(v):
            return default
        return v
    except Exception:
        return default


def _field_coverage(f: Dict[str, Any]) -> float:
    return max(0.0, min(1.0, _safe_float(f.get("coverage"))))


def _field_occurrence(f: Dict[str, Any], record_count: float) -> float:
    occ = _safe_float(f.get("occurrence_count"))
    return occ if occ > 0 else _field_coverage(f) * record_count


def _field_known_count(f: Dict[str, Any], record_count: float) -> float:
    kc = _safe_float(f.get("known_count"))
    return kc if kc > 0 else _field_occurrence(f, record_count)


def _field_distinct_count(f: Dict[str, Any], record_count: float) -> float:
    dc = _safe_float(f.get("distinct_count"))
    if dc > 0:
        return dc
    known = _field_known_count(f, record_count)
    dr = f.get("distinct_ratio")
    if dr is not None and known > 0:
        return max(0.0, min(known, _safe_float(dr) * known))
    dv = str(f.get("dv_type") or f.get("primary_dv_type") or "")
    kind = str(f.get("kind") or "")
    if "BOOLEAN" in dv or kind == "boolean": return min(2.0, max(1.0, known))
    if "CODED" in dv or kind == "coded": return min(max(2.0, math.sqrt(max(known, 1.0))), known) if known else 0.0
    if "DATE" in dv or kind == "temporal": return min(max(known * 0.25, 1.0), known)
    if any(t in dv for t in ["COUNT", "QUANTITY", "PROPORTION"]) or kind == "numeric": return min(max(known * 0.30, 1.0), known)
    if "TEXT" in dv or kind == "text": return min(max(known * 0.50, 1.0), known)
    return min(max(math.sqrt(max(known, 1.0)), 1.0), known) if known else 0.0


def entity_id_for_field(f: Dict[str, Any], level: str = "subgroup") -> str:
    family = f.get("record_family") or "composition"
    group = f.get("form_group") or "group"
    subgroup = f.get("nested_subgroup") or group
    if level == "family": return f"E::{family}"
    if level == "group": return f"E::{family}::{group}"
    return f"E::{family}::{group}::{subgroup}"


def entity_label(entity_id: str) -> str:
    parts = entity_id.split("::")
    return " / ".join(parts[1:]) if len(parts) > 1 else entity_id


def build_acf_graph(forest: Dict[str, Any], entity_level: str = "subgroup") -> Dict[str, Any]:
    record_count = float(forest.get("record_count") or forest.get("json_record_units") or 1.0)
    fields=[]
    for family, tree in (forest.get("trees") or {}).items():
        for f in tree.get("fields", []) or []:
            x=dict(f); x.setdefault("record_family", family)
            x["entity_id"] = entity_id_for_field(x, entity_level)
            x["attribute_id"] = f"A::{x.get('field_id')}"
            fields.append(x)
    entities={}; attrs={}; links=[]; by_entity=defaultdict(list)
    for f in fields: by_entity[f["entity_id"]].append(f)
    for eid, fs in by_entity.items():
        card=max([_field_occurrence(f, record_count) for f in fs] or [0.0])
        entities[eid]={"id":eid,"label":entity_label(eid),"absolute_cardinality":max(card,1.0),"field_count":len(fs)}
        for f in fs:
            aid=f["attribute_id"]; occ=_field_occurrence(f, record_count)
            attrs[aid]={
                "id":aid,"field_id":f.get("field_id"),"entity_id":eid,"label":f.get("label"),"canonical_path":f.get("canonical_path"),
                "record_family":f.get("record_family"),"form_group":f.get("form_group"),"nested_subgroup":f.get("nested_subgroup"),
                "kind":f.get("kind"),"dv_type":f.get("dv_type"),"primary_dv_type":f.get("primary_dv_type", f.get("dv_type")),
                "observed_dv_types":f.get("observed_dv_types") or ([f.get("dv_type")] if f.get("dv_type") else []),
                "supports_null_flavour":bool(f.get("supports_null_flavour") or f.get("has_null_flavour")),
                "absolute_cardinality":max(occ,0.0),"known_count":_field_known_count(f, record_count),"distinct_count":_field_distinct_count(f, record_count),
                "coverage":_field_coverage(f),"depth":len([p for p in str(f.get("canonical_path") or "").split("/") if p.strip()])
            }
            links.append((eid, aid, max(occ,0.0))); links.append((aid, eid, max(occ,0.0)))
    eids=list(entities)
    for i,e1 in enumerate(eids):
        p1=e1.split("::")
        for e2 in eids[i+1:]:
            p2=e2.split("::"); common=0
            for a,b in zip(p1,p2):
                if a==b: common+=1
                else: break
            if common < 2: continue
            c1,c2=entities[e1]["absolute_cardinality"],entities[e2]["absolute_cardinality"]
            link_card=min(c1,c2)*(common/max(len(p1),len(p2)))
            if link_card>0:
                links.append((e1,e2,link_card)); links.append((e2,e1,link_card))
    nodes={**entities, **attrs}
    for n in nodes.values(): n["out_links"]=[]
    for src,dst,card in links:
        if src in nodes and dst in nodes: nodes[src]["out_links"].append([dst,card])
    return {"record_count":record_count,"entities":entities,"attributes":attrs,"nodes":nodes,"links":[list(x) for x in links]}


def compute_relative_cardinality(graph):
    rc={}; nodes=graph["nodes"]
    for src,dst,card in graph["links"]:
        denom=max(_safe_float(nodes.get(dst,{}).get("absolute_cardinality")),1e-12)
        rc[(src,dst)]=max(0.0,_safe_float(card)/denom)
    return rc


def compute_importance_and_entity_queriability(graph, p=0.15, max_iter=100, tol=1e-9, use_p1=True, use_p2=True):
    nodes=graph["nodes"]; rc=compute_relative_cardinality(graph); incoming=defaultdict(list); outgoing=defaultdict(float)
    for (src,dst),val in rc.items(): incoming[dst].append((src,val)); outgoing[src]+=val
    I={nid:(max(_safe_float(n.get("absolute_cardinality")),0.0) if use_p2 else 1.0) for nid,n in nodes.items()}
    if use_p1:
        for _ in range(max_iter):
            new={}; delta=0.0
            for nid in nodes:
                val=p*I[nid]+(1-p)*sum((rcv/(outgoing[src] or 1.0))*I[src] for src,rcv in incoming.get(nid,[]))
                new[nid]=val; delta=max(delta,abs(val-I[nid]))
            I=new
            if delta<tol: break
    total=sum(max(_safe_float(n.get("absolute_cardinality")),0.0) for n in nodes.values()) or 1.0
    return {eid:{"entity_id":eid,"entity_label":e.get("label"),"importance":I.get(eid,0.0),"entity_queriability":I.get(eid,0.0)/total,"absolute_cardinality":e.get("absolute_cardinality"),"field_count":e.get("field_count")} for eid,e in graph["entities"].items()}


def compute_attribute_necessity(graph, use_p5=True):
    out={}; entities=graph["entities"]
    for aid,a in graph["attributes"].items():
        e=entities[a["entity_id"]]
        n=max(0.0,min(1.0,_safe_float(a.get("absolute_cardinality"))/max(_safe_float(e.get("absolute_cardinality")),1e-12))) if use_p5 else 1.0
        out[aid]={"attribute_id":aid,"necessity":n,"attribute_queriability":n}
    return out


def _dv(a): return " ".join([str(a.get("dv_type") or ""),str(a.get("primary_dv_type") or "")," ".join(map(str,a.get("observed_dv_types") or []))])
def _is_numeric(a): return any(t in _dv(a) for t in ["DV_COUNT","DV_QUANTITY","DV_PROPORTION","NUMBER","INTEGER","REAL"])
def _is_single(a): return not any(t in str(a.get("label") or "").lower() for t in ["list","fields/insertions"])
def _is_repeat(a): return not _is_single(a)


def compute_operator_specific_scores(graph, attr_scores, use_p6=True, use_p7=True, use_p8=True, use_p9=True):
    by_entity=defaultdict(list)
    for aid,a in graph["attributes"].items(): by_entity[a["entity_id"]].append(aid)
    attr_size={}
    for aid,a in graph["attributes"].items():
        size=1.0+0.1*max(0,int(a.get("depth") or 1)-3)+(0.5 if _is_repeat(a) else 0)
        attr_size[aid]=size
    out={}
    for aid,a in graph["attributes"].items():
        N=attr_scores[aid]["necessity"]; C=max(_safe_float(a.get("absolute_cardinality")),1e-12); r=min(_safe_float(a.get("distinct_count")),C)
        w_sel=max(0.0,min(1.0,r/C)) if use_p6 else 1.0; q_sel=w_sel*N
        denom=sum(attr_size[x] for x in by_entity[a["entity_id"]]) or 1.0; w_proj=(attr_size[aid]/denom) if use_p7 else 1.0; q_proj=w_proj*N
        required=N>=0.95; w_sort=1.0 if (_is_single(a) and required) else 0.0
        if not use_p8: w_sort=1.0
        q_sort=w_sort*N
        w_agg=1.0 if (_is_numeric(a) and _is_repeat(a)) else 0.0
        if not use_p9: w_agg=1.0 if _is_numeric(a) else 0.0
        q_agg=w_agg*N
        out[aid]={"attribute_id":aid,"field_id":a.get("field_id"),"entity_id":a.get("entity_id"),"label":a.get("label"),"necessity":N,"selectivity_weight":w_sel,"projection_weight":w_proj,"sort_weight":w_sort,"aggregation_weight":w_agg,"q_selection":q_sel,"q_projection":q_proj,"q_sort":q_sort,"q_aggregation":q_agg,"q_operator_total":q_sel+q_proj+q_sort+q_agg}
    return out


def compute_related_entity_scores(graph, entity_scores, use_p3=True, use_p4=True):
    link=defaultdict(float)
    for src,dst,card in graph["links"]:
        if str(src).startswith("E::") and str(dst).startswith("E::"): link[(src,dst)]+=_safe_float(card)
    out={}; eids=list(graph["entities"])
    for i,e1 in enumerate(eids):
        for e2 in eids[i+1:]:
            q1=entity_scores.get(e1,{}).get("entity_queriability",0.0) if use_p3 else 1.0; q2=entity_scores.get(e2,{}).get("entity_queriability",0.0) if use_p3 else 1.0
            c1=max(_safe_float(graph["entities"][e1].get("absolute_cardinality")),1e-12); c2=max(_safe_float(graph["entities"][e2].get("absolute_cardinality")),1e-12)
            r12=link[(e1,e2)]/c1; r21=link[(e2,e1)]/c2; rel=(r12+r21)/2 if use_p4 else 1.0
            q=q1*q2*rel
            if q>0: out[f"{e1}|||{e2}"]={"entity_1":e1,"entity_2":e2,"participation_12":r12,"participation_21":r21,"related_queriability":q}
    return out


def compute_acf_scores(forest, p=0.15, entity_level="subgroup", use_p1=True,use_p2=True,use_p3=True,use_p4=True,use_p5=True,use_p6=True,use_p7=True,use_p8=True,use_p9=True):
    graph=build_acf_graph(forest,entity_level); ent=compute_importance_and_entity_queriability(graph,p=p,use_p1=use_p1,use_p2=use_p2); attr=compute_attribute_necessity(graph,use_p5=use_p5); op=compute_operator_specific_scores(graph,attr,use_p6=use_p6,use_p7=use_p7,use_p8=use_p8,use_p9=use_p9); rel=compute_related_entity_scores(graph,ent,use_p3=use_p3,use_p4=use_p4)
    return {"graph":graph,"entity_scores":ent,"attribute_scores":attr,"operator_scores":op,"related_entity_scores":rel,"params":{"p":p,"entity_level":entity_level,"use_p1":use_p1,"use_p2":use_p2,"use_p3":use_p3,"use_p4":use_p4,"use_p5":use_p5,"use_p6":use_p6,"use_p7":use_p7,"use_p8":use_p8,"use_p9":use_p9}}


def scores_rows(acf):
    graph=acf["graph"]; ent_rows=list(acf["entity_scores"].values()); attr_rows=[]
    for aid,a in graph["attributes"].items():
        row=dict(a); row.update(acf["attribute_scores"].get(aid,{})); row.update(acf["operator_scores"].get(aid,{})); attr_rows.append(row)
    attr_rows.sort(key=lambda r:r.get("q_operator_total",0.0),reverse=True)
    for i,r in enumerate(attr_rows,1): r["operator_rank"]=i
    rel_rows=list(acf["related_entity_scores"].values()); rel_rows.sort(key=lambda r:r.get("related_queriability",0.0),reverse=True)
    return {"entity_scores":ent_rows,"attribute_operator_scores":attr_rows,"related_entity_scores":rel_rows}
