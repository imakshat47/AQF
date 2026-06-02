from __future__ import annotations
from .query_eval import norm


def benchmark_terms(queries):
    terms=set()
    for q in queries:
        for p in q.get("filters", []): terms.add(norm(p.get("field_label") or p.get("canonical_path")))
        for o in q.get("outputs", []): terms.add(norm(o.get("field_label") if isinstance(o, dict) else o))
        if q.get("sort"): terms.add(norm(q["sort"].get("field")))
    return terms


def audit_field_selection(forest, scores, forms, queries):
    terms=benchmark_terms(queries)
    selected_by={form.get("method"): {f.get("field_id") for f in form.get("fields", [])} for form in forms}
    rows=[]
    all_fields=[]
    for family, tree in forest.get("trees", {}).items():
        for f in tree.get("fields", []):
            x=dict(f); x["record_family"]=family; x["score"]=scores.get(f["field_id"],{}).get("overall_score", f.get("coverage",0)); all_fields.append(x)
    ranked=sorted(all_fields, key=lambda f:f.get("score",0), reverse=True)
    for rank, f in enumerate(ranked, start=1):
        label_n=norm(f.get("label")); path_n=norm(f.get("canonical_path"))
        relevance=[]
        for t in terms:
            if t and (t == label_n or t in path_n or label_n in t): relevance.append(t)
        row={"rank":rank,"field_id":f.get("field_id"),"label":f.get("label"),"canonical_path":f.get("canonical_path"),"record_family":f.get("record_family"),"score":f.get("score"),"coverage":f.get("coverage"),"kind":f.get("kind"),"dv_type":f.get("dv_type"),"benchmark_relevance":"; ".join(sorted(set(relevance)))}
        for method, ids in selected_by.items(): row[f"selected_by_{method}"]=f.get("field_id") in ids
        rows.append(row)
    return rows
