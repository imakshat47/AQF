from __future__ import annotations

import ast
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import pandas as pd

# Operator weights are intentionally explicit because the AQF journal draft treats
# operator awareness as a first-class contribution. These weights are reporting
# metrics only; they do not change form generation.
OPERATOR_WEIGHTS = {
    "is_known": 0.50,
    "is_unknown": 0.50,
    "equals": 1.00,
    "not_equals": 1.00,
    "contains": 1.25,
    "in": 1.25,
    ">": 1.25,
    "<": 1.25,
    "before": 1.25,
    "after": 1.25,
    "between": 1.50,
    "count": 2.00,
    "sum": 2.00,
    "avg": 2.00,
    "min": 2.00,
    "max": 2.00,
    "join": 3.00,
}

GENERIC_CONTEXT_GROUPS = {"Flat Fields", "All Fields", "Composition", "Top-level fields"}


def safe_json_load(path: Path, default=None):
    if default is None:
        default = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def parse_jsonish(value, default=None):
    if default is None:
        default = []
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, float) and math.isnan(value):
        return default
    s = str(value).strip()
    if not s:
        return default
    try:
        return json.loads(s)
    except Exception:
        try:
            return ast.literal_eval(s)
        except Exception:
            return default


def norm(s: Any) -> str:
    s = str(s or "").lower()
    s = s.replace("lymph", "linphonodes")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def infer_field_depth(field: Dict[str, Any]) -> int:
    """Depth used in final AQF complexity C(F)=|E_F|+eta*depth(F).

    We use the canonical path because it is the preserved containment lineage.
    A path like "A / B / C" has depth 3. If only group/subgroup metadata exists,
    we use 1 + subgroup segment count.
    """
    path = field.get("canonical_path") or ""
    if path:
        parts = [p.strip() for p in path.split("/") if p.strip()]
        return max(1, len(parts))
    subgroup = field.get("nested_subgroup") or ""
    return max(1, 1 + len([p for p in subgroup.split("/") if p.strip()]))


def form_depth(form: Dict[str, Any]) -> int:
    fields = form.get("fields", [])
    if not fields:
        return 0
    return max(infer_field_depth(f) for f in fields)


def form_utility(form: Dict[str, Any]) -> float:
    return float(sum(float(f.get("score") or 0.0) for f in form.get("fields", [])))


def final_complexity(form: Dict[str, Any], eta: float = 1.0) -> float:
    return float(len(form.get("fields", [])) + eta * form_depth(form))


def operator_weight(op: str) -> float:
    return OPERATOR_WEIGHTS.get(str(op), 1.0)


def valid_operators_for_dv(field: Dict[str, Any]) -> set:
    dv_types = set(field.get("observed_dv_types") or [])
    if field.get("dv_type"):
        dv_types.add(field.get("dv_type"))
    if field.get("primary_dv_type"):
        dv_types.add(field.get("primary_dv_type"))
    ops = {"is_known", "is_unknown"}
    if "DV_CODED_TEXT" in dv_types:
        ops |= {"equals", "not_equals", "in", "contains"}
    if "DV_TEXT" in dv_types:
        ops |= {"equals", "contains"}
    if "DV_BOOLEAN" in dv_types:
        ops |= {"equals"}
    if "DV_DATE" in dv_types or "DV_DATE_TIME" in dv_types:
        ops |= {"equals", "before", "after", "between"}
    if "DV_COUNT" in dv_types or "DV_QUANTITY" in dv_types or "DV_PROPORTION" in dv_types:
        ops |= {"equals", ">", "<", "between"}
    return ops


def weighted_operator_burden(form: Dict[str, Any]) -> Tuple[float, int, int, int]:
    total_weight = 0.0
    total_ops = 0
    valid_ops = 0
    invalid_ops = 0
    for f in form.get("fields", []):
        valid = valid_operators_for_dv(f)
        for op in f.get("operators", []) or []:
            total_ops += 1
            total_weight += operator_weight(op)
            if op in valid:
                valid_ops += 1
            else:
                invalid_ops += 1
    return total_weight, total_ops, valid_ops, invalid_ops


def complexity_breakdown_for_form(form: Dict[str, Any], eta: float = 1.0) -> Dict[str, Any]:
    wop, op_count, valid_ops, invalid_ops = weighted_operator_burden(form)
    groups = form.get("groups", {}) or {}
    subgroup_count = sum(len(v or {}) for v in groups.values()) if isinstance(groups, dict) else 0
    return {
        "method": form.get("method"),
        "field_count": len(form.get("fields", [])),
        "group_count": len(groups) if isinstance(groups, dict) else 0,
        "subgroup_count": subgroup_count,
        "max_depth": form_depth(form),
        "eta": eta,
        "final_complexity": final_complexity(form, eta=eta),
        "legacy_complexity_score": None,
        "operator_count": op_count,
        "valid_operator_count": valid_ops,
        "invalid_or_unwanted_operator_count": invalid_ops,
        "weighted_operator_burden": wop,
        "form_utility": form_utility(form),
    }


def operator_burden_rows(form: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for rank, f in enumerate(form.get("fields", []), start=1):
        ops = f.get("operators", []) or []
        valid = valid_operators_for_dv(f)
        invalid = [op for op in ops if op not in valid]
        rows.append({
            "method": form.get("method"),
            "rank": rank,
            "field_id": f.get("field_id"),
            "label": f.get("label"),
            "canonical_path": f.get("canonical_path"),
            "dv_type": f.get("dv_type"),
            "operator_count": len(ops),
            "operators_exposed": ";".join(map(str, ops)),
            "valid_operator_count": len([op for op in ops if op in valid]),
            "invalid_or_unwanted_operator_count": len(invalid),
            "invalid_or_unwanted_operators": ";".join(map(str, invalid)),
            "weighted_operator_burden": sum(operator_weight(op) for op in ops),
            "score": f.get("score"),
        })
    return rows


def canonical_structure_metrics_for_form(form: Dict[str, Any]) -> Dict[str, Any]:
    fields = form.get("fields", []) or []
    groups = form.get("groups", {}) or {}
    labels = [norm(f.get("label")) for f in fields]
    duplicate_label_count = len(labels) - len(set(labels))
    context_fields = 0
    for f in fields:
        g = f.get("form_group") or ""
        sg = f.get("nested_subgroup") or ""
        if g and g not in GENERIC_CONTEXT_GROUPS and sg and sg not in GENERIC_CONTEXT_GROUPS:
            context_fields += 1
    lineage_fields = sum(1 for f in fields if f.get("canonical_path"))
    subgroup_count = sum(len(v or {}) for v in groups.values()) if isinstance(groups, dict) else 0
    return {
        "method": form.get("method"),
        "field_count": len(fields),
        "form_group_count": len(groups) if isinstance(groups, dict) else 0,
        "subgroup_count": subgroup_count,
        "max_depth": form_depth(form),
        "avg_depth": sum(infer_field_depth(f) for f in fields) / len(fields) if fields else 0.0,
        "context_preservation_rate": context_fields / len(fields) if fields else 0.0,
        "lineage_preservation_rate": lineage_fields / len(fields) if fields else 0.0,
        "ambiguous_label_count": duplicate_label_count,
        "ambiguous_label_resolution_rate": 1.0 if duplicate_label_count == 0 else max(0.0, 1.0 - duplicate_label_count / len(fields)),
    }


def categorize_query(row: pd.Series) -> str:
    text = " ".join([
        str(row.get("query_id", "")),
        str(row.get("missing_fields", "")),
        str(row.get("match_audit", "")),
    ]).lower()
    if any(t in text for t in ["gender", "birth date", "nationality", "race", "ethnic", "educational", "demographic"]):
        return "demographic"
    if any(t in text for t in ["diagnosis", "problem", "staging", "topography", "histopathological", "linphonodes", "lymph"]):
        return "diagnosis_oriented"
    if any(t in text for t in ["procedure", "therapy", "radiotherapy", "chemotherapy", "transplant", "dialysis", "ultrasonography", "treatment"]):
        return "treatment_procedure"
    if any(t in text for t in ["date", "duration", "follow", "age", "before", "after", "between"]):
        return "temporal"
    # Multiple structural contexts in a query audit often indicate cross-context needs.
    if str(row.get("workload", "")).lower().find("cross") >= 0:
        return "cross_context"
    return "general_clinical"


def coverage_by_category(detail: pd.DataFrame) -> pd.DataFrame:
    d = detail.copy()
    d["query_category"] = d.apply(categorize_query, axis=1)
    rows = []
    for (method, category), g in d.groupby(["method", "query_category"]):
        failure_counts = g.loc[~g["strict_supported"], "failure_type"].value_counts()
        rows.append({
            "method": method,
            "category": category,
            "query_count": len(g),
            "strict_coverage": float(g["strict_supported"].mean()),
            "partial_coverage": float(g["partial_score"].mean()),
            "failure_count": int((~g["strict_supported"]).sum()),
            "dominant_failure_reason": failure_counts.index[0] if len(failure_counts) else "SUPPORTED",
        })
    return pd.DataFrame(rows)


def query_realization_results(detail: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in detail.iterrows():
        audit = parse_jsonish(r.get("match_audit"), default=[])
        matched = [a for a in audit if a.get("matched_field")]
        paths_resolved = bool(matched) and len(matched) == len(audit)
        operator_valid = len(parse_jsonish(r.get("missing_operators"), default=[])) == 0
        strict = bool(r.get("strict_supported"))
        # We generate a conservative pseudo-AQL skeleton for validation reporting.
        where_parts = []
        select_parts = []
        order_parts = []
        for a in audit:
            mf = a.get("matched_field")
            qf = a.get("query_field")
            if not mf:
                continue
            if a.get("component") == "filter":
                where_parts.append(f"{mf} = ?")
            elif a.get("component") == "output":
                select_parts.append(str(mf))
            elif a.get("component") == "sort":
                order_parts.append(str(mf))
        pseudo_aql = "SELECT " + (", ".join(select_parts) if select_parts else "*") + " FROM EHR e"
        if where_parts:
            pseudo_aql += " WHERE " + " AND ".join(where_parts)
        if order_parts:
            pseudo_aql += " ORDER BY " + ", ".join(order_parts)
        rows.append({
            "query_id": r.get("query_id"),
            "method": r.get("method"),
            "strict_supported": strict,
            "aql_generated": strict,
            "syntax_valid": strict,  # pseudo-syntax validation; server execution can replace this.
            "paths_resolved": paths_resolved,
            "operator_valid": operator_valid,
            "execution_success": None,
            "result_count": None,
            "realization_failure_type": "SUPPORTED" if strict else r.get("failure_type"),
            "pseudo_aql": pseudo_aql if strict else "",
        })
    return pd.DataFrame(rows)


def build_candidate_pruning_audit(forest: Dict[str, Any], scores: Dict[str, Any], theta: float) -> pd.DataFrame:
    fields = []
    for family, tree in (forest.get("trees") or {}).items():
        for f in tree.get("fields", []) or []:
            score = (scores.get(f.get("field_id"), {}) or {}).get("overall_score", f.get("score", f.get("coverage", 0.0)))
            fields.append({
                "field_id": f.get("field_id"),
                "label": f.get("label"),
                "canonical_path": f.get("canonical_path"),
                "record_family": family,
                "form_group": f.get("form_group"),
                "nested_subgroup": f.get("nested_subgroup"),
                "score": float(score or 0.0),
                "coverage": f.get("coverage"),
                "kind": f.get("kind"),
                "dv_type": f.get("dv_type"),
            })
    if not fields:
        return pd.DataFrame()
    maxscore = max(x["score"] for x in fields) or 0.0
    threshold = theta * maxscore
    for x in fields:
        x["theta"] = theta
        x["maxscore"] = maxscore
        x["threshold"] = threshold
        x["selected_by_theta"] = x["score"] >= threshold
        parts = [p.strip() for p in str(x.get("canonical_path") or "").split("/") if p.strip()]
        x["depth"] = len(parts)
        x["parent_context"] = " / ".join(parts[:-1]) if len(parts) > 1 else ""
    selected = {x["parent_context"] for x in fields if x["selected_by_theta"] and x["parent_context"]}
    for x in fields:
        x["context_retained_for_selected_leaf"] = x["parent_context"] in selected if x["selected_by_theta"] else False
        x["orphan_leaf"] = bool(x["selected_by_theta"] and x["parent_context"] and x["parent_context"] not in selected)
    return pd.DataFrame(fields).sort_values("score", ascending=False)


def relative_ablation_summary(summary: pd.DataFrame, complexity: pd.DataFrame) -> pd.DataFrame:
    s = summary[(summary["workload"] == "ALL") & (summary["difficulty"] == "ALL")].copy() if {"workload", "difficulty"}.issubset(summary.columns) else summary.copy()
    c = complexity.copy()
    by_method = {r["method"]: r for _, r in s.iterrows()}
    cx = {r["method"]: r for _, r in c.iterrows()}
    rows = []

    def add(comparison, claim, metric, aqf_value, baseline_value):
        try:
            delta = float(aqf_value) - float(baseline_value)
            rel = (delta / float(baseline_value) * 100.0) if float(baseline_value) else None
        except Exception:
            delta, rel = None, None
        rows.append({
            "comparison": comparison,
            "primary_claim": claim,
            "metric": metric,
            "aqf_value": aqf_value,
            "baseline_value": baseline_value,
            "absolute_delta": delta,
            "relative_delta_percent": rel,
        })

    aqf = by_method.get("aqf_full")
    aqfc = cx.get("aqf_full")
    if aqf is None or aqfc is None:
        return pd.DataFrame(rows)
    for baseline, claim in [
        ("no_pruning", "compactness relative to full canonical schema"),
        ("no_operator_awareness", "operator awareness reduces unnecessary controls"),
        ("frequency_only", "AQF ranking vs frequency-only ranking"),
        ("flattened_topk", "canonical structure/context preservation"),
    ]:
        b = by_method.get(baseline)
        bc = cx.get(baseline)
        if b is not None:
            add(f"aqf_full_vs_{baseline}", claim, "strict_coverage", aqf.get("strict_coverage"), b.get("strict_coverage"))
            add(f"aqf_full_vs_{baseline}", claim, "partial_coverage", aqf.get("partial_coverage"), b.get("partial_coverage"))
        if bc is not None:
            for metric in ["field_count", "operator_count", "final_complexity", "weighted_operator_burden", "invalid_or_unwanted_operator_count"]:
                if metric in aqfc and metric in bc:
                    add(f"aqf_full_vs_{baseline}", claim, metric, aqfc.get(metric), bc.get(metric))
    return pd.DataFrame(rows)


def pareto_frontier(df: pd.DataFrame, coverage_col="strict_coverage", complexity_col="final_complexity") -> pd.DataFrame:
    rows = []
    for _, r in df.iterrows():
        dominated = False
        for _, q in df.iterrows():
            if q.name == r.name:
                continue
            if (q[coverage_col] >= r[coverage_col] and q[complexity_col] <= r[complexity_col]) and (q[coverage_col] > r[coverage_col] or q[complexity_col] < r[complexity_col]):
                dominated = True
                break
        out = r.to_dict()
        out["pareto_optimal"] = not dominated
        rows.append(out)
    return pd.DataFrame(rows)
