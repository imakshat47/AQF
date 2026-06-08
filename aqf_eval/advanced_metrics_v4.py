
from __future__ import annotations

import ast
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Iterable

import pandas as pd

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

GENERIC_GROUPS = {"Flat Fields", "All Fields", "Composition", "Top-level fields", ""}


def read_csv_if_exists(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def parse_jsonish(value: Any, default=None):
    if default is None:
        default = []
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        if isinstance(value, float) and math.isnan(value):
            return default
    except Exception:
        pass
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


def load_forms(results_dir: Path) -> List[Dict[str, Any]]:
    forms = []
    generated = results_dir / 'generated_forms'
    if not generated.exists():
        return forms
    for p in sorted(generated.glob('*/forms.json')):
        try:
            form = json.loads(p.read_text(encoding='utf-8'))
            if not form.get('method'):
                form['method'] = p.parent.name
            forms.append(form)
        except Exception:
            continue
    return forms


def field_depth(field: Dict[str, Any]) -> int:
    path = str(field.get('canonical_path') or '')
    parts = [x.strip() for x in path.split('/') if x.strip()]
    if parts:
        return len(parts)
    subgroup = str(field.get('nested_subgroup') or '')
    return max(1, 1 + len([x for x in subgroup.split('/') if x.strip()]))


def valid_ops_for_field(field: Dict[str, Any]) -> set:
    dv_types = set(field.get('observed_dv_types') or [])
    for key in ['dv_type', 'primary_dv_type']:
        if field.get(key):
            dv_types.add(field.get(key))
    ops = {'is_known', 'is_unknown'}
    if 'DV_CODED_TEXT' in dv_types:
        ops |= {'equals', 'not_equals', 'in', 'contains'}
    if 'DV_TEXT' in dv_types:
        ops |= {'equals', 'contains'}
    if 'DV_BOOLEAN' in dv_types:
        ops |= {'equals'}
    if 'DV_DATE' in dv_types or 'DV_DATE_TIME' in dv_types:
        ops |= {'equals', 'before', 'after', 'between'}
    if 'DV_COUNT' in dv_types or 'DV_QUANTITY' in dv_types or 'DV_PROPORTION' in dv_types:
        ops |= {'equals', '>', '<', 'between'}
    return ops


def form_complexity_metrics(form: Dict[str, Any], eta: float = 1.0) -> Dict[str, Any]:
    fields = form.get('fields', []) or []
    groups = form.get('groups', {}) or {}
    max_depth = max([field_depth(f) for f in fields] or [0])
    op_count = 0
    valid_count = 0
    invalid_count = 0
    weighted_burden = 0.0
    for f in fields:
        valid = valid_ops_for_field(f)
        for op in f.get('operators', []) or []:
            op_count += 1
            weighted_burden += OPERATOR_WEIGHTS.get(str(op), 1.0)
            if op in valid:
                valid_count += 1
            else:
                invalid_count += 1
    context_fields = 0
    lineage_fields = 0
    labels = []
    for f in fields:
        labels.append(str(f.get('label') or '').strip().lower())
        if f.get('canonical_path'):
            lineage_fields += 1
        if (f.get('form_group') not in GENERIC_GROUPS) and (f.get('nested_subgroup') not in GENERIC_GROUPS):
            context_fields += 1
    duplicate_labels = len(labels) - len(set(labels)) if labels else 0
    return {
        'method': form.get('method'),
        'field_count': len(fields),
        'group_count': len(groups) if isinstance(groups, dict) else 0,
        'subgroup_count': sum(len(v or {}) for v in groups.values()) if isinstance(groups, dict) else 0,
        'max_depth': max_depth,
        'eta': eta,
        'final_complexity': len(fields) + eta * max_depth,
        'form_complexity_elements': len(fields),
        'operator_count': op_count,
        'valid_operator_count': valid_count,
        'invalid_or_unwanted_operator_count': invalid_count,
        'weighted_operator_burden': weighted_burden,
        'context_preservation_rate': context_fields / len(fields) if fields else 0.0,
        'lineage_preservation_rate': lineage_fields / len(fields) if fields else 0.0,
        'ambiguous_label_count': duplicate_labels,
        'form_utility': sum(float(f.get('score') or 0.0) for f in fields),
    }


def used_field_labels_from_detail(detail: pd.DataFrame) -> Dict[str, set]:
    used = {}
    if detail.empty or 'method' not in detail.columns:
        return used
    for _, row in detail.iterrows():
        method = row.get('method')
        used.setdefault(method, set())
        audit = parse_jsonish(row.get('match_audit'), default=[])
        for item in audit:
            mf = item.get('matched_field')
            if mf:
                used[method].add(str(mf).strip().lower())
    return used


def compute_redundancy(forms: List[Dict[str, Any]], detail: pd.DataFrame) -> pd.DataFrame:
    used_by_method = used_field_labels_from_detail(detail)
    rows = []
    for form in forms:
        method = form.get('method')
        fields = form.get('fields', []) or []
        used = used_by_method.get(method, set())
        unused = 0
        for f in fields:
            label = str(f.get('label') or '').strip().lower()
            if label not in used:
                unused += 1
        rows.append({
            'method': method,
            'field_count': len(fields),
            'used_field_count': len(fields) - unused,
            'unused_field_count': unused,
            'redundancy_ratio': unused / len(fields) if fields else 0.0,
        })
    return pd.DataFrame(rows)


def coverage_by_category(detail: pd.DataFrame) -> pd.DataFrame:
    if detail.empty:
        return pd.DataFrame()
    def cat(row):
        text = ' '.join([str(row.get('query_id','')), str(row.get('missing_fields','')), str(row.get('match_audit',''))]).lower()
        if any(t in text for t in ['gender','birth date','nationality','race','educational','ethnic']):
            return 'demographic'
        if any(t in text for t in ['diagnosis','problem','staging','topography','histopathological','linphonodes','lymph']):
            return 'diagnosis_oriented'
        if any(t in text for t in ['procedure','therapy','radiotherapy','chemotherapy','transplant','dialysis','ultrasonography','treatment']):
            return 'treatment_procedure'
        if any(t in text for t in ['date','duration','follow','age','before','after','between']):
            return 'temporal'
        return 'general_clinical'
    d = detail.copy()
    d['query_category'] = d.apply(cat, axis=1)
    rows = []
    for (method, category), g in d.groupby(['method','query_category']):
        failures = g.loc[~g['strict_supported'], 'failure_type'].value_counts() if 'failure_type' in g.columns else pd.Series(dtype=int)
        rows.append({
            'method': method,
            'category': category,
            'query_count': len(g),
            'strict_coverage': float(g['strict_supported'].mean()),
            'partial_coverage': float(g['partial_score'].mean()),
            'failure_count': int((~g['strict_supported']).sum()),
            'dominant_failure_reason': failures.index[0] if len(failures) else 'SUPPORTED',
        })
    return pd.DataFrame(rows)


def build_enhanced_metrics(results_dir: Path, eta: float = 1.0) -> Dict[str, pd.DataFrame]:
    forms = load_forms(results_dir)
    complexity = pd.DataFrame([form_complexity_metrics(f, eta=eta) for f in forms])

    summary = read_csv_if_exists(results_dir/'benchmark_coverage_summary.csv')
    detail = read_csv_if_exists(results_dir/'benchmark_coverage_detail.csv')
    if not summary.empty and {'workload','difficulty'}.issubset(summary.columns):
        overall = summary[(summary['workload']=='ALL') & (summary['difficulty']=='ALL')].copy()
    else:
        overall = summary.copy()

    if not complexity.empty and not overall.empty:
        keep = [c for c in ['method','query_count','strict_coverage','partial_coverage'] if c in overall.columns]
        final = complexity.merge(overall[keep], on='method', how='left')
    else:
        final = complexity.copy()

    if 'strict_coverage' in final.columns:
        final['field_efficiency'] = final['strict_coverage'] / final['field_count'].replace(0, pd.NA)
        final['operator_efficiency'] = final['strict_coverage'] / final['operator_count'].replace(0, pd.NA)
        final['weighted_operator_efficiency'] = final['strict_coverage'] / final['weighted_operator_burden'].replace(0, pd.NA)
        final['complexity_efficiency'] = final['strict_coverage'] / final['final_complexity'].replace(0, pd.NA)

    redundancy = compute_redundancy(forms, detail)
    if not redundancy.empty and not final.empty:
        final = final.merge(redundancy[['method','used_field_count','unused_field_count','redundancy_ratio']], on='method', how='left')

    category = coverage_by_category(detail)

    if not final.empty and 'strict_coverage' in final.columns:
        pareto_rows = []
        for _, r in final.iterrows():
            dominated = False
            for _, q in final.iterrows():
                if q['method'] == r['method']:
                    continue
                if (q.get('strict_coverage',0) >= r.get('strict_coverage',0) and q.get('final_complexity',1e9) <= r.get('final_complexity',1e9)) and (q.get('strict_coverage',0) > r.get('strict_coverage',0) or q.get('final_complexity',1e9) < r.get('final_complexity',1e9)):
                    dominated = True
                    break
            x = r.to_dict(); x['pareto_optimal'] = not dominated; pareto_rows.append(x)
        pareto = pd.DataFrame(pareto_rows)
    else:
        pareto = pd.DataFrame()

    # Relative comparison rows against aqf_full
    rel_rows = []
    if not final.empty and 'aqf_full' in set(final['method']):
        aqf = final[final['method']=='aqf_full'].iloc[0]
        for _, b in final.iterrows():
            if b['method'] == 'aqf_full':
                continue
            for metric in ['strict_coverage','partial_coverage','field_count','operator_count','weighted_operator_burden','final_complexity','field_efficiency','operator_efficiency','redundancy_ratio']:
                if metric in final.columns:
                    av = aqf.get(metric); bv = b.get(metric)
                    try:
                        delta = float(av) - float(bv)
                        rel = delta / float(bv) * 100 if float(bv) != 0 else None
                    except Exception:
                        delta = None; rel = None
                    rel_rows.append({'comparison': f"aqf_full_vs_{b['method']}", 'metric': metric, 'aqf_value': av, 'baseline_value': bv, 'absolute_delta': delta, 'relative_delta_percent': rel})
    relative = pd.DataFrame(rel_rows)

    return {
        'final_metrics_enhanced': final,
        'coverage_by_query_category': category,
        'redundancy_metrics': redundancy,
        'pareto_frontier': pareto,
        'relative_efficiency_summary': relative,
    }


def save_outputs(results_dir: Path, metrics: Dict[str, pd.DataFrame]) -> None:
    for name, df in metrics.items():
        df.to_csv(results_dir/f'{name}.csv', index=False)
