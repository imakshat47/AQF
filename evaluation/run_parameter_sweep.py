#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, itertools, json, math, statistics, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aqf_eval.openehr_utils import scan_json_folder, stable_hash
from aqf_eval.canonical import build_canonical_forest
from aqf_eval.queriability import compute_scores
from aqf_eval.form_generation import generate_form
from aqf_eval.query_eval import evaluate_form, useful_field_labels
from aqf_eval.metrics import summarize_coverage, precision_at_k, recall_at_k, form_complexity, canonical_metrics
from aqf_eval.reporting import write_json, write_csv, append_jsonl
from aqf_eval.selection_audit import audit_field_selection

PARSER_VERSION = "orbda_parser_v2_2_parameter_sweep"
BENCHMARK_VERSION = "expert_curated_v1"


def parse_csv_values(s: str, typ=float):
    return [typ(x.strip()) for x in s.split(',') if x.strip() != '']


def load_json(path: Path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_benchmarks(paths, include_cross=False):
    qs = []
    for p in paths:
        p = Path(p)
        if not include_cross and 'cross' in p.name.lower():
            continue
        if p.exists():
            qs.extend(load_json(p))
    return qs


def fingerprint_dir(data_dir: Path):
    meta = []
    for p in sorted(data_dir.rglob('*.json')):
        if '.cache' in p.parts or 'results' in p.parts:
            continue
        try:
            st = p.stat()
            meta.append((str(p.relative_to(data_dir)), st.st_size, int(st.st_mtime)))
        except Exception:
            pass
    return stable_hash({'parser_version': 'orbda_parser_v2_correctness', 'files': meta})


def ensure_forest_cache(data_dir: Path, cache_dir: Path, use_cache: bool):
    cache_dir.mkdir(parents=True, exist_ok=True)
    fp = fingerprint_dir(data_dir)
    forest_path = cache_dir / 'canonical_forest.json'
    meta_path = cache_dir / 'dataset_fingerprint.json'
    if use_cache and forest_path.exists() and meta_path.exists():
        try:
            meta = load_json(meta_path)
            if meta.get('fingerprint') == fp:
                print(f"[CACHE] Using canonical forest: {forest_path}")
                return load_json(forest_path), True
        except Exception:
            pass
    print('[CACHE] Rebuilding canonical forest...')
    t0 = time.perf_counter()
    record_units = scan_json_folder(data_dir)
    forest = build_canonical_forest(record_units)
    write_json(forest, forest_path)
    write_json({'fingerprint': fp, 'parser_version': PARSER_VERSION, 'data_dir': str(data_dir)}, meta_path)
    print(f"[CACHE] Canonical forest built in {time.perf_counter()-t0:.2f}s | fields={sum(len(t.get('fields', [])) for t in forest.get('trees', {}).values())}")
    return forest, False


def score_cache_key(alpha, beta, lamb):
    return f"scores_a{alpha:.6g}_b{beta:.6g}_l{lamb:.6g}.json".replace('.', 'p')


def ensure_score_cache(forest, cache_dir: Path, alpha: float, beta: float, lamb: float, use_cache: bool):
    scores_dir = cache_dir / 'scores'
    scores_dir.mkdir(parents=True, exist_ok=True)
    score_path = scores_dir / score_cache_key(alpha, beta, lamb)
    if use_cache and score_path.exists():
        print(f"[CACHE] Using scores alpha={alpha} beta={beta} lambda={lamb}: {score_path.name}")
        return load_json(score_path), True
    scores = compute_scores(forest, alpha=alpha, beta=beta, lamb=lamb)
    write_json(scores, score_path)
    return scores, False


def dataset_summary(forest):
    fields = [f for t in forest.get('trees', {}).values() for f in t.get('fields', [])]
    return [{
        'composition_families': len(forest.get('trees', {})),
        'canonical_trees': len(forest.get('trees', {})),
        'form_groups': len({(f.get('record_family'), f.get('form_group')) for f in fields}),
        'nested_subgroups': len({(f.get('record_family'), f.get('form_group'), f.get('nested_subgroup')) for f in fields}),
        'leaf_elements': len(fields),
        'null_flavour_fields': sum(1 for f in fields if f.get('has_null_flavour')),
        'coded_fields': sum(1 for f in fields if f.get('kind') == 'coded'),
        'temporal_fields': sum(1 for f in fields if f.get('kind') == 'temporal'),
        'numeric_fields': sum(1 for f in fields if f.get('kind') == 'numeric'),
    }]


def run_one_combo(forest, scores, queries, useful, args, combo, combo_dir: Path):
    kappa, theta, alpha, beta, lamb = combo
    combo_dir.mkdir(parents=True, exist_ok=True)
    methods = [
        ('aqf_full', True, theta),
        ('flattened_topk', True, theta),
        ('frequency_only', True, theta),
        ('no_pruning', True, 0.0),
        ('aqf_topk_no_threshold', True, 0.0),
        ('no_operator_awareness', False, theta),
    ]
    forms = []
    for method, op_aware, method_theta in methods:
        actual = 'aqf_full' if method == 'no_operator_awareness' else method
        form = generate_form(forest, scores, method=actual, kappa=kappa, theta=method_theta, operator_aware=op_aware, seed=args.seed)
        form['method'] = method
        forms.append(form)
    for i in range(args.random_trials):
        forms.append(generate_form(forest, scores, method=f'random_topk_{i+1}', kappa=kappa, theta=theta, operator_aware=True, seed=args.seed+i))

    coverage_detail, ranking_rows, complexity_rows, canonical_rows, audits = [], [], [], [], []
    gen_dir = combo_dir / 'generated_forms'
    for form in forms:
        rows = evaluate_form(form, queries)
        coverage_detail.extend(rows)
        for r in rows:
            for a in r.get('match_audit', []):
                audits.append({'method': form.get('method'), 'query_id': r.get('query_id'), **a})
        ranking_rows.append({'method': form.get('method'), 'precision_at_10': precision_at_k(form, useful, 10), 'precision_at_20': precision_at_k(form, useful, 20), 'recall_at_20': recall_at_k(form, useful, 20)})
        complexity_rows.append(form_complexity(form))
        canonical_rows.append(canonical_metrics(form))
        write_json(form, gen_dir / form.get('method') / 'forms.json')

    coverage_summary = summarize_coverage(coverage_detail)
    write_json({'kappa': kappa, 'theta': theta, 'alpha': alpha, 'beta': beta, 'lambda': lamb}, combo_dir / 'params.json')
    write_csv(coverage_detail, combo_dir / 'benchmark_coverage_detail.csv')
    write_csv(coverage_summary, combo_dir / 'benchmark_coverage_summary.csv')
    write_csv(ranking_rows, combo_dir / 'queriability_ranking.csv')
    write_csv(complexity_rows, combo_dir / 'form_complexity.csv')
    write_csv(canonical_rows, combo_dir / 'canonical_metrics.csv')
    write_csv(audit_field_selection(forest, scores, forms, queries), combo_dir / 'field_selection_audit.csv')
    append_jsonl(audits, combo_dir / 'field_match_audit.jsonl')

    # Compact run row per method for global comparison.
    rows = []
    complexity_by = {r['method']: r for r in complexity_rows}
    ranking_by = {r['method']: r for r in ranking_rows}
    for r in coverage_summary:
        if r.get('workload') == 'ALL' and r.get('difficulty') == 'ALL':
            method = r['method']
            c = complexity_by.get(method, {})
            qr = ranking_by.get(method, {})
            rows.append({
                'combo_id': combo_dir.name,
                'kappa': kappa,
                'theta': theta,
                'alpha': alpha,
                'beta': beta,
                'lambda': lamb,
                'method': method,
                'query_count': r['query_count'],
                'strict_coverage': r['strict_coverage'],
                'partial_coverage': r['partial_coverage'],
                'field_count': c.get('field_count'),
                'group_count': c.get('group_count'),
                'subgroup_count': c.get('subgroup_count'),
                'operator_count': c.get('operator_count'),
                'complexity_score': c.get('complexity_score'),
                'precision_at_10': qr.get('precision_at_10'),
                'precision_at_20': qr.get('precision_at_20'),
                'recall_at_20': qr.get('recall_at_20'),
            })
    return rows


def fmt_pct(x):
    return f"{100*x:6.2f}%" if x is not None and not math.isnan(x) else '   n/a '


def print_combo_terminal(combo, rows):
    kappa, theta, alpha, beta, lamb = combo
    print('\n' + '='*110)
    print(f"COMBO kappa={kappa} theta={theta} alpha={alpha} beta={beta} lambda={lamb}")
    print('-'*110)
    print(f"{'method':26s} {'strict':>9s} {'partial':>9s} {'fields':>7s} {'operators':>9s} {'complexity':>10s}")
    print('-'*110)
    for r in sorted(rows, key=lambda x: (x['method'].startswith('random'), x['method'])):
        if r['method'].startswith('random') and r['method'] != 'random_topk_1':
            continue
        label = r['method'] if not r['method'].startswith('random') else 'random_topk_* sample'
        print(f"{label:26s} {fmt_pct(r['strict_coverage']):>9s} {fmt_pct(r['partial_coverage']):>9s} {str(r.get('field_count')):>7s} {str(r.get('operator_count')):>9s} {str(round(r.get('complexity_score', 0),2)):>10s}")
    random_rows = [r for r in rows if r['method'].startswith('random')]
    if random_rows:
        strict = [r['strict_coverage'] for r in random_rows]
        partial = [r['partial_coverage'] for r in random_rows]
        print('-'*110)
        print(f"random_topk mean           {fmt_pct(statistics.mean(strict)):>9s} {fmt_pct(statistics.mean(partial)):>9s}")
        print(f"random_topk best           {fmt_pct(max(strict)):>9s} {fmt_pct(max(partial)):>9s}")
        print(f"random_topk worst          {fmt_pct(min(strict)):>9s} {fmt_pct(min(partial)):>9s}")


def summarize_global(all_rows, out_dir: Path):
    import pandas as pd
    df = pd.DataFrame(all_rows)
    write_csv(all_rows, out_dir / 'sweep_all_results.csv')

    main = df[~df['method'].str.startswith('random')].copy()
    random = df[df['method'].str.startswith('random')].copy()

    best_rows, worst_rows, avg_rows = [], [], []
    for method, g in main.groupby('method'):
        best = g.sort_values(['strict_coverage', 'partial_coverage', 'complexity_score'], ascending=[False, False, True]).iloc[0].to_dict()
        worst = g.sort_values(['strict_coverage', 'partial_coverage', 'complexity_score'], ascending=[True, True, False]).iloc[0].to_dict()
        avg = {'method': method, 'combo_count': len(g)}
        for col in ['strict_coverage', 'partial_coverage', 'field_count', 'operator_count', 'complexity_score', 'precision_at_10', 'precision_at_20', 'recall_at_20']:
            avg[f'avg_{col}'] = float(g[col].mean())
            avg[f'std_{col}'] = float(g[col].std(ddof=0)) if len(g) > 1 else 0.0
        best_rows.append(best); worst_rows.append(worst); avg_rows.append(avg)

    if len(random):
        by_combo = random.groupby(['combo_id', 'kappa', 'theta', 'alpha', 'beta', 'lambda']).agg(
            random_mean_strict=('strict_coverage','mean'), random_best_strict=('strict_coverage','max'), random_worst_strict=('strict_coverage','min'),
            random_mean_partial=('partial_coverage','mean'), random_best_partial=('partial_coverage','max'), random_worst_partial=('partial_coverage','min')
        ).reset_index()
        write_csv(by_combo.to_dict('records'), out_dir / 'sweep_random_summary_by_combo.csv')
    else:
        by_combo = None

    write_csv(best_rows, out_dir / 'sweep_best_by_method.csv')
    write_csv(worst_rows, out_dir / 'sweep_worst_by_method.csv')
    write_csv(avg_rows, out_dir / 'sweep_average_by_method.csv')

    print('\n' + '#' * 110)
    print('GLOBAL SWEEP SUMMARY — BEST / WORST / AVERAGE')
    print('#' * 110)
    print('\nBEST BY METHOD')
    print(main.sort_values(['method', 'strict_coverage', 'partial_coverage', 'complexity_score'], ascending=[True, False, False, True])
          .groupby('method').head(1)[['method','kappa','theta','alpha','beta','lambda','strict_coverage','partial_coverage','field_count','operator_count','complexity_score']]
          .to_string(index=False))
    print('\nAVERAGE BY METHOD')
    avg_df = pd.DataFrame(avg_rows)
    print(avg_df[['method','combo_count','avg_strict_coverage','avg_partial_coverage','avg_field_count','avg_operator_count','avg_complexity_score']].to_string(index=False))
    print('\nWORST BY METHOD')
    print(main.sort_values(['method', 'strict_coverage', 'partial_coverage', 'complexity_score'], ascending=[True, True, True, False])
          .groupby('method').head(1)[['method','kappa','theta','alpha','beta','lambda','strict_coverage','partial_coverage','field_count','operator_count','complexity_score']]
          .to_string(index=False))


def main():
    p = argparse.ArgumentParser(description='AQF parameter/matrix sweep with per-combination terminal output and cached canonical artifacts.')
    p.add_argument('--data-dir', required=True)
    p.add_argument('--out-dir', default='results/aqf_sweep_v2_2')
    p.add_argument('--cache-dir', default=None)
    p.add_argument('--use-cache', action='store_true')
    p.add_argument('--kappas', default='20,25,27,30,32,34,35,36,39,42,45,53')
    p.add_argument('--thetas', default='0.00,0.05,0.10,0.15,0.20')
    p.add_argument('--alphas', default='0.70')
    p.add_argument('--betas', default='0.30')
    p.add_argument('--lambdas', default='0.25')
    p.add_argument('--benchmarks', nargs='+', default=[str(ROOT/'evaluation'/'benchmarks'/'benchmark_queries_hcpa.json'), str(ROOT/'evaluation'/'benchmarks'/'benchmark_queries_demographic.json'), str(ROOT/'evaluation'/'benchmarks'/'benchmark_queries_cross_composition.json')])
    p.add_argument('--include-cross', action='store_true')
    p.add_argument('--random-trials', type=int, default=30)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--max-combos', type=int, default=0, help='Optional safety cap; 0 means no cap.')
    args = p.parse_args()

    data_dir = Path(args.data_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = Path(args.cache_dir) if args.cache_dir else out_dir/'.cache'

    forest, forest_cache_used = ensure_forest_cache(data_dir, cache_dir, args.use_cache)
    queries = load_benchmarks(args.benchmarks, include_cross=args.include_cross)
    useful = useful_field_labels(queries)
    write_csv(dataset_summary(forest), out_dir/'dataset_summary.csv')
    write_json({'parser_version': PARSER_VERSION, 'benchmark_version': BENCHMARK_VERSION, 'data_dir': str(data_dir), 'query_count': len(queries)}, out_dir/'sweep_metadata.json')

    kappas = parse_csv_values(args.kappas, int)
    thetas = parse_csv_values(args.thetas, float)
    alphas = parse_csv_values(args.alphas, float)
    betas = parse_csv_values(args.betas, float)
    lambdas = parse_csv_values(args.lambdas, float)
    combos = list(itertools.product(kappas, thetas, alphas, betas, lambdas))
    if args.max_combos and args.max_combos > 0:
        combos = combos[:args.max_combos]

    print(f"[SWEEP] combinations={len(combos)} | queries={len(queries)} | random_trials={args.random_trials}")
    print(f"[SWEEP] output={out_dir}")
    print(f"[SWEEP] cache={cache_dir} | forest_cache_used={forest_cache_used}")

    all_rows = []
    score_cache = {}
    t_start = time.perf_counter()
    for idx, combo in enumerate(combos, start=1):
        kappa, theta, alpha, beta, lamb = combo
        score_key = (alpha, beta, lamb)
        if score_key not in score_cache:
            scores, score_cache_used = ensure_score_cache(forest, cache_dir, alpha, beta, lamb, args.use_cache)
            score_cache[score_key] = scores
        else:
            scores = score_cache[score_key]
            score_cache_used = True
        combo_id = f"combo_{idx:04d}_k{kappa}_t{theta:g}_a{alpha:g}_b{beta:g}_l{lamb:g}".replace('.', 'p')
        combo_dir = out_dir/'combos'/combo_id
        rows = run_one_combo(forest, scores, queries, useful, args, combo, combo_dir)
        all_rows.extend(rows)
        print_combo_terminal(combo, rows)
        print(f"[SWEEP] Completed {idx}/{len(combos)} | score_cache_used={score_cache_used} | elapsed={time.perf_counter()-t_start:.1f}s")

    summarize_global(all_rows, out_dir)
    print(f"\n[SWEEP] Done. Results written to: {out_dir}")


if __name__ == '__main__':
    main()
