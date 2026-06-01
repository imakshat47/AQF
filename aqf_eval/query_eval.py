from __future__ import annotations

import re
from collections import defaultdict

OP_ALIASES = {
    "=": "equals", "equals": "equals", "not_equals": "not_equals", "contains": "contains", "in": "in",
    ">": ">", "<": "<", "greater_than": ">", "less_than": "<", "after": "after", "before": "before", "between": "between",
    "is_known": "is_known", "is_unknown": "is_unknown"
}


def norm(s: str | None) -> str:
    s = str(s or "").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def field_matches(query_field: dict, form_field: dict) -> bool:
    qpath = norm(query_field.get("canonical_path"))
    qlabel = norm(query_field.get("field_label"))
    fpath = norm(form_field.get("canonical_path"))
    flabel = norm(form_field.get("label"))
    if qpath and (qpath == fpath or qpath in fpath or fpath in qpath):
        return True
    if qlabel and qlabel == flabel:
        return True
    if qlabel and qlabel in fpath:
        return True
    return False


def find_form_field(query_field: dict, form: dict):
    for f in form.get("fields", []):
        if field_matches(query_field, f):
            return f
    return None


def operator_supported(op: str, field: dict | None) -> bool:
    if not field:
        return False
    opn = OP_ALIASES.get(str(op), str(op))
    return opn in set(field.get("operators", []))


def evaluate_query_against_form(query: dict, form: dict) -> dict:
    missing_fields = []
    missing_ops = []
    supported_components = 0
    total_components = 0

    for pred in query.get("filters", []):
        total_components += 1
        f = find_form_field(pred, form)
        if not f:
            missing_fields.append(pred.get("canonical_path") or pred.get("field_label"))
            continue
        if not operator_supported(pred.get("operator"), f):
            missing_ops.append({"field": pred.get("field_label"), "operator": pred.get("operator")})
            continue
        supported_components += 1

    for out in query.get("outputs", []):
        total_components += 1
        qf = out if isinstance(out, dict) else {"canonical_path": out, "field_label": out}
        if find_form_field(qf, form):
            supported_components += 1
        else:
            missing_fields.append(qf.get("canonical_path") or qf.get("field_label"))

    sort = query.get("sort")
    if sort:
        total_components += 1
        qf = {"canonical_path": sort.get("field"), "field_label": sort.get("field")}
        f = find_form_field(qf, form)
        if f and ("before" in f.get("operators", []) or ">" in f.get("operators", []) or "equals" in f.get("operators", [])):
            supported_components += 1
        else:
            missing_fields.append(sort.get("field"))

    partial = supported_components / total_components if total_components else 1.0
    strict = (partial == 1.0 and not missing_fields and not missing_ops)
    return {
        "query_id": query.get("query_id"),
        "workload": query.get("workload"),
        "difficulty": query.get("difficulty"),
        "strict_supported": strict,
        "partial_score": partial,
        "missing_fields": missing_fields,
        "missing_operators": missing_ops,
    }


def evaluate_form(form: dict, queries: list[dict]) -> list[dict]:
    rows = []
    for q in queries:
        r = evaluate_query_against_form(q, form)
        r["method"] = form.get("method")
        rows.append(r)
    return rows


def useful_field_labels(queries: list[dict]) -> set[str]:
    out = set()
    for q in queries:
        for p in q.get("filters", []):
            out.add(norm(p.get("field_label") or p.get("canonical_path")))
        for o in q.get("outputs", []):
            if isinstance(o, dict):
                out.add(norm(o.get("field_label") or o.get("canonical_path")))
            else:
                out.add(norm(o))
        if q.get("sort"):
            out.add(norm(q["sort"].get("field")))
    return {x for x in out if x}
