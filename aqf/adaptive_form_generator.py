#!/usr/bin/env python3
"""
adaptive_form_generator.py

Generate final AQF adaptive query forms from operator-aware canonical forms.

Input:
  output/operator_aware/operator_aware_forms.json

Outputs:
  aqf_forms.json
  aqf_forms_summary.csv
  aqf_form_fields.csv
  html/<form_id>.html
  html/index.html

AQF objective:
  maximize U(F) subject to C(F) <= kappa

where:
  U(F) = sum selected operator-adjusted queriability scores
  C(F) = number_of_fields + eta * max_depth
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class AQFFormField:
    field_id: str
    canonical_id: str
    name: str
    role: str
    datatype: Optional[str]
    operator: str
    operator_class: str
    control_type: str
    score: float
    queriability: float
    path: str
    archetype_node_id: Optional[str]
    archetype_id: Optional[str]
    template_id: Optional[str]
    required: bool = False
    ui_group: Optional[str] = None


@dataclass
class AQFRelationship:
    source: str
    target: str
    edge_type: str
    source_schema_edge_type: str
    relationship_role: str
    relationship_priority: float
    weight: float
    structural_connectivity: float
    containment_connectivity: float
    cooccurrence_connectivity: float


@dataclass
class AQFForm:
    form_id: str
    source_operator_aware_form_id: str
    canonical_form_id: str
    form_group: str
    title: str
    description: str
    filters: List[AQFFormField] = field(default_factory=list)
    outputs: List[AQFFormField] = field(default_factory=list)
    relationships: List[AQFRelationship] = field(default_factory=list)
    utility: float = 0.0
    complexity: float = 0.0
    max_depth: int = 0
    selected_field_count: int = 0
    relationship_count: int = 0


class AQFAdaptiveFormGenerator:
    def __init__(
        self,
        kappa: float = 30.0,
        eta: float = 1.0,
        max_filters: Optional[int] = None,
        max_outputs: Optional[int] = None,
        min_field_score: float = 0.0,
        relationship_top_k: Optional[int] = 50,
    ) -> None:
        self.kappa = kappa
        self.eta = eta
        self.max_filters = max_filters
        self.max_outputs = max_outputs
        self.min_field_score = min_field_score
        self.relationship_top_k = relationship_top_k
        self.payload: Dict[str, Any] = {}
        self.forms: List[AQFForm] = []

    def load_operator_aware_forms(self, operator_aware_forms_json: str | Path) -> None:
        with open(operator_aware_forms_json, 'r', encoding='utf-8') as f:
            self.payload = json.load(f)
        if 'operator_aware_forms' not in self.payload:
            raise ValueError("Input JSON does not contain 'operator_aware_forms'.")

    def generate(self) -> List[AQFForm]:
        self.forms = []
        for form in self.payload.get('operator_aware_forms', []):
            aqf_form = self._generate_single_form(form)
            self.forms.append(aqf_form)
        self.forms = sorted(self.forms, key=lambda f: f.utility, reverse=True)
        return self.forms

    def _generate_single_form(self, source_form: Dict[str, Any]) -> AQFForm:
        max_depth = int(source_form.get('max_depth') or 0)
        remaining_budget = max(0.0, self.kappa - self.eta * max_depth)

        filter_candidates = self._deduplicate_fields(self._build_filter_candidates(source_form))
        output_candidates = self._deduplicate_fields(self._build_output_candidates(source_form))

        if self.max_filters is not None:
            filter_candidates = filter_candidates[: self.max_filters]
        if self.max_outputs is not None:
            output_candidates = output_candidates[: self.max_outputs]

        selected_filters, selected_outputs = self._select_fields_under_budget(
            filter_candidates,
            output_candidates,
            remaining_budget,
        )

        relationships = self._select_relationships(source_form.get('operator_relationship_tree', []))
        utility = sum(f.score for f in selected_filters) + sum(f.score for f in selected_outputs)
        selected_field_count = len(selected_filters) + len(selected_outputs)
        complexity = selected_field_count + self.eta * max_depth

        form_group = source_form.get('form_group') or 'AQF Form'
        form_id = f"aqf_{self._slug(form_group)}_{abs(hash(source_form.get('operator_aware_form_id'))) % 100000}"

        return AQFForm(
            form_id=form_id,
            source_operator_aware_form_id=source_form.get('operator_aware_form_id'),
            canonical_form_id=source_form.get('canonical_form_id'),
            form_group=form_group,
            title=f"AQF Query Form - {form_group}",
            description="Automatically generated adaptive query form using operator-aware field selection and bounded complexity constraints.",
            filters=selected_filters,
            outputs=selected_outputs,
            relationships=relationships,
            utility=utility,
            complexity=complexity,
            max_depth=max_depth,
            selected_field_count=selected_field_count,
            relationship_count=len(relationships),
        )

    def _build_filter_candidates(self, source_form: Dict[str, Any]) -> List[AQFFormField]:
        fields = []
        for item in source_form.get('operator_input_tree', []):
            score = float(item.get('best_input_score') or 0.0)
            if score < self.min_field_score:
                continue
            best_op = item.get('best_input_operator') or 'equals'
            op_detail = self._find_operator(item.get('input_operators', []), best_op)
            fields.append(AQFFormField(
                field_id=f"filter_{self._slug(item.get('name'))}_{abs(hash(item.get('canonical_id'))) % 100000}",
                canonical_id=item.get('canonical_id'),
                name=item.get('name', 'unnamed'),
                role='filter',
                datatype=item.get('datatype'),
                operator=best_op,
                operator_class=(op_detail or {}).get('operator_class', 'filter'),
                control_type=(op_detail or {}).get('control_type', self._default_control(item.get('datatype'))),
                score=score,
                queriability=float(item.get('queriability') or 0.0),
                path=item.get('path', ''),
                archetype_node_id=item.get('archetype_node_id'),
                archetype_id=item.get('archetype_id'),
                template_id=item.get('template_id'),
                ui_group=self._infer_ui_group(item.get('path', '')),
            ))
        return sorted(fields, key=lambda f: f.score, reverse=True)

    def _build_output_candidates(self, source_form: Dict[str, Any]) -> List[AQFFormField]:
        fields = []
        for item in source_form.get('operator_output_tree', []):
            score = float(item.get('best_output_score') or 0.0)
            if score < self.min_field_score:
                continue
            best_op = item.get('best_output_operator') or 'project'
            op_detail = self._find_operator(item.get('output_operators', []), best_op)
            fields.append(AQFFormField(
                field_id=f"output_{self._slug(item.get('name'))}_{abs(hash(item.get('canonical_id'))) % 100000}",
                canonical_id=item.get('canonical_id'),
                name=item.get('name', 'unnamed'),
                role='output',
                datatype=item.get('datatype'),
                operator=best_op,
                operator_class=(op_detail or {}).get('operator_class', 'projection'),
                control_type=(op_detail or {}).get('control_type', 'result_column'),
                score=score,
                queriability=float(item.get('queriability') or 0.0),
                path=item.get('path', ''),
                archetype_node_id=item.get('archetype_node_id'),
                archetype_id=item.get('archetype_id'),
                template_id=item.get('template_id'),
                ui_group=self._infer_ui_group(item.get('path', '')),
            ))
        return sorted(fields, key=lambda f: f.score, reverse=True)

    def _select_fields_under_budget(self, filters: List[AQFFormField], outputs: List[AQFFormField], field_budget: float) -> Tuple[List[AQFFormField], List[AQFFormField]]:
        field_budget_int = int(field_budget)
        if field_budget_int <= 0:
            return [], []
        filter_quota = max(1, int(field_budget_int * 0.60))
        output_quota = max(1, field_budget_int - filter_quota)
        selected_filters = filters[:filter_quota]
        selected_outputs = outputs[:output_quota]

        remaining = sorted(filters[filter_quota:] + outputs[output_quota:], key=lambda f: f.score, reverse=True)
        while len(selected_filters) + len(selected_outputs) < field_budget_int and remaining:
            f = remaining.pop(0)
            if f.role == 'filter':
                selected_filters.append(f)
            else:
                selected_outputs.append(f)
        return selected_filters, selected_outputs

    def _select_relationships(self, relationships: List[Dict[str, Any]]) -> List[AQFRelationship]:
        relationships = sorted(relationships, key=lambda r: float(r.get('relationship_priority') or r.get('weight') or 0.0), reverse=True)
        if self.relationship_top_k is not None:
            relationships = relationships[: self.relationship_top_k]
        return [AQFRelationship(
            source=rel.get('source'),
            target=rel.get('target'),
            edge_type=rel.get('edge_type'),
            source_schema_edge_type=rel.get('source_schema_edge_type'),
            relationship_role=rel.get('relationship_role', 'relationship'),
            relationship_priority=float(rel.get('relationship_priority') or 0.0),
            weight=float(rel.get('weight') or 0.0),
            structural_connectivity=float(rel.get('structural_connectivity') or 0.0),
            containment_connectivity=float(rel.get('containment_connectivity') or 0.0),
            cooccurrence_connectivity=float(rel.get('cooccurrence_connectivity') or 0.0),
        ) for rel in relationships]

    def _deduplicate_fields(self, fields: List[AQFFormField]) -> List[AQFFormField]:
        seen = set(); result = []
        for field in fields:
            if field.canonical_id in seen:
                continue
            seen.add(field.canonical_id); result.append(field)
        return result

    def _find_operator(self, operators: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
        for op in operators:
            if op.get('operator') == name:
                return op
        return operators[0] if operators else None

    def _default_control(self, datatype: Optional[str]) -> str:
        if datatype in {'DV_DATE', 'DV_DATE_TIME', 'DV_TIME'}:
            return 'date_picker'
        if datatype in {'DV_COUNT', 'DV_QUANTITY', 'DV_PROPORTION', 'DV_ORDINAL'}:
            return 'numeric_input'
        if datatype in {'DV_CODED_TEXT', 'DV_BOOLEAN'}:
            return 'dropdown'
        return 'text_input'

    def _infer_ui_group(self, path: str) -> str:
        if not path:
            return 'General'
        parts = [p for p in str(path).split('/') if p]
        raw = parts[-2] if len(parts) >= 2 else (parts[0] if parts else 'General')
        tokens = raw.split('|')
        if len(tokens) >= 2:
            return tokens[1].replace('_', ' ').title()
        return raw.replace('_', ' ').title()

    def save_outputs(self, output_dir: str | Path, generate_html: bool = True) -> None:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        self._save_forms_json(output_path / 'aqf_forms.json')
        self._save_summary_csv(output_path / 'aqf_forms_summary.csv')
        self._save_fields_csv(output_path / 'aqf_form_fields.csv')
        if generate_html:
            html_dir = output_path / 'html'
            html_dir.mkdir(parents=True, exist_ok=True)
            for form in self.forms:
                self._save_form_html(form, html_dir / f'{form.form_id}.html')
            self._save_index_html(html_dir / 'index.html')

    def _save_forms_json(self, path: Path) -> None:
        payload = {'metadata': {'form_count': len(self.forms), 'kappa': self.kappa, 'eta': self.eta, 'max_filters': self.max_filters, 'max_outputs': self.max_outputs, 'min_field_score': self.min_field_score, 'relationship_top_k': self.relationship_top_k}, 'aqf_forms': [asdict(form) for form in self.forms]}
        self._write_json(path, payload)

    def _save_summary_csv(self, path: Path) -> None:
        cols = ['form_id', 'form_group', 'utility', 'complexity', 'max_depth', 'selected_field_count', 'filter_count', 'output_count', 'relationship_count']
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=cols); writer.writeheader()
            for form in self.forms:
                writer.writerow({'form_id': form.form_id, 'form_group': form.form_group, 'utility': form.utility, 'complexity': form.complexity, 'max_depth': form.max_depth, 'selected_field_count': form.selected_field_count, 'filter_count': len(form.filters), 'output_count': len(form.outputs), 'relationship_count': form.relationship_count})

    def _save_fields_csv(self, path: Path) -> None:
        cols = ['form_id', 'form_group', 'field_id', 'canonical_id', 'name', 'role', 'datatype', 'operator', 'operator_class', 'control_type', 'score', 'queriability', 'ui_group', 'path']
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=cols); writer.writeheader()
            for form in self.forms:
                for field in form.filters + form.outputs:
                    writer.writerow({'form_id': form.form_id, 'form_group': form.form_group, 'field_id': field.field_id, 'canonical_id': field.canonical_id, 'name': field.name, 'role': field.role, 'datatype': field.datatype, 'operator': field.operator, 'operator_class': field.operator_class, 'control_type': field.control_type, 'score': field.score, 'queriability': field.queriability, 'ui_group': field.ui_group, 'path': field.path})

    def _save_form_html(self, form: AQFForm, path: Path) -> None:
        filter_sections = ''.join(self._render_group(name, fields, True) for name, fields in self._group_fields(form.filters).items())
        output_sections = ''.join(self._render_group(name, fields, False) for name, fields in self._group_fields(form.outputs).items())
        rel_rows = ''.join(f'<tr><td>{html.escape(r.relationship_role)}</td><td>{r.relationship_priority:.3f}</td><td>{r.weight:.3f}</td><td>{html.escape(str(r.source_schema_edge_type))}</td></tr>' for r in form.relationships[:20])
        html_text = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{html.escape(form.title)}</title>
<style>
body{{font-family:Arial,sans-serif;margin:28px;background:#fafafa;color:#222}}
.header{{background:#fff;border:1px solid #ddd;border-radius:10px;padding:18px;margin-bottom:18px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}
.panel{{background:#fff;border:1px solid #ddd;border-radius:10px;padding:16px}}
.group{{border-top:1px solid #eee;padding-top:12px;margin-top:12px}}
.field{{display:grid;grid-template-columns:180px 1fr 130px;gap:10px;align-items:center;margin:8px 0}}
label{{font-weight:600}}
input,select{{padding:8px;border:1px solid #bbb;border-radius:6px}}
.badge{{display:inline-block;background:#eef;border:1px solid #99c;border-radius:12px;padding:2px 8px;font-size:12px}}
table{{width:100%;border-collapse:collapse}}td,th{{border-bottom:1px solid #eee;padding:6px;text-align:left}}
.meta{{font-size:13px;color:#555}}
</style>
</head>
<body>
<div class="header"><h1>{html.escape(form.title)}</h1><p>{html.escape(form.description)}</p><p class="meta">Utility={form.utility:.3f} | Complexity={form.complexity:.2f} | Fields={form.selected_field_count} | RT={form.relationship_count}</p></div>
<div class="grid"><div class="panel"><h2>Input Tree / Filters</h2>{filter_sections}</div><div class="panel"><h2>Output Tree / Results</h2>{output_sections}</div></div>
<div class="panel" style="margin-top:18px"><h2>Relationship Tree</h2><table><tr><th>Role</th><th>Priority</th><th>Weight</th><th>Source edge</th></tr>{rel_rows}</table></div>
</body></html>"""
        path.write_text(html_text, encoding='utf-8')

    def _save_index_html(self, path: Path) -> None:
        links = ''.join(f'<li><a href="{html.escape(form.form_id)}.html">{html.escape(form.title)}</a> - utility={form.utility:.3f}, complexity={form.complexity:.2f}</li>' for form in self.forms)
        index = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>AQF Generated Forms</title>
<style>body{{font-family:Arial,sans-serif;margin:32px;line-height:1.45}} li{{margin:8px 0}}</style></head>
<body><h1>AQF Generated Forms</h1><ul>{links}</ul></body></html>"""
        path.write_text(index, encoding='utf-8')

    def _render_group(self, name: str, fields: List[AQFFormField], is_filter: bool) -> str:
        rows = []
        for field in fields:
            control = self._html_control(field) if is_filter else self._output_control(field)
            rows.append(f'<div class="field"><label>{html.escape(field.name)}</label>{control}<span class="badge">{html.escape(field.operator)} | {field.score:.3f}</span></div>')
        return f'<div class="group"><h3>{html.escape(name)}</h3>{"".join(rows)}</div>'

    def _html_control(self, field: AQFFormField) -> str:
        fid = html.escape(field.field_id)
        if field.control_type == 'date_picker':
            return f'<input type="date" name="{fid}">'
        if field.control_type == 'date_range_picker':
            return f'<input type="date" name="{fid}_from"> <input type="date" name="{fid}_to">'
        if field.control_type in {'range_slider', 'numeric_input', 'numeric_comparator'}:
            return f'<input type="number" name="{fid}_min" placeholder="min"> <input type="number" name="{fid}_max" placeholder="max">'
        if field.control_type in {'dropdown', 'boolean_toggle'}:
            return f'<select name="{fid}"><option value="">Any</option><option>True/Yes/Selected</option><option>False/No</option></select>'
        if field.control_type == 'multi_select':
            return f'<select name="{fid}" multiple><option>Option 1</option><option>Option 2</option></select>'
        return f'<input type="text" name="{fid}" placeholder="Enter value">'

    def _output_control(self, field: AQFFormField) -> str:
        fid = html.escape(field.field_id)
        checked = 'checked' if field.operator in {'project', 'sort'} else ''
        return f'<input type="checkbox" name="{fid}" {checked}> include as {html.escape(field.operator_class)}'

    def _group_fields(self, fields: List[AQFFormField]) -> Dict[str, List[AQFFormField]]:
        groups: Dict[str, List[AQFFormField]] = {}
        for field in fields:
            groups.setdefault(field.ui_group or 'General', []).append(field)
        return groups

    def _write_json(self, path: Path, payload: Dict[str, Any]) -> None:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def _slug(self, text: Optional[str]) -> str:
        text = str(text or 'form').strip().lower()
        text = re.sub(r'[^a-z0-9]+', '_', text)
        text = re.sub(r'_+', '_', text).strip('_')
        return text or 'form'


def generate_aqf_forms(operator_aware_forms_json: str | Path, output_dir: str | Path, kappa: float = 30.0, eta: float = 1.0, max_filters: Optional[int] = None, max_outputs: Optional[int] = None, min_field_score: float = 0.0, relationship_top_k: Optional[int] = 50, no_html: bool = False) -> AQFAdaptiveFormGenerator:
    generator = AQFAdaptiveFormGenerator(kappa=kappa, eta=eta, max_filters=max_filters, max_outputs=max_outputs, min_field_score=min_field_score, relationship_top_k=relationship_top_k)
    generator.load_operator_aware_forms(operator_aware_forms_json)
    generator.generate()
    generator.save_outputs(output_dir, generate_html=not no_html)
    print('AQF adaptive form generation complete.')
    print(f'Input: {operator_aware_forms_json}')
    print(f'Output: {output_dir}')
    print(f'Forms generated: {len(generator.forms)}')
    for form in generator.forms[:5]:
        print(f' - {form.form_id}: utility={form.utility:.3f}, complexity={form.complexity:.2f}, fields={form.selected_field_count}')
    return generator


def main() -> None:
    parser = argparse.ArgumentParser(description='Generate final AQF adaptive query forms from operator-aware forms.')
    parser.add_argument('--operator_aware_forms_json', required=True, help='Path to operator_aware_forms.json')
    parser.add_argument('--output_dir', required=True, help='Output directory for generated AQF forms')
    parser.add_argument('--kappa', type=float, default=30.0, help='Maximum form complexity C(F)')
    parser.add_argument('--eta', type=float, default=1.0, help='Depth penalty in C(F) = |E_F| + eta * depth')
    parser.add_argument('--max_filters', type=int, default=None, help='Maximum filter fields per form')
    parser.add_argument('--max_outputs', type=int, default=None, help='Maximum output fields per form')
    parser.add_argument('--min_field_score', type=float, default=0.0, help='Minimum operator-adjusted field score')
    parser.add_argument('--relationship_top_k', type=int, default=50, help='Top-k relationships to retain per form')
    parser.add_argument('--no_html', action='store_true', help='Do not generate HTML previews')
    args = parser.parse_args()
    generate_aqf_forms(args.operator_aware_forms_json, args.output_dir, args.kappa, args.eta, args.max_filters, args.max_outputs, args.min_field_score, args.relationship_top_k, args.no_html)


if __name__ == '__main__':
    main()
