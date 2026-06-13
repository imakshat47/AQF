#!/usr/bin/env python3
"""
coverage_repair_form_generator.py

Workload-aware coverage repair for AQF forms.

Inputs:
  - aqf_forms.json from adaptive_form_generator.py
  - operator_aware_forms.json from operator_aware_field_selector.py
  - benchmark workload JSON
  - optional field_aliases.json

Output:
  - aqf_forms.json and aqf_forms_repaired.json with additional workload-critical fields
  - repair_report.csv
  - unresolved_requirements.csv

Goal:
  Increase benchmark query support by adding missing workload-required fields from the
  operator-aware canonical forms, while respecting a coverage complexity budget.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---- shared utility functions ----

import json, re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

OPERATOR_ALIASES = {
    "equals": {"equals", "multi_select"},
    "multi_select": {"multi_select", "equals"},
    "range": {"range", "greater_than_less_than", "date_range"},
    "date_range": {"date_range", "date_equals", "range"},
    "date_equals": {"date_equals", "date_range"},
    "contains": {"contains", "starts_with", "equals"},
    "project": {"project"},
    "sort": {"sort"},
    "group_by": {"group_by"},
    "aggregate": {"aggregate"},
    "is_present": {"is_present", "equals"},
}

def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    chars = []
    for ch in text:
        chars.append(ch if ch.isalnum() else " ")
    return " ".join("".join(chars).split())

def safe_identifier(text: Any) -> str:
    text = normalize_text(text).replace(" ", "_")
    text = re.sub(r"[^a-zA-Z0-9_]", "_", text)
    return text or "field"

def load_aliases(path: Optional[str | Path]) -> Dict[str, Any]:
    if not path:
        return {"field_aliases": {}, "context_aliases": {}}
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Alias file not found: {path}")
    with open(p, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return {
        "field_aliases": payload.get("field_aliases", {}),
        "context_aliases": payload.get("context_aliases", {}),
    }

def alias_terms(term: str, alias_map: Dict[str, List[str]]) -> Set[str]:
    terms = {term}
    norm = normalize_text(term)
    for key, vals in alias_map.items():
        group = [key] + list(vals or [])
        norm_group = {normalize_text(x) for x in group}
        if norm in norm_group:
            terms.update(group)
    return {normalize_text(t) for t in terms if normalize_text(t)}

def alias_name_match(required: str, candidate: str, alias_map: Dict[str, List[str]]) -> bool:
    candidate_norm = normalize_text(candidate)
    if not candidate_norm:
        return False
    for term in alias_terms(required, alias_map):
        if term == candidate_norm or term in candidate_norm or candidate_norm in term:
            return True
    return False

def operator_match(required_operator: str, candidate_operator: str) -> bool:
    req = normalize_text(required_operator).replace(" ", "_")
    cand = normalize_text(candidate_operator).replace(" ", "_")
    return cand in OPERATOR_ALIASES.get(req, {req})

def infer_ui_group(path: str) -> str:
    if not path:
        return "General"
    parts = [p for p in str(path).split("/") if p]
    raw = parts[-2] if len(parts) >= 2 else (parts[0] if parts else "General")
    tokens = raw.split("|")
    if len(tokens) >= 2:
        return tokens[1].replace("_", " ").title()
    return raw.replace("_", " ").title()

def find_operator_detail(operators: List[Dict[str, Any]], preferred: Optional[str]) -> Dict[str, Any]:
    if preferred:
        for op in operators or []:
            if op.get("operator") == preferred:
                return op
    return operators[0] if operators else {}


class CoverageRepairGenerator:
    def __init__(self, aliases_json: Optional[str | Path] = None, kappa_coverage: float = 40.0, eta: float = 1.0, allow_over_budget: bool = False) -> None:
        aliases = load_aliases(aliases_json)
        self.field_aliases = aliases["field_aliases"]
        self.context_aliases = aliases["context_aliases"]
        self.kappa_coverage = kappa_coverage
        self.eta = eta
        self.allow_over_budget = allow_over_budget
        self.forms_payload: Dict[str, Any] = {}
        self.operator_payload: Dict[str, Any] = {}
        self.workload: List[Dict[str, Any]] = []
        self.forms: List[Dict[str, Any]] = []
        self.operator_forms: List[Dict[str, Any]] = []
        self.repair_report: List[Dict[str, Any]] = []
        self.unresolved: List[Dict[str, Any]] = []

    def load_inputs(self, aqf_forms_json: str | Path, operator_aware_forms_json: str | Path, workload_json: str | Path) -> None:
        with open(aqf_forms_json, "r", encoding="utf-8") as f:
            self.forms_payload = json.load(f)
        self.forms = self.forms_payload.get("aqf_forms", [])
        if not self.forms:
            raise ValueError("No AQF forms found.")
        with open(operator_aware_forms_json, "r", encoding="utf-8") as f:
            self.operator_payload = json.load(f)
        self.operator_forms = self.operator_payload.get("operator_aware_forms", [])
        if not self.operator_forms:
            raise ValueError("No operator-aware forms found.")
        with open(workload_json, "r", encoding="utf-8") as f:
            w = json.load(f)
        self.workload = w if isinstance(w, list) else w.get("queries", [])
        if not self.workload:
            raise ValueError("No workload queries found.")

    def repair(self) -> List[Dict[str, Any]]:
        for query in self.workload:
            form = self.select_best_form_for_query(query)
            self.repair_query_against_form(query, form)
        for form in self.forms:
            self.recompute_form_metrics(form)
        self.forms = sorted(self.forms, key=lambda f: float(f.get("utility") or 0.0), reverse=True)
        return self.forms

    def select_best_form_for_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        scored = []
        for form in self.forms:
            fr, os = self.form_support(query, form)
            scored.append(((fr, os, float(form.get("utility") or 0.0)), form))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    def form_support(self, query: Dict[str, Any], form: Dict[str, Any]) -> Tuple[float, float]:
        fields = self.form_fields(form)
        required = query.get("required_fields", [])
        ops = query.get("required_operators", {})
        matched = 0; op_ok = 0; op_total = 0
        for req in required:
            candidates = [f for f in fields if alias_name_match(req, f.get("name", ""), self.field_aliases)]
            if candidates:
                matched += 1
            req_ops = ops.get(req, [])
            if isinstance(req_ops, str): req_ops = [req_ops]
            op_total += len(req_ops)
            for req_op in req_ops:
                if any(operator_match(req_op, f.get("operator", "")) for f in candidates):
                    op_ok += 1
        return (matched / len(required) if required else 1.0, op_ok / op_total if op_total else 1.0)

    def repair_query_against_form(self, query: Dict[str, Any], form: Dict[str, Any]) -> None:
        required = query.get("required_fields", [])
        required_ops = query.get("required_operators", {})
        for req in required:
            req_ops = required_ops.get(req, [])
            if isinstance(req_ops, str): req_ops = [req_ops]
            if self.field_already_supported(form, req, req_ops):
                continue
            candidate = self.find_repair_candidate(form, req, req_ops)
            if candidate:
                added = self.add_candidate_to_form(form, candidate)
                self.repair_report.append({"query_id": query.get("query_id"), "required_field": req, "selected_form_id": form.get("form_id"), "candidate_name": candidate.get("name"), "candidate_operator": candidate.get("operator"), "added": added, "reason": "added_from_operator_aware" if added else "budget_or_duplicate"})
                if not added:
                    self.unresolved.append({"query_id": query.get("query_id"), "required_field": req, "reason": "candidate_found_but_not_added_budget_or_duplicate", "form_id": form.get("form_id")})
            else:
                self.unresolved.append({"query_id": query.get("query_id"), "required_field": req, "reason": "no_operator_aware_candidate_found", "form_id": form.get("form_id")})

    def field_already_supported(self, form: Dict[str, Any], required_field: str, required_ops: List[str]) -> bool:
        fields = self.form_fields(form)
        candidates = [f for f in fields if alias_name_match(required_field, f.get("name", ""), self.field_aliases)]
        if not candidates:
            return False
        if not required_ops:
            return True
        return any(operator_match(req_op, f.get("operator", "")) for req_op in required_ops for f in candidates)

    def form_fields(self, form: Dict[str, Any]) -> List[Dict[str, Any]]:
        fields = []
        for role in ("filters", "outputs"):
            for f in form.get(role, []):
                item = dict(f)
                item["aqf_role"] = "filter" if role == "filters" else "output"
                fields.append(item)
        return fields

    def operator_form_for_form(self, form: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        cfid = form.get("canonical_form_id")
        for opf in self.operator_forms:
            if opf.get("canonical_form_id") == cfid:
                return opf
        return None

    def find_repair_candidate(self, form: Dict[str, Any], required_field: str, required_ops: List[str]) -> Optional[Dict[str, Any]]:
        # Prefer same canonical form, but fall back to any operator-aware form.
        search_forms = []
        opf = self.operator_form_for_form(form)
        if opf:
            search_forms.append(opf)
        search_forms.extend([x for x in self.operator_forms if x is not opf])
        candidates = []
        for op_form in search_forms:
            for item in op_form.get("operator_input_tree", []):
                if not alias_name_match(required_field, item.get("name", ""), self.field_aliases):
                    continue
                best_op = item.get("best_input_operator")
                if required_ops and not any(operator_match(req_op, best_op or "") for req_op in required_ops):
                    # Try alternate operators from full operator list if available.
                    alt = self.best_compatible_operator(item.get("input_operators", []), required_ops)
                    if not alt:
                        continue
                    candidate = self.operator_input_to_form_field(item, alt)
                else:
                    detail = find_operator_detail(item.get("input_operators", []), best_op)
                    candidate = self.operator_input_to_form_field(item, detail)
                candidates.append(candidate)
        candidates.sort(key=lambda x: float(x.get("score") or 0.0), reverse=True)
        return candidates[0] if candidates else None

    def best_compatible_operator(self, ops: List[Dict[str, Any]], required_ops: List[str]) -> Optional[Dict[str, Any]]:
        compatible = []
        for op in ops or []:
            if any(operator_match(req_op, op.get("operator", "")) for req_op in required_ops):
                compatible.append(op)
        compatible.sort(key=lambda x: float(x.get("operator_adjusted_queriability") or 0.0), reverse=True)
        return compatible[0] if compatible else None

    def operator_input_to_form_field(self, item: Dict[str, Any], op_detail: Dict[str, Any]) -> Dict[str, Any]:
        op_name = op_detail.get("operator") or item.get("best_input_operator") or "equals"
        score = float(op_detail.get("operator_adjusted_queriability") or item.get("best_input_score") or 0.0)
        return {"field_id": f"repair_filter_{safe_identifier(item.get('name'))}_{abs(hash(item.get('canonical_id'))) % 100000}", "canonical_id": item.get("canonical_id"), "name": item.get("name", "unnamed"), "role": "filter", "datatype": item.get("datatype"), "operator": op_name, "operator_class": op_detail.get("operator_class", "filter"), "control_type": op_detail.get("control_type", "generic_input"), "score": score, "queriability": float(item.get("queriability") or 0.0), "path": item.get("path", ""), "archetype_node_id": item.get("archetype_node_id"), "archetype_id": item.get("archetype_id"), "template_id": item.get("template_id"), "required": False, "ui_group": infer_ui_group(item.get("path", "")), "repair_added": True}

    def add_candidate_to_form(self, form: Dict[str, Any], candidate: Dict[str, Any]) -> bool:
        for f in form.get("filters", []):
            if f.get("canonical_id") == candidate.get("canonical_id") and f.get("operator") == candidate.get("operator"):
                return False
        current_fields = len(form.get("filters", [])) + len(form.get("outputs", []))
        max_depth = int(form.get("max_depth") or 0)
        new_complexity = current_fields + 1 + self.eta * max_depth
        if new_complexity > self.kappa_coverage and not self.allow_over_budget:
            return False
        form.setdefault("filters", []).append(candidate)
        form["selected_field_count"] = current_fields + 1
        form["complexity"] = new_complexity
        form["utility"] = float(form.get("utility") or 0.0) + float(candidate.get("score") or 0.0)
        form["coverage_repaired"] = True
        return True

    def recompute_form_metrics(self, form: Dict[str, Any]) -> None:
        fields = form.get("filters", []) + form.get("outputs", [])
        form["selected_field_count"] = len(fields)
        form["utility"] = sum(float(f.get("score") or 0.0) for f in fields)
        form["complexity"] = len(fields) + self.eta * int(form.get("max_depth") or 0)

    def save_outputs(self, output_dir: str | Path) -> None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        payload = dict(self.forms_payload)
        payload["metadata"] = dict(payload.get("metadata", {}))
        payload["metadata"].update({"coverage_repaired": True, "kappa_coverage": self.kappa_coverage, "eta": self.eta, "allow_over_budget": self.allow_over_budget, "repair_additions": sum(1 for r in self.repair_report if r.get("added"))})
        payload["aqf_forms"] = self.forms
        (out / "aqf_forms.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        (out / "aqf_forms_repaired.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        self.save_csv(out / "repair_report.csv", self.repair_report)
        self.save_csv(out / "unresolved_requirements.csv", self.unresolved)
        self.save_summary(out / "coverage_repair_summary.json")

    def save_csv(self, path: Path, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            path.write_text("", encoding="utf-8")
            return
        cols = sorted({k for row in rows for k in row.keys()})
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=cols)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def save_summary(self, path: Path) -> None:
        summary = {"forms": len(self.forms), "repair_attempts": len(self.repair_report), "repair_additions": sum(1 for r in self.repair_report if r.get("added")), "unresolved_requirements": len(self.unresolved), "kappa_coverage": self.kappa_coverage, "allow_over_budget": self.allow_over_budget}
        path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Workload-aware coverage repair for AQF forms.")
    parser.add_argument("--aqf_forms_json", required=True)
    parser.add_argument("--operator_aware_forms_json", required=True)
    parser.add_argument("--workload_json", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--aliases_json", default=None)
    parser.add_argument("--kappa_coverage", type=float, default=40.0)
    parser.add_argument("--eta", type=float, default=1.0)
    parser.add_argument("--allow_over_budget", action="store_true")
    args = parser.parse_args()
    gen = CoverageRepairGenerator(args.aliases_json, args.kappa_coverage, args.eta, args.allow_over_budget)
    gen.load_inputs(args.aqf_forms_json, args.operator_aware_forms_json, args.workload_json)
    gen.repair()
    gen.save_outputs(args.output_dir)
    print("Coverage repair complete.")
    print(f"Repair additions: {sum(1 for r in gen.repair_report if r.get('added'))}")
    print(f"Unresolved requirements: {len(gen.unresolved)}")
    print(f"Output: {args.output_dir}")

if __name__ == "__main__":
    main()
