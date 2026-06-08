# AQF Advanced Metrics + Visualization Patch v4

This patch adds paper-inspired AQF evaluation metrics and prints all results on screen.

## New metrics

- Strict coverage and partial coverage merged with complexity
- Field efficiency = strict coverage / field count
- Operator efficiency = strict coverage / operator count
- Weighted operator efficiency = strict coverage / weighted operator burden
- Complexity efficiency = strict coverage / final complexity
- Redundancy ratio = unused selected fields / selected fields
- Context preservation rate
- Lineage preservation rate
- Ambiguous label count
- Coverage by query category
- Pareto frontier based on coverage vs complexity
- Relative AQF-full vs baseline comparison

## Run

After any AQF evaluation has produced a result folder:

```bash
python evaluation/aqf_metrics_report.py \
  --results-dir results/aqf_final_c35 \
  --eta 1.0
```

For Windows PowerShell:

```powershell
python evaluation/aqf_metrics_report.py `
  --results-dir results/aqf_final_c35 `
  --eta 1.0
```

## Outputs

CSV files written to the result folder:

```text
final_metrics_enhanced.csv
coverage_by_query_category.csv
redundancy_metrics.csv
pareto_frontier.csv
relative_efficiency_summary.csv
```

Plots written to:

```text
advanced_metric_plots/coverage_vs_complexity.png
advanced_metric_plots/field_efficiency.png
advanced_metric_plots/operator_efficiency.png
advanced_metric_plots/redundancy_ratio.png
advanced_metric_plots/coverage_by_query_category.png
```

## Screen output

The script prints:

1. method-level metrics
2. AQF-full headline
3. coverage by query category
4. relative comparison against baselines
5. Pareto-optimal methods
