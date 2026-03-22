# schema_diagram.py

from __future__ import annotations
from typing import Dict, List, Any, Tuple
import re

def _node_id(s: str) -> str:
    """
    Convert arbitrary label to DOT-safe node id.
    """
    s = re.sub(r"[^A-Za-z0-9_]+", "_", s)
    if not s:
        s = "node"
    return s

def build_schema_flow_dot(union_schema: dict) -> str:
    """
    Build a simple hierarchy flow diagram:
    Composition -> Entry group -> Cluster path -> square box with leaf field count
    """
    comp_label = union_schema.get("composition_label", "Unknown composition")
    lines = [
        'digraph G {',
        'rankdir=TB;',
        'node [fontname="Helvetica", fontsize=11];',
        'edge [color="#555555"];'
    ]

    root_id = "composition_root"
    lines.append(f'{root_id} [label="{comp_label}", shape=box, style="filled", fillcolor="#DCEEFF"];')

    for entry_arch, group in union_schema.get("groups", {}).items():
        entry_name = group.get("entry_name", entry_arch)
        entry_id = _node_id(f"entry_{entry_arch}")
        lines.append(f'{entry_id} [label="{entry_name}", shape=box, style="rounded,filled", fillcolor="#EAF7E6"];')
        lines.append(f"{root_id} -> {entry_id};")

        for subgroup_key, subgroup in group.get("subgroups", {}).items():
            subgroup_id = _node_id(f"{entry_id}_{subgroup_key}")
            label = subgroup_key.replace('"', "'")
            lines.append(f'{subgroup_id} [label="{label}", shape=ellipse, style="filled", fillcolor="#FFF4D6"];')
            lines.append(f"{entry_id} -> {subgroup_id};")

            leaf_count = len(subgroup.get("fields", {}))
            leaf_id = _node_id(f"{subgroup_id}_count")
            lines.append(
                f'{leaf_id} [label="{leaf_count}", shape=square, width=0.4, height=0.4, style="filled", fillcolor="#FDE2E4"];'
            )
            lines.append(f"{subgroup_id} -> {leaf_id};")

    lines.append("}")
    return "\n".join(lines)


def build_touched_paths(criteria: List[Dict], output_fields: List[Dict], sort_state: Dict | None = None) -> List[Dict]:
    """
    Return a normalized list of touched paths for query provenance.

    Expected criteria/output items to include:
      - entry_name
      - cluster_path_str
      - element_name
      - role (filter/output/sort)
    """
    touched = []

    for c in criteria:
        touched.append({
            "role": "FILTER",
            "entry_name": c.get("entry_name", "Unknown entry"),
            "cluster_path_str": c.get("cluster_path_str", "(no cluster)"),
            "element_name": c.get("element_name", c.get("field_key", "Field")),
            "operator": c.get("operator"),
            "value": c.get("value")
        })

    for o in output_fields:
        touched.append({
            "role": "OUTPUT",
            "entry_name": o.get("entry_name", "Unknown entry"),
            "cluster_path_str": o.get("cluster_path_str", "(no cluster)"),
            "element_name": o.get("element_name", o.get("field_key", "Field"))
        })

    if sort_state:
        touched.append({
            "role": "SORT",
            "entry_name": sort_state.get("entry_name", "Unknown entry"),
            "cluster_path_str": sort_state.get("cluster_path_str", "(no cluster)"),
            "element_name": sort_state.get("element_name", sort_state.get("field_key", "Field")),
            "direction": sort_state.get("direction", "asc")
        })

    return touched


def build_touched_query_dot(criteria: List[Dict], output_fields: List[Dict], sort_state: Dict | None = None) -> str:
    """
    Build a simple touched-schema diagram:
    Query -> Entry -> Cluster -> Field [FILTER/OUTPUT/SORT]
    """
    touched = build_touched_paths(criteria, output_fields, sort_state)

    lines = [
        'digraph G {',
        'rankdir=TB;',
        'node [fontname="Helvetica", fontsize=11];',
        'edge [color="#666666"];'
    ]

    root_id = "query_root"
    lines.append(f'{root_id} [label="Query", shape=box, style="filled", fillcolor="#DCEEFF"];')

    seen_entries = set()
    seen_clusters = set()
    seen_fields = set()

    for t in touched:
        entry_name = t["entry_name"]
        cluster = t["cluster_path_str"]
        element = t["element_name"]
        role = t["role"]

        entry_id = _node_id(f"entry_{entry_name}")
        cluster_id = _node_id(f"{entry_id}_{cluster}")
        field_id = _node_id(f"{cluster_id}_{element}_{role}")

        if entry_id not in seen_entries:
            lines.append(f'{entry_id} [label="{entry_name}", shape=box, style="rounded,filled", fillcolor="#EAF7E6"];')
            lines.append(f"{root_id} -> {entry_id};")
            seen_entries.add(entry_id)

        if cluster_id not in seen_clusters:
            cluster_label = cluster.replace('"', "'")
            lines.append(f'{cluster_id} [label="{cluster_label}", shape=ellipse, style="filled", fillcolor="#FFF4D6"];')
            lines.append(f"{entry_id} -> {cluster_id};")
            seen_clusters.add(cluster_id)

        if field_id not in seen_fields:
            suffix = role
            if role == "FILTER":
                suffix = f"FILTER\\n{t.get('operator','')} {t.get('value','')}"
            elif role == "SORT":
                suffix = f"SORT\\n{t.get('direction','asc')}"

            label = f"{element}\\n[{suffix}]".replace('"', "'")
            fill = "#FDE2E4" if role == "FILTER" else ("#E7F0FF" if role == "OUTPUT" else "#E8EAF6")
            lines.append(f'{field_id} [label="{label}", shape=box, style="filled", fillcolor="{fill}"];')
            lines.append(f"{cluster_id} -> {field_id};")
            seen_fields.add(field_id)

    lines.append("}")
    return "\n".join(lines)
