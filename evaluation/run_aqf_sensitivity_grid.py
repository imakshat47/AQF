#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_values(s: str, typ=float):
    return [typ(x.strip()) for x in s.split(',') if x.strip()]


def main():
    p = argparse.ArgumentParser(description='AQF parameter sensitivity grid runner for journal evaluation.')
    p.add_argument('--data-dir', required=True)
    p.add_argument('--out-dir', required=True)
    p.add_argument('--cache-dir', default=None)
    p.add_argument('--use-cache', action='store_true')
    p.add_argument('--complexity-budgets', default='20,25,30,32,35,38,40,45,50,53')
    p.add_argument('--thetas', default='0.00,0.02,0.05,0.08,0.10,0.12,0.15,0.18,0.20,0.25')
    p.add_argument('--lambda-scs', default='0.00,0.10,0.25,0.40,0.50,0.60,0.75,0.90,1.00')
    p.add_argument('--mus', default='0.00,0.05,0.10,0.25,0.40,0.50,0.75,1.00')
    p.add_argument('--etas', default='0.00,0.50,1.00,1.50,2.00')
    p.add_argument('--random-trials', type=int, default=10)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--max-combos', type=int, default=0, help='Limit combinations for smoke testing. 0 means all.')
    p.add_argument('--only-one-at-a-time', action='store_true', help='Run one-factor-at-a-time sweeps around defaults instead of full Cartesian grid.')
    p.add_argument('--default-complexity-budget', type=float, default=35.0)
    p.add_argument('--default-theta', type=float, default=0.10)
    p.add_argument('--default-lambda-sc', type=float, default=0.25)
    p.add_argument('--default-mu', type=float, default=0.25)
    p.add_argument('--default-eta', type=float, default=1.0)
    args = p.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    eval_script = ROOT / 'evaluation' / 'run_evaluation_final.py'
    if not eval_script.exists():
        raise SystemExit('evaluation/run_evaluation_final.py not found. Apply AQF final implementation patch first.')

    cbs = parse_values(args.complexity_budgets, float)
    thetas = parse_values(args.thetas, float)
    lambdas = parse_values(args.lambda_scs, float)
    mus = parse_values(args.mus, float)
    etas = parse_values(args.etas, float)

    combos = []
    if args.only_one_at_a_time:
        for v in cbs:
            combos.append(('complexity_budget', v, v, args.default_theta, args.default_lambda_sc, args.default_mu, args.default_eta))
        for v in thetas:
            combos.append(('theta', v, args.default_complexity_budget, v, args.default_lambda_sc, args.default_mu, args.default_eta))
        for v in lambdas:
            combos.append(('lambda_sc', v, args.default_complexity_budget, args.default_theta, v, args.default_mu, args.default_eta))
        for v in mus:
            combos.append(('mu', v, args.default_complexity_budget, args.default_theta, args.default_lambda_sc, v, args.default_eta))
        for v in etas:
            combos.append(('eta', v, args.default_complexity_budget, args.default_theta, args.default_lambda_sc, args.default_mu, v))
    else:
        for cb, th, la, mu, eta in itertools.product(cbs, thetas, lambdas, mus, etas):
            combos.append(('cartesian', -1, cb, th, la, mu, eta))

    if args.max_combos:
        combos = combos[:args.max_combos]

    for i, (sweep_axis, sweep_value, cb, theta, lam, mu, eta) in enumerate(combos, start=1):
        name = f'combo_{i:05d}_{sweep_axis}_{str(sweep_value).replace(".","p")}_c{cb:g}_t{theta:g}_l{lam:g}_mu{mu:g}_e{eta:g}'.replace('.', 'p')
        combo_dir = out / 'combos' / name
        cmd = [
            sys.executable, str(eval_script),
            '--data-dir', args.data_dir,
            '--out-dir', str(combo_dir),
            '--complexity-budget', str(cb),
            '--theta', str(theta),
            '--lambda-sc', str(lam),
            '--mu', str(mu),
            '--eta', str(eta),
            '--random-trials', str(args.random_trials),
            '--seed', str(args.seed),
        ]
        if args.cache_dir:
            cmd += ['--cache-dir', args.cache_dir]
        if args.use_cache:
            cmd += ['--use-cache']
        print(f'[{i}/{len(combos)}] Running:', ' '.join(cmd))
        subprocess.check_call(cmd)
        # Store parameter metadata as a lightweight TSV/JSON-ish text file.
        (combo_dir / 'sensitivity_params.tsv').write_text(
            'sweep_axis\tsweep_value\tcomplexity_budget\ttheta\tlambda_sc\tmu\teta\n' +
            f'{sweep_axis}\t{sweep_value}\t{cb}\t{theta}\t{lam}\t{mu}\t{eta}\n',
            encoding='utf-8'
        )
    print(f'[OK] Sensitivity runs complete: {out}')


if __name__ == '__main__':
    main()
