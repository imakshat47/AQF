#!/usr/bin/env python3
"""
aqf_query_realizer_alias.py

Alias-aware query realization for AQF forms.

Enhancements over the earlier realizer:
  - field_aliases.json support
  - context_aliases support
  - better matching for benchmark vocabulary vs schema vocabulary
  - generated AQL drafts and realization metrics
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---- shared utility functions ----

import json, re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

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

def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    chars = []
    for ch in text:
        chars.append(ch if ch.isalnum() else " ")
    return " ".join("".join(chars).split())

def safe_identifier(text: Any) -> str:
    text = normalize_text(text).replace(" ", "_")
    text = re.sub(r"[^a-zA-Z0-9_]", "_", text)
    return text or "field"

def load_aliases(path: Optional[str | Path]) -> Dict[str, Any]:
    if not path:
        return {"field_aliases": {}, "context_aliases": {}}
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Alias file not found: {path}")
    with open(p, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return {
        "field_aliases": payload.get("field_aliases", {}),
        "context_aliases": payload.get("context_aliases", {}),
    }

def alias_terms(term: str, alias_map: Dict[str, List[str]]) -> Set[str]:
    terms = {term}
    norm = normalize_text(term)
    for key, vals in alias_map.items():
        group = [key] + list(vals or [])
        norm_group = {normalize_text(x) for x in group}
        if norm in norm_group:
            terms.update(group)
    return {normalize_text(t) for t in terms if normalize_text(t)}

def alias_name_match(required: str, candidate: str, alias_map: Dict[str, List[str]]) -> bool:
    candidate_norm = normalize_text(candidate)
    if not candidate_norm:
        return False
    for term in alias_terms(required, alias_map):
        if term == candidate_norm or term in candidate_norm or candidate_norm in term:
            return True
    return False

def operator_match(required_operator: str, candidate_operator: str) -> bool:
    req = normalize_text(required_operator).replace(" ", "_")
    cand = normalize_text(candidate_operator).replace(" ", "_")
    return cand in OPERATOR_ALIASES.get(req, {req})

def infer_ui_group(path: str) -> str:
    if not path:
        return "General"
    parts = [p for p in str(path).split("/") if p]
    raw = parts[-2] if len(parts) >= 2 else (parts[0] if parts else "General")
    tokens = raw.split("|")
    if len(tokens) >= 2:
        return tokens[1].replace("_", " ").title()
    return raw.replace("_", " ").title()

def find_operator_detail(operators: List[Dict[str, Any]], preferred: Optional[str]) -> Dict[str, Any]:
    if preferred:
        for op in operators or []:
            if op.get("operator") == preferred:
                return op
    return operators[0] if operators else {}


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

class AQFAliasAwareQueryRealizer:
    def __init__(self, aliases_json: Optional[str | Path] = None, strict_context: bool = False) -> None:
        aliases = load_aliases(aliases_json)
        self.field_aliases = aliases["field_aliases"]
        self.context_aliases = aliases["context_aliases"]
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
        self.realized = [self.realize_query(q) for q in self.workload]
        return self.realized

    def realize_query(self, query: Dict[str, Any]) -> RealizedQuery:
        scored = []
        for form in self.forms:
            mappings, fr, os, cs = self.map_query_to_form(query, form)
            realizable = fr >= 1.0 and os >= 1.0 and (cs >= 1.0 or not self.strict_context)
            score_tuple = (1 if realizable else 0, fr, os, cs, float(form.get("utility") or 0.0))
            scored.append((score_tuple, form, mappings, fr, os, cs, realizable))
        scored.sort(key=lambda x: x[0], reverse=True)
        _, best_form, mappings, fr, os, cs, realizable = scored[0]
        select_clause = self.build_select_clause(mappings)
        where_clause = self.build_where_clause(query, mappings)
        aql = self.build_aql(best_form, select_clause, where_clause)
        notes = []
        if not realizable:
            notes.append("Query is not fully realizable from selected AQF form; AQL is partial/template-level.")
        if fr < 1.0:
            notes.append("Missing one or more required fields.")
        if os < 1.0:
            notes.append("Unsupported operator for one or more matched fields.")
        if cs < 1.0:
            notes.append("Required structural context is partially matched.")
        return RealizedQuery(
            query_id=query.get("query_id", "unknown"),
            query_name=query.get("query_name", query.get("description", "unknown")),
            query_complexity=query.get("query_complexity", "unknown"),
            category=query.get("category", "unknown"),
            description=query.get("description", ""),
            selected_form_id=best_form.get("form_id"),
            selected_form_group=best_form.get("form_group"),
            field_recall=fr,
            operator_support=os,
            context_support=cs,
            query_realizable=realizable,
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
        for role in ("filters", "outputs"):
            for f in form.get(role, []):
                item = dict(f)
                item["aqf_role"] = "filter" if role == "filters" else "output"
                form_fields.append(item)
        mappings = []
        matched_count = 0
        op_supported_count = 0
        op_total = 0
        for req_field in required_fields:
            candidates = [f for f in form_fields if alias_name_match(req_field, f.get("name", ""), self.field_aliases)]
            candidates.sort(key=lambda f: float(f.get("score") or 0.0), reverse=True)
            req_ops = required_ops.get(req_field, [])
            if isinstance(req_ops, str):
                req_ops = [req_ops]
            op_total += len(req_ops)
            if candidates:
                best = candidates[0]
                matched_count += 1
                op_supported = True
                if req_ops:
                    op_supported = any(operator_match(req_op, best.get("operator", "")) for req_op in req_ops)
                    if op_supported:
                        op_supported_count += len(req_ops)
                mappings.append(FieldMapping(
                    required_field=req_field,
                    matched=True,
                    matched_field_name=best.get("name"),
                    canonical_id=best.get("canonical_id"),
                    aqf_role=best.get("aqf_role"),
                    datatype=best.get("datatype"),
                    aqf_operator=best.get("operator"),
                    required_operators=req_ops,
                    operator_supported=op_supported,
                    source_path=best.get("path"),
                    aql_path=self.path_to_aql_path(best),
                    archetype_node_id=best.get("archetype_node_id"),
                    archetype_id=best.get("archetype_id"),
                    score=float(best.get("score") or 0.0),
                ))
            else:
                mappings.append(FieldMapping(required_field=req_field, matched=False, required_operators=req_ops))
        fr = matched_count / len(required_fields) if required_fields else 1.0
        os = op_supported_count / op_total if op_total else 1.0
        cs = self.context_support(query, form, form_fields)
        return mappings, fr, os, cs

    def context_support(self, query: Dict[str, Any], form: Dict[str, Any], form_fields: List[Dict[str, Any]]) -> float:
        contexts = query.get("required_contexts", [])
        if not contexts:
            return 1.0
        blob = " ".join([
            str(form.get("form_group", "")),
            " ".join(str(f.get("ui_group", "")) for f in form_fields),
            " ".join(str(f.get("path", "")) for f in form_fields),
        ])
        matched = sum(1 for ctx in contexts if alias_name_match(ctx, blob, self.context_aliases))
        return matched / len(contexts)

    def path_to_aql_path(self, field: Dict[str, Any]) -> str:
        path = field.get("path") or ""
        segments = [s for s in path.split("/") if s]
        parts = []
        for seg in segments:
            toks = seg.split("|")
            if len(toks) >= 3:
                rm_type, name, node_id = toks[0], toks[1], toks[2]
                if node_id and node_id != "none":
                    parts.append(f"/{rm_type}[{node_id}]/{name}")
                else:
                    parts.append(f"/{rm_type}/{name}")
        return "".join(parts) if parts else f"/content[/*]/data[/*]/items[at0000]/{safe_identifier(field.get('name'))}"

    def build_select_clause(self, mappings: List[FieldMapping]) -> str:
        cols = ["e/ehr_id/value AS ehr_id"]
        for m in mappings:
            if m.matched and m.aql_path:
                cols.append(f"c{m.aql_path}/value AS {safe_identifier(m.required_field)}")
        return ",\n  ".join(cols)

    def build_where_clause(self, query: Dict[str, Any], mappings: List[FieldMapping]) -> str:
        constraints = query.get("constraints", {}) or {}
        predicates = []
        for m in mappings:
            if not m.matched or not m.aql_path:
                continue
            constraint = constraints.get(m.required_field)
            req_op = m.required_operators[0] if m.required_operators else m.aqf_operator or "equals"
            predicates.append(self.constraint_to_predicate(m, req_op, constraint))
        return "\n  AND ".join([p for p in predicates if p]) if predicates else "1 = 1"

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
            if c_op in {"<=", "lte", "less_equal"}:
                return f"{path} <= '{constraint.get('value')}'"
            if c_op in {">=", "gte", "greater_equal"}:
                return f"{path} >= '{constraint.get('value')}'"
            if "value" in constraint:
                return f"{path} = '{constraint.get('value')}'"
        if op in {"contains", "starts_with"}:
            return f"LOWER({path}) MATCHES '.*{str(constraint).lower()}.*'"
        return f"{path} = '{constraint}'"

    def build_aql(self, form: Dict[str, Any], select_clause: str, where_clause: str) -> str:
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
        payload = {"metadata": self.summary_metrics(), "realized_queries": [self.realized_to_dict(rq) for rq in self.realized]}
        (out / "realized_queries.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        self.save_csv(out / "realized_queries.csv")
        self.save_summary(out / "query_realization_summary.csv")
        for rq in self.realized:
            (aql_dir / f"{safe_identifier(rq.query_id)}.aql").write_text(rq.aql, encoding="utf-8")

    def save_csv(self, path: Path) -> None:
        cols = ["query_id", "query_name", "query_complexity", "category", "selected_form_id", "selected_form_group", "field_recall", "operator_support", "context_support", "query_realizable", "missing_fields", "unsupported_fields"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=cols)
            writer.writeheader()
            for rq in self.realized:
                missing = [m.required_field for m in rq.field_mappings if not m.matched]
                unsupported = [m.required_field for m in rq.field_mappings if m.matched and not m.operator_supported]
                writer.writerow({"query_id": rq.query_id, "query_name": rq.query_name, "query_complexity": rq.query_complexity, "category": rq.category, "selected_form_id": rq.selected_form_id, "selected_form_group": rq.selected_form_group, "field_recall": rq.field_recall, "operator_support": rq.operator_support, "context_support": rq.context_support, "query_realizable": rq.query_realizable, "missing_fields": "; ".join(missing), "unsupported_fields": "; ".join(unsupported)})

    def save_summary(self, path: Path) -> None:
        summary = self.summary_metrics()
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(summary.keys()))
            writer.writeheader()
            writer.writerow(summary)

    def summary_metrics(self) -> Dict[str, Any]:
        n = len(self.realized)
        if not n:
            return {"query_count": 0}
        cats, comps = {}, {}
        for rq in self.realized:
            cats.setdefault(rq.category, []).append(1 if rq.query_realizable else 0)
            comps.setdefault(rq.query_complexity, []).append(1 if rq.query_realizable else 0)
        return {"query_count": n, "realizable_queries": sum(1 for rq in self.realized if rq.query_realizable), "query_realization_rate": sum(1 for rq in self.realized if rq.query_realizable) / n, "avg_field_recall": sum(rq.field_recall for rq in self.realized) / n, "avg_operator_support": sum(rq.operator_support for rq in self.realized) / n, "avg_context_support": sum(rq.context_support for rq in self.realized) / n, "category_realization": json.dumps({k: sum(v)/len(v) for k,v in cats.items()}, ensure_ascii=False), "complexity_realization": json.dumps({k: sum(v)/len(v) for k,v in comps.items()}, ensure_ascii=False)}

    def realized_to_dict(self, rq: RealizedQuery) -> Dict[str, Any]:
        item = asdict(rq)
        item["field_mappings"] = [asdict(m) for m in rq.field_mappings]
        return item

def main() -> None:
    parser = argparse.ArgumentParser(description="Alias-aware AQF query realization.")
    parser.add_argument("--aqf_forms_json", required=True)
    parser.add_argument("--workload_json", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--aliases_json", default=None)
    parser.add_argument("--strict_context", action="store_true")
    args = parser.parse_args()
    r = AQFAliasAwareQueryRealizer(args.aliases_json, args.strict_context)
    r.load_inputs(args.aqf_forms_json, args.workload_json)
    r.realize_all()
    r.save_outputs(args.output_dir)
    s = r.summary_metrics()
    print("Alias-aware AQF query realization complete.")
    print(f"Queries: {s.get('query_count')}")
    print(f"Realizable: {s.get('realizable_queries')}")
    print(f"Realization rate: {s.get('query_realization_rate'):.3f}")
    print(f"Output: {args.output_dir}")

if __name__ == "__main__":
    main()
