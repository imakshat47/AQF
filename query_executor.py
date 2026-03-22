# query_executor.py

from __future__ import annotations
from typing import Any, Dict, List, Tuple
import time
from composition_loader import load_json
from utils import safe_get, ensure_list

def parse_field_key(field_key: str) -> Dict:
    comp_arch, entry_arch, cluster_path_str, element_name, element_at = field_key.split("|", 4)
    return {
        "composition_archetype": comp_arch,
        "entry_archetype": entry_arch,
        "cluster_path_str": cluster_path_str,
        "element_name": element_name,
        "element_at_code": element_at
    }

def extract_element_values(doc: dict, field_meta: Dict) -> List[Tuple[Any, str]]:
    """
    Return all matching occurrences of a field.
    Uses cluster-path-aware matching and element_name + at-code for robustness.
    """
    comp = safe_get(doc, ["versions", "data"], {}) or {}
    if comp.get("archetype_node_id") != field_meta["composition_archetype"]:
        return []

    content = ensure_list(comp.get("content", []))
    hits = []

    def walk(obj: Any, cluster_stack: List[str]):
        if isinstance(obj, dict) and "type" in obj:
            t = obj.get("type")

            if t == "CLUSTER":
                c_name = safe_get(obj, ["name", "value"], "") or "(cluster)"
                cluster_stack.append(c_name)
                for _, v in obj.items():
                    walk(v, cluster_stack)
                cluster_stack.pop()
                return

            if t == "ELEMENT":
                cluster_path_str = " / ".join(cluster_stack) if cluster_stack else "(no cluster)"
                el_name = safe_get(obj, ["name", "value"], "") or ""
                el_at = obj.get("archetype_node_id", "")

                if (
                    cluster_path_str == field_meta["cluster_path_str"] and
                    el_name == field_meta["element_name"] and
                    el_at == field_meta["element_at_code"]
                ):
                    dv_type = safe_get(obj, ["value", "type"], None)
                    val = safe_get(obj, ["value", "value"], None)
                    if val is None:
                        val = safe_get(obj, ["value", "magnitude"], None)
                    if val is None:
                        val = safe_get(obj, ["value", "defining_code", "code_string"], None)
                    if val is None:
                        dv_type = "NULL_FLAVOUR"
                        val = safe_get(obj, ["null_flavour", "value"], None)

                    hits.append((val, dv_type))
                    return

            for _, v in obj.items():
                walk(v, cluster_stack)

        elif isinstance(obj, list):
            for it in obj:
                walk(it, cluster_stack)

        elif isinstance(obj, dict):
            for _, v in obj.items():
                walk(v, cluster_stack)

    for entry in content:
        if not isinstance(entry, dict):
            continue
        if entry.get("archetype_node_id") != field_meta["entry_archetype"]:
            continue

        for root_key in ["data", "description"]:
            if root_key in entry:
                walk(entry[root_key], [])

    return hits

def match_value(dv_type: str, op: str, doc_value: Any, target: Any) -> bool:
    if op == "is_known":
        return doc_value is not None and dv_type != "NULL_FLAVOUR"

    if op == "is_unknown":
        return dv_type == "NULL_FLAVOUR"

    if doc_value is None:
        return False

    if dv_type in ("DV_COUNT", "DV_QUANTITY"):
        try:
            v = float(doc_value)
            if op == "between":
                lo, hi = target
                return float(lo) <= v <= float(hi)
            t = float(target)
        except Exception:
            return False

        return {
            "=": v == t,
            "!=": v != t,
            ">": v > t,
            "<": v < t
        }.get(op, False)

    if dv_type in ("DV_DATE", "DV_DATE_TIME"):
        s = str(doc_value)
        if op == "between":
            lo, hi = target
            return str(lo) <= s <= str(hi)
        return {
            "=": s == str(target),
            "<": s < str(target),
            ">": s > str(target),
            "contains": str(target).lower() in s.lower()
        }.get(op, False)

    # text / coded text / boolean / null fallback
    s = str(doc_value)
    if op == "between":
        return False
    return {
        "=": s == str(target),
        "!=": s != str(target),
        "contains": str(target).lower() in s.lower()
    }.get(op, False)

def run_query(files: List, query_plan: Dict, occurrence_semantics: str = "ALL", limit: int = 100):
    """
    Execute query over local JSON files.

    Returns:
    {
      "scanned": int,
      "matched": int,
      "elapsed_sec": float,
      "sec_per_doc": float,
      "rows": [...],
      "funnel": [...]
    }
    """
    t0 = time.perf_counter()

    scanned = 0
    matched = 0
    rows = []

    predicates = query_plan.get("predicates", [])

    # Funnel structure:
    # stage 0 = total scanned
    # stage 1..N = docs surviving predicate 1..N
    funnel_counts = [0] * (len(predicates) + 1)

    for fp in files:
        doc = load_json(fp)
        scanned += 1
        funnel_counts[0] += 1

        ok = True

        for idx, p in enumerate(predicates):
            meta = parse_field_key(p["field_key"])
            occ = extract_element_values(doc, meta)

            if not occ:
                ok = False
                break

            if occurrence_semantics == "ALL":
                passed = all(match_value(dtype, p["operator"], val, p["value"]) for val, dtype in occ)
            else:
                passed = any(match_value(dtype, p["operator"], val, p["value"]) for val, dtype in occ)

            if not passed:
                ok = False
                break

            funnel_counts[idx + 1] += 1

        if ok:
            matched += 1
            row = {"_file": str(fp.name)}

            for out_fk in query_plan.get("outputs", []):
                meta = parse_field_key(out_fk)
                occ = extract_element_values(doc, meta)
                vals = [v for v, _ in occ if v is not None]
                row[out_fk] = vals if len(vals) > 1 else (vals[0] if vals else None)

            rows.append(row)

        if len(rows) >= limit:
            break

    elapsed = time.perf_counter() - t0
    sec_per_doc = elapsed / scanned if scanned > 0 else 0.0

    funnel = []
    funnel.append({
        "stage": "Scanned files",
        "count": funnel_counts[0]
    })

    for idx, p in enumerate(predicates):
        funnel.append({
            "stage": f"After predicate {idx+1}",
            "count": funnel_counts[idx + 1],
            "field_key": p["field_key"],
            "operator": p["operator"],
            "value": p["value"]
        })

    return {
        "scanned": scanned,
        "matched": matched,
        "elapsed_sec": round(elapsed, 4),
        "sec_per_doc": sec_per_doc,
        "rows": rows,
        "funnel": funnel
    }
