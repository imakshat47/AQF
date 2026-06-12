# AQF Schema Graph Generation Patch

This patch adds:

```text
evaluation/generate_aqf_schema_graphs.py
```

It generates three graph views:

1. **Schema Graph** — full canonical EHR schema/context graph.
2. **Weighted Schema Graph** — schema graph annotated with coverage, effective diversity, AQF visual weight, operator count, and weighted operator burden.
3. **Reduced Schema Graph** — complexity-bounded AQF selected interface graph, based on `generated_forms/aqf_full/forms.json` if available.

## Recommended usage

```bash
python evaluation/generate_aqf_schema_graphs.py \
  --data-dir orbda_10k/mixed \
  --results-dir results/aqf_final_c35 \
  --out-dir results/aqf_final_c35/schema_graphs \
  --mu 0.25
```

## Usage with cached canonical forest

```bash
python evaluation/generate_aqf_schema_graphs.py \
  --canonical-forest results/aqf_final_c35/.cache/canonical_forest.json \
  --forms-json results/aqf_final_c35/generated_forms/aqf_full/forms.json \
  --out-dir results/aqf_final_c35/schema_graphs
```

## Outputs

For each graph:

```text
*.json
*.graphml
*.dot
*_nodes.csv
*_edges.csv
*.png
```

Also:

```text
schema_graph_summary.csv
README_schema_graphs.md
```
