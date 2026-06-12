# AQF Parameter Sensitivity Patch v5

This patch generates parameter-range experiments and plots to justify why AQF uses specific values for the final evaluation.

## Why this patch exists

Reviewers often ask why a paper selected particular parameter values. This patch creates one-factor-at-a-time and optional full Cartesian sensitivity runs for:

```text
κ / complexity_budget
θ / candidate pruning threshold
λ / structural-connectivity balance
μ / neighborhood reinforcement
η / depth penalty
```

It excludes these methods from final charts by default:

```text
aqf_topk_no_threshold
frequency_only
```

## Files added

```text
evaluation/run_aqf_sensitivity_grid.py
evaluation/summarize_aqf_sensitivity.py
```

## Recommended reviewer-friendly run: one-factor-at-a-time

This is the best first run because it is interpretable and not too expensive.

```bash
python evaluation/run_aqf_sensitivity_grid.py \
  --data-dir orbda_10k/mixed \
  --out-dir results/aqf_param_sensitivity_oat \
  --use-cache \
  --only-one-at-a-time \
  --complexity-budgets 20,25,30,32,35,38,40,45,50,53 \
  --thetas 0.00,0.02,0.05,0.08,0.10,0.12,0.15,0.18,0.20,0.25 \
  --lambda-scs 0.00,0.10,0.25,0.40,0.50,0.60,0.75,0.90,1.00 \
  --mus 0.00,0.05,0.10,0.25,0.40,0.50,0.75,1.00 \
  --etas 0.00,0.50,1.00,1.50,2.00 \
  --random-trials 10
```

Then summarize:

```bash
python evaluation/summarize_aqf_sensitivity.py \
  --sensitivity-dir results/aqf_param_sensitivity_oat
```

## Smoke test

```bash
python evaluation/run_aqf_sensitivity_grid.py \
  --data-dir orbda_10k/mixed \
  --out-dir results/aqf_param_sensitivity_smoke \
  --use-cache \
  --only-one-at-a-time \
  --complexity-budgets 30,35 \
  --thetas 0.08,0.10 \
  --lambda-scs 0.25 \
  --mus 0.25 \
  --etas 1.0 \
  --random-trials 3 \
  --max-combos 5
```

## Optional full Cartesian grid

Use only if runtime is acceptable:

```bash
python evaluation/run_aqf_sensitivity_grid.py \
  --data-dir orbda_10k/mixed \
  --out-dir results/aqf_param_sensitivity_cartesian \
  --use-cache \
  --complexity-budgets 25,30,35,40,45,53 \
  --thetas 0.00,0.05,0.10,0.15,0.20 \
  --lambda-scs 0.00,0.25,0.50,0.75,1.00 \
  --mus 0.00,0.10,0.25,0.50,1.00 \
  --etas 0.50,1.00,1.50 \
  --random-trials 5
```

Then summarize:

```bash
python evaluation/summarize_aqf_sensitivity.py \
  --sensitivity-dir results/aqf_param_sensitivity_cartesian
```

## Outputs

```text
aqf_parameter_sensitivity_all_results.csv
aqf_parameter_sensitivity_best_configs.csv
aqf_parameter_sensitivity_one_factor_summary.csv
parameter_sensitivity_report.md
parameter_sensitivity_plots/support_vs_complexity_budget.png
parameter_sensitivity_plots/support_vs_theta.png
parameter_sensitivity_plots/support_vs_lambda_sc.png
parameter_sensitivity_plots/support_vs_mu.png
parameter_sensitivity_plots/support_vs_eta.png
parameter_sensitivity_plots/efficiency_vs_complexity_budget.png
parameter_sensitivity_plots/efficiency_vs_theta.png
parameter_sensitivity_plots/efficiency_vs_lambda_sc.png
parameter_sensitivity_plots/efficiency_vs_mu.png
parameter_sensitivity_plots/efficiency_vs_eta.png
```

For Cartesian runs, additional heatmaps are produced:

```text
parameter_sensitivity_plots/heatmap_theta_vs_complexity_budget.png
parameter_sensitivity_plots/heatmap_lambda_sc_vs_mu.png
parameter_sensitivity_plots/heatmap_eta_vs_complexity_budget.png
parameter_sensitivity_plots/heatmap_theta_vs_mu.png
```
