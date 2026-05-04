# field_catalog.py

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List
from config import CACHE_DIR

VALUE_SUGGESTIONS_FILE = CACHE_DIR / "value_suggestions.json"

def build_field_key(composition_arch: str, entry_arch: str, cluster_path_str: str, element_name: str, element_at: str) -> str:
    return f"{composition_arch}|{entry_arch}|{cluster_path_str}|{element_name}|{element_at}"

def ensure_cache_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

def load_value_suggestions_cache() -> Dict:
    ensure_cache_dir()
    if VALUE_SUGGESTIONS_FILE.exists():
        with open(VALUE_SUGGESTIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_value_suggestions_cache(cache: Dict):
    ensure_cache_dir()
    with open(VALUE_SUGGESTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

def determine_suggestion_mode(dv_type: str, has_null_flavour: bool, suggested_values: List[str]) -> str:
    if dv_type in ("DV_CODED_TEXT", "DV_TEXT"):
        return "categorical"
    if dv_type == "DV_BOOLEAN":
        return "boolean"
    if dv_type in ("DV_COUNT", "DV_QUANTITY"):
        return "numeric"
    if dv_type in ("DV_DATE", "DV_DATE_TIME"):
        return "date"
    if has_null_flavour and suggested_values:
        return "categorical"
    return "none"

def build_tooltip(field_key: str, entry_name: str, cluster_path_str: str, element_name: str, dv_type: str, has_null_flavour: bool) -> str:
    unknown_text = "Yes" if has_null_flavour else "No"
    return (
        f"Field: {element_name}\n"
        f"Group: {entry_name}\n"
        f"Cluster path: {cluster_path_str}\n"
        f"Type: {dv_type}\n"
        f"Supports unknown/null flavour: {unknown_text}\n"
        f"Field key: {field_key}"
    )

def build_field_catalog(union_schema: Dict) -> List[Dict]:
    """
    Convert union schema to a flat field catalog used by UI + backend.
    Labels are derived directly from JSON labels (entry.name.value, cluster.name.value, element.name.value).
    """
    cache = load_value_suggestions_cache()
    catalog = []
    comp_arch = union_schema["composition_archetype"]

    for entry_arch, g in union_schema["groups"].items():
        entry_name = g["entry_name"]

        for subgroup_key, sg in g["subgroups"].items():
            for _, field in sg["fields"].items():
                field_key = build_field_key(
                    comp_arch,
                    entry_arch,
                    field["cluster_path_str"],
                    field["element_name"],
                    field["element_at_code"]
                )

                label = (
                    f"{entry_name} → {subgroup_key} → {field['element_name']}"
                    if subgroup_key != "(no cluster)"
                    else f"{entry_name} → {field['element_name']}"
                )

                # Merge/update suggestion cache
                cached = cache.get(field_key, {"values": {}})
                for v, cnt in field["sample_values"].items():
                    cached["values"][v] = cached["values"].get(v, 0) + cnt
                cache[field_key] = cached

                # top N suggestions
                sorted_vals = sorted(cached["values"].items(), key=lambda x: x[1], reverse=True)
                suggested_values = [v for v, cnt in sorted_vals[:20]]

                suggestion_mode = determine_suggestion_mode(
                    field["dv_type"],
                    field["has_null_flavour"],
                    suggested_values
                )

                tooltip = build_tooltip(
                    field_key=field_key,
                    entry_name=entry_name,
                    cluster_path_str=field["cluster_path_str"],
                    element_name=field["element_name"],
                    dv_type=field["dv_type"],
                    has_null_flavour=field["has_null_flavour"]
                )

                catalog.append({
                    "field_key": field_key,
                    "entry_name": entry_name,
                    "entry_arch": entry_arch,
                    "cluster_path": field["cluster_path"],
                    "cluster_path_str": field["cluster_path_str"],
                    "element_name": field["element_name"],
                    "element_at_code": field["element_at_code"],
                    "dv_type": field["dv_type"],
                    "has_null_flavour": field["has_null_flavour"],
                    "label": label,

                    # suggestions + tooltip
                    "tooltip": tooltip,
                    "suggested_values": suggested_values,
                    "suggestion_mode": suggestion_mode
                })

    save_value_suggestions_cache(cache)
    return catalog
