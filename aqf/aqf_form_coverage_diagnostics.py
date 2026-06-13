#!/usr/bin/env python3
"""
aqf_form_coverage_diagnostics.py

Diagnose why benchmark queries are not covered by generated AQF forms.

Checks whether benchmark-required fields are present at each stage:
  1. reduced_schema_graph.json
  2. canonical_forms.json
  3. operator_aware_forms.json
  4. aqf_forms.json

Outputs:
  stage_field_coverage.csv
  missing_by_stage.csv
  form_group_summary.csv
  diagnostic_summary.json
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
    s = str(x).lower().strip()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def load_json(path: Optional[str | Path]) -> Dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def load_aliases(path: Optional[str | Path]) -> Dict[str, List[str]]:
    if not path or not Path(path).exists():
        return {}
    payload = load_json(path)
    return payload.get("field_aliases", {})


def aliases_for(field: str, alias_map: Dict[str, List[str]]) -> Set[str]:
    out = {norm(field)}
    nf = norm(field)
    for k, vals in alias_map.items():
        group = [k] + list(vals or [])
        ng = {norm(v) for v in group}
        if nf in ng:
            out.update(ng)
    return {x for x in out if x}


def match(field: str, candidate: str, alias_map: Dict[str, List[str]]) -> bool:
    c = norm(candidate)
    if not c:
        return False
    for a in aliases_for(field, alias_map):
        if a == c or a in c or c in a:
            return True
    return False


def workload_fields(workload_json: str | Path) -> List[Dict[str, Any]]:
    payload = load_json(workload_json)
    queries = payload if isinstance(payload, list) else payload.get("queries", [])
    rows = []
    for q in queries:
        for f in q.get("required_fields", []):
            rows.append({
                "query_id": q.get("query_id"),
                "query_name": q.get("query_name"),
                "category": q.get("category"),
                "query_complexity": q.get("query_complexity"),
                "required_field": f,
            })
    return rows


def reduced_fields(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for n in payload.get("nodes", []):
        if n.get("aqf_type") == "leaf":
            rows.append({"name": n.get("name"), "stage_id": n.get("node_id"), "path": n.get("path", ""), "datatype": n.get("datatype")})
    return rows


def canonical_fields(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for form in payload.get("canonical_forms", []):
        for key in ("input_tree_nodes", "output_tree_nodes"):
            for n in form.get(key, []):
                if n.get("canonical_type") == "form_element":
                    rows.append({"name": n.get("name"), "stage_id": n.get("canonical_id"), "path": n.get("path", ""), "datatype": n.get("datatype"), "form_group": form.get("form_group")})
    return rows


def operator_fields(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for form in payload.get("operator_aware_forms", []):
        for key in ("operator_input_tree", "operator_output_tree"):
            for n in form.get(key, []):
                rows.append({"name": n.get("name"), "stage_id": n.get("canonical_id"), "path": n.get("path", ""), "datatype": n.get("datatype"), "form_group": form.get("form_group"), "operator": n.get("best_input_operator") or n.get("best_output_operator")})
    return rows


def aqf_fields(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for form in payload.get("aqf_forms", []):
        for key in ("filters", "outputs"):
            for n in form.get(key, []):
                rows.append({"name": n.get("name"), "stage_id": n.get("canonical_id"), "path": n.get("path", ""), "datatype": n.get("datatype"), "form_group": form.get("form_group"), "operator": n.get("operator"), "role": key[:-1], "form_id": form.get("form_id")})
    return rows


def present(required: str, candidates: List[Dict[str, Any]], alias_map: Dict[str, List[str]]) -> bool:
    return any(match(required, c.get("name", ""), alias_map) for c in candidates)


def examples(required: str, candidates: List[Dict[str, Any]], alias_map: Dict[str, List[str]]) -> str:
    ex = [c.get("name", "") for c in candidates if match(required, c.get("name", ""), alias_map)]
    return "; ".join(sorted(set(ex))[:5])


def main() -> None:
    ap = argparse.ArgumentParser(description="Diagnose AQF field coverage by pipeline stage.")
    ap.add_argument("--workload_json", required=True)
    ap.add_argument("--reduced_schema_graph_json", required=True)
    ap.add_argument("--canonical_forms_json", required=True)
    ap.add_argument("--operator_aware_forms_json", required=True)
    ap.add_argument("--aqf_forms_json", required=True)
    ap.add_argument("--aliases_json", default=None)
    ap.add_argument("--output_dir", required=True)
    args = ap.parse_args()

    alias_map = load_aliases(args.aliases_json)
    wrows = workload_fields(args.workload_json)
    required_unique = sorted(set(r["required_field"] for r in wrows))

    stages = {
        "reduced_schema_graph": reduced_fields(load_json(args.reduced_schema_graph_json)),
        "canonical_forms": canonical_fields(load_json(args.canonical_forms_json)),
        "operator_aware_forms": operator_fields(load_json(args.operator_aware_forms_json)),
        "aqf_forms": aqf_fields(load_json(args.aqf_forms_json)),
    }

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    coverage_rows = []
    for f in required_unique:
        row = {"required_field": f}
        for stage, candidates in stages.items():
            row[f"present_in_{stage}"] = present(f, candidates, alias_map)
            row[f"matched_names_{stage}"] = examples(f, candidates, alias_map)
        coverage_rows.append(row)

    with open(out / "stage_field_coverage.csv", "w", newline="", encoding="utf-8") as fp:
        cols = list(coverage_rows[0].keys()) if coverage_rows else ["required_field"]
        writer = csv.DictWriter(fp, fieldnames=cols)
        writer.writeheader()
        writer.writerows(coverage_rows)

    missing_rows = []
    for row in coverage_rows:
        for stage in stages:
            if not row[f"present_in_{stage}"]:
                missing_rows.append({"required_field": row["required_field"], "missing_stage": stage})
    with open(out / "missing_by_stage.csv", "w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=["required_field", "missing_stage"])
        writer.writeheader()
        writer.writerows(missing_rows)

    form_rows = []
    aqf_payload = load_json(args.aqf_forms_json)
    for form in aqf_payload.get("aqf_forms", []):
        form_rows.append({
            "form_id": form.get("form_id"),
            "form_group": form.get("form_group"),
            "complexity": form.get("complexity"),
            "selected_field_count": form.get("selected_field_count"),
            "filter_count": len(form.get("filters", [])),
            "output_count": len(form.get("outputs", [])),
            "field_names": "; ".join(sorted(set([x.get("name", "") for x in form.get("filters", []) + form.get("outputs", [])]))),
        })
    with open(out / "form_group_summary.csv", "w", newline="", encoding="utf-8") as fp:
        cols = ["form_id", "form_group", "complexity", "selected_field_count", "filter_count", "output_count", "field_names"]
        writer = csv.DictWriter(fp, fieldnames=cols)
        writer.writeheader()
        writer.writerows(form_rows)

    summary = {
        "required_unique_fields": len(required_unique),
        "stage_coverage": {
            stage: sum(1 for f in required_unique if present(f, candidates, alias_map)) / max(len(required_unique), 1)
            for stage, candidates in stages.items()
        },
        "stage_field_counts": {stage: len(set(c.get("name", "") for c in candidates)) for stage, candidates in stages.items()},
        "aqf_form_count": len(aqf_payload.get("aqf_forms", [])),
    }
    (out / "diagnostic_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Diagnostics saved to: {out}")


if __name__ == "__main__":
    main()
