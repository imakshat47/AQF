# AQF Schema Graph Generation Patch v2 — Organic Layout + Weighted Labels

This replaces `evaluation/generate_aqf_schema_graphs.py` with a visual version closer to the AQF paper-style schema graph diagram.

## Changes from v1

- Root node label changed from `Canonical EHR Schema` to **`EHR Schema`**.
- PNG layout changed from rigid multipartite layout to **organic radial parent expansion**.
- Child nodes expand outward from each parent node in angular sectors.
- Weighted schema graph PNG now displays field weights directly on field nodes:

```text
field label
w=<aqf_visual_weight>
cov=<coverage>, div=<effective_diversity>
```

- Weighted field-edge labels are shown for top weighted field containment edges.
- Reduced schema graph uses the same organic expansion but only includes AQF-selected fields and their ancestors.

## Usage

```bash
python evaluation/generate_aqf_schema_graphs.py \
  --data-dir orbda_10k/mixed \
  --results-dir results/aqf_final_c35 \
  --out-dir results/aqf_final_c35/schema_graphs \
  --mu 0.25
```

PowerShell:

```powershell
python evaluation/generate_aqf_schema_graphs.py `
  --data-dir orbda_10k/mixed `
  --results-dir results/aqf_final_c35 `
  --out-dir results/aqf_final_c35/schema_graphs `
  --mu 0.25
```

## Outputs

```text
schema_graph.png
weighted_schema_graph.png
reduced_schema_graph.png
schema_graph.graphml
weighted_schema_graph.graphml
reduced_schema_graph.graphml
schema_graph_nodes.csv / edges.csv
weighted_schema_graph_nodes.csv / edges.csv
reduced_schema_graph_nodes.csv / edges.csv
schema_graph_summary.csv
```
