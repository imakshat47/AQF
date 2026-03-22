# aqf_results.py

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter

import pandas as pd

# -----------------------------
# Constants / heuristics
# -----------------------------
SORTABLE_TYPES = {"DV_COUNT", "DV_QUANTITY", "DV_DATE", "DV_DATE_TIME", "DV_ORDINAL"}
TEXT_TYPES = {"DV_TEXT", "DV_CODED_TEXT"}

DEFAULT_SWEEP_THRESHOLDS = [2, 4, 6, 8, 10, 12]

# Utility to avoid division-by-zero
EPS = 1e-9


# -----------------------------
# Basic I/O
# -----------------------------
def load_json(path: str | Path) -> Any:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(obj: Any, path: str | Path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def save_csv(df: pd.DataFrame, path: str | Path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


# -----------------------------
# Math helpers
# -----------------------------
def entropy_from_counts(counts: Dict[str, int]) -> float:
    total = sum(counts.values())
    if total <= 1:
        return 0.0
    h = 0.0
    for c in counts.values():
        if c <= 0:
            continue
        p = c / total
        h -= p * math.log2(p)
    return h


def normalize_map(values: Dict[str, float]) -> Dict[str, float]:
    if not values:
        return {}
    mn = min(values.values())
    mx = max(values.values())
    if abs(mx - mn) < EPS:
        return {k: 1.0 for k in values}
    return {k: (v - mn) / (mx - mn) for k, v in values.items()}


def safe_ratio(num: float, den: float) -> float:
    return num / den if abs(den) > EPS else 0.0


# -----------------------------
# Schema parsing / flattening
# -----------------------------
def parse_union_schema(union_schema: Dict[str, Any]) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Parse schema_union.json into three tables:
      - sections
      - subgroups
      - fields

    Expected structure:
      union_schema["groups"][entry_arch] = {
        "entry_name": ...,
        "entry_type": ...,
        "subgroups": {
           subgroup_key: {
             "fields": {
                field_sig: {
                    "entry_arch": ...,
                    "entry_name": ...,
                    "cluster_path": [...],
                    "cluster_path_str": ...,
                    "element_name": ...,
                    "element_at_code": ...,
                    "dv_type": ...,
                    "has_null_flavour": bool,
                    "occurrences": int,
                    "sample_values": {value: count},
                    "sample_value_count": int,
                    "has_known_values": bool,
                    "has_unknown_values": bool
                }
             }
           }
        }
      }
    """
    section_rows = []
    subgroup_rows = []
    field_rows = []

    comp_arch = union_schema.get("composition_archetype", "UNKNOWN_COMPOSITION")
    comp_label = union_schema.get("composition_label", "Unknown composition")

    groups = union_schema.get("groups", {})
    for entry_arch, group in groups.items():
        entry_name = group.get("entry_name", entry_arch)
        entry_type = group.get("entry_type", "ENTRY")

        subgroups = group.get("subgroups", {})
        section_rows.append({
            "composition_archetype": comp_arch,
            "composition_label": comp_label,
            "entry_arch": entry_arch,
            "entry_name": entry_name,
            "entry_type": entry_type,
            "subgroup_count": len(subgroups)
        })

        for subgroup_key, subgroup in subgroups.items():
            fields = subgroup.get("fields", {})
            subgroup_rows.append({
                "composition_archetype": comp_arch,
                "entry_arch": entry_arch,
                "entry_name": entry_name,
                "subgroup_key": subgroup_key,
                "field_count": len(fields)
            })

            for field_sig, field in fields.items():
                sample_values = field.get("sample_values", {})
                sample_value_count = field.get("sample_value_count", 0)
                unknown_count = sample_values.get("unknown", 0)

                field_rows.append({
                    "composition_archetype": comp_arch,
                    "entry_arch": entry_arch,
                    "entry_name": entry_name,
                    "subgroup_key": subgroup_key,
                    "field_sig": field_sig,
                    "cluster_path_str": field.get("cluster_path_str", subgroup_key),
                    "element_name": field.get("element_name", "(element)"),
                    "element_at_code": field.get("element_at_code", ""),
                    "dv_type": field.get("dv_type", "UNKNOWN_DV"),
                    "has_null_flavour": bool(field.get("has_null_flavour", False)),
                    "occurrences": int(field.get("occurrences", 0)),
                    "sample_value_count": int(sample_value_count),
                    "unique_values": len(sample_values),
                    "unknown_count": int(unknown_count),
                    "unknown_ratio": safe_ratio(unknown_count, sample_value_count),
                    "entropy_raw": entropy_from_counts(sample_values),
                    "sample_values_json": json.dumps(sample_values, ensure_ascii=False),
                    "has_known_values": bool(field.get("has_known_values", False)),
                    "has_unknown_values": bool(field.get("has_unknown_values", False)),
                })

    sections_df = pd.DataFrame(section_rows)
    subgroups_df = pd.DataFrame(subgroup_rows)
    fields_df = pd.DataFrame(field_rows)

    return sections_df, subgroups_df, fields_df


# -----------------------------
# Structure metrics
# -----------------------------
def compute_structure_metrics(union_schema: Dict[str, Any]) -> pd.DataFrame:
    sections_df, subgroups_df, fields_df = parse_union_schema(union_schema)

    total_sections = len(sections_df)
    total_subgroups = len(subgroups_df)
    total_fields = len(fields_df)

    rows = [{
        "composition_archetype": union_schema.get("composition_archetype", "UNKNOWN_COMPOSITION"),
        "composition_label": union_schema.get("composition_label", "Unknown composition"),
        "section_count": total_sections,
        "subgroup_count": total_subgroups,
        "field_count": total_fields,
        "avg_subgroups_per_section": safe_ratio(total_subgroups, total_sections),
        "avg_fields_per_subgroup": safe_ratio(total_fields, total_subgroups),
        "avg_fields_per_section": safe_ratio(total_fields, total_sections),
        "null_supporting_fields": int(fields_df["has_null_flavour"].sum()) if not fields_df.empty else 0
    }]

    return pd.DataFrame(rows)


# -----------------------------
# Queriability
# -----------------------------
def compute_queriability_scores(union_schema: Dict[str, Any], fields_catalog: Optional[List[Dict[str, Any]]] = None) -> Dict[str, pd.DataFrame]:
    """
    Returns:
      {
        "sections": DataFrame,
        "subgroups": DataFrame,
        "fields": DataFrame
      }
    """
    sections_df, subgroups_df, fields_df = parse_union_schema(union_schema)

    # -------------------------
    # Section queriability
    # Signals:
    # - coverage proxy: total field occurrences under section
    # - connectedness proxy: subgroup_count + total fields
    # - knownness proxy: average known fraction under section
    # -------------------------
    if sections_df.empty:
        return {
            "sections": sections_df,
            "subgroups": subgroups_df,
            "fields": fields_df
        }

    section_occ = fields_df.groupby(["entry_arch", "entry_name"])["occurrences"].sum().to_dict()
    section_field_count = fields_df.groupby(["entry_arch", "entry_name"]).size().to_dict()
    section_knownness = (
        1.0 - fields_df.groupby(["entry_arch", "entry_name"])["unknown_ratio"].mean().fillna(0.0)
    ).to_dict()

    raw_section_cov = {}
    raw_section_conn = {}
    raw_section_known = {}
    for _, row in sections_df.iterrows():
        key = (row["entry_arch"], row["entry_name"])
        raw_section_cov["|".join(key)] = float(section_occ.get(key, 0))
        raw_section_conn["|".join(key)] = float(row["subgroup_count"] + section_field_count.get(key, 0))
        raw_section_known["|".join(key)] = float(section_knownness.get(key, 0))

    norm_section_cov = normalize_map(raw_section_cov)
    norm_section_conn = normalize_map(raw_section_conn)
    norm_section_known = normalize_map(raw_section_known)

    section_scores = []
    for _, row in sections_df.iterrows():
        skey = "|".join([row["entry_arch"], row["entry_name"]])
        coverage = norm_section_cov.get(skey, 0)
        connectedness = norm_section_conn.get(skey, 0)
        knownness = norm_section_known.get(skey, 0)

        # weighted composite
        entity_q = 0.45 * coverage + 0.35 * connectedness + 0.20 * knownness

        section_scores.append({
            **row.to_dict(),
            "coverage_score": coverage,
            "connectedness_score": connectedness,
            "knownness_score": knownness,
            "entity_queriability": entity_q
        })

    sections_q_df = pd.DataFrame(section_scores)

    # -------------------------
    # Subgroup queriability
    # Signals:
    # - coverage proxy: total occurrences of fields under subgroup
    # - richness proxy: field_count
    # - knownness proxy: avg known fraction
    # -------------------------
    subgroup_occ = fields_df.groupby(["entry_arch", "entry_name", "subgroup_key"])["occurrences"].sum().to_dict()
    subgroup_knownness = (
        1.0 - fields_df.groupby(["entry_arch", "entry_name", "subgroup_key"])["unknown_ratio"].mean().fillna(0.0)
    ).to_dict()

    raw_sub_cov = {}
    raw_sub_rich = {}
    raw_sub_known = {}
    for _, row in subgroups_df.iterrows():
        key = (row["entry_arch"], row["entry_name"], row["subgroup_key"])
        skey = "|".join(key)
        raw_sub_cov[skey] = float(subgroup_occ.get(key, 0))
        raw_sub_rich[skey] = float(row["field_count"])
        raw_sub_known[skey] = float(subgroup_knownness.get(key, 0))

    norm_sub_cov = normalize_map(raw_sub_cov)
    norm_sub_rich = normalize_map(raw_sub_rich)
    norm_sub_known = normalize_map(raw_sub_known)

    subgroup_scores = []
    for _, row in subgroups_df.iterrows():
        skey = "|".join([row["entry_arch"], row["entry_name"], row["subgroup_key"]])
        coverage = norm_sub_cov.get(skey, 0)
        richness = norm_sub_rich.get(skey, 0)
        knownness = norm_sub_known.get(skey, 0)

        subgroup_q = 0.45 * coverage + 0.30 * richness + 0.25 * knownness

        subgroup_scores.append({
            **row.to_dict(),
            "coverage_score": coverage,
            "richness_score": richness,
            "knownness_score": knownness,
            "subgroup_queriability": subgroup_q
        })

    subgroups_q_df = pd.DataFrame(subgroup_scores)

    # -------------------------
    # Field queriability / operator-specific scores
    # Signals:
    # - coverage
    # - entropy (normalized)
    # - knownness (1 - unknown_ratio)
    # - sortability
    # -------------------------
    raw_field_cov = {r["field_sig"]: float(r["occurrences"]) for _, r in fields_df.iterrows()}
    raw_field_entropy = {r["field_sig"]: float(r["entropy_raw"]) for _, r in fields_df.iterrows()}
    raw_field_known = {r["field_sig"]: float(1.0 - r["unknown_ratio"]) for _, r in fields_df.iterrows()}

    norm_field_cov = normalize_map(raw_field_cov)
    norm_field_entropy = normalize_map(raw_field_entropy)
    norm_field_known = normalize_map(raw_field_known)

    field_scores = []
    for _, row in fields_df.iterrows():
        field_sig = row["field_sig"]
        coverage = norm_field_cov.get(field_sig, 0.0)
        entropy = norm_field_entropy.get(field_sig, 0.0)
        knownness = norm_field_known.get(field_sig, 0.0)
        sortability = 1.0 if row["dv_type"] in SORTABLE_TYPES else 0.0

        # selection: coverage + diversity + knownness
        selection_q = 0.45 * coverage + 0.35 * entropy + 0.20 * knownness

        # projection: stable presence + knownness + semantic informativeness proxy
        # here semantic informativeness proxy is just entropy damped for very sparse fields
        projection_q = 0.55 * coverage + 0.25 * knownness + 0.20 * entropy

        # ordering: presence + orderability + knownness
        ordering_q = 0.55 * coverage + 0.30 * sortability + 0.15 * knownness

        default_role = max(
            [("selection", selection_q), ("projection", projection_q), ("ordering", ordering_q)],
            key=lambda x: x[1]
        )[0]

        field_scores.append({
            **row.to_dict(),
            "coverage_score": coverage,
            "entropy_score": entropy,
            "knownness_score": knownness,
            "sortability_score": sortability,
            "selection_score": selection_q,
            "projection_score": projection_q,
            "ordering_score": ordering_q,
            "default_role": default_role,
            "max_role_score": max(selection_q, projection_q, ordering_q)
        })

    fields_q_df = pd.DataFrame(field_scores)

    # Optional join with fields.json (if supplied)
    if fields_catalog:
        cat_df = pd.DataFrame(fields_catalog)
        if not cat_df.empty and "field_key" in cat_df.columns:
            # map field_sig -> field_key if available
            # safest partial join by label names
            pass

    return {
        "sections": sections_q_df,
        "subgroups": subgroups_q_df,
        "fields": fields_q_df
    }


# -----------------------------
# Threshold sweep
# -----------------------------
def _select_fields_with_structure(fields_q_df: pd.DataFrame, threshold: int, max_groups: Optional[int] = None) -> pd.DataFrame:
    """
    Structure-aware selection:
    1) rank groups by avg field score
    2) optionally keep top groups
    3) within each subgroup, keep top fields until total threshold is exhausted
    """
    if fields_q_df.empty:
        return fields_q_df.copy()

    work = fields_q_df.copy()

    # group score
    grp_scores = (
        work.groupby(["entry_arch", "entry_name"])["max_role_score"]
        .mean()
        .reset_index()
        .sort_values("max_role_score", ascending=False)
    )

    if max_groups is not None:
        grp_scores = grp_scores.head(max_groups)

    keep_groups = set(zip(grp_scores["entry_arch"], grp_scores["entry_name"]))
    work = work[work.apply(lambda r: (r["entry_arch"], r["entry_name"]) in keep_groups, axis=1)]

    # subgroup-wise top ranking
    work = work.sort_values(
        ["entry_arch", "subgroup_key", "max_role_score"],
        ascending=[True, True, False]
    )

    selected_rows = []
    remaining = threshold

    for (_, _, subgroup_key), subdf in work.groupby(["entry_arch", "entry_name", "subgroup_key"], sort=False):
        if remaining <= 0:
            break
        take_n = min(len(subdf), max(1, math.ceil(threshold / max(1, work["subgroup_key"].nunique()))))
        chosen = subdf.head(min(take_n, remaining))
        selected_rows.append(chosen)
        remaining -= len(chosen)

    if selected_rows:
        selected = pd.concat(selected_rows, ignore_index=True)
    else:
        selected = work.head(0).copy()

    # if still under threshold, fill globally from remaining
    if len(selected) < threshold:
        selected_ids = set(selected["field_sig"].tolist())
        remaining_df = work[~work["field_sig"].isin(selected_ids)].sort_values("max_role_score", ascending=False)
        fill = remaining_df.head(threshold - len(selected))
        if not fill.empty:
            selected = pd.concat([selected, fill], ignore_index=True)

    return selected


def _select_fields_no_structure(fields_q_df: pd.DataFrame, threshold: int) -> pd.DataFrame:
    if fields_q_df.empty:
        return fields_q_df.copy()
    return fields_q_df.sort_values("max_role_score", ascending=False).head(threshold).copy()


def _compute_structural_coverage(selected: pd.DataFrame, all_fields: pd.DataFrame) -> Tuple[float, float, float]:
    if all_fields.empty:
        return 0.0, 0.0, 0.0

    total_sections = all_fields[["entry_arch", "entry_name"]].drop_duplicates().shape[0]
    total_subgroups = all_fields[["entry_arch", "entry_name", "subgroup_key"]].drop_duplicates().shape[0]
    total_fields = all_fields["field_sig"].nunique()

    sel_sections = selected[["entry_arch", "entry_name"]].drop_duplicates().shape[0] if not selected.empty else 0
    sel_subgroups = selected[["entry_arch", "entry_name", "subgroup_key"]].drop_duplicates().shape[0] if not selected.empty else 0
    sel_fields = selected["field_sig"].nunique() if not selected.empty else 0

    return (
        safe_ratio(sel_sections, total_sections),
        safe_ratio(sel_subgroups, total_subgroups),
        safe_ratio(sel_fields, total_fields)
    )


def _compute_complexity(selected: pd.DataFrame) -> float:
    """
    Simple complexity proxy:
      visible fields + 0.5 * subgroups + 1.0 * groups
    """
    if selected.empty:
        return 0.0
    field_count = selected["field_sig"].nunique()
    subgroup_count = selected[["entry_arch", "entry_name", "subgroup_key"]].drop_duplicates().shape[0]
    section_count = selected[["entry_arch", "entry_name"]].drop_duplicates().shape[0]
    return field_count + 0.5 * subgroup_count + 1.0 * section_count


def run_threshold_sweep(union_schema: Dict[str, Any],
                        thresholds: Optional[List[int]] = None,
                        max_groups: Optional[int] = None) -> pd.DataFrame:
    """
    AQF threshold sweep over visible field budget.

    Returns one row per threshold with:
      - form_set_size (visible section count as current proxy)
      - structural_expressivity
      - section/subgroup/field coverage
      - complexity
    """
    thresholds = thresholds or DEFAULT_SWEEP_THRESHOLDS
    scores = compute_queriability_scores(union_schema)
    fields_q_df = scores["fields"]

    rows = []
    total_possible_score = fields_q_df["max_role_score"].sum() if not fields_q_df.empty else 0.0

    for t in thresholds:
        selected = _select_fields_with_structure(fields_q_df, threshold=t, max_groups=max_groups)

        sec_cov, sub_cov, fld_cov = _compute_structural_coverage(selected, fields_q_df)
        complexity = _compute_complexity(selected)
        expressivity = safe_ratio(selected["max_role_score"].sum(), total_possible_score)

        form_set_size = selected[["entry_arch", "entry_name"]].drop_duplicates().shape[0] if not selected.empty else 0

        rows.append({
            "threshold": t,
            "form_set_size": form_set_size,
            "structural_expressivity": expressivity,
            "section_coverage": sec_cov,
            "subgroup_coverage": sub_cov,
            "field_coverage": fld_cov,
            "complexity": complexity,
            "selected_fields": int(selected["field_sig"].nunique()) if not selected.empty else 0
        })

    return pd.DataFrame(rows)


# -----------------------------
# Ablations
# -----------------------------
def _apply_ablation_variant(fields_q_df: pd.DataFrame, variant: str) -> pd.DataFrame:
    df = fields_q_df.copy()

    if variant == "full":
        return df

    if variant == "no_structure_awareness":
        return df

    if variant == "no_operator_specific_scoring":
        # replace operator-specific scores by generic coverage-only score
        generic = 0.7 * df["coverage_score"] + 0.3 * df["knownness_score"]
        df["selection_score"] = generic
        df["projection_score"] = generic
        df["ordering_score"] = generic
        df["max_role_score"] = generic
        return df

    if variant == "no_missingness_handling":
        # ignore unknown penalty
        coverage = df["coverage_score"]
        entropy = df["entropy_score"]
        sortability = df["sortability_score"]

        df["selection_score"] = 0.50 * coverage + 0.50 * entropy
        df["projection_score"] = 0.65 * coverage + 0.35 * entropy
        df["ordering_score"] = 0.65 * coverage + 0.35 * sortability
        df["max_role_score"] = df[["selection_score", "projection_score", "ordering_score"]].max(axis=1)
        return df

    if variant == "no_progressive_disclosure":
        # emulate higher visible complexity penalty:
        # keep scores, but later utility will be penalized
        return df

    if variant == "no_suggestion_cache":
        # Not much effect on pure structural scores; can reflect later in usability proxy.
        return df

    raise ValueError(f"Unknown ablation variant: {variant}")


def run_ablations(union_schema: Dict[str, Any],
                  threshold: int = 8,
                  max_groups: Optional[int] = None,
                  variants: Optional[List[str]] = None) -> pd.DataFrame:
    variants = variants or [
        "full",
        "no_structure_awareness",
        "no_operator_specific_scoring",
        "no_missingness_handling",
        "no_progressive_disclosure"
    ]

    scores = compute_queriability_scores(union_schema)
    base_fields = scores["fields"]

    rows = []
    base_total_score = base_fields["max_role_score"].sum() if not base_fields.empty else 0.0

    for variant in variants:
        fields_q_df = _apply_ablation_variant(base_fields, variant)

        if variant == "no_structure_awareness":
            selected = _select_fields_no_structure(fields_q_df, threshold)
        else:
            selected = _select_fields_with_structure(fields_q_df, threshold=threshold, max_groups=max_groups)

        sec_cov, sub_cov, fld_cov = _compute_structural_coverage(selected, base_fields)
        complexity = _compute_complexity(selected)
        expressivity = safe_ratio(selected["max_role_score"].sum(), base_total_score)

        # Utility proxy:
        # combine expressivity + field coverage - normalized complexity penalty
        complexity_penalty = safe_ratio(complexity, max(1.0, threshold + 2.0))
        utility = 0.50 * expressivity + 0.30 * fld_cov + 0.20 * max(0.0, 1.0 - min(1.0, complexity_penalty))

        if variant == "no_progressive_disclosure":
            utility *= 0.85  # explicit penalty for exposing too much

        rows.append({
            "variant": variant,
            "threshold": threshold,
            "structural_expressivity": expressivity,
            "section_coverage": sec_cov,
            "subgroup_coverage": sub_cov,
            "field_coverage": fld_cov,
            "complexity": complexity,
            "utility_proxy": utility,
            "selected_fields": int(selected["field_sig"].nunique()) if not selected.empty else 0
        })

    return pd.DataFrame(rows)


# -----------------------------
# Execution metrics
# -----------------------------
def run_execution_benchmark(query_executor_module,
                            query_compiler_module,
                            dataset_folder: str,
                            composition_archetype: str,
                            query_cases: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    query_cases format:
    [
      {
        "name": "state_is_sp",
        "form_state": {
          "criteria": [...],
          "output_fields": [...],
          "sort": {...} | None,
          "advanced": {...}
        }
      },
      ...
    ]
    """
    # Resolve files lazily from current dataset
    from composition_loader import group_docs_by_composition_archetype

    valid_groups, skipped = group_docs_by_composition_archetype(Path(dataset_folder))
    files = [p for p, _ in valid_groups.get(composition_archetype, [])]

    rows = []
    for case in query_cases:
        name = case["name"]
        form_state = case["form_state"]

        t0 = time.perf_counter()
        plan = query_compiler_module.compile_query(form_state)
        compile_sec = time.perf_counter() - t0

        t1 = time.perf_counter()
        out = query_executor_module.run_query(
            files[: int(form_state.get("advanced", {}).get("slice_size", 200))],
            plan,
            occurrence_semantics=form_state.get("advanced", {}).get("occurrence_semantics", "ALL"),
            limit=int(form_state.get("advanced", {}).get("result_limit", 100))
        )
        exec_sec = time.perf_counter() - t1

        interactions = (
            len(form_state.get("criteria", []))
            + len(form_state.get("output_fields", []))
            + (1 if form_state.get("sort") else 0)
            + 1  # run query click
        )

        rows.append({
            "query_name": name,
            "compile_sec": compile_sec,
            "execution_sec": exec_sec,
            "scanned": out.get("scanned", 0),
            "matched": out.get("matched", 0),
            "sec_per_doc": out.get("sec_per_doc", 0.0),
            "interaction_count": interactions
        })

    return pd.DataFrame(rows)


# -----------------------------
# Qualitative / structured matrices
# -----------------------------
def make_related_work_matrix() -> pd.DataFrame:
    rows = [
        {
            "approach_family": "Workload-driven automatic query forms",
            "input_assumption": "Representative query workload available",
            "hierarchy_support": "Limited / schema-centric",
            "workload_dependency": "High",
            "query_generation_style": "Canonical form -> declarative query",
            "explainability": "Low",
            "limitation": "Hard to use in cold-start settings"
        },
        {
            "approach_family": "Schema/content-driven form generation",
            "input_assumption": "Schema + data content",
            "hierarchy_support": "Moderate",
            "workload_dependency": "Low",
            "query_generation_style": "Forms derived from queriability",
            "explainability": "Low",
            "limitation": "Weaker direct grounding in actual user intent"
        },
        {
            "approach_family": "Visual exploration systems",
            "input_assumption": "Interactive navigation / browsing",
            "hierarchy_support": "High",
            "workload_dependency": "Low",
            "query_generation_style": "Navigation-first / exploratory",
            "explainability": "Moderate",
            "limitation": "Often not form-centric or directly executable"
        },
        {
            "approach_family": "AQF",
            "input_assumption": "Schema + content + structure-aware extraction",
            "hierarchy_support": "High",
            "workload_dependency": "Low initially",
            "query_generation_style": "Generated form -> AQL",
            "explainability": "High",
            "limitation": "First generation is structure-driven, not yet workload-adaptive"
        }
    ]
    return pd.DataFrame(rows)


def make_aqf_metric_matrix() -> pd.DataFrame:
    rows = [
        {
            "aqf_component": "Structure extraction",
            "correctness": 1,
            "coverage": 1,
            "expressivity": 0,
            "complexity": 0,
            "latency": 0,
            "usability": 0,
            "explanation_quality": 0
        },
        {
            "aqf_component": "Queriability scoring",
            "correctness": 0,
            "coverage": 1,
            "expressivity": 1,
            "complexity": 1,
            "latency": 0,
            "usability": 0,
            "explanation_quality": 0
        },
        {
            "aqf_component": "Form composition",
            "correctness": 0,
            "coverage": 1,
            "expressivity": 1,
            "complexity": 1,
            "latency": 0,
            "usability": 1,
            "explanation_quality": 0
        },
        {
            "aqf_component": "Query compilation",
            "correctness": 1,
            "coverage": 0,
            "expressivity": 0,
            "complexity": 0,
            "latency": 1,
            "usability": 0,
            "explanation_quality": 0
        },
        {
            "aqf_component": "Explainability",
            "correctness": 0,
            "coverage": 0,
            "expressivity": 0,
            "complexity": 0,
            "latency": 0,
            "usability": 1,
            "explanation_quality": 1
        }
    ]
    return pd.DataFrame(rows)


def make_baseline_vs_aqf_matrix() -> pd.DataFrame:
    rows = [
        {
            "system_family": "Workload-driven forms",
            "cold_start_support": "Low",
            "hierarchical_awareness": "Medium",
            "operator_specific_reasoning": "Medium",
            "explainability": "Low",
            "user_effort": "Medium",
            "scalability": "High"
        },
        {
            "system_family": "Schema/content-driven forms",
            "cold_start_support": "High",
            "hierarchical_awareness": "Medium",
            "operator_specific_reasoning": "High",
            "explainability": "Low",
            "user_effort": "Medium",
            "scalability": "High"
        },
        {
            "system_family": "Visual exploration systems",
            "cold_start_support": "High",
            "hierarchical_awareness": "High",
            "operator_specific_reasoning": "Low",
            "explainability": "Medium",
            "user_effort": "Higher",
            "scalability": "Medium"
        },
        {
            "system_family": "AQF",
            "cold_start_support": "High",
            "hierarchical_awareness": "High",
            "operator_specific_reasoning": "High",
            "explainability": "High",
            "user_effort": "Lower",
            "scalability": "High"
        }
    ]
    return pd.DataFrame(rows)


def make_operator_suitability_matrix(fields_q_df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "entry_name", "subgroup_key", "element_name", "dv_type",
        "selection_score", "projection_score", "ordering_score", "default_role"
    ]
    if fields_q_df.empty:
        return pd.DataFrame(columns=cols)
    return fields_q_df[cols].sort_values(
        ["entry_name", "subgroup_key", "selection_score"],
        ascending=[True, True, False]
    ).reset_index(drop=True)


# -----------------------------
# Main package generation
# -----------------------------
def generate_results_package(cache_dir: str | Path,
                             out_dir: str | Path,
                             thresholds: Optional[List[int]] = None,
                             max_groups: Optional[int] = None):
    cache_dir = Path(cache_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    union_schema = load_json(cache_dir / "schema_union.json")
    fields_catalog = load_json(cache_dir / "fields.json") if (cache_dir / "fields.json").exists() else []

    # structure metrics
    structure_df = compute_structure_metrics(union_schema)
    save_csv(structure_df, out_dir / "derived_metrics" / "structure_metrics.csv")

    # queriability
    q = compute_queriability_scores(union_schema, fields_catalog)
    save_csv(q["sections"], out_dir / "derived_metrics" / "queriability_sections.csv")
    save_csv(q["subgroups"], out_dir / "derived_metrics" / "queriability_subgroups.csv")
    save_csv(q["fields"], out_dir / "derived_metrics" / "queriability_fields.csv")

    # threshold sweep
    threshold_df = run_threshold_sweep(union_schema, thresholds=thresholds, max_groups=max_groups)
    save_csv(threshold_df, out_dir / "derived_metrics" / "threshold_sweep.csv")

    # ablations
    ablation_df = run_ablations(union_schema, threshold=max(thresholds or DEFAULT_SWEEP_THRESHOLDS), max_groups=max_groups)
    save_csv(ablation_df, out_dir / "derived_metrics" / "ablation_results.csv")

    # qualitative matrices
    save_csv(make_related_work_matrix(), out_dir / "qualitative_tables" / "related_work_matrix.csv")
    save_csv(make_aqf_metric_matrix(), out_dir / "qualitative_tables" / "aqf_metric_matrix.csv")
    save_csv(make_baseline_vs_aqf_matrix(), out_dir / "qualitative_tables" / "baseline_vs_aqf_matrix.csv")
    save_csv(make_operator_suitability_matrix(q["fields"]), out_dir / "qualitative_tables" / "operator_suitability_matrix.csv")

    # summary JSON
    summary = {
        "structure_metrics_rows": len(structure_df),
        "queriability_sections_rows": len(q["sections"]),
        "queriability_subgroups_rows": len(q["subgroups"]),
        "queriability_fields_rows": len(q["fields"]),
        "threshold_points": len(threshold_df),
        "ablation_rows": len(ablation_df)
    }
    save_json(summary, out_dir / "summary.json")

    return {
        "structure_metrics": structure_df,
        "queriability": q,
        "threshold_sweep": threshold_df,
        "ablation_results": ablation_df
    }