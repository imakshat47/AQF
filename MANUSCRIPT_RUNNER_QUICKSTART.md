# AQF Manuscript Runner - Quick Start Guide

This is a quick reference for the most common use cases of the manuscript-aligned AQF runner.

## Installation

No additional installation needed! The runner uses the existing AQF pipeline modules.

## Basic Commands

### Run the Complete Pipeline

Generate publication-ready results in one command:

```bash
python aqf_manuscript_runner.py all --data-dir dataset/mixed
```

Results will be saved to `results/aqf_manuscript/`.

### Custom Output Directory

```bash
python aqf_manuscript_runner.py all --data-dir dataset/mixed --out-base results/my_experiment
```

### Use Different Parameters

```bash
python aqf_manuscript_runner.py all \
  --data-dir dataset/mixed \
  --complexity-budget 40 \
  --theta 0.15 \
  --lambda-sc 0.30 \
  --mu 0.35 \
  --eta 1.5
```

## Step-by-Step Pipeline

### 1. Run Evaluation Only

```bash
python aqf_manuscript_runner.py evaluate --data-dir dataset/mixed
```

This generates:
- Canonical forest representation
- Generated AQF forms
- Coverage and complexity metrics

Output: `results/aqf_eval_manuscript/evaluation/`

### 2. Postprocess Results

```bash
python aqf_manuscript_runner.py postprocess --results-dir results/aqf_eval_manuscript/evaluation
```

Adds detailed metrics to results.

### 3. Generate Report

```bash
python aqf_manuscript_runner.py report --results-dir results/aqf_eval_manuscript/evaluation
```

Generates:
- Coverage metrics
- Complexity analysis
- Operator burden calculations
- Category-wise statistics

### 4. Generate Visualizations

```bash
python aqf_manuscript_runner.py visualize \
  --results-dir results/aqf_eval_manuscript/evaluation \
  --data-dir dataset/mixed
```

Generates PNG schema graphs and diagrams.

## Advanced Usage

### Dry Run (Preview Commands)

See what would be executed without running:

```bash
python aqf_manuscript_runner.py --dry-run all --data-dir dataset/mixed
```

### Verbose Logging

Get detailed output for debugging:

```bash
python aqf_manuscript_runner.py --verbose all --data-dir dataset/mixed
```

### Skip Specific Steps

Run pipeline but skip postprocessing and report:

```bash
python aqf_manuscript_runner.py all \
  --data-dir dataset/mixed \
  --skip-postprocess \
  --skip-report
```

### Update Visualizations Only

If evaluation is already done, regenerate with different visual parameters:

```bash
python aqf_manuscript_runner.py visualize \
  --results-dir results/aqf_manuscript/evaluation \
  --data-dir dataset/mixed \
  --fig-width 60 \
  --fig-height 45 \
  --font-size 18
```

## Output Structure

After running `all`, you'll have:

```
results/aqf_manuscript/
├── evaluation/
│   ├── .cache/                    # Cached intermediate data
│   ├── generated_forms/           # Generated AQF forms
│   ├── metrics/                   # CSV metrics files
│   ├── postprocessed_metrics/     # Postprocessing results
│   └── derived_metrics/           # Final computed metrics
├── schema_graphs/                 # PNG visualizations
├── pipeline.log                   # Complete execution log
└── ...
```

## Default Parameters (Manuscript-Aligned)

These defaults are used for publication-ready results:

| Parameter | Value | Purpose |
|-----------|-------|---------|
| complexity_budget | 35 | Field complexity constraint |
| theta | 0.10 | Threshold parameter |
| lambda_sc | 0.25 | Lambda score weight |
| mu | 0.25 | Mu parameter |
| eta | 1.0 | Depth weight |
| random_trials | 30 | Trials for robustness |

## Common Workflows

### For Paper Submission

```bash
# Generate complete, publication-ready results
python aqf_manuscript_runner.py all --data-dir dataset/mixed --out-base results/paper_v2_4

# Wait for completion, then check results
ls results/paper_v2_4/evaluation/metrics/
ls results/paper_v2_4/schema_graphs/
```

### For Sensitivity Analysis

```bash
# Test multiple complexity budgets
for c in 30 35 40 45; do
  python aqf_manuscript_runner.py all \
    --data-dir dataset/mixed \
    --out-base results/sensitivity_c$c \
    --complexity-budget $c \
    --skip-postprocess  # Optional: speed up
done
```

### For Quick Iteration

```bash
# Evaluation only (fastest)
python aqf_manuscript_runner.py evaluate --data-dir dataset/mixed

# Then test different visualization parameters
for w in 40 50 60; do
  python aqf_manuscript_runner.py visualize \
    --results-dir results/aqf_eval_manuscript/evaluation \
    --data-dir dataset/mixed \
    --out-dir results/viz_w$w \
    --fig-width $w
done
```

### For Iterative Development

```bash
# Test with smaller dataset first (if available)
python aqf_manuscript_runner.py all --data-dir dataset/mixed_mini --dry-run

# Run with cache enabled for faster re-runs
python aqf_manuscript_runner.py all --data-dir dataset/mixed --use-cache
```

## Troubleshooting

### Command Not Found

Make sure you're in the AQF root directory:

```bash
cd /path/to/AQF
python aqf_manuscript_runner.py all --data-dir dataset/mixed
```

### Dataset Not Found

Verify dataset path:

```bash
ls dataset/mixed/
# Should contain JSON files
```

### Out of Memory

Reduce visualization parameters:

```bash
python aqf_manuscript_runner.py visualize \
  --results-dir results/aqf_manuscript/evaluation \
  --data-dir dataset/mixed \
  --max-field-labels 100 \
  --fig-width 36 \
  --fig-height 28
```

### Start Fresh (Clear Cache)

```bash
rm -rf results/aqf_manuscript/evaluation/.cache
python aqf_manuscript_runner.py evaluate --data-dir dataset/mixed
```

## Getting Help

### Show All Commands

```bash
python aqf_manuscript_runner.py --help
```

### Help for Specific Command

```bash
python aqf_manuscript_runner.py evaluate --help
python aqf_manuscript_runner.py all --help
python aqf_manuscript_runner.py visualize --help
```

## Examples

### Example 1: Minimal (Evaluate Only)

```bash
python aqf_manuscript_runner.py evaluate --data-dir dataset/mixed
```

**Time**: ~5-15 minutes (depends on dataset size)

### Example 2: Full Pipeline

```bash
python aqf_manuscript_runner.py all --data-dir dataset/mixed
```

**Time**: ~10-20 minutes

**Output**: Complete evaluation, metrics, reports, and visualizations

### Example 3: Custom Configuration

```bash
python aqf_manuscript_runner.py all \
  --data-dir dataset/mixed \
  --out-base results/final_submission \
  --complexity-budget 35 \
  --theta 0.10 \
  --lambda-sc 0.25 \
  --mu 0.25 \
  --eta 1.0 \
  --random-trials 30
```

### Example 4: Sensitivity Analysis

```bash
# Test different theta values
for theta in 0.05 0.10 0.15 0.20; do
  python aqf_manuscript_runner.py all \
    --data-dir dataset/mixed \
    --out-base results/theta_sensitivity_${theta} \
    --theta $theta \
    --skip-postprocess
done
```

### Example 5: Verify Before Running

```bash
# Check what would be executed
python aqf_manuscript_runner.py --dry-run all --data-dir dataset/mixed

# Then run for real
python aqf_manuscript_runner.py all --data-dir dataset/mixed
```

## See Also

- `README_MANUSCRIPT_RUNNER.md` - Full documentation
- `evaluation/` - Individual evaluation scripts
- `aqf_eval/` - Metrics calculation modules
- `cmd.txt` - Additional command examples

## Tips

1. **Use `--dry-run`** to preview commands before running
2. **Use `--verbose`** when debugging issues
3. **Use `--use-cache`** to speed up re-runs
4. **Check `pipeline.log`** in results directory for execution details
5. **Start with smaller datasets** (`dataset/mixed_mini`) for testing
6. **Parameter tuning**: Start with defaults, then adjust based on results
