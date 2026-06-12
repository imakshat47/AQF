# AQF Correctness Patch v2.1 — Matcher + Baseline Separation

This patch is applied on top of `aqf_correctness_patch_v2`.

## Fixes

1. **Matcher v2.1**
   - Normalized alias map for `invaded regional lymph nodes` ↔ `Invaded regional linphonodes`.
   - Safer matching: parent/context terms like `Problem`, `Diagnosis`, `structure`, and `components` cannot win over leaf matches.
   - Context guards prevent radiotherapy/chemotherapy cross-matching.
   - Output/sort components reuse resolved filter matches for the same field.

2. **Baseline separation**
   - `no_pruning` is now a true no-pruning baseline: all canonical fields, no kappa cap.
   - Adds `aqf_topk_no_threshold` as the previous top-k/no-threshold ablation.
   - `flattened_topk` remains flat and frequency-oriented.
   - `frequency_only` remains canonical but ignores AQF scoring components.

3. **Selection audit**
   - Adds `field_selection_audit.csv` to show rank, score, coverage, selected_by_method, and benchmark relevance.

## Run

```bash
python evaluation/run_evaluation.py \
  --data-dir /path/to/orbda_10k/mixed \
  --out-dir results/aqf_eval_v2_1_k30 \
  --use-cache \
  --kappa 30 \
  --theta 0.10 \
  --alpha 0.70 \
  --beta 0.30 \
  --lamb 0.25
```

## Expected impact

- Q10/Q19/Q26 should be fixed by matching `invaded regional lymph nodes` to `Invaded regional linphonodes`.
- At kappa=30, strict coverage is expected to rise from 36/42 to approximately 39/42 if Q21-Q23 remain sparse-domain failures.
- `no_pruning` should now separate from AQF-full by field count, complexity, and possibly coverage.
