from __future__ import annotations
from collections import defaultdict, Counter
from .query_eval import norm

def summarize_coverage(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[(r.get("method"), r.get("workload"), r.get("difficulty"))].append(r)
        groups[(r.get("method"), r.get("workload"), "ALL")].append(r)
        groups[(r.get("method"), "ALL", "ALL")].append(r)
    return [{"method": m, "workload": w, "difficulty": d, "query_count": len(xs), "strict_coverage": sum(1 for x in xs if x.get("strict_supported"))/len(xs), "partial_coverage": sum(x.get("partial_score",0) for x in xs)/len(xs)} for (m,w,d), xs in sorted(groups.items())]

def precision_at_k(form, useful_labels, k=20):
    fields = sorted(form.get("fields", []), key=lambda f: f.get("score", 0), reverse=True)[:k]
    if not fields: return 0.0
    hits = sum(1 for f in fields if norm(f.get("label")) in useful_labels or norm(f.get("canonical_path")) in useful_labels)
    return hits/len(fields)

def recall_at_k(form, useful_labels, k=20):
    if not useful_labels: return 0.0
    fields = sorted(form.get("fields", []), key=lambda f: f.get("score", 0), reverse=True)[:k]
    found = {norm(f.get("label")) for f in fields if norm(f.get("label")) in useful_labels}
    return len(found)/len(useful_labels)

def form_complexity(form):
    groups = form.get("groups", {}); field_count=len(form.get("fields", [])); group_count=len(groups); subgroup_count=sum(len(sg) for sg in groups.values()); operator_count=sum(len(f.get("operators", [])) for f in form.get("fields", [])); complexity=min(100.0, field_count + subgroup_count*1.5 + group_count*2.0 + operator_count*0.15)
    return {"method": form.get("method"), "field_count": field_count, "group_count": group_count, "subgroup_count": subgroup_count, "operator_count": operator_count, "complexity_score": complexity}

def canonical_metrics(form):
    fields=form.get("fields", []); flat = form.get("method") == "flattened_topk"
    with_context=[f for f in fields if f.get("form_group") and f.get("nested_subgroup") and not flat]
    labels=Counter([norm(f.get("label")) for f in fields]); ambiguous=[l for l,c in labels.items() if l and c>1]
    return {"method": form.get("method"), "context_preservation_rate": len(with_context)/len(fields) if fields else 0, "ambiguous_label_count": len(ambiguous), "ambiguity_resolution_rate": 1.0 if not ambiguous else 0.0}
