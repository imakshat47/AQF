#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description="Wrapper: run AQF parameter sweep, then journal post-processing.")
    p.add_argument("--data-dir", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--cache-dir", default=None)
    p.add_argument("--use-cache", action="store_true")
    p.add_argument("--kappas", default="25,27,30,32,35,39,42,45,53")
    p.add_argument("--thetas", default="0.00,0.02,0.05,0.08,0.10,0.12,0.15,0.20")
    p.add_argument("--alphas", default="0.70")
    p.add_argument("--betas", default="0.30")
    p.add_argument("--lambdas", default="0.25")
    p.add_argument("--etas", default="1.0", help="Comma-separated eta values for post-processing only. Run multiple postprocess passes.")
    p.add_argument("--random-trials", type=int, default=30)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--max-combos", type=int, default=0)
    args = p.parse_args()

    sweep_script = ROOT / "evaluation" / "run_parameter_sweep.py"
    if not sweep_script.exists():
        raise SystemExit("run_parameter_sweep.py not found. Apply v2.2 sweep patch first.")
    cmd = [
        sys.executable, str(sweep_script),
        "--data-dir", args.data_dir,
        "--out-dir", args.out_dir,
        "--kappas", args.kappas,
        "--thetas", args.thetas,
        "--alphas", args.alphas,
        "--betas", args.betas,
        "--lambdas", args.lambdas,
        "--random-trials", str(args.random_trials),
        "--seed", str(args.seed),
    ]
    if args.cache_dir:
        cmd += ["--cache-dir", args.cache_dir]
    if args.use_cache:
        cmd += ["--use-cache"]
    if args.max_combos:
        cmd += ["--max-combos", str(args.max_combos)]
    print("[RUN]", " ".join(cmd))
    subprocess.check_call(cmd)

    post = ROOT / "evaluation" / "run_journal_postprocess.py"
    for eta in [x.strip() for x in args.etas.split(",") if x.strip()]:
        post_cmd = [sys.executable, str(post), "--results-dir", args.out_dir, "--eta", eta]
        print("[POST]", " ".join(post_cmd))
        subprocess.check_call(post_cmd)


if __name__ == "__main__":
    main()
