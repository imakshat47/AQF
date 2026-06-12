#!/usr/bin/env python3
"""
adaptive_form_generator_coverage_v2.py

Coverage-friendly AQF form generator.

Compared with the earlier generator, this version supports:
  - larger target field counts, e.g. 35 fields
  - keeping all operator-aware forms, even low-utility/demographic forms
  - optional workload-priority fields using aliases
  - less aggressive 60/40 filter-output split

Input:
  operator_aware_forms.json

Output:
  aqf_forms.json, aqf_forms_summary.csv, aqf_form_fields.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


def norm(x: Any) -> str:
    if x is None:
        return ""
    s = str(x).strip().lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def slug(x: Any) -> str:
    s = norm(x).replace(" ", "_")
    return s or "field"


def load_json(path: Optional[str | Path]) -> Dict[str, Any]:
    if not path or not Path(path).exists():
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_aliases(path: Optional[str | Path]) -> Dict[str, List[str]]:
    payload = load_json(path)
    return payload.get("field_aliases", {}) if payload else {}


def alias_terms(term: str, alias_map: Dict[str, List[str]]) -> Set[str]:
    out = {norm(term)}
    nt = norm(term)
    for k, vals in alias_map.items():
        group = [k] + list(vals or [])
        ng = {norm(v) for v in group}
        if nt in ng:
            out.update(ng)
    return {x for x in out if x}


def alias_match(required: str, candidate: str, alias_map: Dict[str, List[str]]) -> bool:
    c = norm(candidate)
    return any(a == c or a in c or c in a for a in alias_terms(required, alias_map))


def workload_required_fields(workload_json: Optional[str | Path]) -> List[str]:
    if not workload_json:
        return []
    payload = load_json(workload_json)
    queries = payload if isinstance(payload, list) else payload.get("queries", [])
    out = []
    for q in queries:
        out.extend(q.get("required_fields", []))
    return sorted(set(out))


def infer_ui_group(path: str) -> str:
    if not path:
        return "General"
    parts = [p for p in str(path).split("/") if p]
    raw = parts[-2] if len(parts) >= 2 else (parts[0] if parts else "General")
    toks = raw.split("|")
    if len(toks) >= 2:
        return toks[1].replace("_", " ").title()
    return raw.replace("_", " ").title()


def field_from_input(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "field_id": f"filter_{slug(item.get('name'))}_{abs(hash(item.get('canonical_id'))) % 100000}",
        "canonical_id": item.get("canonical_id"),
        "name": item.get("name"),
        "role": "filter",
        "datatype": item.get("datatype"),
        "operator": item.get("best_input_operator") or "equals",
        "operator_class": "filter",
        "control_type": (item.get("input_operators") or [{}])[0].get("control_type", "generic_input"),
        "score": float(item.get("best_input_score") or 0.0),
        "queriability": float(item.get("queriability") or 0.0),
        "path": item.get("path", ""),
        "archetype_node_id": item.get("archetype_node_id"),
        "archetype_id": item.get("archetype_id"),
        "template_id": item.get("template_id"),
        "required": False,
        "ui_group": infer_ui_group(item.get("path", "")),
    }


def field_from_output(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "field_id": f"output_{slug(item.get('name'))}_{abs(hash(item.get('canonical_id'))) % 100000}",
        "canonical_id": item.get("canonical_id"),
        "name": item.get("name"),
        "role": "output",
        "datatype": item.get("datatype"),
        "operator": item.get("best_output_operator") or "project",
        "operator_class": "projection",
        "control_type": (item.get("output_operators") or [{}])[0].get("control_type", "result_column"),
        "score": float(item.get("best_output_score") or 0.0),
        "queriability": float(item.get("queriability") or 0.0),
        "path": item.get("path", ""),
        "archetype_node_id": item.get("archetype_node_id"),
        "archetype_id": item.get("archetype_id"),
        "template_id": item.get("template_id"),
        "required": False,
        "ui_group": infer_ui_group(item.get("path", "")),
    }


def prioritize(fields: List[Dict[str, Any]], required_fields: List[str], alias_map: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    def key(f):
        is_req = any(alias_match(r, f.get("name", ""), alias_map) for r in required_fields)
        return (1 if is_req else 0, float(f.get("score") or 0.0))
    return sorted(fields, key=key, reverse=True)


def dedupe(fields: List[Dict[str, Any]], role_sensitive: bool = True) -> List[Dict[str, Any]]:
    seen = set(); out = []
    for f in fields:
        key = (f.get("role"), f.get("canonical_id")) if role_sensitive else f.get("canonical_id")
        if key in seen:
            continue
        seen.add(key); out.append(f)
    return out


def generate_forms(payload: Dict[str, Any], target_total_fields: int, max_filters: int, max_outputs: int, kappa: float, eta: float, required_fields: List[str], alias_map: Dict[str, List[str]], preserve_all_forms: bool) -> List[Dict[str, Any]]:
    forms = []
    for opf in payload.get("operator_aware_forms", []):
        filters = dedupe([field_from_input(x) for x in opf.get("operator_input_tree", [])], role_sensitive=False)
        outputs = dedupe([field_from_output(x) for x in opf.get("operator_output_tree", [])], role_sensitive=False)
        filters = prioritize(filters, required_fields, alias_map)
        outputs = prioritize(outputs, required_fields, alias_map)

        budget = int(max(kappa - eta * int(opf.get("max_depth") or 0), 0))
        target = min(target_total_fields, budget) if kappa > 0 else target_total_fields
        target_filters = min(max_filters, max(1, int(target * 0.65)))
        target_outputs = min(max_outputs, max(1, target - target_filters))

        selected_filters = filters[:target_filters]
        selected_outputs = outputs[:target_outputs]
        # Fill any remaining room with best unused filters/outputs.
        selected_keys = {(f.get("role"), f.get("canonical_id")) for f in selected_filters + selected_outputs}
        rest = [f for f in filters[target_filters:] + outputs[target_outputs:] if (f.get("role"), f.get("canonical_id")) not in selected_keys]
        rest = sorted(rest, key=lambda x: float(x.get("score") or 0.0), reverse=True)
        while len(selected_filters) + len(selected_outputs) < target and rest:
            f = rest.pop(0)
            if f["role"] == "filter" and len(selected_filters) < max_filters:
                selected_filters.append(f)
            elif f["role"] == "output" and len(selected_outputs) < max_outputs:
                selected_outputs.append(f)
            elif len(selected_filters) < max_filters:
                f2 = dict(f); f2["role"] = "filter"; selected_filters.append(f2)
            elif len(selected_outputs) < max_outputs:
                f2 = dict(f); f2["role"] = "output"; selected_outputs.append(f2)
            else:
                break

        if not preserve_all_forms and not selected_filters and not selected_outputs:
            continue

        group = opf.get("form_group") or "AQF Form"
        fields = selected_filters + selected_outputs
        complexity = len(fields) + eta * int(opf.get("max_depth") or 0)
        forms.append({
            "form_id": f"aqf_{slug(group)}_{abs(hash(opf.get('operator_aware_form_id'))) % 100000}",
            "source_operator_aware_form_id": opf.get("operator_aware_form_id"),
            "canonical_form_id": opf.get("canonical_form_id"),
            "form_group": group,
            "title": f"AQF Query Form - {group}",
            "description": "Coverage-friendly AQF query form generated with benchmark-prioritized field selection.",
            "filters": selected_filters,
            "outputs": selected_outputs,
            "relationships": opf.get("operator_relationship_tree", []),
            "utility": sum(float(f.get("score") or 0.0) for f in fields),
            "complexity": complexity,
            "max_depth": int(opf.get("max_depth") or 0),
            "selected_field_count": len(fields),
            "relationship_count": len(opf.get("operator_relationship_tree", [])),
        })
    return sorted(forms, key=lambda x: float(x.get("utility") or 0.0), reverse=True)


def save_outputs(forms: List[Dict[str, Any]], output_dir: str | Path, meta: Dict[str, Any]) -> None:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    payload = {"metadata": dict(meta, form_count=len(forms)), "aqf_forms": forms}
    (out / "aqf_forms.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    with open(out / "aqf_forms_summary.csv", "w", newline="", encoding="utf-8") as f:
        cols = ["form_id", "form_group", "utility", "complexity", "max_depth", "selected_field_count", "filter_count", "output_count", "relationship_count"]
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for form in forms:
            w.writerow({"form_id": form["form_id"], "form_group": form["form_group"], "utility": form["utility"], "complexity": form["complexity"], "max_depth": form["max_depth"], "selected_field_count": form["selected_field_count"], "filter_count": len(form["filters"]), "output_count": len(form["outputs"]), "relationship_count": form["relationship_count"]})
    with open(out / "aqf_form_fields.csv", "w", newline="", encoding="utf-8") as f:
        cols = ["form_id", "form_group", "field_id", "canonical_id", "name", "role", "datatype", "operator", "score", "queriability", "ui_group", "path"]
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for form in forms:
            for field in form["filters"] + form["outputs"]:
                w.writerow({"form_id": form["form_id"], "form_group": form["form_group"], "field_id": field.get("field_id"), "canonical_id": field.get("canonical_id"), "name": field.get("name"), "role": field.get("role"), "datatype": field.get("datatype"), "operator": field.get("operator"), "score": field.get("score"), "queriability": field.get("queriability"), "ui_group": field.get("ui_group"), "path": field.get("path")})


def main() -> None:
    ap = argparse.ArgumentParser(description="Coverage-friendly AQF adaptive form generator.")
    ap.add_argument("--operator_aware_forms_json", required=True)
    ap.add_argument("--output_dir", required=True)
    ap.add_argument("--workload_json", default=None)
    ap.add_argument("--aliases_json", default=None)
    ap.add_argument("--target_total_fields", type=int, default=35)
    ap.add_argument("--kappa", type=float, default=40.0)
    ap.add_argument("--eta", type=float, default=1.0)
    ap.add_argument("--max_filters", type=int, default=25)
    ap.add_argument("--max_outputs", type=int, default=15)
    ap.add_argument("--preserve_all_forms", action="store_true")
    args = ap.parse_args()
    payload = load_json(args.operator_aware_forms_json)
    alias_map = load_aliases(args.aliases_json)
    req = workload_required_fields(args.workload_json)
    forms = generate_forms(payload, args.target_total_fields, args.max_filters, args.max_outputs, args.kappa, args.eta, req, alias_map, args.preserve_all_forms)
    save_outputs(forms, args.output_dir, {"target_total_fields": args.target_total_fields, "kappa": args.kappa, "eta": args.eta, "max_filters": args.max_filters, "max_outputs": args.max_outputs, "preserve_all_forms": args.preserve_all_forms, "workload_priority_fields": len(req)})
    print(f"Generated {len(forms)} coverage-friendly AQF forms in {args.output_dir}")
    for form in forms:
        print(f" - {form['form_id']} | group={form['form_group']} | fields={form['selected_field_count']} | complexity={form['complexity']}")

if __name__ == "__main__":
    main()
