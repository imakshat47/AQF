# schema_union_builder.py

from __future__ import annotations
from typing import Any, Dict, List
from utils import safe_get, ensure_list

def is_openehr_node(obj: Any) -> bool:
    return isinstance(obj, dict) and "type" in obj and (
        "archetype_node_id" in obj or safe_get(obj, ["name", "value"]) is not None
    )

def node_name(obj: dict) -> str:
    return safe_get(obj, ["name", "value"], "") or ""

def node_type(obj: dict) -> str:
    return obj.get("type", "UNKNOWN")

def node_at(obj: dict) -> str:
    return obj.get("archetype_node_id", "") or ""

def extract_element_value_and_kind(el: dict):
    """
    Extract a display/query value from an openEHR ELEMENT.

    Order matters because composition files can contain:
    - value.value
    - value.magnitude
    - value.defining_code.code_string
    - null_flavour.value
    """
    dv_type = safe_get(el, ["value", "type"], None)

    val = safe_get(el, ["value", "value"], None)
    if val is not None:
        return val, dv_type or "UNKNOWN_DV"

    val = safe_get(el, ["value", "magnitude"], None)
    if val is not None:
        return val, dv_type or "UNKNOWN_DV"

    val = safe_get(el, ["value", "defining_code", "code_string"], None)
    if val is not None:
        return val, dv_type or "UNKNOWN_DV"

    val = safe_get(el, ["null_flavour", "value"], None)
    if val is not None:
        return val, "NULL_FLAVOUR"

    return None, "UNKNOWN_DV"

def build_union_schema(docs: List[dict]) -> Dict[str, Any]:
    """
    Build a union schema from one composition family.
    Output:
      composition_archetype -> groups(entry) -> subgroups(cluster path) -> fields(elements)

    Handles:
    - items as list or dict
    - description.items as list or dict
    - null_flavour instead of value
    - repeated at-codes with different labels
    """
    if not docs:
        raise ValueError("No valid composition documents passed into build_union_schema().")

    first_content = safe_get(docs[0], ["versions", "data", "content"], None)
    if not isinstance(first_content, list):
        raise ValueError(
            "Input documents are not composition-version documents "
            "(missing versions.data.content[])."
        )

    composition_archetype = safe_get(docs[0], ["versions", "data", "archetype_node_id"], "UNKNOWN_COMPOSITION")
    composition_label = safe_get(docs[0], ["versions", "data", "name", "value"], "Unknown composition")

    union = {
        "composition_archetype": composition_archetype,
        "composition_label": composition_label,
        "groups": {}
    }

    for doc in docs:
        content = safe_get(doc, ["versions", "data", "content"], [])
        for entry in ensure_list(content):
            if not isinstance(entry, dict):
                continue

            entry_arch = entry.get("archetype_node_id", "UNKNOWN_ENTRY")
            entry_name = safe_get(entry, ["name", "value"], entry.get("type", "ENTRY")) or "ENTRY"

            group = union["groups"].setdefault(entry_arch, {
                "entry_name": entry_name,
                "entry_type": entry.get("type", "ENTRY"),
                "subgroups": {}
            })

            for root_key in ["data", "description"]:
                if root_key not in entry:
                    continue

                def walk(obj: Any, cluster_path: List[str]):
                    if isinstance(obj, dict) and is_openehr_node(obj):
                        t = node_type(obj)

                        if t == "CLUSTER":
                            c_name = node_name(obj) or "(cluster)"
                            new_path = cluster_path + [c_name]
                            for _, v in obj.items():
                                walk(v, new_path)
                            return

                        if t == "ELEMENT":
                            subgroup_key = " / ".join(cluster_path) if cluster_path else "(no cluster)"
                            subgroup = group["subgroups"].setdefault(subgroup_key, {"fields": {}})

                            el_name = node_name(obj) or node_at(obj) or "(element)"
                            el_at = node_at(obj)
                            val, dv_kind = extract_element_value_and_kind(obj)

                            # Stable field signature:
                            # include element_name because repeated at-codes may occur with different labels
                            field_sig = f"{entry_arch}|{subgroup_key}|{el_name}|{el_at}"

                            field = subgroup["fields"].setdefault(field_sig, {
                                "entry_arch": entry_arch,
                                "entry_name": entry_name,
                                "cluster_path": cluster_path,
                                "cluster_path_str": subgroup_key,
                                "element_name": el_name,
                                "element_at_code": el_at,
                                "dv_type": dv_kind,
                                "has_null_flavour": False,
                                "occurrences": 0,

                                # suggestion support
                                "sample_values": {},
                                "sample_value_count": 0,
                                "has_known_values": False,
                                "has_unknown_values": False
                            })

                            if dv_kind == "NULL_FLAVOUR":
                                field["has_null_flavour"] = True
                                field["has_unknown_values"] = True
                            else:
                                field["has_known_values"] = True

                            if val is not None:
                                sval = str(val)
                                field["sample_values"][sval] = field["sample_values"].get(sval, 0) + 1
                                field["sample_value_count"] += 1

                            field["occurrences"] += 1
                            return

                        # other node types
                        for _, v in obj.items():
                            walk(v, cluster_path)
                        return

                    elif isinstance(obj, dict):
                        for _, v in obj.items():
                            walk(v, cluster_path)
                    elif isinstance(obj, list):
                        for it in obj:
                            walk(it, cluster_path)

                walk(entry[root_key], [])

    return union
