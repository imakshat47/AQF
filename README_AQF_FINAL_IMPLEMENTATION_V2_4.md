# AQF Final Draft Aligned Implementation v2.4

This patch updates AQF evaluation and generation to follow the final manuscript formulas:

```text
LU(v) = cov(v) * div(v)
SC(u,v) = lambda * CC(u,v) + (1-lambda) * CO(u,v)
Q(v) = LU(v) + mu * sum SC(u,v) * LU(u)
AQ(v,o) = Q(v) * compat(v,o)
C(F) = |E_F| + eta * depth(F)
maximize U(F) subject to C(F) <= complexity_budget
```

## New files

```text
aqf_eval/queriability_final.py
aqf_eval/form_generation_final.py
aqf_eval/journal_metrics_final.py
evaluation/run_evaluation_final.py
evaluation/run_final_parameter_sweep.py
```

## Single run

```bash
python evaluation/run_evaluation_final.py \
  --data-dir orbda_10k/mixed \
  --out-dir results/aqf_final_c35 \
  --use-cache \
  --complexity-budget 35 \
  --theta 0.10 \
  --lambda-sc 0.25 \
  --mu 0.25 \
  --eta 1.0 \
  --random-trials 30
```

## Exhaustive journal sweep

```bash
python evaluation/run_final_parameter_sweep.py \
  --data-dir orbda_10k/mixed \
  --out-dir results/aqf_final_sweep \
  --use-cache \
  --complexity-budgets 30,32,35,39,42,45,53 \
  --thetas 0.00,0.02,0.05,0.08,0.10,0.12,0.15,0.20 \
  --lambda-scs 0.00,0.25,0.50,0.75,1.00 \
  --mus 0.00,0.10,0.25,0.50,0.75,1.00 \
  --etas 0.0,0.5,1.0,1.5,2.0 \
  --random-trials 30
```

## Key outputs

```text
field_scores_final.csv
benchmark_coverage_summary.csv
benchmark_coverage_detail.csv
final_aqf_metrics.csv
complexity_breakdown.csv
operator_burden.csv
operator_burden_summary.csv
relative_ablation_summary.csv
canonical_structure_metrics.csv
coverage_by_query_category.csv
query_realization_results.csv
pareto_frontier.csv
field_selection_audit.csv
field_match_audit.jsonl
```

## Important note

This is a final-draft aligned implementation. Because the draft's raw diversity formula can reprioritize fields differently from earlier correctness patches, expect AQF vs baselines to diverge more clearly. Use this version for journal evaluation tables.
