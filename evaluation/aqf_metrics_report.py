#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aqf_eval import advanced_metrics_v4


def pct(x):
    try:
        return f"{float(x)*100:.2f}%"
    except Exception:
        return str(x)


def print_screen_report(metrics: dict):
    final = metrics.get('final_metrics_enhanced', pd.DataFrame())
    category = metrics.get('coverage_by_query_category', pd.DataFrame())
    rel = metrics.get('relative_efficiency_summary', pd.DataFrame())
    pareto = metrics.get('pareto_frontier', pd.DataFrame())

    print('\n' + '='*120)
    print('AQF ADVANCED EVALUATION METRICS')
    print('='*120)

    if not final.empty:
        cols = [c for c in ['method','query_count','strict_coverage','partial_coverage','field_count','operator_count','weighted_operator_burden','final_complexity','field_efficiency','operator_efficiency','complexity_efficiency','redundancy_ratio','context_preservation_rate','pareto_optimal'] if c in final.columns]
        display = final[cols].copy()
        for c in ['strict_coverage','partial_coverage','field_efficiency','operator_efficiency','complexity_efficiency','redundancy_ratio','context_preservation_rate']:
            if c in display.columns:
                display[c] = display[c].apply(lambda x: f"{float(x):.4f}" if pd.notna(x) else '')
        print('\n[1] Method-level metrics')
        print(display.to_string(index=False))

        if 'aqf_full' in set(final['method']):
            aqf = final[final['method']=='aqf_full'].iloc[0]
            print('\n[2] AQF-full headline')
            print(f"Strict coverage       : {pct(aqf.get('strict_coverage'))}")
            print(f"Partial coverage      : {pct(aqf.get('partial_coverage'))}")
            print(f"Field count           : {aqf.get('field_count')}")
            print(f"Operator count        : {aqf.get('operator_count')}")
            print(f"Final complexity      : {aqf.get('final_complexity')}")
            print(f"Field efficiency      : {aqf.get('field_efficiency'):.6f}")
            print(f"Operator efficiency   : {aqf.get('operator_efficiency'):.6f}")
            if 'redundancy_ratio' in aqf:
                print(f"Redundancy ratio      : {pct(aqf.get('redundancy_ratio'))}")

    if not category.empty:
        print('\n[3] Coverage by query category')
        cat = category.copy()
        for c in ['strict_coverage','partial_coverage']:
            cat[c] = cat[c].apply(lambda x: f"{float(x):.4f}")
        print(cat.to_string(index=False))

    if not rel.empty:
        print('\n[4] AQF-full relative comparison against baselines')
        subset = rel[rel['metric'].isin(['strict_coverage','field_count','operator_count','weighted_operator_burden','field_efficiency','operator_efficiency','redundancy_ratio'])].copy()
        print(subset.to_string(index=False))

    if not pareto.empty:
        print('\n[5] Pareto-optimal methods')
        p = pareto[pareto['pareto_optimal'] == True]
        cols = [c for c in ['method','strict_coverage','final_complexity','field_count','operator_count'] if c in p.columns]
        print(p[cols].to_string(index=False))

    print('\nGenerated CSV files:')
    print(' - final_metrics_enhanced.csv')
    print(' - coverage_by_query_category.csv')
    print(' - redundancy_metrics.csv')
    print(' - pareto_frontier.csv')
    print(' - relative_efficiency_summary.csv')
    print('='*120 + '\n')


def make_plots(results_dir: Path, metrics: dict):
    plots = results_dir / 'advanced_metric_plots'
    plots.mkdir(exist_ok=True)
    final = metrics.get('final_metrics_enhanced', pd.DataFrame())
    category = metrics.get('coverage_by_query_category', pd.DataFrame())

    if final.empty:
        return

    # Coverage vs final complexity scatter
    if {'final_complexity','strict_coverage','method'}.issubset(final.columns):
        plt.figure(figsize=(9,6))
        for _, r in final.iterrows():
            plt.scatter(r['final_complexity'], r['strict_coverage']*100)
            plt.annotate(str(r['method']), (r['final_complexity'], r['strict_coverage']*100), fontsize=8)
        plt.xlabel('Final complexity')
        plt.ylabel('Strict coverage (%)')
        plt.title('Coverage vs complexity')
        plt.tight_layout()
        plt.savefig(plots/'coverage_vs_complexity.png', dpi=200)
        plt.close()

    # Field efficiency
    if {'method','field_efficiency'}.issubset(final.columns):
        x = final.sort_values('field_efficiency', ascending=False)
        plt.figure(figsize=(10,5))
        plt.bar(x['method'], x['field_efficiency'])
        plt.xticks(rotation=45, ha='right')
        plt.ylabel('Strict coverage / field count')
        plt.title('Field efficiency')
        plt.tight_layout()
        plt.savefig(plots/'field_efficiency.png', dpi=200)
        plt.close()

    # Operator efficiency
    if {'method','operator_efficiency'}.issubset(final.columns):
        x = final.sort_values('operator_efficiency', ascending=False)
        plt.figure(figsize=(10,5))
        plt.bar(x['method'], x['operator_efficiency'])
        plt.xticks(rotation=45, ha='right')
        plt.ylabel('Strict coverage / operator count')
        plt.title('Operator efficiency')
        plt.tight_layout()
        plt.savefig(plots/'operator_efficiency.png', dpi=200)
        plt.close()

    # Redundancy
    if {'method','redundancy_ratio'}.issubset(final.columns):
        x = final.sort_values('redundancy_ratio')
        plt.figure(figsize=(10,5))
        plt.bar(x['method'], x['redundancy_ratio']*100)
        plt.xticks(rotation=45, ha='right')
        plt.ylabel('Unused selected fields (%)')
        plt.title('Redundancy ratio')
        plt.tight_layout()
        plt.savefig(plots/'redundancy_ratio.png', dpi=200)
        plt.close()

    # Coverage by category
    if not category.empty and {'method','category','strict_coverage'}.issubset(category.columns):
        pivot = category.pivot_table(index='category', columns='method', values='strict_coverage', aggfunc='first') * 100
        pivot.plot(kind='bar', figsize=(12,6))
        plt.ylabel('Strict coverage (%)')
        plt.title('Coverage by query category')
        plt.tight_layout()
        plt.savefig(plots/'coverage_by_query_category.png', dpi=200)
        plt.close()

    print(f"Plots written to: {plots}")


def main():
    parser = argparse.ArgumentParser(description='Compute and show AQF advanced metrics.')
    parser.add_argument('--results-dir', required=True, help='AQF result directory containing benchmark_coverage_summary.csv and generated_forms/')
    parser.add_argument('--eta', type=float, default=1.0)
    parser.add_argument('--no-plots', action='store_true')
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    metrics = advanced_metrics_v4.build_enhanced_metrics(results_dir, eta=args.eta)
    advanced_metrics_v4.save_outputs(results_dir, metrics)
    print_screen_report(metrics)
    if not args.no_plots:
        make_plots(results_dir, metrics)


if __name__ == '__main__':
    main()
