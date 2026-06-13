# AQF Parameter Sweep Patch v2.2

Adds a parameter/matrix sweep runner with:

- Terminal printout for every parameter combination.
- Per-combination output folders.
- Global comparison CSVs for all results.
- Best/worst/average case summaries by method.
- Cache support across sweep runs.

## Cache behaviour

The sweep uses two cache layers:

1. `canonical_forest.json` cache, keyed by dataset fingerprint.
2. `queriability_scores` cache, keyed by `(alpha, beta, lambda)`.

This means it is safe to sweep `kappa` and `theta` without recomputing the forest or scores. It is also safe to sweep `alpha`, `beta`, and `lambda`; new score files are computed once per unique scoring triple and reused afterward.

## Example: kappa sweep only

```bash
python evaluation/run_parameter_sweep.py \
  --data-dir /path/to/orbda_10k/mixed \
  --out-dir results/sweep_kappa \
  --use-cache \
  --kappas 20,25,27,30,32,34,35,36,39,42,45,53 \
  --thetas 0.10 \
  --alphas 0.70 \
  --betas 0.30 \
  --lambdas 0.25 \
  --random-trials 30
```

## Example: smaller scoring sweep

```bash
python evaluation/run_parameter_sweep.py \
  --data-dir /path/to/orbda_10k/mixed \
  --out-dir results/sweep_scoring \
  --use-cache \
  --kappas 30,35,39 \
  --thetas 0.10 \
  --alphas 0.50,0.60,0.70,0.80 \
  --betas 0.50,0.40,0.30,0.20 \
  --lambdas 0.00,0.10,0.25,0.50 \
  --random-trials 30
```

Note: the scoring sweep above uses the Cartesian product of alpha/beta values. If you only want paired alpha/beta values, run separate commands or use `--max-combos` for debugging first.

## Outputs

Global outputs:

- `sweep_all_results.csv`
- `sweep_best_by_method.csv`
- `sweep_worst_by_method.csv`
- `sweep_average_by_method.csv`
- `sweep_random_summary_by_combo.csv`
- `dataset_summary.csv`
- `sweep_metadata.json`

Per-combination outputs live under:

- `combos/combo_*/benchmark_coverage_summary.csv`
- `combos/combo_*/benchmark_coverage_detail.csv`
- `combos/combo_*/form_complexity.csv`
- `combos/combo_*/field_selection_audit.csv`
- `combos/combo_*/field_match_audit.jsonl`
- `combos/combo_*/generated_forms/*/forms.json`
