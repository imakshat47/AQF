from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple


def _safe_float(x, default=0.0):
    try:
        if x is None: return default
        v = float(x)
        if math.isnan(v): return default
        return v
    except Exception:
        return default


def _coverage(f: Dict[str, Any]) -> float:
    if f.get("coverage") is not None:
        return max(0.0, min(1.0, _safe_float(f.get("coverage"))))
    known = _safe_float(f.get("known_count"))
    rec = _safe_float(f.get("record_count"))
    if rec > 0:
        return max(0.0, min(1.0, known / rec))
    return 0.0


def _diversity(f: Dict[str, Any]) -> float:
    """Final-draft value diversity: |distinct(v)| / |R_v|.

    If distinct_count/known_count is unavailable, use distinct_ratio if present.
    Values are clipped to [0, 1].
    """
    distinct = _safe_float(f.get("distinct_count"))
    known = _safe_float(f.get("known_count"))
    if known > 0 and distinct >= 0:
        return max(0.0, min(1.0, distinct / known))
    if f.get("distinct_ratio") is not None:
        return max(0.0, min(1.0, _safe_float(f.get("distinct_ratio"))))
    return 0.0


def _path_parts(f: Dict[str, Any]) -> List[str]:
    path = str(f.get("canonical_path") or "")
    return [p.strip().lower() for p in path.split("/") if p.strip()]


def _same_context_cc(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    """Normalized containment connectivity CC(u,v).

    ORBDA/openEHR containment metadata is available as canonical path, form group,
    subgroup, and record family. We convert this to a normalized context score.
    """
    if a.get("field_id") == b.get("field_id"):
        return 0.0
    if a.get("record_family") and a.get("record_family") == b.get("record_family"):
        base = 0.10
    else:
        base = 0.0
    if a.get("form_group") and a.get("form_group") == b.get("form_group"):
        base = max(base, 0.50)
    if a.get("nested_subgroup") and a.get("nested_subgroup") == b.get("nested_subgroup") and a.get("form_group") == b.get("form_group"):
        base = max(base, 0.85)
    pa, pb = _path_parts(a), _path_parts(b)
    common = 0
    for x, y in zip(pa, pb):
        if x == y: common += 1
        else: break
    if common:
        base = max(base, min(1.0, common / max(len(pa), len(pb), 1)))
    return base


def _cooccurrence_support(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    """Normalized empirical co-occurrence support CO(u,v).

    If explicit co-occurrence is unavailable, a conservative upper-bound proxy is
    min(cov(u), cov(v)), because both fields cannot co-occur more often than the
    less prevalent field. This keeps the final formula executable on current
    ORBDA artifacts while remaining aligned with the draft definition.
    """
    if a.get("field_id") == b.get("field_id"):
        return 0.0
    # Optional future artifact support.
    co = a.get("cooccurrence", {}) or {}
    if isinstance(co, dict) and b.get("field_id") in co:
        return max(0.0, min(1.0, _safe_float(co[b.get("field_id")])) )
    return min(_coverage(a), _coverage(b))


def _all_fields(forest: Dict[str, Any]) -> List[Dict[str, Any]]:
    fields = []
    for family, tree in (forest.get("trees") or {}).items():
        for f in tree.get("fields", []) or []:
            x = dict(f)
            x.setdefault("record_family", family)
            # Normalize naming differences from earlier patches.
            if x.get("supports_null_flavour") is None:
                x["supports_null_flavour"] = bool(x.get("has_null_flavour"))
            fields.append(x)
    return fields


def compute_scores_final(forest: Dict[str, Any], lambda_sc: float = 0.25, mu: float = 0.25, max_neighbors: int = 50) -> Dict[str, Dict[str, Any]]:
    """Compute AQF final-draft queriability scores.

    LU(v) = cov(v) * div(v)
    SC(u,v) = lambda * CC(u,v) + (1-lambda) * CO(u,v)
    Q(v) = LU(v) + mu * sum_{u in N(v)} SC(u,v) * LU(u)

    The implementation keeps all intermediate values for auditability.
    """
    fields = _all_fields(forest)
    local = {}
    for f in fields:
        cov = _coverage(f)
        div = _diversity(f)
        lu = cov * div
        local[f["field_id"]] = {"coverage": cov, "diversity": div, "local_utility": lu}

    scores: Dict[str, Dict[str, Any]] = {}
    for f in fields:
        fid = f["field_id"]
        neigh_terms = []
        for u in fields:
            uid = u["field_id"]
            if uid == fid:
                continue
            cc = _same_context_cc(f, u)
            co = _cooccurrence_support(f, u)
            # Treat zero structural/empirical relationship as non-neighbor.
            if cc <= 0 and co <= 0:
                continue
            sc = lambda_sc * cc + (1.0 - lambda_sc) * co
            term = sc * local[uid]["local_utility"]
            neigh_terms.append((term, uid, cc, co, sc))
        neigh_terms.sort(reverse=True, key=lambda x: x[0])
        if max_neighbors and len(neigh_terms) > max_neighbors:
            neigh_terms = neigh_terms[:max_neighbors]
        reinforcement = sum(t[0] for t in neigh_terms)
        q = local[fid]["local_utility"] + mu * reinforcement
        scores[fid] = {
            "coverage": local[fid]["coverage"],
            "diversity": local[fid]["diversity"],
            "local_utility": local[fid]["local_utility"],
            "neighborhood_reinforcement": reinforcement,
            "overall_score": q,
            "final_queriability": q,
            "lambda_sc": lambda_sc,
            "mu": mu,
            "neighbor_count": len(neigh_terms),
            "top_neighbors": [
                {"field_id": uid, "term": term, "containment_connectivity": cc, "cooccurrence_support": co, "structural_connectivity": sc}
                for term, uid, cc, co, sc in neigh_terms[:10]
            ],
        }
    return scores


def scores_to_rows(forest: Dict[str, Any], scores: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows=[]
    for family, tree in (forest.get("trees") or {}).items():
        for f in tree.get("fields", []) or []:
            s=scores.get(f.get("field_id"), {})
            rows.append({
                "field_id": f.get("field_id"),
                "label": f.get("label"),
                "canonical_path": f.get("canonical_path"),
                "record_family": family,
                "coverage": s.get("coverage"),
                "diversity": s.get("diversity"),
                "local_utility": s.get("local_utility"),
                "neighborhood_reinforcement": s.get("neighborhood_reinforcement"),
                "final_queriability": s.get("final_queriability"),
                "neighbor_count": s.get("neighbor_count"),
                "kind": f.get("kind"),
                "dv_type": f.get("dv_type"),
            })
    rows.sort(key=lambda r: (r.get("final_queriability") or 0), reverse=True)
    for i,r in enumerate(rows, start=1): r["rank"] = i
    return rows
