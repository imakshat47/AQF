from __future__ import annotations

import random
from collections import defaultdict


def operators_for_field(field: dict, operator_aware: bool = True) -> list[str]:
    if not operator_aware:
        return ["equals", "contains", "is_known", "is_unknown", ">", "<", "after", "before"]
    kind = field.get("kind")
    ops = ["is_known", "is_unknown"]
    if kind == "coded":
        return ["equals", "not_equals", "in", "is_known", "is_unknown"]
    if kind == "boolean":
        return ["equals", "is_known", "is_unknown"]
    if kind == "temporal":
        return ["equals", "before", "after", "between", "is_known", "is_unknown"]
    if kind == "numeric":
        return ["equals", ">", "<", "between", "is_known", "is_unknown"]
    if kind == "null":
        return ["is_unknown", "is_known"]
    return ["contains", "equals", "is_known", "is_unknown"]


def generate_form(forest: dict, scores: dict, method: str = "aqf_full", kappa: int = 60, theta: float = 0.10, operator_aware: bool = True, seed: int = 42) -> dict:
    all_fields = []
    for family, tree in forest.get("trees", {}).items():
        for f in tree.get("fields", []):
            x = dict(f)
            x["record_family"] = family
            x["score"] = scores.get(f["field_id"], {}).get("overall_score", f.get("coverage", 0.0))
            all_fields.append(x)
    max_score = max([f.get("score", 0) for f in all_fields] or [0])

    if method == "flattened_topk":
        selected = sorted(all_fields, key=lambda f: (f.get("coverage", 0), f.get("occurrence_count", 0)), reverse=True)[:kappa]
        for f in selected:
            f["form_group"] = "Flat Fields"
            f["nested_subgroup"] = "All Fields"
    elif method == "frequency_only":
        selected = sorted(all_fields, key=lambda f: f.get("coverage", 0), reverse=True)[:kappa]
    elif method == "no_pruning":
        selected = sorted(all_fields, key=lambda f: f.get("score", 0), reverse=True)
    elif method.startswith("random_topk"):
        rng = random.Random(seed)
        selected = list(all_fields)
        rng.shuffle(selected)
        selected = selected[:kappa]
    else:  # aqf_full and variants
        retained = [f for f in all_fields if max_score == 0 or f.get("score", 0) >= theta * max_score]
        selected = sorted(retained, key=lambda f: f.get("score", 0), reverse=True)[:kappa]

    fields = []
    for f in selected:
        fields.append({
            "field_id": f["field_id"],
            "label": f.get("label"),
            "canonical_path": f.get("canonical_path"),
            "record_family": f.get("record_family"),
            "form_group": f.get("form_group"),
            "nested_subgroup": f.get("nested_subgroup"),
            "kind": f.get("kind"),
            "dv_type": f.get("dv_type"),
            "operators": operators_for_field(f, operator_aware=operator_aware),
            "score": f.get("score", 0.0),
        })
    groups = defaultdict(lambda: defaultdict(list))
    for f in fields:
        groups[f.get("form_group") or "Composition"][f.get("nested_subgroup") or "Top-level fields"].append(f["field_id"])
    return {
        "method": method,
        "kappa": kappa,
        "theta": theta,
        "field_count": len(fields),
        "fields": fields,
        "groups": {g: dict(sgs) for g, sgs in groups.items()},
    }
