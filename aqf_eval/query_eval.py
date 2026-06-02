from __future__ import annotations

import re, math
from collections import Counter

OP_ALIASES = {"=":"equals","equals":"equals","not_equals":"not_equals","contains":"contains","in":"in",">":">","<":"<","greater_than":">","less_than":"<","after":"after","before":"before","between":"between","is_known":"is_known","is_unknown":"is_unknown"}

GENERIC_TOKENS = {
    "problem", "diagnosis", "structure", "components", "component", "data", "general",
    "hcpa", "patient", "demographic", "procedure", "undertaken", "list", "single",
    "tree", "simple", "evaluation", "clinical", "pathological", "tnm", "cancer"
}

RAW_FIELD_ALIASES = {
    "invaded regional lymph nodes": ["invaded regional linphonodes", "invaded regional lymph nodes", "regional linphonodes"],
    "tumour topography": ["topography", "tumour tnm cancer staging topography"],
    "histopathological grading": ["histopathological grading g", "histopathological grading"],
    "body mass index": ["body mass index", "body mass index single body mass index"],
    "duration of follow up months": ["duration of follow up months", "duration of follow up", "duration of follow up months"],
    "procedure": ["procedure"],
    "irradiated area 1": ["irradiated area 1"],
    "date of discharge": ["date of discharge"],
    "reason for discharge": ["reason for discharge"],
}

MUTUALLY_EXCLUSIVE_TOKENS = [
    ("radiotherapy", "chemotherapy"),
    ("dialysis", "chemotherapy"),
    ("dialysis", "radiotherapy"),
    ("transplantation", "radiotherapy"),
    ("transplantation", "chemotherapy"),
    ("bariatric", "nephrology"),
]


def norm(s: str | None) -> str:
    s = str(s or "").lower()
    # Harmonise ORBDA/local spelling variants but keep full tokens useful.
    s = s.replace("lymph", "linphonodes")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def tokens(s: str | None, *, drop_generic: bool = False) -> set[str]:
    ts = set(norm(s).split())
    ts = {t for t in ts if len(t) > 2}
    if drop_generic:
        ts = {t for t in ts if t not in GENERIC_TOKENS}
    return ts

NORMALIZED_FIELD_ALIASES = {norm(k): [norm(v) for v in vals] for k, vals in RAW_FIELD_ALIASES.items()}


def cosine(a: str, b: str) -> float:
    ca, cb = Counter(norm(a).split()), Counter(norm(b).split())
    if not ca or not cb: return 0.0
    dot = sum(ca[k] * cb.get(k, 0) for k in ca)
    na = math.sqrt(sum(v*v for v in ca.values())); nb = math.sqrt(sum(v*v for v in cb.values()))
    return dot / (na * nb) if na and nb else 0.0


def has_context_conflict(q: str, f: str) -> bool:
    qt, ft = tokens(q), tokens(f)
    for a, b in MUTUALLY_EXCLUSIVE_TOKENS:
        if a in qt and b in ft: return True
        if b in qt and a in ft: return True
    return False


def _query_names(query_field: dict):
    vals = [query_field.get("canonical_path"), query_field.get("field_label")]
    out=[]
    for v in vals:
        n=norm(v)
        if n: out.append(n)
        # aliases by full normalized label OR by final path segment.
        final = norm(str(v or "").split("/")[-1])
        for key in (n, final):
            for alias in NORMALIZED_FIELD_ALIASES.get(key, []): out.append(alias)
    return list(dict.fromkeys([x for x in out if x]))


def _field_names(form_field: dict):
    return [norm(form_field.get("canonical_path")), norm(form_field.get("label"))]


def match_form_field(query_field: dict, form_field: dict):
    qnames = _query_names(query_field)
    fpath, flabel = norm(form_field.get("canonical_path")), norm(form_field.get("label"))
    fcombo = f"{fpath} {flabel}"
    if any(has_context_conflict(q, fcombo) for q in qnames):
        return False, "context_conflict", 0.0

    # 1 exact path / label
    for q in qnames:
        if q and q == fpath: return True, "exact_path", 1.0
        if q and q == flabel: return True, "exact_label", 1.0

    # 2 exact alias to field label/path, not broad parent containment.
    for q in qnames:
        aliases = NORMALIZED_FIELD_ALIASES.get(q, [])
        if fpath in aliases or flabel in aliases or any(a == flabel or a == fpath for a in aliases):
            return True, "alias_exact", 0.98
        for a in aliases:
            if a and (a == flabel or a in fpath):
                return True, "alias_path", 0.96

    # 3 leaf-token subset. Use non-generic final/leaf tokens only.
    for q in qnames:
        qt = tokens(q, drop_generic=True)
        flt = tokens(flabel, drop_generic=True)
        fpt = tokens(fpath, drop_generic=True)
        if qt and flt and (qt <= flt or flt <= qt):
            return True, "leaf_token_subset", 0.93
        if len(qt) >= 2 and len(qt & fpt) / len(qt) >= 0.80:
            return True, "path_token_subset", 0.90

    # 4 controlled cosine fallback on leaf/path, high threshold.
    best = max([cosine(q, fcombo) for q in qnames] or [0.0])
    if best >= 0.90:
        return True, "cosine_high_confidence", best
    return False, "no_match", best


def find_form_field(query_field: dict, form: dict):
    candidates=[]
    for f in form.get("fields", []):
        ok, mt, score = match_form_field(query_field, f)
        if ok:
            priority = {"exact_path":5,"exact_label":5,"alias_exact":4,"alias_path":4,"leaf_token_subset":3,"path_token_subset":2,"cosine_high_confidence":1}.get(mt,0)
            candidates.append((priority, score, f, mt))
    if not candidates: return None, "no_match", 0.0
    priority, score, f, mt = sorted(candidates, key=lambda x:(x[0], x[1], x[2].get("score",0)), reverse=True)[0]
    return f, mt, score


def operator_supported(op: str, field: dict | None) -> bool:
    if not field: return False
    return OP_ALIASES.get(str(op), str(op)) in set(field.get("operators", []))


def _field_key(qf: dict | str | None) -> str:
    if isinstance(qf, dict):
        return norm(qf.get("field_label") or qf.get("canonical_path"))
    return norm(qf)


def evaluate_query_against_form(query: dict, form: dict) -> dict:
    missing_fields, missing_ops, match_audit = [], [], []
    supported_components = 0; total_components = 0
    resolved = {}

    for pred in query.get("filters", []):
        total_components += 1
        f, mt, score = find_form_field(pred, form)
        key = _field_key(pred)
        if f: resolved[key] = f
        match_audit.append({"component":"filter","query_field":pred.get("field_label") or pred.get("canonical_path"),"matched_field":f.get("label") if f else None,"match_type":mt,"score":score})
        if not f:
            missing_fields.append(pred.get("canonical_path") or pred.get("field_label")); continue
        if not operator_supported(pred.get("operator"), f):
            missing_ops.append({"field":pred.get("field_label"),"operator":pred.get("operator"),"available":f.get("operators",[])})
            continue
        supported_components += 1

    for out in query.get("outputs", []):
        total_components += 1
        qf = out if isinstance(out, dict) else {"canonical_path":out,"field_label":out}
        key = _field_key(qf)
        f = resolved.get(key)
        if f:
            mt, score = "reuse_filter_match", 1.0
        else:
            f, mt, score = find_form_field(qf, form)
        match_audit.append({"component":"output","query_field":qf.get("field_label") or qf.get("canonical_path"),"matched_field":f.get("label") if f else None,"match_type":mt,"score":score})
        if f: supported_components += 1
        else: missing_fields.append(qf.get("canonical_path") or qf.get("field_label"))

    sort = query.get("sort")
    if sort:
        total_components += 1
        qf = {"canonical_path": sort.get("field"), "field_label": sort.get("field")}
        key = _field_key(qf)
        f = resolved.get(key)
        if f:
            mt, score = "reuse_filter_match", 1.0
        else:
            f, mt, score = find_form_field(qf, form)
        match_audit.append({"component":"sort","query_field":sort.get("field"),"matched_field":f.get("label") if f else None,"match_type":mt,"score":score})
        if f: supported_components += 1
        else: missing_fields.append(sort.get("field"))

    partial = supported_components / total_components if total_components else 1.0
    strict = partial == 1.0 and not missing_fields and not missing_ops
    if strict: failure_type = "SUPPORTED"
    elif missing_ops and not missing_fields: failure_type = "PRESENT_BUT_OPERATOR_MISSING"
    elif missing_fields and missing_ops: failure_type = "FIELD_AND_OPERATOR_ISSUES"
    else: failure_type = "ABSENT_OR_PRUNED_OR_MATCH_FAILED"
    return {"query_id":query.get("query_id"),"workload":query.get("workload"),"difficulty":query.get("difficulty"),"strict_supported":strict,"partial_score":partial,"missing_fields":missing_fields,"missing_operators":missing_ops,"failure_type":failure_type,"match_audit":match_audit}


def evaluate_form(form: dict, queries: list[dict]) -> list[dict]:
    rows=[]
    for q in queries:
        r=evaluate_query_against_form(q, form); r["method"]=form.get("method"); rows.append(r)
    return rows


def useful_field_labels(queries: list[dict]) -> set[str]:
    out=set()
    for q in queries:
        for p in q.get("filters", []): out.add(norm(p.get("field_label") or p.get("canonical_path")))
        for o in q.get("outputs", []): out.add(norm(o.get("field_label") if isinstance(o,dict) else o))
        if q.get("sort"): out.add(norm(q["sort"].get("field")))
    return {x for x in out if x}
