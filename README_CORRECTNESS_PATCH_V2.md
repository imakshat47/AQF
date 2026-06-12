# AQF Correctness Patch v2

This patch replaces the evaluation engine modules with correctness fixes for ORBDA/openEHR JSON parsing and benchmark evaluation.

## What changed

1. **Traversal completeness**
   - Adds traversal of `ACTION.description`, `ism_transition`, and `instruction_details`.
   - This is required for ORBDA `procedure-sus` fields such as `Procedure` and `irradiated area`.

2. **Datatype extraction**
   - Supports `DV_COUNT.magnitude`, `DV_QUANTITY.magnitude`, `DV_PROPORTION`, `DV_BOOLEAN`, `DV_DATE`, `DV_DATE_TIME`, `DV_CODED_TEXT`, `DV_TEXT`, and `NULL_FLAVOUR`.

3. **Mixed datatype aggregation**
   - Canonical fields now preserve `observed_dv_types`, `primary_dv_type`, and `supports_null_flavour`.
   - `NULL_FLAVOUR` no longer erases real date/coded/numeric datatypes.

4. **Operator rules**
   - `DV_CODED_TEXT` now supports `contains` in addition to equality/inclusion operators.
   - Mixed null/date fields receive temporal operators and null predicates.

5. **Hybrid benchmark matching**
   - Adds exact, alias, token-subset, and high-threshold cosine fallback matching.
   - Writes match audit to `field_match_audit.jsonl`.

6. **Caching**
   - Use `--use-cache` to reuse `canonical_forest.json` and `queriability_scores.json` when data fingerprint is unchanged.

7. **Flat run log**
   - Appends high-level metrics to `evaluation_run_log.csv`.

## Install

Copy the `aqf_eval/` and `evaluation/run_evaluation.py` files into the AQF evaluation project, replacing the previous versions.

## Run default corrected evaluation

```bash
python evaluation/run_evaluation.py \
  --data-dir /path/to/orbda_10k/mixed \
  --out-dir results/aqf_eval_corrected \
  --use-cache \
  --kappa 25 \
  --theta 0.10 \
  --alpha 0.70 \
  --beta 0.30 \
  --lamb 0.25
```

## Expected outputs

```text
benchmark_coverage_summary.csv
benchmark_coverage_detail.csv
field_match_audit.jsonl
evaluation_run_log.csv
form_complexity.csv
canonical_metrics.csv
queriability_ranking.csv
runtime.csv
artifacts/canonical_forest.json
artifacts/queriability_scores.json
generated_forms/*/forms.json
```

## Notes

Run once without an existing cache. Subsequent runs with unchanged data and parser version will skip the ~expensive JSON scan.
