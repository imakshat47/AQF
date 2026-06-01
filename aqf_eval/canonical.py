from __future__ import annotations

from collections import defaultdict, Counter
from typing import Any
from .openehr_utils import walk_elements, stable_hash


def infer_kind(dv_type: str | None) -> str:
    s = str(dv_type or "").upper()
    if "DATE" in s or "TIME" in s:
        return "temporal"
    if any(x in s for x in ["QUANTITY", "COUNT", "INTEGER", "REAL", "DOUBLE", "LONG"]):
        return "numeric"
    if "BOOLEAN" in s:
        return "boolean"
    if "CODED" in s:
        return "coded"
    if "NULL_FLAVOUR" in s:
        return "null"
    return "text"


def field_id_for(el: dict) -> str:
    identity = {
        "composition": el.get("composition_archetype"),
        "entry": el.get("entry_archetype"),
        "group": el.get("form_group"),
        "subgroup": el.get("nested_subgroup"),
        "label": el.get("label"),
        "element_archetype": el.get("element_archetype"),
    }
    return "cf_" + stable_hash(identity)[:14]


def build_canonical_forest(record_units: list[dict]) -> dict:
    """Build one canonical tree per composition family from record units."""
    trees: dict[str, dict] = {}
    per_family_records = defaultdict(list)
    for unit in record_units:
        per_family_records[unit.get("record_family", "UNKNOWN")].append(unit)

    for family, units in per_family_records.items():
        fields = {}
        record_field_presence = defaultdict(set)
        cooccurrence = Counter()
        for unit in units:
            elements = walk_elements(unit["raw_composition"])
            seen = set()
            for el in elements:
                fid = field_id_for(el)
                seen.add(fid)
                f = fields.setdefault(fid, {
                    "field_id": fid,
                    "label": el.get("label"),
                    "canonical_path": el.get("canonical_path"),
                    "form_group": el.get("form_group"),
                    "nested_subgroup": el.get("nested_subgroup"),
                    "composition_archetype": el.get("composition_archetype"),
                    "entry_archetype": el.get("entry_archetype"),
                    "entry_type": el.get("entry_type"),
                    "element_archetype": el.get("element_archetype"),
                    "dv_types": Counter(),
                    "observed_values": Counter(),
                    "known_count": 0,
                    "unknown_count": 0,
                    "record_count": 0,
                    "occurrence_count": 0,
                })
                f["dv_types"][str(el.get("dv_type") or "UNKNOWN")] += 1
                val = el.get("display_value")
                if val is not None:
                    f["observed_values"][str(val)] += 1
                if el.get("is_known"):
                    f["known_count"] += 1
                else:
                    f["unknown_count"] += 1
                f["occurrence_count"] += 1
            for fid in seen:
                fields[fid]["record_count"] += 1
                record_field_presence[unit["unit_id"]].add(fid)
            # co-occurrence within the same record; capped for speed.
            s = list(seen)
            for i in range(min(len(s), 100)):
                for j in range(i + 1, min(len(s), 100)):
                    cooccurrence[tuple(sorted((s[i], s[j])))] += 1

        total_records = len(units)
        nodes = []
        edges = []
        group_ids = {}
        subgroup_ids = {}
        for fid, f in fields.items():
            group_label = f["form_group"] or "Composition"
            subgroup_label = f["nested_subgroup"] or "Top-level fields"
            gid = "group_" + stable_hash({"family": family, "group": group_label})[:12]
            sid = "subgroup_" + stable_hash({"family": family, "group": group_label, "subgroup": subgroup_label})[:12]
            if gid not in group_ids:
                group_ids[gid] = True
                nodes.append({"node_id": gid, "node_type": "FORM_GROUP", "label": group_label})
            if sid not in subgroup_ids:
                subgroup_ids[sid] = True
                nodes.append({"node_id": sid, "node_type": "NESTED_SUBGROUP", "label": subgroup_label, "parent": gid})
                edges.append({"source": gid, "target": sid, "edge_type": "containment"})
            dv_type = f["dv_types"].most_common(1)[0][0] if f["dv_types"] else "UNKNOWN"
            kind = infer_kind(dv_type)
            coverage = f["record_count"] / total_records if total_records else 0.0
            distinct_count = len(f["observed_values"])
            occurrence_count = max(1, f["occurrence_count"])
            distinct_ratio = distinct_count / occurrence_count
            f_export = {
                **{k: v for k, v in f.items() if k not in {"dv_types", "observed_values"}},
                "dv_type": dv_type,
                "kind": kind,
                "coverage": coverage,
                "sparsity": 1.0 - coverage,
                "distinct_count": distinct_count,
                "distinct_ratio": distinct_ratio,
                "top_values": [x for x, _ in f["observed_values"].most_common(10)],
                "has_null_flavour": f["unknown_count"] > 0,
                "parent": sid,
            }
            fields[fid] = f_export
            nodes.append({"node_id": fid, "node_type": "FORM_ELEMENT", **f_export})
            edges.append({"source": sid, "target": fid, "edge_type": "containment"})
        # Build simple cooccurrence edges between canonical fields.
        co_edges = []
        for (a, b), c in cooccurrence.items():
            if c > 1:
                co_edges.append({"source": a, "target": b, "edge_type": "cooccurrence", "count": c})
        trees[family] = {
            "tree_id": "tree_" + stable_hash(family)[:12],
            "record_family": family,
            "record_count": total_records,
            "nodes": nodes,
            "edges": edges,
            "cooccurrence_edges": co_edges,
            "fields": list(fields.values()),
        }
    return {"trees": trees, "tree_count": len(trees), "record_count": len(record_units)}


def flatten_fields(forest: dict) -> list[dict]:
    out = []
    for family, tree in forest.get("trees", {}).items():
        for f in tree.get("fields", []):
            x = dict(f)
            x["record_family"] = family
            out.append(x)
    return out
