from __future__ import annotations

import re, math, json
from collections import Counter

OP_ALIASES = {"=": "equals", "equals": "equals", "not_equals": "not_equals", "contains": "contains", "in": "in", ">": ">", "<": "<", "greater_than": ">", "less_than": "<", "after": "after", "before": "before", "between": "between", "is_known": "is_known", "is_unknown": "is_unknown"}

FIELD_ALIASES = {
    "invaded regional lymph nodes": ["invaded regional linphonodes", "regional lymph nodes"],
    "tumour topography": ["topography", "tumour tnm cancer staging topography"],
    "histopathological grading": ["histopathological grading g"],
    "body mass index": ["body mass index"],
    "duration of follow up months": ["duration of follow up months", "duration of follow up"],
    "procedure": ["procedure", "procedure undertaken procedure"],
    "irradiated area 1": ["irradiated area", "irradiated area 1"],
    "date of discharge": ["date of discharge"],
    "reason for discharge": ["reason for discharge"],
}


def norm(s: str | None) -> str:
    s = str(s or "").lower()
    s = s.replace("lymph", "linph")  # ORBDA local spelling harmonization
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def tokens(s): return set(norm(s).split())

def cosine(a: str, b: str) -> float:
    ca, cb = Counter(norm(a).split()), Counter(norm(b).split())
    if not ca or not cb: return 0.0
    dot = sum(ca[k] * cb.get(k, 0) for k in ca)
    na = math.sqrt(sum(v*v for v in ca.values())); nb = math.sqrt(sum(v*v for v in cb.values()))
    return dot / (na * nb) if na and nb else 0.0


def _query_names(query_field: dict):
    vals = [query_field.get("canonical_path"), query_field.get("field_label")]
    out = []
    for v in vals:
        n = norm(v)
        if n: out.append(n)
        for alias in FIELD_ALIASES.get(n, []): out.append(norm(alias))
    return list(dict.fromkeys(out))


def match_form_field(query_field: dict, form_field: dict):
    qnames = _query_names(query_field)
    fpath = norm(form_field.get("canonical_path")); flabel = norm(form_field.get("label"))
    fcombo = f"{fpath} {flabel}"
    # 1 exact canonical path / 2 exact label
    for q in qnames:
        if q and q == fpath: return True, "exact_path", 1.0
        if q and q == flabel: return True, "exact_label", 1.0
    # 3 alias / normalized contains
    for q in qnames:
        if q and (q in fcombo or flabel in q): return True, "alias_or_contains", 0.95
    # 4 token subset against path; require at least 2 meaningful tokens or exact single token.
    for q in qnames:
        qt = {t for t in q.split() if len(t) > 2}
        ft = tokens(fcombo)
        if qt and (qt <= ft or (len(qt) >= 2 and len(qt & ft) / len(qt) >= 0.75)):
            return True, "token_subset", 0.90
    # 5 cosine high confidence fallback
    best = max([cosine(q, fcombo) for q in qnames] or [0.0])
    if best >= 0.88: return True, "cosine_high_confidence", best
    return False, "no_match", best


def find_form_field(query_field: dict, form: dict):
    best = None
    for f in form.get("fields", []):
        ok, mt, score = match_form_field(query_field, f)
        if ok and (best is None or score > best[2]): best = (f, mt, score)
    return best if best else (None, "no_match", 0.0)


def operator_supported(op: str, field: dict | None) -> bool:
    if not field: return False
    opn = OP_ALIASES.get(str(op), str(op))
    return opn in set(field.get("operators", []))


def evaluate_query_against_form(query: dict, form: dict) -> dict:
    missing_fields, missing_ops, match_audit = [], [], []
    supported_components = 0; total_components = 0
    for pred in query.get("filters", []):
        total_components += 1
        f, mt, score = find_form_field(pred, form)
        match_audit.append({"component": "filter", "query_field": pred.get("field_label") or pred.get("canonical_path"), "matched_field": f.get("label") if f else None, "match_type": mt, "score": score})
        if not f:
            missing_fields.append(pred.get("canonical_path") or pred.get("field_label")); continue
        if not operator_supported(pred.get("operator"), f):
            missing_ops.append({"field": pred.get("field_label"), "operator": pred.get("operator"), "available": f.get("operators", [])}); continue
        supported_components += 1
    for out in query.get("outputs", []):
        total_components += 1
        qf = out if isinstance(out, dict) else {"canonical_path": out, "field_label": out}
        f, mt, score = find_form_field(qf, form)
        match_audit.append({"component": "output", "query_field": qf.get("field_label") or qf.get("canonical_path"), "matched_field": f.get("label") if f else None, "match_type": mt, "score": score})
        if f: supported_components += 1
        else: missing_fields.append(qf.get("canonical_path") or qf.get("field_label"))
    sort = query.get("sort")
    if sort:
        total_components += 1
        qf = {"canonical_path": sort.get("field"), "field_label": sort.get("field")}
        f, mt, score = find_form_field(qf, form)
        match_audit.append({"component": "sort", "query_field": sort.get("field"), "matched_field": f.get("label") if f else None, "match_type": mt, "score": score})
        if f: supported_components += 1
        else: missing_fields.append(sort.get("field"))
    partial = supported_components / total_components if total_components else 1.0
    strict = (partial == 1.0 and not missing_fields and not missing_ops)
    if strict: failure_type = "SUPPORTED"
    elif missing_ops and not missing_fields: failure_type = "PRESENT_BUT_OPERATOR_MISSING"
    elif missing_fields and missing_ops: failure_type = "FIELD_AND_OPERATOR_ISSUES"
    else: failure_type = "ABSENT_OR_PRUNED_OR_MATCH_FAILED"
    return {"query_id": query.get("query_id"), "workload": query.get("workload"), "difficulty": query.get("difficulty"),
            "strict_supported": strict, "partial_score": partial, "missing_fields": missing_fields,
            "missing_operators": missing_ops, "failure_type": failure_type, "match_audit": match_audit}


def evaluate_form(form: dict, queries: list[dict]) -> list[dict]:
    rows = []
    for q in queries:
        r = evaluate_query_against_form(q, form); r["method"] = form.get("method"); rows.append(r)
    return rows


def useful_field_labels(queries: list[dict]) -> set[str]:
    out = set()
    for q in queries:
        for p in q.get("filters", []): out.add(norm(p.get("field_label") or p.get("canonical_path")))
        for o in q.get("outputs", []): out.add(norm(o.get("field_label") if isinstance(o, dict) else o))
        if q.get("sort"): out.add(norm(q["sort"].get("field")))
    return {x for x in out if x}
