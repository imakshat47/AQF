# form_definition_builder.py

from __future__ import annotations
from typing import Dict, List
from operator_registry import operators_for_dv_type

def build_form_definition(union_schema: Dict, field_catalog: List[Dict]) -> Dict:
    """
    Build the accordion-based UI definition:
    top-level groups = composition children (content[] entries)
    subgroups = cluster paths
    fields = leaf elements
    """
    form = {
        "composition_label": union_schema["composition_label"],
        "composition_archetype": union_schema["composition_archetype"],
        "criteria_groups": [],
        "output_fields": [],
        "advanced_options": [
            {"key": "occurrence_semantics", "label": "Repeated occurrence semantics", "choices": ["ALL", "ANY"], "default": "ALL"},
            {"key": "include_unknown", "label": "Include unknown values", "choices": [True, False], "default": False},
        ]
    }

    # index catalog by entry + subgroup
    by_group = {}
    for f in field_catalog:
        by_group.setdefault((f["entry_name"], f["cluster_path_str"]), []).append(f)

    for entry_arch, g in union_schema["groups"].items():
        entry_name = g["entry_name"]
        grp = {"group_label": entry_name, "subgroups": []}

        for subgroup_key in g["subgroups"].keys():
            fields = []
            for f in by_group.get((entry_name, subgroup_key), []):
                fields.append({
                    "field_key": f["field_key"],
                    "label": f["element_name"],
                    "full_label": f["label"],
                    "dv_type": f["dv_type"],
                    "operators": operators_for_dv_type(f["dv_type"], f["has_null_flavour"]),

                    # tooltip + suggestions
                    "tooltip": f["tooltip"],
                    "suggested_values": f["suggested_values"],
                    "suggestion_mode": f["suggestion_mode"]
                })

            grp["subgroups"].append({
                "label": subgroup_key,
                "fields": fields
            })

        form["criteria_groups"].append(grp)

    # output fields kept flat
    form["output_fields"] = [
        {"field_key": f["field_key"], "label": f["label"], "dv_type": f["dv_type"]}
        for f in field_catalog
    ]

    return form
