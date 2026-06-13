# AQF Graph Visualization Script

This package adds PNG visualization for AQF schema graph outputs.

## Usage

First generate the AQF graph JSON files:

```bash
python aqf_schema_graph.py --input data --output output --cooccurrence_scope leaf
```

Then visualize the reduced graph:

```bash
python visualize_schema_graph.py \
  --graph_json output/reduced_schema_graph.json \
  --output_png output/reduced_schema_graph.png \
  --edge_mode all \
  --max_nodes 80 \
  --title "AQF Reduced Weighted Schema Graph"
```

For a clean paper figure, containment-only is often better:

```bash
python visualize_schema_graph.py \
  --graph_json output/reduced_schema_graph.json \
  --output_png output/reduced_schema_graph_containment.png \
  --edge_mode containment \
  --max_nodes 100
```

For dense graphs:

```bash
python visualize_schema_graph.py \
  --graph_json output/reduced_schema_graph.json \
  --output_png output/reduced_schema_graph_dense.png \
  --hide_labels \
  --max_nodes 200
```

## Dependency

```bash
pip install matplotlib
```
