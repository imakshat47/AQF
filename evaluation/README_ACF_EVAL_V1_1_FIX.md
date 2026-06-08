# ACF Evaluation v1.1 Fix

This patch fixes the most likely runtime failure in v1: JSON serialization/cache of tuple keys in `related_entity_scores`.

## What changed

- `related_entity_scores` now uses string keys: `entity1|||entity2`.
- `form_generation.py` accepts both old tuple/list keys and new string keys.
- Cache key prefix changed to `v1_1_` so stale v1 cache files are not reused.
- `run_acf_evaluation.py` now prints the full traceback if a new error occurs.
- `no_pruning` is now a true all-field upper bound.

## Run

```bash
python evaluation/run_acf_evaluation.py \
  --data-dir orbda_10k/mixed \
  --out-dir results/acf_eval_default \
  --use-cache \
  --k-e 5 \
  --k-a 10 \
  --k-r 1 \
  --k-sigma 6 \
  --k-pi 6 \
  --k-tau 3 \
  --k-gamma 2 \
  --field-complexity 30 \
  --p 0.15 \
  --random-trials 30
```

If the previous v1 run created a bad cache, either keep this v1.1 patch's new cache key or delete:

```text
results/acf_eval_default/.cache/acf_scores/
```
