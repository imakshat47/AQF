from __future__ import annotations
from collections import defaultdict

def operator_compatibility(field: dict, operator_class: str) -> float:
    kind = field.get("kind")
    if operator_class == "filter":
        if kind in {"coded", "boolean", "temporal", "numeric", "text"}: return 1.0
        if kind == "null": return 0.7
        return 0.6
    if operator_class == "project": return 1.0 if field.get("coverage", 0) > 0 else 0.0
    if operator_class == "sort": return 1.0 if kind in {"temporal", "numeric", "coded", "text"} else 0.4
    return 0.5

def compute_scores(forest: dict, alpha: float = 0.7, beta: float = 0.3, lamb: float = 0.25) -> dict:
    scores = {}
    for family, tree in forest.get("trees", {}).items():
        fields = tree.get("fields", [])
        subgroup_counts = defaultdict(int); co_degree = defaultdict(int)
        for f in fields: subgroup_counts[(f.get("form_group"), f.get("nested_subgroup"))] += 1
        for e in tree.get("cooccurrence_edges", []):
            co_degree[e["source"]] += e.get("count", 1); co_degree[e["target"]] += e.get("count", 1)
        max_co = max(co_degree.values()) if co_degree else 1
        for f in fields:
            fid = f["field_id"]; necessity = f.get("coverage", 0.0); selectivity = min(1.0, f.get("distinct_ratio", 0.0))
            containment = 1.0 / max(1, subgroup_counts[(f.get("form_group"), f.get("nested_subgroup"))])
            co = co_degree.get(fid, 0) / max_co if max_co else 0.0
            importance = necessity + lamb * (alpha * containment + beta * co) * necessity
            filter_score = importance * operator_compatibility(f, "filter") * (0.5 + 0.5 * selectivity)
            output_score = importance * operator_compatibility(f, "project")
            sort_score = importance * operator_compatibility(f, "sort")
            scores[fid] = {"field_id": fid, "record_family": family, "label": f.get("label"), "canonical_path": f.get("canonical_path"), "coverage": necessity, "distinct_ratio": selectivity, "importance": importance, "filter_score": filter_score, "output_score": output_score, "sort_score": sort_score, "overall_score": 0.45*filter_score + 0.35*output_score + 0.20*sort_score}
    return scores
