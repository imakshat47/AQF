#!/usr/bin/env python3
"""Plot reverse AQF sweep results."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--reverse_sweep_results_csv', required=True)
    ap.add_argument('--output_dir', required=True)
    ap.add_argument('--target_min', type=float, default=0.92)
    ap.add_argument('--target_max', type=float, default=0.94)
    args=ap.parse_args()
    out=Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    df=pd.read_csv(args.reverse_sweep_results_csv).sort_values('iteration')

    plt.figure(figsize=(9,5))
    plt.plot(df['iteration'], df['query_realization_rate'], marker='o')
    plt.axhline(args.target_min, linestyle='--')
    plt.axhline(args.target_max, linestyle='--')
    plt.xlabel('Reverse sweep iteration')
    plt.ylabel('Query realization rate')
    plt.title('Reverse AQF tuning toward compact target band')
    plt.tight_layout(); plt.savefig(out/'reverse_sweep_realization_rate.png',dpi=220); plt.close()

    plt.figure(figsize=(7,5))
    plt.scatter(df['total_selected_fields'], df['query_realization_rate'], s=30)
    plt.axhline(args.target_min, linestyle='--')
    plt.axhline(args.target_max, linestyle='--')
    plt.xlabel('Selected AQF fields')
    plt.ylabel('Query realization rate')
    plt.title('Field budget vs realization')
    plt.tight_layout(); plt.savefig(out/'reverse_fields_vs_realization.png',dpi=220); plt.close()

    plt.figure(figsize=(7,5))
    plt.scatter(df['total_complexity'], df['query_realization_rate'], s=30)
    plt.axhline(args.target_min, linestyle='--')
    plt.axhline(args.target_max, linestyle='--')
    plt.xlabel('Total form complexity')
    plt.ylabel('Query realization rate')
    plt.title('Compactness vs expressivity')
    plt.tight_layout(); plt.savefig(out/'reverse_complexity_vs_realization.png',dpi=220); plt.close()

    if 'avg_operator_support' in df.columns:
        plt.figure(figsize=(7,5))
        plt.scatter(df['avg_operator_support'], df['query_realization_rate'], s=30)
        plt.xlabel('Average operator support')
        plt.ylabel('Query realization rate')
        plt.title('Operator support vs realization')
        plt.tight_layout(); plt.savefig(out/'reverse_operator_support_vs_realization.png',dpi=220); plt.close()

    best=df.iloc[df['compactness_score'].idxmax()].to_dict()
    (out/'reverse_plot_summary.json').write_text(json.dumps({'best':best,'iterations':len(df)},indent=2),encoding='utf-8')
    print('Reverse sweep plots saved to', out)
if __name__=='__main__': main()
