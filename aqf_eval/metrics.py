from __future__ import annotations

from collections import defaultdict, Counter
from .query_eval import norm


def summarize_coverage(rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for r in rows:
        groups[(r.get("method"), r.get("workload"), r.get("difficulty"))].append(r)
        groups[(r.get("method"), r.get("workload"), "ALL")].append(r)
        groups[(r.get("method"), "ALL", "ALL")].append(r)
    out = []
    for (method, workload, difficulty), xs in sorted(groups.items()):
        out.append({
            "method": method,
            "workload": workload,
            "difficulty": difficulty,
            "query_count": len(xs),
            "strict_coverage": sum(1 for x in xs if x.get("strict_supported")) / len(xs) if xs else 0,
            "partial_coverage": sum(x.get("partial_score", 0) for x in xs) / len(xs) if xs else 0,
        })
    return out


def precision_at_k(form: dict, useful_labels: set[str], k: int = 20) -> float:
    fields = sorted(form.get("fields", []), key=lambda f: f.get("score", 0), reverse=True)[:k]
    if not fields:
        return 0.0
    hits = 0
    for f in fields:
        if norm(f.get("label")) in useful_labels or norm(f.get("canonical_path")) in useful_labels:
            hits += 1
    return hits / len(fields)


def recall_at_k(form: dict, useful_labels: set[str], k: int = 20) -> float:
    if not useful_labels:
        return 0.0
    fields = sorted(form.get("fields", []), key=lambda f: f.get("score", 0), reverse=True)[:k]
    found = set()
    for f in fields:
        if norm(f.get("label")) in useful_labels:
            found.add(norm(f.get("label")))
    return len(found) / len(useful_labels)


def form_complexity(form: dict) -> dict:
    groups = form.get("groups", {})
    group_count = len(groups)
    subgroup_count = sum(len(sg) for sg in groups.values())
    field_count = len(form.get("fields", []))
    operator_count = sum(len(f.get("operators", [])) for f in form.get("fields", []))
    complexity = min(100.0, field_count * 1.0 + subgroup_count * 1.5 + group_count * 2.0 + operator_count * 0.15)
    return {
        "method": form.get("method"),
        "field_count": field_count,
        "group_count": group_count,
        "subgroup_count": subgroup_count,
        "operator_count": operator_count,
        "complexity_score": complexity,
    }


def canonical_metrics(form: dict) -> dict:
    fields = form.get("fields", [])
    with_context = [f for f in fields if f.get("form_group") and f.get("nested_subgroup")]
    labels = Counter([norm(f.get("label")) for f in fields])
    ambiguous = [l for l, c in labels.items() if l and c > 1]
    disambig = 0
    for l in ambiguous:
        contexts = {(f.get("form_group"), f.get("nested_subgroup")) for f in fields if norm(f.get("label")) == l}
        if len(contexts) > 1:
            disambig += 1
    return {
        "method": form.get("method"),
        "context_preservation_rate": len(with_context) / len(fields) if fields else 0,
        "ambiguous_label_count": len(ambiguous),
        "ambiguity_resolution_rate": disambig / len(ambiguous) if ambiguous else 1.0,
    }
