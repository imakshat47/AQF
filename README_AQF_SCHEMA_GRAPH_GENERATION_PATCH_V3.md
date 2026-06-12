# AQF Schema Graph Generation Patch v3 — Readable PNG + Schema Node Queriability

This patch updates `evaluation/generate_aqf_schema_graphs.py`.

## Changes

- Larger PNG canvas by default: `30 x 22` inches at high DPI.
- Larger text and nodes; configurable with `--font-size`, `--fig-width`, `--fig-height`.
- Root node remains **EHR Schema**.
- Computes queriability for **every schema node**, not only field nodes.
- Field queriability starts from AQF visual field weight.
- Parent schema node queriability is the sum of child queriabilities.
- Each containment edge gets:

```text
relative_queriability = Q(child) / sum(Q(children of parent))
```

- Weighted and reduced graph PNGs show:

```text
Q=<normalized node queriability>
rq=<relative edge queriability>
```

- Edge thickness is proportional to relative queriability.

## Recommended command

```bash
python evaluation/generate_aqf_schema_graphs.py \
  --data-dir orbda_10k/mixed \
  --results-dir results/aqf_final_c35 \
  --out-dir results/aqf_final_c35/schema_graphs \
  --mu 0.25 \
  --fig-width 34 \
  --fig-height 26 \
  --font-size 11 \
  --max-field-labels 140
```

PowerShell:

```powershell
python evaluation/generate_aqf_schema_graphs.py `
  --data-dir orbda_10k/mixed `
  --results-dir results/aqf_final_c35 `
  --out-dir results/aqf_final_c35/schema_graphs `
  --mu 0.25 `
  --fig-width 34 `
  --fig-height 26 `
  --font-size 11 `
  --max-field-labels 140
```
