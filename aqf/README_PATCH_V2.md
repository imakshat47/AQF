# Patch v2: Readable Organic AQF Graph Visualization

This patch updates `visualize_all_aqf_graphs.py` with:

1. **Edge weight labels** on the strongest edges.
2. **Thicker weighted edges** so graph complexity is visually clearer.
3. **Dynamic larger node sizes** using configurable `--min_node_size` and `--max_node_size`.
4. **Readable paper fonts** with default node labels around 16 pt and subtitle around 16 pt.
5. **White label backgrounds** for readability over dense graphs.

## Apply patch

From the folder containing `visualize_all_aqf_graphs.py`:

```bash
patch visualize_all_aqf_graphs.py < aqf_visualization_readability_v2.patch
```

If you are on Windows and do not have `patch`, open the patch file and manually copy the changed blocks, or use Git Bash:

```bash
git apply aqf_visualization_readability_v2.patch
```

## Run with edge weights and 16/18 pt labels

```bash
python visualize_all_aqf_graphs.py \
  --input_dir output \
  --output_dir output/figures_readable \
  --max_nodes 120 \
  --edge_mode all \
  --show_edge_weights \
  --node_font_size 16 \
  --edge_font_size 14 \
  --title_font_size 22 \
  --subtitle_font_size 16 \
  --legend_font_size 14 \
  --min_node_size 750 \
  --max_node_size 6000
```

## Cleaner paper figure

```bash
python visualize_all_aqf_graphs.py \
  --input_dir output \
  --output_dir output/figures_readable_containment \
  --edge_mode containment \
  --max_nodes 120 \
  --show_edge_weights \
  --node_font_size 16 \
  --edge_font_size 14
```

## Dense complexity figure

```bash
python visualize_all_aqf_graphs.py \
  --input_dir output \
  --output_dir output/figures_complexity \
  --edge_mode all \
  --hide_labels \
  --show_edge_weights \
  --max_nodes 250
```
