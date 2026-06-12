# ACF Evaluation — Paper Formula Implementation for Standardized EHR Repositories

This patch creates a separate `acf_eval` implementation based on the attached paper:

**Automated Creation of a Forms-based Database Query Interface** by Jayapandian and Jagadish.

It is intentionally separate from `aqf_eval` so that AQF and ACF can be compared cleanly.

## Implemented paper formulas

- Formula 1: Relative cardinality
- Formula 2: Iterative entity importance and entity queriability
- Formula 3: Related-entity queriability for binary relationships
- Formula 4: Attribute necessity and attribute queriability
- Formula 5: Operator-specific attribute queriability
- Formula 6: Selection-attribute queriability
- Formula 7: Projection-attribute queriability
- Formula 8: Sort-attribute queriability
- Formula 9: Aggregation-attribute queriability
- Algorithm 3 style entity/attribute/related-entity thresholding
- Algorithm 4 style operator-specific pruning

## EHR mapping

The original paper uses entities, attributes, and relationships. For standardized EHR repositories:

```text
Composition / form group / subgroup -> entity-like node
Canonical leaf element              -> attribute node
Containment path                    -> schema link
Observed field coverage             -> absolute/link cardinality proxy
Shared context/co-presence          -> related entity participation proxy
```

## Single run

```bash
python evaluation/run_acf_evaluation.py \
  --data-dir orbda_10k/mixed \
  --out-dir results/acf_eval_default \
  --use-cache \
  --k-e 5 \
  --k-a 10 \
  --k-r 1 \
  --k-sigma 6 \
  --k-pi 6 \
  --k-tau 3 \
  --k-gamma 2 \
  --field-complexity 30 \
  --p 0.15 \
  --random-trials 30
```

## Postulate ablations

Disable individual postulates using flags:

```bash
--no-p1   # disable schema connectedness propagation
--no-p2   # disable data-cardinality initialization
--no-p3   # disable individual entity queriability in related entity scores
--no-p4   # disable relationship participation/cardinality in related entity scores
--no-p5   # disable attribute necessity
--no-p6   # disable selection selectivity
--no-p7   # disable projection size
--no-p8   # disable sort mandatory/single-valued indicator
--no-p9   # disable aggregation numeric/repeatable indicator
```

## Sweep

```bash
python evaluation/run_acf_parameter_sweep.py \
  --data-dir orbda_10k/mixed \
  --out-dir results/acf_sweep \
  --use-cache \
  --k-es 3,5,8,10 \
  --k-as 5,7,10,12 \
  --k-rs 0,1,2 \
  --field-complexities 20,25,30,35,40 \
  --ps 0.15,0.30,0.50 \
  --random-trials 30
```

## Outputs

```text
acf_entity_scores.csv
acf_attribute_operator_scores.csv
acf_related_entity_scores.csv
benchmark_coverage_summary.csv
benchmark_coverage_detail.csv
final_acf_metrics.csv
relative_ablation_summary.csv
operator_burden.csv
operator_burden_summary.csv
canonical_structure_metrics.csv
coverage_by_query_category.csv
generated_forms/*/forms.json
field_match_audit.jsonl
```

## Expected use

Use this to answer whether paper-derived ACF formulas create different field selections and baseline distinctions on ORBDA. Compare:

```text
acf_full vs frequency_only
acf_full vs necessity_only
acf_full vs selection_only
acf_full vs no_operator_specific
acf_full vs random_entities
acf_full vs no_pruning
```

If `acf_full` and `frequency_only` still tie, the dataset's top-ranked useful fields are genuinely coverage-dominated under the paper formulas. If they diverge, ACF demonstrates formula-driven selection effects.
