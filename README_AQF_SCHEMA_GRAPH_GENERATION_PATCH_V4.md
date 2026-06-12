# AQF Schema Graph Generation Patch v4 — Larger Nodes + Global Queriability

This patch updates `evaluation/generate_aqf_schema_graphs.py`.

## Changes

- Node size increased substantially by default.
- New `--node-scale` parameter controls node size globally.
- Larger default canvas: `40 x 30` inches.
- Larger default font: `13`.
- Computes two queriability scores for every node:
  - `UQ`: upward/containment queriability from field leaves to ancestors.
  - `GQ`: global queriability using PageRank-like propagation over all schema nodes, including far-away nodes.
- Containment edges have `relative_queriability` (`rq`) and edge thickness proportional to `rq`.

## Recommended command

```bash
python evaluation/generate_aqf_schema_graphs.py \
  --data-dir orbda_10k/mixed \
  --results-dir results/aqf_final_c35 \
  --out-dir results/aqf_final_c35/schema_graphs \
  --mu 0.25 \
  --fig-width 44 \
  --fig-height 34 \
  --font-size 14 \
  --max-field-labels 180 \
  --node-scale 2.2
```

PowerShell:

```powershell
python evaluation/generate_aqf_schema_graphs.py `
  --data-dir orbda_10k/mixed `
  --results-dir results/aqf_final_c35 `
  --out-dir results/aqf_final_c35/schema_graphs `
  --mu 0.25 `
  --fig-width 44 `
  --fig-height 34 `
  --font-size 14 `
  --max-field-labels 180 `
  --node-scale 2.2
```
