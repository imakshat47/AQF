# AQF — Automatic Query Forms for Hierarchical Healthcare Records

AQF is a **structure-aware, schema/content-driven query interface framework** for standardized healthcare data represented as hierarchical JSON records. AQF automatically extracts recurring record structure, ranks useful sections and fields, generates bounded-complexity query forms, compiles completed form state into AQL, and augments the querying process with explainability artifacts such as structure summaries, plain-English query descriptions, touched-path lineage, and query funnels.

---

## 1. Why AQF exists

Complex healthcare records are rich in information but hard to search directly. Important values are often buried inside nested sections and repeated substructures. Typical users should not have to know:

- where a field lives in a complex hierarchy,
- how to write raw query syntax,
- or how to interpret technical paths and backend-specific representations.

AQF addresses this gap by turning recurring record structure into user-friendly forms.

### Design foundations
AQF combines three main ideas:

1. **Canonical form logic** — forms should separate criteria, outputs, and structural context, and should balance expressivity with bounded complexity.
2. **Schema/content-driven generation** — when query logs are unavailable, the interface can still be derived from the structure and content of the data itself.
3. **Structure-aware explainability** — generated forms should not behave like black boxes; users should be able to see what structure was used and what paths a query touched.

---

## 2. Core capabilities

### 2.1 Structure extraction
AQF scans hierarchical healthcare JSON and builds a reusable structure union over recurring record families:

- **major sections** become top-level form groups,
- **nested subgroup paths** become subgroups,
- **leaf elements** become candidate fields.

### 2.2 Queriability-driven ranking
AQF does not rely on a historical query workload in the cold-start stage. Instead, it estimates field usefulness from the data itself:

- section coverage,
- subgroup richness,
- field coverage,
- value diversity,
- known vs unknown prevalence,
- operator suitability for selection, projection, and ordering.

### 2.3 Automatic form generation
AQF generates forms organized into:

- **Criteria** — filtering conditions
- **Output** — returned fields
- **Advanced** — sorting and execution controls

The interface uses progressive disclosure so that users are not overwhelmed by the full structure at once.

### 2.4 Query generation and execution
AQF translates filled form state into:

1. an internal query plan,
2. then into executable **AQL**,
3. and finally into runtime results and explainability artifacts.

### 2.5 Explainability
AQF adds multiple trust-building layers:

- **Structure overview** — what the generated form was built from
- **Touched-path lineage** — what parts of the structure the query used
- **Plain-English query summary** — what the query means in simple language
- **Query funnel** — how many records were scanned and matched

---

## 3. AQF architecture

![AQF Architecture](aqf_architecture_diagram.png)

### 3.1 User interaction layer
The AQF UI is implemented in Streamlit and is designed around four user-facing panes:

- **Criteria**
- **Output**
- **Advanced**
- **Results**

The UI also includes:

- cache-first startup,
- explicit schema refresh,
- reset actions,
- status messaging,
- field search,
- and results transparency.

### 3.2 Structure extraction layer
This layer reads hierarchical record files and derives:

- record families,
- major sections,
- subgroup paths,
- leaf fields.

It also normalizes common issues such as:

- repeated low-level identifiers,
- sparse sections,
- optional paths,
- explicit unknown/null-like values,
- and list/object layout variations.

### 3.3 Queriability and field catalog layer
This layer computes the signals that determine which parts of the record should be exposed prominently in the generated forms.

Outputs include:

- section scores,
- subgroup scores,
- operator-specific field scores,
- default role selection,
- and value suggestions.

### 3.4 Form composition layer
This layer converts ranked structure into a bounded-complexity form specification.

It determines:

- which sections are visible by default,
- which subgroups are exposed,
- which fields appear in Criteria, Output, and Advanced,
- and how progressive disclosure is applied.

### 3.5 Query generation layer
This layer maps visible user interaction into executable query logic.

Pipeline:

- form state → query plan
- query plan → AQL
- AQL / runtime execution → result rows + metrics

### 3.6 Explainability and evaluation layer
This layer produces:

- structure diagrams,
- touched-path lineage,
- plain-English summaries,
- query funnels,
- threshold sweep results,
- heatmaps,
- ablations,
- execution metrics,
- and comparison matrices.

---

## 4. Repository / module overview

A typical AQF repository contains the following modules.

### Runtime / app modules
- `app.py` — Streamlit application
- `composition_loader.py` — loads and groups record files by family
- `schema_union_builder.py` — builds reusable structure union
- `field_catalog.py` — extracts normalized field catalog
- `form_definition_builder.py` — creates form-ready structure
- `query_compiler.py` — compiles form state into internal query plan / AQL mapping
- `query_executor.py` — executes the compiled query over benchmark data slices
- `result_formatter.py` — turns raw rows into readable display tables
- `schema_diagram.py` — structure overview and touched-path diagrams
- `query_summary.py` — plain-English query summary

### Results / evaluation modules
- `aqf_results.py` — computes structural metrics, queriability, threshold sweeps, ablations, matrices
- `generate_results.py` — batch result package generation
- `generate_execution_metrics.py` — benchmark execution metrics generation
- `render_threshold_figure.py` — threshold sweep figure
- `render_heatmap.py` — queriability heatmap
- `render_ablation_figure.py` — ablation figure
- `render_execution_figure.py` — execution summary figure
- `make_query_cases_30.py` — 30-query benchmark pack generation

### Cached artifacts
AQF stores reusable artifacts under `.cache/` such as:

- `schema_union.json`
- `fields.json`
- `schema_metadata.json`
- optional value suggestion cache

### Result package artifacts
AQF result generation writes into a package-like structure such as:

- `derived_metrics/`
- `qualitative_tables/`
- `figures/`
- `paper_assets/`

---

## 5. AQF data flow

### Phase A — Structure preparation
This is the expensive but reusable phase:

1. read hierarchical record files,
2. group them into recurring record families,
3. build structure union,
4. compute field catalog,
5. compute queriability,
6. build form definition,
7. cache the artifacts.

### Phase B — Interactive querying
This is the user-facing phase:

1. load cached form definition,
2. user edits criteria / outputs / advanced settings,
3. AQF compiles the form into a query plan,
4. AQF executes the query,
5. AQF renders results + explainability artifacts.

This separation keeps the application responsive and avoids rebuilding structure repeatedly.

---

## 6. Queriability model

AQF uses a schema/content-driven queriability model.

### 6.1 Section queriability
Signals typically include:

- section coverage,
- structural connectedness,
- descendant knownness.

### 6.2 Subgroup queriability
Signals typically include:

- subgroup coverage,
- subgroup richness,
- subgroup knownness.

### 6.3 Field queriability
AQF computes operator-specific scores for:

- **Selection**
- **Projection**
- **Ordering**

Typical field-level signals include:

- coverage,
- entropy / diversity,
- knownness,
- sortability.

---

## 7. Thresholding and bounded complexity

AQF does not expose all extracted fields at once.

It controls visible complexity using:

- visible section thresholds,
- visible field thresholds,
- progressive disclosure,
- bounded suggestion lists,
- and role-specific filtering.

A simple complexity proxy typically combines:

- number of visible fields,
- number of subgroup headings,
- number of major section groups.

This allows AQF to balance:

- **expressivity** — how much useful structure is queryable,
- **complexity** — how much the user sees at once.

---

## 8. Results package and evaluation outputs

AQF evaluation typically includes:

### Quantitative artifacts
- structure metrics
- queriability tables
- threshold sweeps
- ablation studies
- execution metrics

### Qualitative / structured artifacts
- related work matrix
- AQF metric matrix
- baseline-vs-AQF matrix
- operator suitability matrix

### Hero figures
- architecture / pipeline figure
- threshold sweep figure
- queriability heatmap
- ablation figure
- execution summary figure

---

## 9. Benchmark query pack

AQF benchmark execution can be driven from `query_cases.json` files.

The current recommended benchmark set contains **30 queries** divided into:

- **10 simple queries**
- **10 medium queries**
- **10 harder / specialized queries**

This split supports:

- quick sanity checks,
- realistic multi-condition form use,
- harder structure-aware stress tests.

---

## 10. How to run AQF

### 10.1 Start the app
```bash
streamlit run app.py
```

### 10.2 Build / refresh schema
In the app:

1. enter dataset folder,
2. click **Build / Refresh Schema**,
3. or reuse cached artifacts if already present.

### 10.3 Run benchmark results package
```bash
python generate_results.py --cache_dir .cache --out_dir results_package
```

### 10.4 Generate benchmark execution metrics
```bash
python generate_execution_metrics.py   --dataset_folder data   --composition_archetype "openEHR-EHR-COMPOSITION.outpatient_high_complexity_procedures.v1"   --query_cases query_cases_30.json
```

### 10.5 Render evaluation figures
```bash
python render_threshold_figure.py
python render_heatmap.py
python render_ablation_figure.py
python render_execution_figure.py
```

---

## 11. Output files you should expect

### Cached structural artifacts
- `.cache/schema_union.json`
- `.cache/fields.json`
- `.cache/schema_metadata.json`

### Derived metrics
- `results_package/derived_metrics/structure_metrics.csv`
- `results_package/derived_metrics/queriability_sections.csv`
- `results_package/derived_metrics/queriability_subgroups.csv`
- `results_package/derived_metrics/queriability_fields.csv`
- `results_package/derived_metrics/threshold_sweep.csv`
- `results_package/derived_metrics/ablation_results.csv`
- `results_package/derived_metrics/execution_metrics.csv`

### Figures
- `results_package/figures/fig_threshold_sweep.png`
- `results_package/figures/fig_queriability_heatmap.png`
- `results_package/figures/fig_ablation.png`
- `results_package/figures/fig_execution_summary.png`

### Qualitative tables
- `results_package/qualitative_tables/related_work_matrix.csv`
- `results_package/qualitative_tables/aqf_metric_matrix.csv`
- `results_package/qualitative_tables/baseline_vs_aqf_matrix.csv`
- `results_package/qualitative_tables/operator_suitability_matrix.csv`

---

## 12. How to interpret the core outputs

### Threshold sweep
Shows how AQF balances:
- form size,
- structural expressivity,
- coverage,
- and visible complexity.

### Queriability heatmap
Shows which fields are most suitable for:
- filtering,
- display,
- sorting.

### Ablation figure
Shows which AQF components matter most, such as:
- operator-specific scoring,
- missingness handling,
- progressive disclosure,
- structure awareness.

### Execution summary
Shows objective runtime behavior:
- compile time,
- execution time,
- scanned vs matched records,
- interaction count.

---

## 13. Explainability outputs

AQF explainability should be treated as part of the system, not as decoration.

Typical outputs include:

- **structure overview** — how the form was built
- **touched-path lineage** — what the query used
- **plain-English summary** — what the query means
- **query funnel** — how records were narrowed down

These make generated forms easier to trust and validate.

---

## 14. Limitations and next steps

The current AQF implementation is already suitable for:

- structure-aware form generation,
- cold-start query interface creation,
- explainable querying,
- reproducible result generation.

However, future work should continue on:

- broader record-family coverage,
- richer AQL operator support,
- workload-aware refinement once real logs exist,
- stronger user studies,
- improved structure-aware selection strategies.

---

## 15. Suggested paper appendices

A complete AQF paper can include appendices for:

- datasets and query sets,
- structure extraction and field catalog details,
- queriability and thresholding formulation,
- additional evaluation figures and tables,
- AQL compilation examples,
- explainability artifacts,
- reproducibility details,
- limitations and threats to validity.

---

## 16. Summary

AQF is a framework that turns complex hierarchical healthcare records into readable, executable, and explainable query forms.

It does this by combining:

- structure extraction,
- schema/content-driven ranking,
- bounded-complexity form generation,
- AQL compilation,
- and transparent result explanation.

AQF is therefore not just a UI generator. It is a full, structure-aware query interface pipeline.
