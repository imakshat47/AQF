from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any, Iterable

LIST_LIKE_KEYS = {
    "content", "items", "events", "activities", "protocol", "state",
    "other_context", "data", "rows", "cells", "versions", "description",
    "ism_transition", "instruction_details"
}

ENTRY_CLASSES = {"OBSERVATION", "EVALUATION", "INSTRUCTION", "ACTION", "ADMIN_ENTRY"}
CONTAINER_CLASSES = {"SECTION", "CLUSTER", "ITEM_TREE", "ITEM_LIST", "ITEM_TABLE", "ITEM_SINGLE"}

# openEHR child branches to inspect. `description` is critical for ACTION.procedure-sus in ORBDA.
CHILD_KEYS = [
    "content", "items", "events", "activities", "data", "state", "protocol",
    "other_context", "rows", "cells", "item", "description", "ism_transition",
    "instruction_details"
]


def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def stable_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def name_of(node: Any) -> str:
    if not isinstance(node, dict):
        return ""
    name = node.get("name")
    if isinstance(name, dict):
        return str(name.get("value", "") or "")
    if isinstance(name, str):
        return name
    return ""


def archetype_of(node: Any) -> str:
    if not isinstance(node, dict):
        return ""
    arch = node.get("archetype_node_id")
    if isinstance(arch, str) and arch:
        return arch
    details = node.get("archetype_details", {})
    if isinstance(details, dict):
        aid = details.get("archetype_id", {})
        if isinstance(aid, dict):
            return str(aid.get("value", "") or "")
        if isinstance(aid, str):
            return aid
    return ""


def uid_of(node: Any) -> str:
    if not isinstance(node, dict):
        return ""
    uid = node.get("uid") or node.get("id")
    if isinstance(uid, dict):
        return str(uid.get("value", "") or uid.get("id", "") or "")
    if isinstance(uid, str):
        return uid
    return ""


def detect_rm_class(node: Any) -> str:
    if not isinstance(node, dict):
        return "UNKNOWN"
    typ = node.get("type") or node.get("_type")
    if isinstance(typ, str) and typ:
        return typ.upper()
    arch = archetype_of(node).upper()
    for token in ["COMPOSITION", "SECTION", "OBSERVATION", "EVALUATION", "INSTRUCTION", "ACTION", "ADMIN_ENTRY", "CLUSTER", "ELEMENT", "ITEM_TREE", "ITEM_LIST", "ITEM_TABLE", "ITEM_SINGLE"]:
        if token in arch:
            return token
    return "UNKNOWN"


def looks_like_composition(obj: Any) -> bool:
    return isinstance(obj, dict) and ("COMPOSITION" in archetype_of(obj).upper() or detect_rm_class(obj) == "COMPOSITION")


def normalize_list_like_keys(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in {"content", "items", "events", "activities", "protocol", "state", "other_context", "rows", "cells", "versions"}:
                out[k] = [normalize_list_like_keys(x) for x in as_list(v)]
            else:
                out[k] = normalize_list_like_keys(v)
        return out
    if isinstance(obj, list):
        return [normalize_list_like_keys(x) for x in obj]
    return obj


def find_compositions(obj: Any) -> list[dict]:
    if looks_like_composition(obj):
        return [obj]
    found = []
    if isinstance(obj, dict):
        for v in obj.values():
            found.extend(find_compositions(v))
    elif isinstance(obj, list):
        for x in obj:
            found.extend(find_compositions(x))
    return found


def scan_json_folder(folder: Path) -> list[dict]:
    units = []
    for path in sorted(folder.rglob("*.json")):
        if ".cache" in path.parts or "results" in path.parts:
            continue
        try:
            obj = load_json(path)
        except Exception:
            continue
        comps = find_compositions(obj)
        if not comps:
            continue
        ehr_id = None
        if isinstance(obj, dict):
            e = obj.get("ehr_id") or obj.get("ehrId")
            if isinstance(e, dict): ehr_id = e.get("value")
            elif isinstance(e, str): ehr_id = e
        for i, comp in enumerate(comps):
            comp = normalize_list_like_keys(comp)
            subject_id = None
            try:
                first_content = as_list(comp.get("content"))[0]
                ext = first_content.get("subject", {}).get("external_ref", {}).get("id", {})
                if isinstance(ext, dict): subject_id = ext.get("value")
            except Exception:
                pass
            family = archetype_of(comp) or "UNKNOWN_COMPOSITION"
            units.append({
                "unit_id": stable_hash({"path": str(path), "index": i, "uid": uid_of(comp), "family": family}),
                "source_file": str(path), "ehr_id": ehr_id or subject_id, "subject_id": subject_id,
                "record_family": family, "composition_name": name_of(comp), "composition_uid": uid_of(comp),
                "raw_composition": comp,
            })
    return units


def _to_num(x):
    try:
        if x is None or x == "": return None
        if isinstance(x, bool): return x
        if isinstance(x, (int, float)): return x
        s = str(x)
        return float(s) if "." in s else int(s)
    except Exception:
        return x


def value_info(element: dict) -> dict:
    """Extract value from openEHR DV_* datatypes, including magnitude-based numeric types."""
    if "value" in element:
        val = element.get("value")
        if isinstance(val, dict):
            dv_type = str(val.get("type", "UNKNOWN"))
            raw = None
            display = None
            units = val.get("units")
            if dv_type in {"DV_COUNT", "DV_QUANTITY"}:
                raw = _to_num(val.get("magnitude", val.get("value")))
                display = raw if units is None else f"{raw} {units}"
            elif dv_type == "DV_PROPORTION":
                num, den = _to_num(val.get("numerator")), _to_num(val.get("denominator"))
                raw = None if num is None or den in (None, 0) else num / den
                display = f"{num}/{den}" if num is not None and den is not None else raw
            elif dv_type == "DV_BOOLEAN":
                v = val.get("value")
                raw = str(v).lower() == "true" if isinstance(v, str) else bool(v)
                display = str(raw).lower()
            else:
                raw = val.get("value")
                display = raw
            code = None; term = None
            dc = val.get("defining_code")
            if isinstance(dc, dict):
                code = dc.get("code_string")
                tid = dc.get("terminology_id", {})
                if isinstance(tid, dict): term = tid.get("value")
            return {"is_known": True, "value": raw, "display_value": display, "dv_type": dv_type,
                    "code_string": code, "terminology_id": term, "units": units, "null_flavour": None}
        return {"is_known": True, "value": val, "display_value": val, "dv_type": "UNKNOWN",
                "code_string": None, "terminology_id": None, "units": None, "null_flavour": None}
    if "null_flavour" in element:
        nf = element.get("null_flavour")
        if isinstance(nf, dict):
            code = nf.get("defining_code", {}).get("code_string") if isinstance(nf.get("defining_code"), dict) else None
            return {"is_known": False, "value": None, "display_value": nf.get("value", "unknown"),
                    "dv_type": "NULL_FLAVOUR", "code_string": code, "terminology_id": None, "units": None,
                    "null_flavour": nf.get("value", "unknown")}
        return {"is_known": False, "value": None, "display_value": str(nf), "dv_type": "NULL_FLAVOUR",
                "code_string": None, "terminology_id": None, "units": None, "null_flavour": str(nf)}
    return {"is_known": False, "value": None, "display_value": None, "dv_type": "UNKNOWN",
            "code_string": None, "terminology_id": None, "units": None, "null_flavour": None}


def iter_children(node: dict) -> Iterable[tuple[str, Any]]:
    for key in CHILD_KEYS:
        if key in node:
            v = node[key]
            if isinstance(v, list):
                for x in v: yield key, x
            elif isinstance(v, dict):
                yield key, v


def walk_elements(node: Any, ctx: dict | None = None) -> list[dict]:
    ctx = dict(ctx or {})
    out = []
    if not isinstance(node, dict): return out
    rm = detect_rm_class(node)
    label = name_of(node)
    arch = archetype_of(node)

    if rm == "COMPOSITION":
        ctx.update({"composition_name": label or ctx.get("composition_name"), "composition_archetype": arch or ctx.get("composition_archetype")})
    elif rm == "SECTION":
        ctx.update({"section_name": label or ctx.get("section_name"), "section_archetype": arch or ctx.get("section_archetype")})
    elif rm in ENTRY_CLASSES:
        ctx.update({"entry_name": label or ctx.get("entry_name"), "entry_archetype": arch or ctx.get("entry_archetype"), "entry_type": rm})
        # ACTION.description often lacks container label; keep ACTION label as group.
    elif rm in CONTAINER_CLASSES:
        parts = list(ctx.get("cluster_path_parts", []))
        if label and label not in parts[-2:]: parts.append(label)
        ctx.update({"cluster_path_parts": parts, "cluster_rm_class": rm})
    elif rm == "ELEMENT":
        vi = value_info(node)
        cluster_path = " / ".join(ctx.get("cluster_path_parts", [])) or "Top-level fields"
        group = ctx.get("entry_name") or ctx.get("section_name") or ctx.get("composition_name") or "Composition"
        element_label = label or arch or "Unnamed element"
        canonical_path = f"{group} / {cluster_path} / {element_label}"
        out.append({
            "label": element_label, "canonical_path": canonical_path, "form_group": group,
            "nested_subgroup": cluster_path, "rm_class": rm, "element_archetype": arch,
            "composition_archetype": ctx.get("composition_archetype"), "entry_archetype": ctx.get("entry_archetype"),
            "entry_type": ctx.get("entry_type"), "value": vi.get("value"), "display_value": vi.get("display_value"),
            "dv_type": vi.get("dv_type"), "is_known": vi.get("is_known"), "null_flavour": vi.get("null_flavour"),
            "code_string": vi.get("code_string"), "units": vi.get("units"),
        })
        return out

    for _, child in iter_children(node):
        out.extend(walk_elements(child, ctx))
    return out
