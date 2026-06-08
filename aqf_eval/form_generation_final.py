from __future__ import annotations

import random
from collections import defaultdict
from typing import Any, Dict, List, Tuple


def infer_depth(field: Dict[str, Any]) -> int:
    path = field.get("canonical_path") or ""
    parts = [p.strip() for p in str(path).split("/") if p.strip()]
    if parts:
        return max(1, len(parts))
    subgroup = field.get("nested_subgroup") or ""
    return max(1, 1 + len([p for p in str(subgroup).split("/") if p.strip()]))


def form_complexity_candidate(fields: List[Dict[str, Any]], eta: float = 1.0) -> float:
    if not fields:
        return 0.0
    return len(fields) + eta * max(infer_depth(f) for f in fields)


def operators_for_field_final(field: Dict[str, Any], operator_aware: bool = True) -> List[str]:
    if not operator_aware:
        return ["equals", "not_equals", "in", "contains", ">", "<", "before", "after", "between", "is_known", "is_unknown"]
    dv_types = set(field.get("observed_dv_types") or [])
    if field.get("dv_type"): dv_types.add(field.get("dv_type"))
    if field.get("primary_dv_type"): dv_types.add(field.get("primary_dv_type"))
    ops=set(["is_known", "is_unknown"])
    if "DV_CODED_TEXT" in dv_types:
        ops.update(["equals", "not_equals", "in", "contains"])
    if "DV_TEXT" in dv_types:
        ops.update(["equals", "contains"])
    if "DV_DATE" in dv_types or "DV_DATE_TIME" in dv_types:
        ops.update(["equals", "before", "after", "between"])
    if "DV_COUNT" in dv_types or "DV_QUANTITY" in dv_types or "DV_PROPORTION" in dv_types:
        ops.update(["equals", ">", "<", "between"])
    if "DV_BOOLEAN" in dv_types:
        ops.update(["equals"])
    order=["equals","not_equals","in","contains",">","<","before","after","between","is_known","is_unknown"]
    return [o for o in order if o in ops]


def operator_compatibility(field: Dict[str, Any], op: str) -> float:
    return 1.0 if op in operators_for_field_final(field, operator_aware=True) else 0.0


def operator_adjusted_score(field: Dict[str, Any], base_score: float) -> float:
    ops = operators_for_field_final(field, operator_aware=True)
    if not ops:
        return 0.0
    # Projection/output remains possible for all retained form elements, while
    # filtering/sorting controls are limited by datatype compatibility. A field
    # with several valid controls is slightly preferred, but Q(v) remains primary.
    return base_score * (1.0 + 0.05 * min(len(ops), 6))


def _all_fields(forest: Dict[str, Any], scores: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    fields=[]
    for family, tree in (forest.get("trees") or {}).items():
        for f in tree.get("fields", []) or []:
            x=dict(f)
            x.setdefault("record_family", family)
            s=scores.get(x.get("field_id"), {})
            x["score"] = float(s.get("overall_score", s.get("final_queriability", x.get("coverage", 0.0))) or 0.0)
            x["final_queriability"] = x["score"]
            x["coverage"] = float(s.get("coverage", x.get("coverage", 0.0)) or 0.0)
            x["diversity"] = s.get("diversity")
            x["local_utility"] = s.get("local_utility")
            x["neighborhood_reinforcement"] = s.get("neighborhood_reinforcement")
            if x.get("supports_null_flavour") is None:
                x["supports_null_flavour"] = bool(x.get("has_null_flavour"))
            fields.append(x)
    return fields


def _select_under_budget(candidates: List[Dict[str, Any]], complexity_budget: float, eta: float) -> List[Dict[str, Any]]:
    selected=[]
    for f in candidates:
        trial = selected + [f]
        if form_complexity_candidate(trial, eta=eta) <= complexity_budget:
            selected.append(f)
    return selected


def _decorate_fields(fields: List[Dict[str, Any]], method: str, operator_aware: bool, flattened: bool = False) -> List[Dict[str, Any]]:
    out=[]
    for rank, f in enumerate(fields, start=1):
        group = "Flat Fields" if flattened else f.get("form_group")
        subgroup = "All Fields" if flattened else f.get("nested_subgroup")
        out.append({
            "field_id": f.get("field_id"),
            "label": f.get("label"),
            "canonical_path": f.get("canonical_path"),
            "record_family": f.get("record_family"),
            "form_group": group,
            "nested_subgroup": subgroup,
            "kind": f.get("kind"),
            "dv_type": f.get("dv_type"),
            "primary_dv_type": f.get("primary_dv_type", f.get("dv_type")),
            "observed_dv_types": f.get("observed_dv_types") or ([f.get("dv_type")] if f.get("dv_type") else []),
            "supports_null_flavour": f.get("supports_null_flavour"),
            "operators": operators_for_field_final(f, operator_aware=operator_aware),
            "score": f.get("score", 0.0),
            "final_queriability": f.get("final_queriability", f.get("score", 0.0)),
            "local_utility": f.get("local_utility"),
            "diversity": f.get("diversity"),
            "coverage": f.get("coverage"),
            "rank": rank,
        })
    return out


def _groups(fields: List[Dict[str, Any]]):
    groups=defaultdict(lambda: defaultdict(list))
    for f in fields:
        groups[f.get("form_group") or "Composition"][f.get("nested_subgroup") or "Top-level fields"].append(f["field_id"])
    return {g: dict(sgs) for g,sgs in groups.items()}


def generate_form_final(
    forest: Dict[str, Any],
    scores: Dict[str, Dict[str, Any]],
    method: str = "aqf_full",
    complexity_budget: float = 35.0,
    theta: float = 0.10,
    eta: float = 1.0,
    seed: int = 42,
) -> Dict[str, Any]:
    all_fields = _all_fields(forest, scores)
    max_score = max([f.get("score", 0.0) for f in all_fields] or [0.0])
    threshold = theta * max_score

    # Base candidate pools per ablation.
    if method == "no_pruning":
        selected = sorted(all_fields, key=lambda f: f.get("score", 0.0), reverse=True)
        operator_aware=True; flattened=False
    elif method == "frequency_only":
        candidates = sorted(all_fields, key=lambda f: (f.get("coverage", 0.0), f.get("label") or ""), reverse=True)
        selected = _select_under_budget(candidates, complexity_budget, eta)
        operator_aware=True; flattened=False
    elif method == "flattened_topk":
        candidates = [f for f in all_fields if f.get("score", 0.0) >= threshold]
        candidates = sorted(candidates, key=lambda f: operator_adjusted_score(f, f.get("score", 0.0)), reverse=True)
        selected = _select_under_budget(candidates, complexity_budget, eta)
        operator_aware=True; flattened=True
    elif method == "aqf_topk_no_threshold":
        candidates = sorted(all_fields, key=lambda f: operator_adjusted_score(f, f.get("score", 0.0)), reverse=True)
        selected = _select_under_budget(candidates, complexity_budget, eta)
        operator_aware=True; flattened=False
    elif method == "no_operator_awareness":
        candidates = [f for f in all_fields if f.get("score", 0.0) >= threshold]
        candidates = sorted(candidates, key=lambda f: operator_adjusted_score(f, f.get("score", 0.0)), reverse=True)
        selected = _select_under_budget(candidates, complexity_budget, eta)
        operator_aware=False; flattened=False
    elif method.startswith("random_topk"):
        rng=random.Random(seed)
        candidates=list(all_fields)
        rng.shuffle(candidates)
        selected = _select_under_budget(candidates, complexity_budget, eta)
        operator_aware=True; flattened=False
    else:  # aqf_full
        candidates = [f for f in all_fields if f.get("score", 0.0) >= threshold]
        candidates = sorted(candidates, key=lambda f: operator_adjusted_score(f, f.get("score", 0.0)), reverse=True)
        selected = _select_under_budget(candidates, complexity_budget, eta)
        operator_aware=True; flattened=False

    fields = _decorate_fields(selected, method=method, operator_aware=operator_aware, flattened=flattened)
    return {
        "method": method,
        "complexity_budget": complexity_budget,
        "theta": theta,
        "eta": eta,
        "field_count": len(fields),
        "max_depth": max([infer_depth(f) for f in fields] or [0]),
        "final_complexity": form_complexity_candidate(fields, eta=eta),
        "fields": fields,
        "groups": _groups(fields),
    }
