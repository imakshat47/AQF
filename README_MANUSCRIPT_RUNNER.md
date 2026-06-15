# AQF Manuscript-Aligned Runner

This is the final orchestration layer for running the complete AQF (Adaptive Query Forms) evaluation, postprocessing, reporting, and visualization pipeline in a manuscript-aligned configuration.

## Overview

The manuscript runner provides a unified CLI interface to execute the entire AQF pipeline with sensible defaults for publication-ready results. It handles:

1. **Evaluation** - Core AQF evaluation on a dataset
2. **Postprocessing** - Journal postprocessing of evaluation results
3. **Reporting** - Metrics and coverage analysis reports
4. **Visualization** - Schema graphs and figure generation
5. **All** - Complete end-to-end pipeline

## Quick Start

### Prerequisites

- Python 3.8+
- Dataset in `dataset/mixed` or your preferred location
- Required dependencies installed (see `requirements.txt`)

### Basic Usage

```bash
# Run complete pipeline
python aqf_manuscript_runner.py all --data-dir dataset/mixed

# Run only evaluation
python aqf_manuscript_runner.py evaluate --data-dir dataset/mixed

# Run only postprocessing (on existing results)
python aqf_manuscript_runner.py postprocess \
  --results-dir results/aqf_manuscript/evaluation

# Generate report
python aqf_manuscript_runner.py report \
  --results-dir results/aqf_manuscript/evaluation

# Generate visualizations
python aqf_manuscript_runner.py visualize \
  --results-dir results/aqf_manuscript/evaluation \
  --data-dir dataset/mixed
```

## Commands

### `evaluate`

Run AQF evaluation on a dataset.

```bash
python aqf_manuscript_runner.py evaluate \
  --data-dir dataset/mixed \
  --out-dir results/aqf_eval \
  --complexity-budget 35 \
  --theta 0.10 \
  --lambda-sc 0.25 \
  --mu 0.25 \
  --eta 1.0
```

**Options:**
- `--data-dir` (required): Path to dataset directory
- `--out-dir`: Output directory (default: `results/aqf_eval_manuscript/evaluation`)
- `--cache-dir`: Cache directory for intermediate results
- `--use-cache`: Use cached data if available (default: enabled)
- `--complexity-budget`: Field complexity budget (default: 35)
- `--theta`: Threshold parameter (default: 0.10)
- `--lambda-sc`: Lambda score parameter (default: 0.25)
- `--mu`: Mu parameter (default: 0.25)
- `--eta`: Eta parameter (default: 1.0)
- `--random-trials`: Number of random trials (default: 30)
- `--seed`: Random seed (default: 42)

**Output:**
Generates evaluation results in `out-dir` including:
- `.cache/` - Cached intermediate results
- `generated_forms/` - Generated AQF forms
- Coverage and complexity metrics

### `postprocess`

Run postprocessing on evaluation results.

```bash
python aqf_manuscript_runner.py postprocess \
  --results-dir results/aqf_manuscript/evaluation \
  --eta 1.0 \
  --theta 0.10
```

**Options:**
- `--results-dir` (required): Path to evaluation results directory
- `--eta`: Eta parameter (default: 1.0)
- `--theta`: Theta parameter (default: 0.10)
- `--out-dir`: Output directory (defaults to results-dir)

**Output:**
Enhances evaluation results with postprocessed metrics and analysis.

### `report`

Generate comprehensive metrics report.

```bash
python aqf_manuscript_runner.py report \
  --results-dir results/aqf_manuscript/evaluation \
  --eta 1.0
```

**Options:**
- `--results-dir` (required): Path to evaluation results directory
- `--eta`: Eta parameter for metrics (default: 1.0)
- `--out-dir`: Output directory for reports

**Output:**
Generates CSV and JSON reports with:
- Query coverage metrics
- Field complexity analysis
- Operator burden calculations
- Category-wise coverage statistics

### `visualize`

Generate schema graphs and visualizations.

```bash
python aqf_manuscript_runner.py visualize \
  --results-dir results/aqf_manuscript/evaluation \
  --data-dir dataset/mixed \
  --mu 0.25 \
  --fig-width 48 \
  --fig-height 38 \
  --font-size 15 \
  --max-field-labels 200
```

**Options:**
- `--results-dir` (required): Path to evaluation results directory
- `--data-dir`: Path to dataset (optional, for enhanced graphs)
- `--mu`: Mu parameter (default: 0.25)
- `--out-dir`: Output directory (default: `<results-dir>/schema_graphs`)
- `--fig-width`: Figure width in inches (default: 48)
- `--fig-height`: Figure height in inches (default: 38)
- `--font-size`: Font size for labels (default: 15)
- `--max-field-labels`: Maximum field labels (default: 200)

**Output:**
Generates PNG visualizations in `out-dir`:
- Schema relationship graphs
- Field hierarchy diagrams
- Coverage heatmaps

### `all`

Run the complete pipeline.

```bash
python aqf_manuscript_runner.py all \
  --data-dir dataset/mixed \
  --out-base results/aqf_manuscript \
  --complexity-budget 35 \
  --theta 0.10 \
  --lambda-sc 0.25 \
  --mu 0.25 \
  --eta 1.0
```

**Options:**
- `--data-dir` (required): Path to dataset directory
- `--out-base`: Base output directory (default: `results/aqf_manuscript`)
- `--skip-evaluation`: Skip evaluation step
- `--skip-postprocess`: Skip postprocessing
- `--skip-report`: Skip report generation
- `--skip-visualization`: Skip visualization
- All evaluation parameters (complexity-budget, theta, lambda-sc, mu, eta, random-trials)

**Output:**
Complete pipeline results in `out-base`:
```
results/aqf_manuscript/
├── evaluation/
│   ├── .cache/              # Cached data
│   ├── generated_forms/     # AQF forms
│   ├── metrics/             # Metrics CSVs
│   └── ...
├── schema_graphs/           # Visualizations
├── pipeline.log            # Execution log
└── ...
```

## Manuscript-Aligned Defaults

The runner uses sensible defaults optimized for publication-ready results:

```python
complexity_budget = 35      # Field complexity constraint
theta = 0.10                # Threshold parameter
lambda_sc = 0.25            # Lambda score weight
mu = 0.25                   # Mu parameter
eta = 1.0                   # Eta parameter (depth weight)
random_trials = 30          # Trials for robustness
```

These defaults align with the manuscript's recommendations and can be overridden as needed.

## Advanced Usage

### Dry Run

Preview what commands would be executed without running them:

```bash
python aqf_manuscript_runner.py all \
  --data-dir dataset/mixed \
  --dry-run
```

### Verbose Logging

See detailed command and output information:

```bash
python aqf_manuscript_runner.py all \
  --data-dir dataset/mixed \
  --verbose
```

### Custom Parameters

Override defaults for sensitivity analysis:

```bash
python aqf_manuscript_runner.py all \
  --data-dir dataset/mixed \
  --out-base results/aqf_custom_params \
  --complexity-budget 40 \
  --theta 0.15 \
  --lambda-sc 0.30 \
  --mu 0.35 \
  --eta 1.5
```

### Partial Pipeline

Run only specific steps:

```bash
# Evaluation only
python aqf_manuscript_runner.py all \
  --data-dir dataset/mixed \
  --skip-postprocess \
  --skip-report \
  --skip-visualization

# Postprocessing and reporting only
python aqf_manuscript_runner.py all \
  --data-dir dataset/mixed \
  --skip-evaluation \
  --skip-visualization
```

### Using Cached Results

For subsequent analysis, use cached results to save time:

```bash
python aqf_manuscript_runner.py all \
  --data-dir dataset/mixed \
  --use-cache \
  --skip-evaluation  # Use cached evaluation
```

## Output Structure

### Evaluation Output
```
evaluation/
├── .cache/
│   ├── canonical_forest.json    # Canonical forest representation
│   ├── dataset_fingerprint.json # Dataset metadata
│   └── scores/
├── generated_forms/             # Generated AQF forms
│   └── aqf_full/
│       ├── forms.json           # Form definitions
│       └── forms_by_composition # Forms by archetype
├── metrics/
│   ├── complexity.csv           # Complexity metrics
│   ├── coverage.csv             # Coverage metrics
│   ├── operator_burden.csv      # Operator burden
│   └── ...
└── summary.json                 # Evaluation summary
```

### Postprocessing Output
```
evaluation/
├── postprocessed_metrics/
│   ├── coverage_by_category.csv
│   ├── query_realization.csv
│   └── ...
└── derived_metrics/
```

### Report Output
```
evaluation/
├── metrics/
│   ├── complexity_report.csv
│   ├── canonical_metrics.csv
│   ├── ablation_analysis.csv
│   ├── pareto_frontier.csv
│   └── ...
└── derived_metrics/
```

### Visualization Output
```
schema_graphs/
├── aqf_full_schema_graph.png
├── field_heatmap.png
├── coverage_analysis.png
└── ...
```

## Pipeline Log

Each run generates a `pipeline.log` file recording:
- Start and end times
- All commands executed
- Success/failure status
- Execution timing

Example:
```
[2024-01-15 10:30:45] [INFO] MANUSCRIPT-ALIGNED AQF PIPELINE STARTED
[2024-01-15 10:30:46] [INFO] Starting AQF Evaluation
[2024-01-15 10:30:46] [INFO] Running: AQF Evaluation
[2024-01-15 10:35:12] [SUCCESS] ✓ AQF Evaluation completed successfully
[2024-01-15 10:35:13] [INFO] Starting Postprocessing
...
[2024-01-15 10:45:30] [INFO] PIPELINE COMPLETED SUCCESSFULLY in 615.2s
[2024-01-15 10:45:30] [INFO] Results saved to: results/aqf_manuscript/evaluation
```

## Common Workflows

### Publish-Ready Results

Generate complete, publication-ready results:

```bash
python aqf_manuscript_runner.py all \
  --data-dir dataset/mixed \
  --out-base results/aqf_final_v2_4 \
  --random-trials 30
```

### Quick Evaluation with Visualization

Fast evaluation with graph generation:

```bash
python aqf_manuscript_runner.py evaluate --data-dir dataset/mixed && \
python aqf_manuscript_runner.py visualize \
  --results-dir results/aqf_eval_manuscript/evaluation \
  --data-dir dataset/mixed
```

### Sensitivity Analysis

Test multiple parameter combinations:

```bash
for complexity in 30 35 40; do
  python aqf_manuscript_runner.py all \
    --data-dir dataset/mixed \
    --out-base "results/sensitivity_c$complexity" \
    --complexity-budget $complexity \
    --skip-postprocess  # Faster if only interested in structure
done
```

### Update Visualizations Only

Regenerate visualizations with different parameters:

```bash
python aqf_manuscript_runner.py visualize \
  --results-dir results/aqf_manuscript/evaluation \
  --data-dir dataset/mixed \
  --fig-width 60 \
  --fig-height 45 \
  --font-size 18
```

## Troubleshooting

### "No files found for composition archetype"

Ensure your dataset directory has the correct structure and contains JSON files with the expected composition archetypes.

### Out of memory during visualization

Reduce `--fig-width`, `--fig-height`, or `--max-field-labels`:

```bash
python aqf_manuscript_runner.py visualize \
  --results-dir results/aqf_manuscript/evaluation \
  --data-dir dataset/mixed \
  --max-field-labels 100 \
  --fig-width 36 \
  --fig-height 28
```

### Cache issues

Clear the cache and re-run:

```bash
rm -rf results/aqf_manuscript/evaluation/.cache
python aqf_manuscript_runner.py evaluate --data-dir dataset/mixed
```

## Integration with Other Tools

The runner generates standard outputs (CSV, JSON, PNG) compatible with:
- Tableau/Power BI for further analysis
- LaTeX/Markdown for paper generation
- Jupyter notebooks for interactive exploration

## See Also

- `evaluation/run_evaluation_final.py` - Core evaluation implementation
- `evaluation/run_journal_postprocess.py` - Postprocessing details
- `evaluation/aqf_metrics_report.py` - Metrics calculation
- `evaluation/generate_aqf_schema_graphs.py` - Graph generation
- `README.md` - Main AQF documentation
- `cmd.txt` - Additional command examples
