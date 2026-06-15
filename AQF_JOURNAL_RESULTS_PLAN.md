# AQF Journal Results Plan

## Purpose

Create one reproducible, journal-ready result pipeline for Adaptive Query Forms (AQF) from the multiple implementations in this repository. The goal is to produce defensible tables, figures, and artifact folders that support a research paper, while avoiding accidental mixing of legacy UI code, early graph prototypes, and final manuscript-aligned evaluation code.

## Implementation Decision

Use `aqf_eval/` and `evaluation/run_evaluation_final.py` as the canonical research implementation.

Treat the other implementations as follows:

- `aqf_eval/`: primary evaluation package. This contains the final-draft aligned scoring, form generation, query evaluation, metrics, audits, and reporting.
- `evaluation/`: primary experiment runner layer. This should own command-line experiment execution, parameter sweeps, postprocessing, and paper artifact generation.
- `aqf/`: secondary experimental/visualization layer. Use it for schema graph visuals, workload expansion, reverse-sweep validation, and query-realization diagnostics, but do not use it as the main metrics source unless outputs are explicitly reconciled with `aqf_eval`.
- `aqf_implement/`: clean minimal graph prototype. Use only as method intuition or appendix material, not as the journal result engine.
- Root Streamlit/UI files such as `app.py`, `app_v2.py`, `aqf_v2_1_1.py`, and `aqf_v2_1_2_auto_parser.py`: product/demo implementations. Use for screenshots or system demonstration only, not for quantitative claims.
- `acf_eval/`: older/parallel evaluation terminology. Keep as historical comparison only unless the manuscript explicitly discusses ACF.

## Research Claims To Support

The results should support five claims:

1. AQF can construct canonical queryable form structures from heterogeneous hierarchical healthcare records.
2. AQF selects compact field sets while preserving useful query coverage.
3. AQF-aware selection improves over random top-k selection and provides better operator discipline than non-operator-aware forms.
4. Canonical grouping preserves schema context better than flattened forms.
5. Coverage, complexity, and operator burden expose an interpretable trade-off curve suitable for choosing journal-reported operating points.

## Primary Dataset And Workloads

Primary dataset:

- `dataset/mixed`
- Current observed size: 115 JSON files.
- Existing final-sweep canonical summary reports 2 composition families and 35 canonical fields.

Primary benchmark workload:

- `evaluation/benchmarks/benchmark_queries_hcpa.json`: 30 queries.
- `evaluation/benchmarks/benchmark_queries_demographic.json`: 12 queries.
- Total primary workload: 42 queries.

Stress-test workload:

- `evaluation/benchmarks/benchmark_queries_cross_composition.json`: 6 queries.
- Report separately as cross-composition stress testing, not mixed into the main 42-query headline unless clearly labelled.

Optional validation workloads:

- `aqf/workload_expansion_v2/benchmark_workload_154.json`.
- `aqf/workload_expansion_v2/synthetic_workload_10000.json`.

Use these only after the primary 42-query result is stable.

## Canonical Formula Set

The journal pipeline should report the final-draft formulas implemented in `aqf_eval/queriability_final.py` and `aqf_eval/form_generation_final.py`:

```text
LU(v) = cov(v) * div(v)
SC(u,v) = lambda * CC(u,v) + (1 - lambda) * CO(u,v)
Q(v) = LU(v) + mu * sum SC(u,v) * LU(u)
AQ(v,o) = Q(v) * compat(v,o)
C(F) = |E_F| + eta * depth(F)
maximize U(F) subject to C(F) <= complexity_budget
```

The paper should explicitly state that query evaluation is logical AQF query realization over benchmark specifications, not native AQL execution, unless a validated AQL renderer/backend is later added.

## Experimental Design

### Phase 1: Reproducible Single Run

Purpose: produce the main paper operating-point result.

Recommended command:

```powershell
python evaluation/run_evaluation_final.py `
  --data-dir dataset/mixed `
  --out-dir results/journal_locked/main_run `
  --use-cache `
  --complexity-budget 30 `
  --theta 0.0 `
  --lambda-sc 0.0 `
  --mu 0.1 `
  --eta 1.0 `
  --random-trials 30 `
  --seed 42
```

Rationale:

- This mirrors one existing completed sweep point: `results/final_sweep/combos/combo_0008_c30_t0_l0_mu0p1_e1`.
- Existing result at that point shows AQF strict coverage of 30/42 queries, partial coverage about 0.767, 24 selected fields, 132 operators, and final complexity 30.
- `no_pruning` acts as an upper-bound/reference form with 35 fields, 187 operators, final complexity 41, and strict coverage about 40/42.

### Phase 2: Locked Parameter Sweep

Purpose: show sensitivity and the coverage-complexity trade-off.

Use a staged grid rather than an uncontrolled exploratory sweep.

Recommended compact journal grid:

```powershell
python evaluation/run_final_parameter_sweep.py `
  --data-dir dataset/mixed `
  --out-dir results/journal_locked/final_sweep `
  --use-cache `
  --complexity-budgets 20,24,28,30,32,35,39,42 `
  --thetas 0.0,0.05,0.10,0.15 `
  --lambda-scs 0.0,0.25,0.50 `
  --mus 0.0,0.10,0.25,0.50 `
  --etas 0.0,1.0,2.0 `
  --random-trials 30 `
  --seed 42
```

If runtime is too high, split into three separate sweeps:

- Budget sweep: vary `complexity_budget`, fix `theta=0.0`, `lambda_sc=0.0`, `mu=0.1`, `eta=1.0`.
- Threshold sweep: vary `theta`, fix the selected budget/scoring parameters.
- Scoring sensitivity: vary `lambda_sc` and `mu`, fix the selected budget and theta.

### Phase 3: Cross-Composition Stress Test

Purpose: evaluate whether AQF can handle queries spanning composition families.

Run the same selected operating point with cross-composition queries included:

```powershell
python evaluation/run_evaluation_final.py `
  --data-dir dataset/mixed `
  --out-dir results/journal_locked/cross_composition `
  --use-cache `
  --complexity-budget 30 `
  --theta 0.0 `
  --lambda-sc 0.0 `
  --mu 0.1 `
  --eta 1.0 `
  --random-trials 30 `
  --seed 42 `
  --include-cross
```

Report this separately from the main 42-query table.

### Phase 4: Enhanced Metrics And Plots

Purpose: convert raw run folders into paper-facing metrics and figures.

For the main run:

```powershell
python evaluation/aqf_metrics_report.py `
  --results-dir results/journal_locked/main_run `
  --eta 1.0
```

For a sweep root:

```powershell
python evaluation/run_journal_postprocess.py `
  --results-dir results/journal_locked/final_sweep `
  --eta 1.0 `
  --theta 0.0
```

Important quality note:

- Do not rely on `results/aqf_final` as a paper artifact in its current state. It contains empty `field_scores_final.csv` and `operator_burden.csv`, and `final_aqf_metrics.csv` currently reports zero fields for all methods.
- Prefer `results/final_sweep` as the existing usable baseline, then regenerate into `results/journal_locked/` for clean provenance.

### Phase 5: Schema Graph Visual Evidence

Purpose: produce conceptual and explanatory figures showing how AQF transforms hierarchical records into queryable structures.

Use `evaluation/generate_aqf_schema_graphs.py` for paper visuals from the same canonical forest used by the main evaluation.

Recommended command:

```powershell
python evaluation/generate_aqf_schema_graphs.py `
  --data-dir dataset/mixed `
  --results-dir results/journal_locked/main_run `
  --output-dir results/journal_locked/schema_graphs `
  --mu 0.1
```

Expected visual outputs should include:

- canonical schema graph;
- AQF-weighted schema graph;
- selected-field subgraph;
- simplified publication figure with readable labels.

If the script interface differs, inspect `python evaluation/generate_aqf_schema_graphs.py --help` and keep outputs under `results/journal_locked/schema_graphs`.

### Phase 6: Optional Large-Workload Validation

Purpose: show generalization beyond the expert-curated benchmark.

Use the `aqf/` realization pipeline only after the canonical metrics are stable.

Recommended validation:

- Run selected compact AQF forms against `aqf/workload_expansion_v2/benchmark_workload_154.json`.
- Run selected compact AQF forms against `aqf/workload_expansion_v2/synthetic_workload_10000.json`.
- Analyze remaining failures with `aqf/aqf_realization_failure_analyzer.py`.

Report this as supplementary validation, not as the primary evidence, unless the methods are reconciled with `aqf_eval/query_eval.py`.

## Paper Tables

Table 1: Dataset and canonical schema summary.

Source files:

- `dataset_summary.csv`
- `canonical_structure_metrics.csv`

Columns:

- JSON records;
- composition families;
- canonical fields;
- coded/temporal/numeric/boolean fields;
- form groups;
- subgroups;
- max depth;
- context preservation rate.

Table 2: Main method comparison.

Source files:

- `final_aqf_metrics.csv`
- `operator_burden_summary.csv`

Rows:

- `aqf_full`;
- `frequency_only`;
- `flattened_topk`;
- `no_operator_awareness`;
- `no_pruning`;
- random top-k mean and standard deviation across 30 trials.

Columns:

- strict coverage;
- partial coverage;
- field count;
- operator count;
- valid operator count;
- invalid operator count;
- weighted operator burden;
- final complexity.

Table 3: Coverage by query category.

Source file:

- `coverage_by_query_category.csv`

Columns:

- category;
- query count;
- strict coverage;
- partial coverage;
- dominant failure reason.

Table 4: Ablation and efficiency summary.

Source files:

- `relative_ablation_summary.csv`
- `final_metrics_enhanced.csv`, if generated.

Columns:

- coverage delta versus AQF;
- field efficiency;
- operator efficiency;
- complexity efficiency;
- redundancy ratio.

Table 5: Parameter sensitivity.

Source files:

- `journal_all_results.csv`
- `journal_best_by_method.csv`
- `journal_average_by_method.csv`
- `pareto_frontier.csv`

Columns:

- complexity budget;
- theta;
- lambda;
- mu;
- eta;
- strict coverage;
- final complexity;
- operator burden;
- Pareto optimal flag.

## Paper Figures

Figure 1: AQF pipeline overview.

Use a hand-drawn or publication diagram showing:

```text
records -> canonical forest -> queriability scoring -> complexity-bounded form generation -> benchmark query realization -> metrics
```

Figure 2: Canonical schema graph.

Source:

- `results/journal_locked/schema_graphs`.

Figure 3: Coverage versus complexity.

Source:

- `pareto_frontier.csv`;
- `journal_all_results.csv`;
- `advanced_metric_plots/coverage_vs_complexity.png`, if generated.

Figure 4: Operator burden by method.

Source:

- `operator_burden_summary.csv`;
- `journal_plots/operator_burden_by_method.png`, if generated.

Figure 5: Coverage by query category.

Source:

- `coverage_by_query_category.csv`;
- generated category plot.

Figure 6: Random baseline distribution.

Create from `journal_all_results.csv`:

- box plot of strict coverage for `random_topk_*`;
- overlay `aqf_full`, `frequency_only`, and `no_pruning`.

## Quality Gates Before Reporting

Before using any result folder in the manuscript:

1. Confirm `run_metadata.json` exists and records parser version, benchmark version, parameters, and cache use.
2. Confirm `field_scores_final.csv` is non-empty.
3. Confirm `operator_burden.csv` is non-empty.
4. Confirm `final_aqf_metrics.csv` has non-zero field counts for generated forms.
5. Confirm `benchmark_coverage_summary.csv` has `workload=ALL` and `difficulty=ALL` rows.
6. Confirm random baselines include all 30 trials.
7. Confirm `no_operator_awareness` has invalid/unwanted operators greater than zero; this supports the operator-awareness ablation.
8. Confirm `flattened_topk` has context preservation near zero while canonical AQF has context preservation near one.
9. Confirm all reported query counts match the intended workload: 42 primary or 48 with cross-composition.
10. Store all final outputs under `results/journal_locked/` and avoid editing them manually.

## Interpretation Of Current Results

Existing usable baseline:

- `results/final_sweep` contains 20 parameter combos and 720 total method/trial rows.
- Existing best non-random methods reach strict coverage about 0.881 on 42 primary queries at complexity 30.
- `no_pruning` reaches about 0.952 strict coverage with higher complexity and operator burden.
- Random baselines vary substantially and usually underperform the best AQF/frequency operating points.

Current caveat:

- The existing `results/aqf_final` folder should be treated as a failed or incomplete run because several key outputs are empty and method metrics report zero selected fields.

## Recommended Main Manuscript Narrative

Frame AQF as a compactness-versus-expressivity method rather than claiming it always maximizes raw coverage. The clean story is:

1. `no_pruning` gives the upper-bound coverage but produces larger forms.
2. `aqf_full` gives a compact, canonical, operator-valid form under an explicit complexity budget.
3. `no_operator_awareness` shows why datatype/operator compatibility matters: similar coverage can come with many invalid or unwanted controls.
4. `flattened_topk` shows that coverage alone does not preserve clinical/schema context.
5. Random top-k shows that compact coverage is not simply a consequence of selecting any fields under budget.

## Final Deliverable Folder

Create this final artifact layout:

```text
results/journal_locked/
  main_run/
  final_sweep/
  cross_composition/
  schema_graphs/
  figures/
  tables/
  manuscript_values.json
```

The `tables/` folder should contain cleaned CSVs ready for paper import. The `figures/` folder should contain high-resolution PNG/PDF figures. The `manuscript_values.json` file should hold the exact headline numbers used in the paper text so the manuscript can be checked against the generated artifacts.
