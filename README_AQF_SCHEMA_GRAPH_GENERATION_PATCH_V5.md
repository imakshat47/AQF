# AQF Schema Graph Generation Patch v5 — Full Cartesian Queriability

This patch replaces `evaluation/generate_aqf_schema_graphs.py`.

## What changed from v4

- Computes **full cartesian-product queriability** across all node pairs.
- Every node is adjusted against every other node in the schema graph.
- The central root node **EHR Schema** is anchored to `CQ=1.000`.
- All other nodes are normalized below `1.000`.
- Pairwise source-target influences are exported to CSV.
- Node sizes are increased again and controlled with `--node-scale`.

## Formula used

For target node `v` and source node `u`:

```text
influence(u -> v) = base_Q(u) * exp(-decay * dist(u,v)) * type_affinity(u,v)
```

Then:

```text
raw_CQ(v) = sum over all u in V influence(u -> v)
CQ(EHR Schema) = 1.000
CQ(v != root) = 0.999 * raw_CQ(v) / max_non_root(raw_CQ)
```

This gives a true all-node Cartesian adjustment while preserving the interpretation that only the central EHR Schema node has queriability equal to one.

## Recommended command

```bash
python evaluation/generate_aqf_schema_graphs.py \
  --data-dir orbda_10k/mixed \
  --results-dir results/aqf_final_c35 \
  --out-dir results/aqf_final_c35/schema_graphs \
  --mu 0.25 \
  --fig-width 48 \
  --fig-height 38 \
  --font-size 15 \
  --max-field-labels 200 \
  --node-scale 2.8
```

PowerShell:

```powershell
python evaluation/generate_aqf_schema_graphs.py `
  --data-dir orbda_10k/mixed `
  --results-dir results/aqf_final_c35 `
  --out-dir results/aqf_final_c35/schema_graphs `
  --mu 0.25 `
  --fig-width 48 `
  --fig-height 38 `
  --font-size 15 `
  --max-field-labels 200 `
  --node-scale 2.8
```
