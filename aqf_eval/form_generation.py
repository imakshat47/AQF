from __future__ import annotations

import random
from collections import defaultdict


def operators_for_field(field: dict, operator_aware: bool = True) -> list[str]:
    if not operator_aware:
        return ["equals", "contains", "is_known", "is_unknown", ">", "<", "after", "before", "between", "in", "not_equals"]
    dv_types = set(field.get("observed_dv_types") or [field.get("dv_type")])
    primary = field.get("primary_dv_type") or field.get("dv_type")
    effective = set(dv_types); effective.add(primary)
    ops=set()
    if "DV_CODED_TEXT" in effective: ops.update(["equals","not_equals","in","contains"])
    if "DV_TEXT" in effective: ops.update(["contains","equals"])
    if any(t in effective for t in ["DV_DATE","DV_DATE_TIME"]): ops.update(["equals","before","after","between"])
    if any(t in effective for t in ["DV_COUNT","DV_QUANTITY","DV_PROPORTION"]): ops.update(["equals",">","<","between"])
    if "DV_BOOLEAN" in effective: ops.update(["equals"])
    if field.get("supports_null_flavour") or field.get("has_null_flavour") or "NULL_FLAVOUR" in effective: ops.update(["is_known","is_unknown"])
    else: ops.update(["is_known","is_unknown"])
    order=["equals","not_equals","in","contains",">","<","before","after","between","is_known","is_unknown"]
    return [o for o in order if o in ops]


def _all_fields(forest: dict, scores: dict):
    all_fields=[]
    for family, tree in forest.get("trees", {}).items():
        for f in tree.get("fields", []):
            x=dict(f); x["record_family"]=family; x["score"]=scores.get(f["field_id"],{}).get("overall_score", f.get("coverage",0.0)); all_fields.append(x)
    return all_fields


def generate_form(forest: dict, scores: dict, method: str = "aqf_full", kappa: int = 60, theta: float = 0.10, operator_aware: bool = True, seed: int = 42) -> dict:
    all_fields=_all_fields(forest, scores)
    max_score=max([f.get("score",0) for f in all_fields] or [0])

    if method == "flattened_topk":
        # Deliberately composition-agnostic, frequency-oriented baseline.
        selected=sorted(all_fields, key=lambda f:(f.get("coverage",0), f.get("occurrence_count",0), f.get("label","")), reverse=True)[:kappa]
        for f in selected: f["form_group"]="Flat Fields"; f["nested_subgroup"]="All Fields"
    elif method == "frequency_only":
        # Frequency-only ignores distinctness, operators, containment, and co-occurrence.
        selected=sorted(all_fields, key=lambda f:(f.get("coverage",0), f.get("record_count",0), f.get("label","")), reverse=True)[:kappa]
    elif method == "no_pruning":
        # True no-pruning baseline: expose all canonical candidates, no kappa cap.
        selected=sorted(all_fields, key=lambda f:f.get("score",0), reverse=True)
    elif method == "aqf_topk_no_threshold":
        # Optional ablation: top-k AQF score without theta threshold.
        selected=sorted(all_fields, key=lambda f:f.get("score",0), reverse=True)[:kappa]
    elif method.startswith("random_topk"):
        rng=random.Random(seed); selected=list(all_fields); rng.shuffle(selected); selected=selected[:kappa]
    else:
        retained=[f for f in all_fields if max_score == 0 or f.get("score",0) >= theta * max_score]
        selected=sorted(retained, key=lambda f:f.get("score",0), reverse=True)[:kappa]

    fields=[]
    for rank, f in enumerate(selected, start=1):
        fields.append({"field_id":f["field_id"],"label":f.get("label"),"canonical_path":f.get("canonical_path"),"record_family":f.get("record_family"),"form_group":f.get("form_group"),"nested_subgroup":f.get("nested_subgroup"),"kind":f.get("kind"),"dv_type":f.get("dv_type"),"primary_dv_type":f.get("primary_dv_type"),"observed_dv_types":f.get("observed_dv_types"),"supports_null_flavour":f.get("supports_null_flavour"),"operators":operators_for_field(f, operator_aware=operator_aware),"score":f.get("score",0.0),"rank":rank})
    groups=defaultdict(lambda: defaultdict(list))
    for f in fields: groups[f.get("form_group") or "Composition"][f.get("nested_subgroup") or "Top-level fields"].append(f["field_id"])
    return {"method":method,"kappa":kappa,"theta":theta,"field_count":len(fields),"fields":fields,"groups":{g:dict(sgs) for g,sgs in groups.items()}}
