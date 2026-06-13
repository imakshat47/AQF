#!/usr/bin/env python3
"""
operator_aware_field_selector.py

Generate operator-aware AQF canonical forms from canonical_forms.json.

Input:
  output/canonical/canonical_forms.json

Outputs:
  operator_aware_forms.json
  operator_aware_fields.json
  operator_aware_fields.csv
  operator_aware_form_summary.csv

Core idea:
  AQ(v, o) = Q(v) * compat(v, o)

Where:
  Q(v)          = canonical element queriability inherited from weighted schema graph
  compat(v, o) = datatype/operator compatibility score

This module refines:
  IT = input tree based on filter-compatible operators
  OT = output tree based on projection/sort/group/aggregation-compatible operators
  RT = relationship tree with relation role and relation priority
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# Dataclasses
# ============================================================

@dataclass
class OperatorScore:
    operator: str
    operator_class: str
    compatibility: float
    operator_adjusted_queriability: float
    control_type: str
    reason: str


@dataclass
class OperatorAwareField:
    canonical_id: str
    source_node_id: str
    name: str
    datatype: Optional[str]
    canonical_type: str
    rm_type: str
    path: str
    archetype_node_id: Optional[str]
    archetype_id: Optional[str]
    template_id: Optional[str]
    queriability: float
    input_operators: List[OperatorScore] = field(default_factory=list)
    output_operators: List[OperatorScore] = field(default_factory=list)
    best_input_operator: Optional[str] = None
    best_output_operator: Optional[str] = None
    best_input_score: float = 0.0
    best_output_score: float = 0.0
    field_role: str = "unused"


# ============================================================
# Operator-Aware Selector
# ============================================================

class AQFOperatorAwareFieldSelector:
    """Compute operator-aware fields and refine IT, OT, RT for canonical forms."""

    INPUT_OPERATOR_RULES: Dict[str, List[Tuple[str, str, float, str, str]]] = {
        "temporal": [
            ("date_range", "filter", 1.00, "date_range_picker", "Temporal values support interval predicates."),
            ("date_equals", "filter", 0.72, "date_picker", "Temporal values may support exact-date filtering."),
            ("is_present", "filter", 0.45, "checkbox", "Presence predicates are useful for sparse clinical concepts."),
        ],
        "numeric": [
            ("range", "filter", 1.00, "range_slider", "Numeric values support range predicates."),
            ("greater_than_less_than", "filter", 0.95, "numeric_comparator", "Numeric values support comparative predicates."),
            ("equals", "filter", 0.60, "numeric_input", "Exact numeric filtering may be useful but less general than ranges."),
            ("is_present", "filter", 0.45, "checkbox", "Presence predicates are useful for sparse clinical concepts."),
        ],
        "categorical": [
            ("equals", "filter", 1.00, "dropdown", "Coded values naturally support equality filtering."),
            ("multi_select", "filter", 0.95, "multi_select", "Coded values support selecting multiple categories."),
            ("is_present", "filter", 0.45, "checkbox", "Presence predicates are useful for sparse clinical concepts."),
        ],
        "text": [
            ("contains", "filter", 0.90, "text_search", "Text values support contains/search predicates."),
            ("starts_with", "filter", 0.65, "text_input", "Prefix search can be useful for text fields."),
            ("equals", "filter", 0.40, "text_input", "Exact text equality is usually less robust."),
            ("is_present", "filter", 0.45, "checkbox", "Presence predicates are useful for sparse clinical concepts."),
        ],
        "boolean": [
            ("equals", "filter", 1.00, "boolean_toggle", "Boolean values support true/false filtering."),
            ("is_present", "filter", 0.45, "checkbox", "Presence predicates are useful for sparse clinical concepts."),
        ],
        "unknown": [
            ("equals", "filter", 0.35, "generic_input", "Unknown datatype receives conservative equality compatibility."),
            ("is_present", "filter", 0.50, "checkbox", "Presence filtering is datatype independent."),
        ],
    }

    OUTPUT_OPERATOR_RULES: Dict[str, List[Tuple[str, str, float, str, str]]] = {
        "temporal": [
            ("project", "projection", 0.92, "result_column", "Temporal values are useful result attributes."),
            ("sort", "ordering", 1.00, "sort_control", "Temporal values naturally support chronological ordering."),
            ("group_by", "grouping", 0.55, "group_control", "Temporal grouping may be useful by date/month/year."),
        ],
        "numeric": [
            ("project", "projection", 0.92, "result_column", "Numeric values are useful result attributes."),
            ("sort", "ordering", 0.92, "sort_control", "Numeric values support ordering."),
            ("aggregate", "aggregation", 0.88, "aggregation_control", "Numeric values support min/max/avg/count aggregation."),
            ("group_by", "grouping", 0.45, "group_control", "Numeric grouping is possible but less common than categorical grouping."),
        ],
        "categorical": [
            ("project", "projection", 0.90, "result_column", "Coded values are useful result attributes."),
            ("group_by", "grouping", 0.95, "group_control", "Categorical values naturally support grouping."),
            ("sort", "ordering", 0.55, "sort_control", "Categorical values may support lexical or coded ordering."),
        ],
        "text": [
            ("project", "projection", 0.92, "result_column", "Text values are useful result attributes."),
            ("sort", "ordering", 0.35, "sort_control", "Text sorting is possible but often less clinically meaningful."),
            ("group_by", "grouping", 0.25, "group_control", "Free text grouping is usually weak."),
        ],
        "boolean": [
            ("project", "projection", 0.82, "result_column", "Boolean values can be displayed as result attributes."),
            ("group_by", "grouping", 0.85, "group_control", "Boolean values support grouping."),
        ],
        "unknown": [
            ("project", "projection", 0.55, "result_column", "Unknown datatype receives conservative projection compatibility."),
        ],
    }

    DATATYPE_GROUPS = {
        "DV_DATE": "temporal",
        "DV_DATE_TIME": "temporal",
        "DV_TIME": "temporal",
        "DV_DURATION": "numeric",
        "DV_COUNT": "numeric",
        "DV_QUANTITY": "numeric",
        "DV_PROPORTION": "numeric",
        "DV_ORDINAL": "numeric",
        "DV_CODED_TEXT": "categorical",
        "DV_BOOLEAN": "boolean",
        "DV_TEXT": "text",
        "DV_MULTIMEDIA": "unknown",
        "DV_IDENTIFIER": "categorical",
        "DV_URI": "text",
    }

    def __init__(
        self,
        min_input_aq: float = 0.0,
        min_output_aq: float = 0.0,
        top_k_input_per_form: Optional[int] = None,
        top_k_output_per_form: Optional[int] = None,
        keep_all_operator_scores: bool = True,
    ) -> None:
        self.min_input_aq = min_input_aq
        self.min_output_aq = min_output_aq
        self.top_k_input_per_form = top_k_input_per_form
        self.top_k_output_per_form = top_k_output_per_form
        self.keep_all_operator_scores = keep_all_operator_scores

        self.canonical_payload: Dict[str, Any] = {}
        self.operator_fields: Dict[str, OperatorAwareField] = {}
        self.operator_forms: List[Dict[str, Any]] = []

    # --------------------------------------------------------
    # Public API
    # --------------------------------------------------------

    def load_canonical_forms(self, canonical_forms_json: str | Path) -> None:
        with open(canonical_forms_json, "r", encoding="utf-8") as f:
            self.canonical_payload = json.load(f)

        if "canonical_forms" not in self.canonical_payload:
            raise ValueError("Input file does not contain 'canonical_forms'.")

    def generate(self) -> Tuple[Dict[str, OperatorAwareField], List[Dict[str, Any]]]:
        self._collect_and_score_fields()
        self._build_operator_aware_forms()
        return self.operator_fields, self.operator_forms

    def save_outputs(self, output_dir: str | Path) -> None:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        self._save_operator_fields_json(output_path / "operator_aware_fields.json")
        self._save_operator_forms_json(output_path / "operator_aware_forms.json")
        self._save_operator_fields_csv(output_path / "operator_aware_fields.csv")
        self._save_operator_form_summary_csv(output_path / "operator_aware_form_summary.csv")

    # --------------------------------------------------------
    # Field scoring
    # --------------------------------------------------------

    def _collect_and_score_fields(self) -> None:
        for form in self.canonical_payload.get("canonical_forms", []):
            nodes = []
            nodes.extend(form.get("input_tree_nodes", []))
            nodes.extend(form.get("output_tree_nodes", []))

            seen = set()
            for node in nodes:
                canonical_id = node.get("canonical_id")
                if not canonical_id or canonical_id in seen:
                    continue
                seen.add(canonical_id)

                if node.get("canonical_type") != "form_element":
                    continue

                field = self._score_node(node)
                self.operator_fields[canonical_id] = field

    def _score_node(self, node: Dict[str, Any]) -> OperatorAwareField:
        datatype = node.get("datatype")
        datatype_group = self._datatype_group(datatype)
        q = float(node.get("queriability") or 0.0)

        input_scores = self._score_operators(q, datatype_group, self.INPUT_OPERATOR_RULES)
        output_scores = self._score_operators(q, datatype_group, self.OUTPUT_OPERATOR_RULES)

        input_scores = [s for s in input_scores if s.operator_adjusted_queriability >= self.min_input_aq]
        output_scores = [s for s in output_scores if s.operator_adjusted_queriability >= self.min_output_aq]

        if not self.keep_all_operator_scores:
            input_scores = input_scores[:1]
            output_scores = output_scores[:1]

        best_input = input_scores[0] if input_scores else None
        best_output = output_scores[0] if output_scores else None

        if best_input and best_output:
            role = "input_output"
        elif best_input:
            role = "input_only"
        elif best_output:
            role = "output_only"
        else:
            role = "unused"

        return OperatorAwareField(
            canonical_id=node.get("canonical_id"),
            source_node_id=node.get("source_node_id"),
            name=node.get("name", "unnamed"),
            datatype=datatype,
            canonical_type=node.get("canonical_type", "form_element"),
            rm_type=node.get("rm_type", "UNKNOWN"),
            path=node.get("path", ""),
            archetype_node_id=node.get("archetype_node_id"),
            archetype_id=node.get("archetype_id"),
            template_id=node.get("template_id"),
            queriability=q,
            input_operators=input_scores,
            output_operators=output_scores,
            best_input_operator=best_input.operator if best_input else None,
            best_output_operator=best_output.operator if best_output else None,
            best_input_score=best_input.operator_adjusted_queriability if best_input else 0.0,
            best_output_score=best_output.operator_adjusted_queriability if best_output else 0.0,
            field_role=role,
        )

    def _score_operators(
        self,
        queriability: float,
        datatype_group: str,
        rules: Dict[str, List[Tuple[str, str, float, str, str]]],
    ) -> List[OperatorScore]:
        scores = []
        for operator, operator_class, compatibility, control_type, reason in rules.get(datatype_group, rules["unknown"]):
            aq = queriability * compatibility
            scores.append(
                OperatorScore(
                    operator=operator,
                    operator_class=operator_class,
                    compatibility=compatibility,
                    operator_adjusted_queriability=aq,
                    control_type=control_type,
                    reason=reason,
                )
            )
        return sorted(scores, key=lambda x: x.operator_adjusted_queriability, reverse=True)

    def _datatype_group(self, datatype: Optional[str]) -> str:
        if datatype is None:
            return "unknown"
        return self.DATATYPE_GROUPS.get(str(datatype).upper(), "unknown")

    # --------------------------------------------------------
    # Operator-aware canonical forms
    # --------------------------------------------------------

    def _build_operator_aware_forms(self) -> None:
        for form in self.canonical_payload.get("canonical_forms", []):
            input_ids = form.get("input_tree", [])
            output_ids = form.get("output_tree", [])

            operator_input_tree = []
            for fid in input_ids:
                field = self.operator_fields.get(fid)
                if not field or not field.input_operators:
                    continue
                operator_input_tree.append(self._field_input_dict(field))

            operator_output_tree = []
            for fid in output_ids:
                field = self.operator_fields.get(fid)
                if not field or not field.output_operators:
                    continue
                operator_output_tree.append(self._field_output_dict(field))

            operator_input_tree = sorted(operator_input_tree, key=lambda x: x["best_input_score"], reverse=True)
            operator_output_tree = sorted(operator_output_tree, key=lambda x: x["best_output_score"], reverse=True)

            if self.top_k_input_per_form is not None:
                operator_input_tree = operator_input_tree[: self.top_k_input_per_form]
            if self.top_k_output_per_form is not None:
                operator_output_tree = operator_output_tree[: self.top_k_output_per_form]

            operator_relationship_tree = self._operator_aware_rt(form.get("relationship_tree", []))

            form_payload = {
                "operator_aware_form_id": f"oaf_{form.get('canonical_form_id')}",
                "canonical_form_id": form.get("canonical_form_id"),
                "source_tree_id": form.get("source_tree_id"),
                "form_group": form.get("form_group"),
                "root_canonical_id": form.get("root_canonical_id"),
                "operator_input_tree": operator_input_tree,
                "operator_output_tree": operator_output_tree,
                "operator_relationship_tree": operator_relationship_tree,
                "input_field_count": len(operator_input_tree),
                "output_field_count": len(operator_output_tree),
                "relationship_count": len(operator_relationship_tree),
                "operator_form_utility": self._form_utility(operator_input_tree, operator_output_tree),
                "max_depth": form.get("max_depth", 0),
            }
            self.operator_forms.append(form_payload)

    def _field_input_dict(self, field: OperatorAwareField) -> Dict[str, Any]:
        return {
            "canonical_id": field.canonical_id,
            "name": field.name,
            "datatype": field.datatype,
            "queriability": field.queriability,
            "best_input_operator": field.best_input_operator,
            "best_input_score": field.best_input_score,
            "input_operators": [asdict(op) for op in field.input_operators],
            "path": field.path,
            "archetype_node_id": field.archetype_node_id,
            "archetype_id": field.archetype_id,
            "template_id": field.template_id,
        }

    def _field_output_dict(self, field: OperatorAwareField) -> Dict[str, Any]:
        return {
            "canonical_id": field.canonical_id,
            "name": field.name,
            "datatype": field.datatype,
            "queriability": field.queriability,
            "best_output_operator": field.best_output_operator,
            "best_output_score": field.best_output_score,
            "output_operators": [asdict(op) for op in field.output_operators],
            "path": field.path,
            "archetype_node_id": field.archetype_node_id,
            "archetype_id": field.archetype_id,
            "template_id": field.template_id,
        }

    def _operator_aware_rt(self, relationship_tree: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = []
        for rel in relationship_tree:
            source_type = rel.get("source_schema_edge_type")
            weight = float(rel.get("weight") or rel.get("structural_connectivity") or 0.0)
            if source_type == "containment":
                role = "containment_join"
                execution_priority = 1.0
            elif source_type == "cooccurrence":
                role = "cooccurrence_association"
                execution_priority = 0.65
            else:
                role = "structural_association"
                execution_priority = 0.5

            item = dict(rel)
            item["relationship_role"] = role
            item["relationship_priority"] = weight * execution_priority
            result.append(item)
        return sorted(result, key=lambda x: x.get("relationship_priority", 0.0), reverse=True)

    def _form_utility(self, input_tree: List[Dict[str, Any]], output_tree: List[Dict[str, Any]]) -> float:
        input_score = sum(float(x.get("best_input_score") or 0.0) for x in input_tree)
        output_score = sum(float(x.get("best_output_score") or 0.0) for x in output_tree)
        return input_score + output_score

    # --------------------------------------------------------
    # Export helpers
    # --------------------------------------------------------

    def _save_operator_fields_json(self, path: Path) -> None:
        payload = {
            "metadata": {
                "field_count": len(self.operator_fields),
                "min_input_aq": self.min_input_aq,
                "min_output_aq": self.min_output_aq,
                "top_k_input_per_form": self.top_k_input_per_form,
                "top_k_output_per_form": self.top_k_output_per_form,
            },
            "operator_aware_fields": [self._field_to_dict(f) for f in self.operator_fields.values()],
        }
        self._write_json(path, payload)

    def _save_operator_forms_json(self, path: Path) -> None:
        payload = {
            "metadata": {
                "operator_aware_form_count": len(self.operator_forms),
                "min_input_aq": self.min_input_aq,
                "min_output_aq": self.min_output_aq,
            },
            "operator_aware_forms": self.operator_forms,
        }
        self._write_json(path, payload)

    def _save_operator_fields_csv(self, path: Path) -> None:
        columns = [
            "canonical_id", "name", "datatype", "queriability", "field_role",
            "best_input_operator", "best_input_score", "best_output_operator", "best_output_score",
            "input_operator_count", "output_operator_count", "path"
        ]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            for field in self.operator_fields.values():
                writer.writerow({
                    "canonical_id": field.canonical_id,
                    "name": field.name,
                    "datatype": field.datatype,
                    "queriability": field.queriability,
                    "field_role": field.field_role,
                    "best_input_operator": field.best_input_operator,
                    "best_input_score": field.best_input_score,
                    "best_output_operator": field.best_output_operator,
                    "best_output_score": field.best_output_score,
                    "input_operator_count": len(field.input_operators),
                    "output_operator_count": len(field.output_operators),
                    "path": field.path,
                })

    def _save_operator_form_summary_csv(self, path: Path) -> None:
        columns = [
            "operator_aware_form_id", "canonical_form_id", "form_group",
            "input_field_count", "output_field_count", "relationship_count",
            "operator_form_utility", "max_depth"
        ]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            for form in self.operator_forms:
                writer.writerow({
                    "operator_aware_form_id": form["operator_aware_form_id"],
                    "canonical_form_id": form["canonical_form_id"],
                    "form_group": form["form_group"],
                    "input_field_count": form["input_field_count"],
                    "output_field_count": form["output_field_count"],
                    "relationship_count": form["relationship_count"],
                    "operator_form_utility": form["operator_form_utility"],
                    "max_depth": form["max_depth"],
                })

    def _field_to_dict(self, field: OperatorAwareField) -> Dict[str, Any]:
        item = asdict(field)
        item["input_operators"] = [asdict(x) for x in field.input_operators]
        item["output_operators"] = [asdict(x) for x in field.output_operators]
        return item

    def _write_json(self, path: Path, payload: Dict[str, Any]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)


# ============================================================
# CLI
# ============================================================

def run_operator_aware_selector(
    canonical_forms_json: str | Path,
    output_dir: str | Path,
    min_input_aq: float = 0.0,
    min_output_aq: float = 0.0,
    top_k_input_per_form: Optional[int] = None,
    top_k_output_per_form: Optional[int] = None,
    best_operator_only: bool = False,
) -> AQFOperatorAwareFieldSelector:
    selector = AQFOperatorAwareFieldSelector(
        min_input_aq=min_input_aq,
        min_output_aq=min_output_aq,
        top_k_input_per_form=top_k_input_per_form,
        top_k_output_per_form=top_k_output_per_form,
        keep_all_operator_scores=not best_operator_only,
    )
    selector.load_canonical_forms(canonical_forms_json)
    selector.generate()
    selector.save_outputs(output_dir)

    print("Operator-aware field selection complete.")
    print(f"Input canonical forms: {canonical_forms_json}")
    print(f"Output folder: {output_dir}")
    print(f"Operator-aware fields: {len(selector.operator_fields)}")
    print(f"Operator-aware forms: {len(selector.operator_forms)}")
    return selector


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate operator-aware IT, OT and RT from AQF canonical forms.")
    parser.add_argument("--canonical_forms_json", required=True, help="Path to canonical_forms.json")
    parser.add_argument("--output_dir", required=True, help="Output folder")
    parser.add_argument("--min_input_aq", type=float, default=0.0, help="Minimum operator-adjusted queriability for input fields")
    parser.add_argument("--min_output_aq", type=float, default=0.0, help="Minimum operator-adjusted queriability for output fields")
    parser.add_argument("--top_k_input_per_form", type=int, default=None, help="Keep only top-k input fields per form")
    parser.add_argument("--top_k_output_per_form", type=int, default=None, help="Keep only top-k output fields per form")
    parser.add_argument("--best_operator_only", action="store_true", help="Keep only best operator per input/output field")

    args = parser.parse_args()
    run_operator_aware_selector(
        canonical_forms_json=args.canonical_forms_json,
        output_dir=args.output_dir,
        min_input_aq=args.min_input_aq,
        min_output_aq=args.min_output_aq,
        top_k_input_per_form=args.top_k_input_per_form,
        top_k_output_per_form=args.top_k_output_per_form,
        best_operator_only=args.best_operator_only,
    )


if __name__ == "__main__":
    main()
