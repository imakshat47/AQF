#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

RENAME_METHOD = {
    'aqf_full': 'AQF Proposed',
    'flattened_topk': 'Context-Flattened',
    'no_operator_awareness': 'Operator-Unaware',
    'no_pruning': 'Unpruned Schema Graph',
    'random_topk_mean': 'Random Candidate Mean',
}

EXCLUDE_DEFAULT = {'aqf_topk_no_threshold', 'frequency_only'}


def read_params(combo_dir: Path):
    p = combo_dir / 'sensitivity_params.tsv'
    if not p.exists():
        # Try parse from run_metadata.json if available later.
        return {}
    df = pd.read_csv(p, sep='\t')
    return df.iloc[0].to_dict()


def random_aggregate(df: pd.DataFrame) -> pd.DataFrame:
    rand = df[df['method'].str.startswith('random')].copy()
    if rand.empty:
        return pd.DataFrame()
    numeric_cols = rand.select_dtypes(include=[np.number]).columns.tolist()
    row = {'method': 'random_topk_mean'}
    for c in numeric_cols:
        row[c] = rand[c].mean()
        row[c + '_std'] = rand[c].std()
    return pd.DataFrame([row])


def collect_results(root: Path, exclude=EXCLUDE_DEFAULT) -> pd.DataFrame:
    rows = []
    for combo in sorted((root / 'combos').glob('combo_*')):
        fm = combo / 'final_aqf_metrics.csv'
        if not fm.exists():
            fm = combo / 'final_metrics_enhanced.csv'
        if not fm.exists():
            continue
        df = pd.read_csv(fm)
        params = read_params(combo)
        # Add random aggregate and drop individual random rows from final summary.
        rag = random_aggregate(df)
        df = df[~df['method'].str.startswith('random')]
        if not rag.empty:
            df = pd.concat([df, rag], ignore_index=True, sort=False)
        df = df[~df['method'].isin(exclude)].copy()
        for k, v in params.items():
            df[k] = v
        df['combo_id'] = combo.name
        rows.append(df)
    if not rows:
        return pd.DataFrame()
    all_df = pd.concat(rows, ignore_index=True, sort=False)
    # Normalize parameter dtypes.
    for c in ['sweep_value','complexity_budget','theta','lambda_sc','mu','eta']:
        if c in all_df.columns:
            all_df[c] = pd.to_numeric(all_df[c], errors='coerce')
    # Recompute efficiency if absent.
    if 'field_efficiency' not in all_df.columns and {'strict_coverage','field_count'}.issubset(all_df.columns):
        all_df['field_efficiency'] = all_df['strict_coverage'] / all_df['field_count'].replace(0, np.nan)
    if 'operator_efficiency' not in all_df.columns and {'strict_coverage','operator_count'}.issubset(all_df.columns):
        all_df['operator_efficiency'] = all_df['strict_coverage'] / all_df['operator_count'].replace(0, np.nan)
    if 'complexity_efficiency' not in all_df.columns and {'strict_coverage','final_complexity'}.issubset(all_df.columns):
        all_df['complexity_efficiency'] = all_df['strict_coverage'] / all_df['final_complexity'].replace(0, np.nan)
    return all_df


def best_by_objective(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    aqf = df[df['method'] == 'aqf_full'].copy()
    if aqf.empty:
        return pd.DataFrame()
    objectives = {
        'max_exact_support': ['strict_coverage', False, 'final_complexity', True],
        'max_constraint_support': ['partial_coverage', False, 'final_complexity', True],
        'max_field_efficiency': ['field_efficiency', False, 'strict_coverage', False],
        'max_operator_efficiency': ['operator_efficiency', False, 'strict_coverage', False],
        'min_complexity_at_90pct_support': ['final_complexity', True, 'strict_coverage', False],
    }
    for name, spec in objectives.items():
        sub = aqf.copy()
        if name == 'min_complexity_at_90pct_support':
            sub = sub[sub['strict_coverage'] >= 0.90]
            if sub.empty:
                continue
        primary, asc1, secondary, asc2 = spec
        sub = sub.sort_values([primary, secondary], ascending=[asc1, asc2])
        r = sub.iloc[0].to_dict()
        r['objective'] = name
        rows.append(r)
    return pd.DataFrame(rows)


def one_factor_summary(df: pd.DataFrame) -> pd.DataFrame:
    aqf = df[df['method'] == 'aqf_full'].copy()
    if aqf.empty or 'sweep_axis' not in aqf.columns:
        return pd.DataFrame()
    rows = []
    for axis, g in aqf.groupby('sweep_axis'):
        if axis == 'cartesian':
            continue
        for _, r in g.sort_values('sweep_value').iterrows():
            rows.append({
                'parameter': axis,
                'value': r.get('sweep_value'),
                'exact_query_support': r.get('strict_coverage'),
                'constraint_level_support': r.get('partial_coverage'),
                'bounded_form_complexity': r.get('final_complexity'),
                'exposed_form_elements': r.get('field_count'),
                'exposed_query_operators': r.get('operator_count'),
                'support_per_form_element': r.get('field_efficiency'),
                'support_per_operator': r.get('operator_efficiency'),
                'support_per_complexity_unit': r.get('complexity_efficiency'),
            })
    return pd.DataFrame(rows)


def plot_one_factor(df: pd.DataFrame, out: Path):
    aqf = df[df['method'] == 'aqf_full'].copy()
    if aqf.empty or 'sweep_axis' not in aqf.columns:
        return
    plots = out / 'parameter_sensitivity_plots'
    plots.mkdir(exist_ok=True)
    axes = [x for x in aqf['sweep_axis'].dropna().unique() if x != 'cartesian']
    label_map = {
        'complexity_budget': 'Complexity budget κ',
        'theta': 'Candidate pruning threshold θ',
        'lambda_sc': 'Structural-connectivity balance λ',
        'mu': 'Neighborhood reinforcement μ',
        'eta': 'Depth penalty η',
    }
    for axis in axes:
        g = aqf[aqf['sweep_axis'] == axis].sort_values('sweep_value')
        if g.empty:
            continue
        x = g['sweep_value']
        # Coverage plot
        plt.figure(figsize=(8.5, 5.5))
        plt.plot(x, g['strict_coverage'] * 100, marker='o', label='Exact Query Support')
        if 'partial_coverage' in g.columns:
            plt.plot(x, g['partial_coverage'] * 100, marker='o', label='Constraint-Level Support')
        plt.xlabel(label_map.get(axis, axis))
        plt.ylabel('Support (%)')
        plt.title(f'AQF support sensitivity: {label_map.get(axis, axis)}')
        plt.legend()
        plt.tight_layout()
        plt.savefig(plots / f'support_vs_{axis}.png', dpi=220)
        plt.close()

        # Complexity/efficiency plot
        fig, ax1 = plt.subplots(figsize=(8.5, 5.5))
        ax1.plot(x, g['final_complexity'], marker='o', label='Bounded Form Complexity')
        ax1.set_xlabel(label_map.get(axis, axis))
        ax1.set_ylabel('Bounded Form Complexity')
        ax2 = ax1.twinx()
        ax2.plot(x, g['field_efficiency'], marker='s', linestyle='--', label='Support per Form Element')
        ax2.set_ylabel('Support per Form Element')
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='best')
        plt.title(f'AQF complexity/efficiency sensitivity: {label_map.get(axis, axis)}')
        fig.tight_layout()
        plt.savefig(plots / f'efficiency_vs_{axis}.png', dpi=220)
        plt.close()


def plot_cartesian_heatmaps(df: pd.DataFrame, out: Path):
    aqf = df[(df['method'] == 'aqf_full') & (df.get('sweep_axis') == 'cartesian')].copy()
    if aqf.empty:
        return
    plots = out / 'parameter_sensitivity_plots'
    plots.mkdir(exist_ok=True)
    # For heatmaps, aggregate across other params using max support, then min complexity tie handled by groupby agg.
    pairs = [('theta','complexity_budget'), ('lambda_sc','mu'), ('eta','complexity_budget'), ('theta','mu')]
    for y, x in pairs:
        if not {x, y, 'strict_coverage'}.issubset(aqf.columns):
            continue
        piv = aqf.pivot_table(index=y, columns=x, values='strict_coverage', aggfunc='max') * 100
        if piv.empty:
            continue
        plt.figure(figsize=(9, 6))
        plt.imshow(piv.values, aspect='auto', origin='lower')
        plt.colorbar(label='Exact Query Support (%)')
        plt.xticks(range(len(piv.columns)), [str(c) for c in piv.columns], rotation=45, ha='right')
        plt.yticks(range(len(piv.index)), [str(i) for i in piv.index])
        plt.xlabel(x)
        plt.ylabel(y)
        plt.title(f'AQF parameter heatmap: {y} vs {x}')
        plt.tight_layout()
        plt.savefig(plots / f'heatmap_{y}_vs_{x}.png', dpi=220)
        plt.close()


def write_markdown_report(out: Path, all_df: pd.DataFrame, best: pd.DataFrame, one_factor: pd.DataFrame):
    lines = []
    lines.append('# AQF Parameter Sensitivity Report')
    lines.append('')
    lines.append('This report explains how AQF parameter choices were evaluated across continuous/ranged values.')
    lines.append('')
    lines.append('## Parameters evaluated')
    lines.append('')
    lines.append('- `complexity_budget` / κ: bounded interface complexity budget.')
    lines.append('- `theta` / θ: candidate pruning threshold.')
    lines.append('- `lambda_sc` / λ: balance between containment and co-occurrence structural connectivity.')
    lines.append('- `mu` / μ: neighborhood reinforcement strength.')
    lines.append('- `eta` / η: depth penalty in bounded form complexity.')
    lines.append('')
    if not best.empty:
        lines.append('## Best AQF configurations by objective')
        lines.append('')
        keep = ['objective','strict_coverage','partial_coverage','final_complexity','field_count','operator_count','complexity_budget','theta','lambda_sc','mu','eta']
        keep = [c for c in keep if c in best.columns]
        lines.append(best[keep].to_markdown(index=False))
        lines.append('')
    if not one_factor.empty:
        lines.append('## One-factor-at-a-time sensitivity table')
        lines.append('')
        lines.append(one_factor.head(200).to_markdown(index=False))
        lines.append('')
    (out / 'parameter_sensitivity_report.md').write_text('\n'.join(lines), encoding='utf-8')


def main():
    p = argparse.ArgumentParser(description='Summarize and visualize AQF parameter sensitivity runs.')
    p.add_argument('--sensitivity-dir', required=True, help='Directory created by run_aqf_sensitivity_grid.py')
    p.add_argument('--exclude', default='aqf_topk_no_threshold,frequency_only')
    args = p.parse_args()
    root = Path(args.sensitivity_dir)
    exclude = {x.strip() for x in args.exclude.split(',') if x.strip()}
    df = collect_results(root, exclude=exclude)
    if df.empty:
        raise SystemExit('No sensitivity results found. Expected combos/*/final_aqf_metrics.csv')
    df.to_csv(root / 'aqf_parameter_sensitivity_all_results.csv', index=False)
    best = best_by_objective(df)
    best.to_csv(root / 'aqf_parameter_sensitivity_best_configs.csv', index=False)
    ofs = one_factor_summary(df)
    ofs.to_csv(root / 'aqf_parameter_sensitivity_one_factor_summary.csv', index=False)
    plot_one_factor(df, root)
    plot_cartesian_heatmaps(df, root)
    write_markdown_report(root, df, best, ofs)
    print('[OK] Wrote:')
    print(' - aqf_parameter_sensitivity_all_results.csv')
    print(' - aqf_parameter_sensitivity_best_configs.csv')
    print(' - aqf_parameter_sensitivity_one_factor_summary.csv')
    print(' - parameter_sensitivity_report.md')
    print(' - parameter_sensitivity_plots/*.png')
    if not best.empty:
        print('\nBest configurations:')
        keep = [c for c in ['objective','strict_coverage','partial_coverage','final_complexity','field_count','operator_count','complexity_budget','theta','lambda_sc','mu','eta'] if c in best.columns]
        print(best[keep].to_string(index=False))


if __name__ == '__main__':
    main()
