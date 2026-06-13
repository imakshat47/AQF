#!/usr/bin/env python3
"""
aqf_query_realizer.py

Realize benchmark workload queries as openEHR-style AQL query drafts using generated AQF forms.

Inputs:
  --aqf_forms_json output/aqf_forms/aqf_forms.json
  --workload_json aqf_benchmark_workload.json

Outputs:
  realized_queries.json
  realized_queries.csv
  query_realization_summary.csv
  aql/<query_id>.aql

Purpose:
  This module moves AQF evaluation from form expressivity toward query realization.
  It checks whether generated AQF forms expose the required fields/operators/contexts,
  maps workload constraints to AQL WHERE predicates, and emits executable-style AQL drafts.

Important:
  The generated AQL is template-style because exact openEHR AQL paths depend on local
  archetype/template path conventions. The module preserves source paths and archetype IDs
  so you can later refine path conversion for your CDR/AQL engine.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


OPERATOR_ALIASES = {
    "equals": {"equals", "multi_select"},
    "multi_select": {"multi_select", "equals"},
    "range": {"range", "greater_than_less_than", "date_range"},
    "date_range": {"date_range", "date_equals", "range"},
    "date_equals": {"date_equals", "date_range"},
    "contains": {"contains", "starts_with", "equals"},
    "project": {"project"},
    "sort": {"sort"},
    "group_by": {"group_by"},
    "aggregate": {"aggregate"},
    "is_present": {"is_present", "equals"},
}


@dataclass
class FieldMapping:
    required_field: str
    matched: bool
    matched_field_name: Optional[str] = None
    canonical_id: Optional[str] = None
    aqf_role: Optional[str] = None
    datatype: Optional[str] = None
    aqf_operator: Optional[str] = None
    required_operators: List[str] = field(default_factory=list)
    operator_supported: bool = False
    source_path: Optional[str] = None
    aql_path: Optional[str] = None
    archetype_node_id: Optional[str] = None
    archetype_id: Optional[str] = None
    score: float = 0.0


@dataclass
class RealizedQuery:
    query_id: str
    query_name: str
    query_complexity: str
    category: str
    description: str
    selected_form_id: Optional[str]
    selected_form_group: Optional[str]
    field_recall: float
    operator_support: float
    context_support: float
    query_realizable: bool
    field_mappings: List[FieldMapping]
    aql: str
    where_clause: str
    select_clause: str
    notes: List[str] = field(default_factory=list)


# ------------------------------------------------------------
# Normalization and matching
# ------------------------------------------------------------

def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    chars = []
    for ch in text:
        chars.append(ch if ch.isalnum() else " ")
    return " ".join("".join(chars).split())


def name_match(required: str, candidate: str) -> bool:
    r = normalize_text(required)
    c = normalize_text(candidate)
    if not r or not c:
        return False
    return r == c or r in c or c in r


def operator_match(required_operator: str, candidate_operator: str) -> bool:
    req = normalize_text(required_operator).replace(" ", "_")
    cand = normalize_text(candidate_operator).replace(" ", "_")
    return cand in OPERATOR_ALIASES.get(req, {req})


def safe_identifier(text: Any) -> str:
    text = normalize_text(text).replace(" ", "_")
    text = re.sub(r"[^a-zA-Z0-9_]", "_", text)
    return text or "field"


# ------------------------------------------------------------
# Main realizer
# ------------------------------------------------------------

class AQFQueryRealizer:
    def __init__(self, strict_context: bool = False) -> None:
        self.strict_context = strict_context
        self.forms: List[Dict[str, Any]] = []
        self.workload: List[Dict[str, Any]] = []
        self.realized: List[RealizedQuery] = []

    def load_inputs(self, aqf_forms_json: str | Path, workload_json: str | Path) -> None:
        with open(aqf_forms_json, "r", encoding="utf-8") as f:
            forms_payload = json.load(f)
        self.forms = forms_payload.get("aqf_forms", [])
        if not self.forms:
            raise ValueError("No AQF forms found in aqf_forms_json.")

        with open(workload_json, "r", encoding="utf-8") as f:
            workload_payload = json.load(f)
        self.workload = workload_payload if isinstance(workload_payload, list) else workload_payload.get("queries", [])
        if not self.workload:
            raise ValueError("No workload queries found in workload_json.")

    def realize_all(self) -> List[RealizedQuery]:
        self.realized = []
        for query in self.workload:
            self.realized.append(self.realize_query(query))
        return self.realized

    def realize_query(self, query: Dict[str, Any]) -> RealizedQuery:
        scored = []
        for form in self.forms:
            mappings, field_recall, operator_support, context_support = self.map_query_to_form(query, form)
            query_realizable = field_recall >= 1.0 and operator_support >= 1.0 and (context_support >= 1.0 or not self.strict_context)
            score_tuple = (1 if query_realizable else 0, field_recall, operator_support, context_support, float(form.get("utility") or 0.0))
            scored.append((score_tuple, form, mappings, field_recall, operator_support, context_support, query_realizable))

        scored.sort(key=lambda x: x[0], reverse=True)
        _, best_form, mappings, field_recall, operator_support, context_support, query_realizable = scored[0]
        select_clause = self.build_select_clause(mappings)
        where_clause = self.build_where_clause(query, mappings)
        aql = self.build_aql(best_form, select_clause, where_clause)

        notes = []
        if not query_realizable:
            notes.append("Query is not fully realizable from selected AQF form; generated AQL is partial/template-level.")
        if context_support < 1.0:
            notes.append("One or more required contexts were not fully matched in the selected form.")
        if operator_support < 1.0:
            notes.append("One or more required operators were not supported by matched AQF fields.")
        if field_recall < 1.0:
            notes.append("One or more required fields were not available in the selected form.")

        return RealizedQuery(
            query_id=query.get("query_id", "unknown"),
            query_name=query.get("query_name", query.get("description", "unknown")),
            query_complexity=query.get("query_complexity", "unknown"),
            category=query.get("category", "unknown"),
            description=query.get("description", ""),
            selected_form_id=best_form.get("form_id"),
            selected_form_group=best_form.get("form_group"),
            field_recall=field_recall,
            operator_support=operator_support,
            context_support=context_support,
            query_realizable=query_realizable,
            field_mappings=mappings,
            aql=aql,
            where_clause=where_clause,
            select_clause=select_clause,
            notes=notes,
        )

    def map_query_to_form(self, query: Dict[str, Any], form: Dict[str, Any]) -> Tuple[List[FieldMapping], float, float, float]:
        required_fields = query.get("required_fields", [])
        required_ops = query.get("required_operators", {})
        form_fields = []
        for f in form.get("filters", []):
            item = dict(f)
            item["aqf_role"] = "filter"
            form_fields.append(item)
        for f in form.get("outputs", []):
            item = dict(f)
            item["aqf_role"] = "output"
            form_fields.append(item)

        mappings: List[FieldMapping] = []
        matched_field_count = 0
        supported_operator_count = 0
        total_operator_count = 0

        for req_field in required_fields:
            candidates = [f for f in form_fields if name_match(req_field, f.get("name", ""))]
            candidates.sort(key=lambda f: float(f.get("score") or 0.0), reverse=True)
            required_operator_list = required_ops.get(req_field, [])
            if isinstance(required_operator_list, str):
                required_operator_list = [required_operator_list]
            total_operator_count += len(required_operator_list)

            if candidates:
                best = candidates[0]
                matched_field_count += 1
                op_supported = True
                if required_operator_list:
                    op_supported = any(operator_match(req_op, best.get("operator", "")) for req_op in required_operator_list)
                    if op_supported:
                        supported_operator_count += len(required_operator_list)
                mapping = FieldMapping(
                    required_field=req_field,
                    matched=True,
                    matched_field_name=best.get("name"),
                    canonical_id=best.get("canonical_id"),
                    aqf_role=best.get("aqf_role"),
                    datatype=best.get("datatype"),
                    aqf_operator=best.get("operator"),
                    required_operators=required_operator_list,
                    operator_supported=op_supported,
                    source_path=best.get("path"),
                    aql_path=self.path_to_aql_path(best),
                    archetype_node_id=best.get("archetype_node_id"),
                    archetype_id=best.get("archetype_id"),
                    score=float(best.get("score") or 0.0),
                )
            else:
                mapping = FieldMapping(
                    required_field=req_field,
                    matched=False,
                    required_operators=required_operator_list,
                    operator_supported=False,
                )
            mappings.append(mapping)

        field_recall = matched_field_count / len(required_fields) if required_fields else 1.0
        operator_support = supported_operator_count / total_operator_count if total_operator_count else 1.0
        context_support = self.context_support(query, form, form_fields)
        return mappings, field_recall, operator_support, context_support

    def context_support(self, query: Dict[str, Any], form: Dict[str, Any], form_fields: List[Dict[str, Any]]) -> float:
        required_contexts = query.get("required_contexts", [])
        if not required_contexts:
            return 1.0
        blob = " ".join([
            str(form.get("form_group", "")),
            " ".join(str(f.get("ui_group", "")) for f in form_fields),
            " ".join(str(f.get("path", "")) for f in form_fields),
        ])
        matched = sum(1 for ctx in required_contexts if name_match(ctx, blob))
        return matched / len(required_contexts)

    def path_to_aql_path(self, field: Dict[str, Any]) -> str:
        """Convert AQF structural path to an AQL-like placeholder path.

        The source path segments look like:
          rm_type|name|archetype_node_id|archetype_id

        We create a readable template path that preserves archetype-node IDs.
        Exact AQL may need local template-specific path resolution later.
        """
        path = field.get("path") or ""
        segments = [s for s in path.split("/") if s]
        aql_parts = []
        for seg in segments:
            tokens = seg.split("|")
            if len(tokens) >= 3:
                rm_type, name, node_id = tokens[0], tokens[1], tokens[2]
                if node_id and node_id != "none":
                    aql_parts.append(f"/{rm_type}[{node_id}]/{name}")
                else:
                    aql_parts.append(f"/{rm_type}/{name}")
        if not aql_parts:
            return f"/content[/*]/data[/*]/items[at0000]/{safe_identifier(field.get('name'))}"
        return "".join(aql_parts)

    def build_select_clause(self, mappings: List[FieldMapping]) -> str:
        selected = [m for m in mappings if m.matched and m.aql_path]
        if not selected:
            return "e/ehr_id/value AS ehr_id"
        cols = ["e/ehr_id/value AS ehr_id"]
        for m in selected:
            alias = safe_identifier(m.required_field)
            cols.append(f"c{m.aql_path}/value AS {alias}")
        return ",\n  ".join(cols)

    def build_where_clause(self, query: Dict[str, Any], mappings: List[FieldMapping]) -> str:
        constraints = query.get("constraints", {}) or {}
        predicates = []
        for m in mappings:
            if not m.matched or not m.aql_path:
                continue
            constraint = constraints.get(m.required_field)
            req_ops = m.required_operators or []
            req_op = req_ops[0] if req_ops else m.aqf_operator or "equals"
            predicate = self.constraint_to_predicate(m, req_op, constraint)
            if predicate:
                predicates.append(predicate)
        return "\n  AND ".join(predicates) if predicates else "1 = 1"

    def constraint_to_predicate(self, mapping: FieldMapping, required_operator: str, constraint: Any) -> str:
        path = f"c{mapping.aql_path}/value"
        op = normalize_text(required_operator).replace(" ", "_")
        if constraint is None:
            return f"{path} IS NOT NULL"
        if isinstance(constraint, dict):
            c_op = constraint.get("operator", op)
            if c_op in {"before", "<"}:
                return f"{path} < '{constraint.get('value')}'"
            if c_op in {"after", ">"}:
                return f"{path} > '{constraint.get('value')}'"
            if c_op in {"between", "range"}:
                return f"{path} >= '{constraint.get('from')}' AND {path} <= '{constraint.get('to')}'"
            if c_op in {">=", "lte", "less_equal"}:
                return f"{path} <= '{constraint.get('value')}'"
            if c_op in {"<=", "gte", "greater_equal"}:
                return f"{path} >= '{constraint.get('value')}'"
            if "value" in constraint:
                return f"{path} = '{constraint.get('value')}'"
        if op in {"contains", "starts_with"}:
            return f"LOWER({path}) MATCHES '.*{str(constraint).lower()}.*'"
        if op in {"date_range", "range"}:
            # If a scalar is supplied for a range-style operator, use equality fallback.
            return f"{path} = '{constraint}'"
        return f"{path} = '{constraint}'"

    def build_aql(self, form: Dict[str, Any], select_clause: str, where_clause: str) -> str:
        # Template-style AQL. Composition archetype restriction can be refined later
        # using form_group/archetype_id if needed.
        return f"""SELECT
  {select_clause}
FROM EHR e
CONTAINS COMPOSITION c
WHERE
  {where_clause}
"""

    def save_outputs(self, output_dir: str | Path) -> None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        aql_dir = out / "aql"
        aql_dir.mkdir(parents=True, exist_ok=True)
        self.save_json(out / "realized_queries.json")
        self.save_csv(out / "realized_queries.csv")
        self.save_summary(out / "query_realization_summary.csv")
        for rq in self.realized:
            (aql_dir / f"{safe_identifier(rq.query_id)}.aql").write_text(rq.aql, encoding="utf-8")

    def save_json(self, path: Path) -> None:
        payload = {
            "metadata": self.summary_metrics(),
            "realized_queries": [self.realized_to_dict(rq) for rq in self.realized],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def save_csv(self, path: Path) -> None:
        cols = [
            "query_id", "query_name", "query_complexity", "category", "selected_form_id",
            "selected_form_group", "field_recall", "operator_support", "context_support",
            "query_realizable", "missing_fields", "unsupported_fields"
        ]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=cols)
            writer.writeheader()
            for rq in self.realized:
                missing = [m.required_field for m in rq.field_mappings if not m.matched]
                unsupported = [m.required_field for m in rq.field_mappings if m.matched and not m.operator_supported]
                writer.writerow({
                    "query_id": rq.query_id,
                    "query_name": rq.query_name,
                    "query_complexity": rq.query_complexity,
                    "category": rq.category,
                    "selected_form_id": rq.selected_form_id,
                    "selected_form_group": rq.selected_form_group,
                    "field_recall": rq.field_recall,
                    "operator_support": rq.operator_support,
                    "context_support": rq.context_support,
                    "query_realizable": rq.query_realizable,
                    "missing_fields": "; ".join(missing),
                    "unsupported_fields": "; ".join(unsupported),
                })

    def save_summary(self, path: Path) -> None:
        summary = self.summary_metrics()
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(summary.keys()))
            writer.writeheader()
            writer.writerow(summary)

    def summary_metrics(self) -> Dict[str, Any]:
        n = len(self.realized)
        if n == 0:
            return {"query_count": 0}
        category = {}
        complexity = {}
        for rq in self.realized:
            category.setdefault(rq.category, []).append(1 if rq.query_realizable else 0)
            complexity.setdefault(rq.query_complexity, []).append(1 if rq.query_realizable else 0)
        return {
            "query_count": n,
            "realizable_queries": sum(1 for rq in self.realized if rq.query_realizable),
            "query_realization_rate": sum(1 for rq in self.realized if rq.query_realizable) / n,
            "avg_field_recall": sum(rq.field_recall for rq in self.realized) / n,
            "avg_operator_support": sum(rq.operator_support for rq in self.realized) / n,
            "avg_context_support": sum(rq.context_support for rq in self.realized) / n,
            "category_realization": json.dumps({k: sum(v)/len(v) for k, v in category.items()}, ensure_ascii=False),
            "complexity_realization": json.dumps({k: sum(v)/len(v) for k, v in complexity.items()}, ensure_ascii=False),
        }

    def realized_to_dict(self, rq: RealizedQuery) -> Dict[str, Any]:
        item = asdict(rq)
        item["field_mappings"] = [asdict(m) for m in rq.field_mappings]
        return item


def run_query_realization(aqf_forms_json: str | Path, workload_json: str | Path, output_dir: str | Path, strict_context: bool = False) -> AQFQueryRealizer:
    realizer = AQFQueryRealizer(strict_context=strict_context)
    realizer.load_inputs(aqf_forms_json, workload_json)
    realizer.realize_all()
    realizer.save_outputs(output_dir)
    summary = realizer.summary_metrics()
    print("AQF query realization complete.")
    print(f"Queries: {summary.get('query_count')}")
    print(f"Realizable: {summary.get('realizable_queries')}")
    print(f"Realization rate: {summary.get('query_realization_rate'):.3f}")
    print(f"Output: {output_dir}")
    return realizer


def main() -> None:
    parser = argparse.ArgumentParser(description="Realize AQF benchmark workload queries as AQL drafts from generated AQF forms.")
    parser.add_argument("--aqf_forms_json", required=True, help="Path to aqf_forms.json")
    parser.add_argument("--workload_json", required=True, help="Path to benchmark workload JSON")
    parser.add_argument("--output_dir", required=True, help="Output directory")
    parser.add_argument("--strict_context", action="store_true", help="Require full context support for query_realizable=true")
    args = parser.parse_args()
    run_query_realization(args.aqf_forms_json, args.workload_json, args.output_dir, args.strict_context)


if __name__ == "__main__":
    main()
