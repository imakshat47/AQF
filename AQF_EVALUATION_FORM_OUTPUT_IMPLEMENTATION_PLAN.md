# AQF Evaluation And Form Output Implementation Plan

## Scope

This plan covers the missing implementation pieces needed to support the final AQF manuscript draft:

- evaluation outputs aligned with the manuscript evaluation section;
- generated adaptive form outputs that can be shown as concrete paper artifacts;
- one-command reproducible execution for the complete AQF pipeline.

The manuscript expects a 64-query benchmark workload:

- HCPA Clinical: 30 queries;
- Demographic: 12 queries;
- Hospitalisation: 12 queries;
- Cross-Composition: 10 queries.

The current implementation already has the core AQF evaluation engine. The missing work is mostly artifact discipline: exports, table generation, form rendering, run manifests, and paper-ready summaries.

## Current Baseline

Canonical implementation:

- `aqf_eval/queriability_final.py`
- `aqf_eval/form_generation_final.py`
- `aqf_eval/query_eval.py`
- `aqf_eval/journal_metrics_final.py`
- `evaluation/run_evaluation_final.py`
- `evaluation/run_journal_aqf_pipeline.py`

Current three-composition benchmark files:

- `evaluation/benchmarks/benchmark_queries_hcpa.json`
- `evaluation/benchmarks/benchmark_queries_demographic.json`
- `evaluation/benchmarks/benchmark_queries_hospitalisation.json`
- `evaluation/benchmarks/benchmark_queries_cross_composition.json`

Current reproducible runner:

```powershell
venv\Scripts\python.exe -B evaluation\run_journal_aqf_pipeline.py `
  --out-dir results\journal_locked\main_run `
  --target-coverage 0.90
```

Important note:

- The manuscript says 64 queries. The current primary runner reaches 54 queries unless `--include-cross` is passed. The final paper run must use `--include-cross` or the manuscript must clearly separate 54 primary queries from 10 cross-composition stress queries.

## Implementation Track 1: Evaluation Completeness

### 1.1 Add A Benchmark Manifest

Add:

```text
evaluation/benchmarks/benchmark_manifest.json
```

Contents:

- workload name;
- source JSON file;
- expected query count;
- expected Easy/Medium/Hard counts;
- composition families covered;
- whether included in primary or stress evaluation.

Acceptance criteria:

- Manifest totals equal manuscript Table III.
- Runner validates query counts before evaluation starts.
- Failure should be explicit if a benchmark file count changes.

### 1.2 Add Benchmark Validation Script

Add:

```text
evaluation/validate_benchmarks.py
```

Checks:

- all JSON parses;
- every query has `query_id`, `workload`, `difficulty`, `query_name`, `filters`, `outputs`, `sort`;
- query IDs are unique across all files;
- operators are in the supported operator vocabulary;
- difficulty counts match the manifest;
- primary workload count is either 54 or 64 depending on config;
- all benchmark fields resolve against the current canonical forest, with a warning list for unresolved labels.

Acceptance criteria:

- `validate_benchmarks.py --data-dir dataset/mixed --include-cross` passes before any journal run.
- It writes `benchmark_validation_report.csv` and `benchmark_validation_report.json`.

### 1.3 Lock Manuscript Evaluation Configuration

Add:

```text
evaluation/configs/journal_locked_v17_1_1.json
```

Fields:

- data directory: `dataset/mixed`;
- include cross-composition: true;
- complexity budget;
- theta;
- lambda_sc;
- mu;
- eta;
- random trials;
- seed;
- benchmark manifest path;
- target strict coverage.

Acceptance criteria:

- `run_journal_aqf_pipeline.py --config evaluation/configs/journal_locked_v17_1_1.json` runs without requiring duplicated command flags.
- Run metadata copies the full config into the result folder.

### 1.4 Export Manuscript Tables Directly

Add:

```text
evaluation/export_manuscript_tables.py
```

Input:

```text
results/journal_locked/final_64/
```

Outputs:

```text
results/journal_locked/final_64/tables/
  table_ii_parameters.csv
  table_iii_benchmark_distribution.csv
  table_iv_query_realization_complexity.csv
  table_v_design_component_ablation.csv
  table_operator_awareness.csv
  table_category_coverage.csv
  table_random_baseline_summary.csv
```

Table mapping:

- Table II: from locked config.
- Table III: from benchmark manifest and validation report.
- Table IV: from `final_aqf_metrics.csv`.
- Table V: from `final_aqf_metrics.csv`, `operator_burden_summary.csv`, and `relative_ablation_summary.csv`.
- Operator-awareness table: compare `aqf_full` vs `no_operator_awareness`.
- Category coverage: from `coverage_by_query_category.csv`.
- Random baseline: mean, min, max, standard deviation across `random_topk_*`.

Acceptance criteria:

- Exported tables match manuscript row names and percentages.
- Percent fields are rounded consistently.
- `manuscript_values.json` is generated from the same table exporter, not manually edited.

### 1.5 Add Sensitivity Export

Add or update:

```text
evaluation/run_journal_sensitivity.py
evaluation/export_sensitivity_figures.py
```

Recommended sensitivity axes:

- complexity budget: 45, 47, 50, 53, 56, 60;
- theta: 0.00, 0.05, 0.10, 0.15;
- lambda_sc: 0.00, 0.25, 0.50;
- mu: 0.00, 0.10, 0.25;
- eta: 0.0, 1.0, 2.0.

Outputs:

```text
results/journal_locked/sensitivity/
  journal_all_results.csv
  budget_curve.csv
  theta_curve.csv
  scoring_sensitivity.csv
  pareto_frontier.csv
  figures/coverage_vs_complexity.png
  figures/budget_sensitivity.png
  figures/operator_burden_sensitivity.png
```

Acceptance criteria:

- Supports RQ4 without relying on ad hoc command history.
- Clearly shows whether budget is the dominant coverage factor.

## Implementation Track 2: Adaptive Form Output

### 2.1 Define A Stable Form Output Schema

Add:

```text
aqf_eval/form_output_schema.py
```

Schema levels:

- form metadata;
- form groups;
- subgroups;
- fields;
- field roles;
- operators;
- canonical path;
- datatype;
- score;
- coverage;
- query examples supported by the field;
- AQL/path realization metadata.

Output file:

```text
generated_forms/<method>/adaptive_form_output.json
```

Acceptance criteria:

- The schema is deterministic and sorted.
- Every field has enough metadata to support rendering and query realization.
- `adaptive_form_output.json` is separate from internal `forms.json`.

### 2.2 Add Form Output Exporter

Add:

```text
evaluation/export_adaptive_forms.py
```

Inputs:

- result directory;
- selected method, default `aqf_full`;
- benchmark detail file;
- canonical forest artifact.

Outputs:

```text
results/journal_locked/final_64/form_outputs/
  aqf_full_form.json
  aqf_full_form.md
  aqf_full_form.html
  aqf_full_supported_queries.csv
  aqf_full_field_query_trace.csv
```

Markdown/HTML sections:

- header with run metadata;
- field count, operator count, complexity;
- groups and subgroups;
- fields with compatible operators;
- example queries realized by the form;
- missing/unsupported query components.

Acceptance criteria:

- The HTML can be opened directly in a browser.
- It contains no interactive UI dependency.
- It is suitable for screenshots or appendix inclusion.

### 2.3 Add Representative Form Selection

Add:

```text
evaluation/select_representative_forms.py
```

Select:

- full AQF form;
- one compact group from HCPA;
- one hospitalisation group;
- one demographic group;
- one unsupported/missing-treatment example for limitation analysis.

Outputs:

```text
results/journal_locked/final_64/form_outputs/representative/
  representative_form_hcpa.md
  representative_form_hospitalisation.md
  representative_form_demographic.md
  representative_failure_case.md
```

Acceptance criteria:

- These artifacts directly support manuscript text around generated form output.
- Each representative form cites exact source fields and supported benchmark queries.

### 2.4 Add Query Realization Output

Add:

```text
aqf_eval/query_realization_export.py
```

Outputs:

```text
results/journal_locked/final_64/query_outputs/
  realized_queries.jsonl
  realized_queries.md
  realized_query_examples/
    Q1.md
    H8.md
    X7.md
```

Each realized query artifact should include:

- benchmark query ID;
- filters;
- outputs;
- sort;
- matched AQF form fields;
- operator compatibility;
- deterministic repository paths;
- generated logical query representation;
- generated AQL text if AQL generation is implemented;
- status: realized, partially realized, or unsupported.

Acceptance criteria:

- The current implementation may mark AQL as logical/pseudo-AQL unless a validated AQL backend is added.
- The paper must not claim native AQL execution unless these generated queries are syntax-validated against an AQL engine.

### 2.5 Add Paper Figure Form Render

Add:

```text
evaluation/render_form_output_figure.py
```

Generate a static publication-friendly PNG/PDF from `aqf_full_form.json`.

Outputs:

```text
results/journal_locked/final_64/figures/
  representative_adaptive_form.png
  representative_adaptive_form.pdf
```

Rendering requirements:

- show form groups and subgroups;
- show selected fields;
- show operators as compact labels;
- show score/coverage only if readable;
- avoid UI-specific controls that imply a production interface.

Acceptance criteria:

- Figure can replace the manuscript’s `Figure ??` adaptive form placeholder.
- Labels are readable at manuscript column width.

## Implementation Track 3: One-Command Final Run

Update:

```text
evaluation/run_journal_aqf_pipeline.py
```

Add stages:

1. validate benchmarks;
2. run final evaluation;
3. export enhanced metrics;
4. export manuscript tables;
5. export adaptive form outputs;
6. export query realization outputs;
7. generate static figures;
8. write final `run_summary.md`.

Target command:

```powershell
venv\Scripts\python.exe -B evaluation\run_journal_aqf_pipeline.py `
  --config evaluation\configs\journal_locked_v17_1_1.json `
  --out-dir results\journal_locked\final_64
```

Acceptance criteria:

- A single command produces every artifact needed for the evaluation section.
- The command exits non-zero if strict coverage is below target.
- The command exits non-zero if benchmark counts differ from the manifest.
- The result directory is self-contained.

## Final Artifact Layout

Expected final output:

```text
results/journal_locked/final_64/
  run_metadata.json
  run_summary.md
  manuscript_values.json
  benchmark_validation_report.json
  benchmark_validation_report.csv
  final_aqf_metrics.csv
  final_metrics_enhanced.csv
  benchmark_coverage_summary.csv
  benchmark_coverage_detail.csv
  coverage_by_query_category.csv
  operator_burden_summary.csv
  relative_ablation_summary.csv
  pareto_frontier.csv
  tables/
  figures/
  form_outputs/
  query_outputs/
  generated_forms/
  artifacts/
```

## Validation Criteria

The implementation is complete when:

1. the 64-query workload is validated from the benchmark manifest;
2. the final run reaches the manuscript target or explicitly reports the new achieved value;
3. Table II through Table V can be generated directly from artifacts;
4. `aqf_full_form.html` and `representative_adaptive_form.png` exist;
5. query realization examples exist for HCPA, demographic, hospitalisation, and cross-composition workloads;
6. all generated results are under `results/journal_locked/final_64`;
7. no manuscript number requires manual calculation.

## Risk Items

The main technical risk is the distinction between logical query realization and executable AQL. The manuscript currently says the resulting AQL query can be executed directly. The implementation should either:

- add real AQL generation plus syntax validation, or
- revise the claim to logical AQF query realization.

Until this is resolved, final evaluation language should avoid claiming validated native AQL execution.

The second risk is metric drift. Existing latest output with the 54-query primary workload reached 90.74% strict coverage at complexity budget 50. The manuscript’s 64-query claim must be re-run with `--include-cross` and locked before final numbers are used.
