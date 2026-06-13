# AQF Organic Graph Visualization Package

This script creates paper-style organic/radial visualizations for all three AQF graph stages:

1. `schema_graph.json`
2. `weighted_schema_graph.json`
3. `reduced_schema_graph.json`

It places composition/section nodes near the center and spreads entries, clusters, item structures, and elements outward.

## Install dependency

```bash
pip install matplotlib
```

## Step 1: Generate AQF graph JSON files

```bash
python aqf_schema_graph.py --input data --output output --cooccurrence_scope leaf
```

## Step 2: Generate all three paper figures

```bash
python visualize_all_aqf_graphs.py \
  --input_dir output \
  --output_dir output/figures \
  --max_nodes 180
```

This creates:

```text
output/figures/01_schema_graph_organic.png
output/figures/02_weighted_schema_graph_organic.png
output/figures/03_reduced_schema_graph_organic.png
output/figures/graph_complexity_summary.csv
```

## Cleaner paper version

For a cleaner figure like a structural schema snapshot, use containment-only edges:

```bash
python visualize_all_aqf_graphs.py \
  --input_dir output \
  --output_dir output/figures_containment \
  --edge_mode containment \
  --max_nodes 180
```

## Dense graph version

```bash
python visualize_all_aqf_graphs.py \
  --input_dir output \
  --output_dir output/figures_dense \
  --edge_mode all \
  --hide_labels \
  --max_nodes 300
```

## Notes

- Node color indicates AQF node type:
  - blue: composition / section
  - orange: entry / cluster / item structure
  - green: element / leaf
- Node size indicates queriability where available.
- Edge width indicates structural connectivity where available.
- Schema graph figure emphasizes high structural complexity.
- Weighted schema graph figure emphasizes queriability and connectivity overhead.
- Reduced schema graph figure emphasizes selected query-relevant candidate regions.
