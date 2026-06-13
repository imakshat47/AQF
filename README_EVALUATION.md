# AQF Evaluation Engine

This package adds a standalone, reproducible evaluation pipeline for AQF.

It is designed to support the AQF paper's experimental claims:

- composition-agnostic repository analysis,
- canonical tree construction,
- queriability-guided field selection,
- bounded-complexity adaptive form generation,
- baseline comparison,
- Easy/Medium/Hard benchmark query coverage,
- query realization readiness.

## Files

```text
aqf_eval/
  openehr_utils.py        Generic openEHR JSON scanning and ELEMENT extraction
  canonical.py            Canonical forest/tree construction
  queriability.py         Paper-inspired queriability scoring
  form_generation.py      AQF and baseline form generation
  query_eval.py           Benchmark query expressivity evaluator
  metrics.py              Coverage, complexity, canonical metrics
  reporting.py            CSV/JSON/plot writers

evaluation/
  run_evaluation.py       Main CLI runner
  benchmarks/*.json       Expert-curated benchmark queries
  configs/eval_default.json
```

## Run

From the extracted package root:

```bash
python evaluation/run_evaluation.py --data-dir /path/to/ehr/json/folder --out-dir results/aqf_eval
```

Include cross-composition challenge queries:

```bash
python evaluation/run_evaluation.py --data-dir /path/to/ehr/json/folder --out-dir results/aqf_eval_cross --include-cross
```

## Outputs

```text
results/aqf_eval/
  dataset_summary.csv
  benchmark_coverage_detail.csv
  benchmark_coverage_summary.csv
  queriability_ranking.csv
  form_complexity.csv
  canonical_metrics.csv
  runtime.csv
  artifacts/canonical_forest.json
  artifacts/queriability_scores.json
  generated_forms/*/forms.json
  figures/coverage_by_method.png
```

## Interpretation

- `benchmark_coverage_summary.csv` is the main expressivity table.
- `queriability_ranking.csv` supports H1: queriability ranking validity.
- `form_complexity.csv` supports bounded-complexity evaluation.
- `canonical_metrics.csv` supports canonical composition benefit.
- `runtime.csv` supports scalability/practicality.

## Important limitation

This evaluation engine measures benchmark query **expressibility** and generated form support. It does not claim native AQL execution unless you add and validate an AQL renderer/backend. If your current AQF executes internal JSON query plans, report that as logical AQF query realization, not full AQL execution.
