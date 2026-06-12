# AQF Journal Evaluation Patch v2.3

This patch adds journal-grade evaluation reporting for the final AQF manuscript.

It is an evaluation/reporting patch. It does not change the parser, matcher, or current form generator.

## New files

```text
aqf_eval/journal_metrics.py
evaluation/run_journal_postprocess.py
evaluation/run_journal_parameter_sweep.py
evaluation/journal_eval_config.json
```

## What it produces

For any existing AQF result directory, it writes:

```text
final_aqf_metrics.csv
complexity_breakdown.csv
operator_burden.csv
operator_burden_summary.csv
relative_ablation_summary.csv
candidate_pruning_audit.csv
canonical_structure_metrics.csv
coverage_by_query_category.csv
query_realization_results.csv
pareto_frontier.csv
journal_plots/
```

For a sweep root containing `combos/combo_*`, it also writes:

```text
journal_all_results.csv
journal_pareto_frontier.csv
```

## Why this patch is needed

The final AQF manuscript defines final complexity as:

```text
C(F) = |E_F| + eta * depth(F)
```

and treats operator awareness, canonical context preservation, candidate pruning, relative ablations, and query realization as distinct claims. This patch reports each claim separately.

## Run on an existing single AQF result folder

```bash
python evaluation/run_journal_postprocess.py \
  --results-dir results/aqf_eval_v2_1_k30 \
  --eta 1.0 \
  --theta 0.10
```

## Run on an existing sweep folder

```bash
python evaluation/run_journal_postprocess.py \
  --results-dir results/sweep_kappa \
  --eta 1.0 \
  --theta 0.10
```

## Run a sweep and journal post-processing together

Requires `evaluation/run_parameter_sweep.py` from the v2.2 sweep patch.

```bash
python evaluation/run_journal_parameter_sweep.py \
  --data-dir orbda_10k/mixed \
  --out-dir results/journal_sweep \
  --use-cache \
  --kappas 25,27,30,32,35,39,42,45,53 \
  --thetas 0.00,0.02,0.05,0.08,0.10,0.12,0.15,0.20 \
  --alphas 0.70 \
  --betas 0.30 \
  --lambdas 0.00,0.25,0.50,0.75,1.00 \
  --etas 0.0,0.5,1.0,1.5,2.0 \
  --random-trials 30
```

## Notes

- `eta` is used for final complexity reporting.
- Current v2.2 sweep varies `lambda` as the existing scoring parameter. A full algorithmic scoring patch can later introduce manuscript-level `mu` into actual field selection. Until then, `mu` should be discussed as a planned scoring-sensitivity extension if not implemented in the generator.
- `query_realization_results.csv` currently validates path/operator resolution and produces conservative pseudo-AQL skeletons. If an openEHR server is available, replace `execution_success` and `result_count` with real execution outcomes.
