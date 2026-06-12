# AQF Reverse Sweep + 154 Semi-curated Workload

This update implements your faster strategy:

1. Increase semi-curated workload to **154 queries**.
2. Start from a high-coverage AQF configuration and **sweep downward**.
3. Stop when realization lands near **92–94%**.
4. Use the selected compact configuration for journal curves and validation.

## Files

```text
aqf_reverse_evaluation_sweep.py
aqf_workload_expander_v2.py
aqf_reverse_sweep_plotter.py
README.md
requirements.txt
```

## 1. Generate 154-query semi-curated workload

```bat
python aqf_workload_expander_v2.py ^
  --base_workload_json aqf_benchmark_workload.json ^
  --output_dir output_best/workloads_v2 ^
  --curated_count 154 ^
  --synthetic_count 10000 ^
  --seed 42
```

Outputs:

```text
output_best/workloads_v2/benchmark_workload_154.json
output_best/workloads_v2/synthetic_workload_10000.json
output_best/workloads_v2/workload_generation_summary.csv
```

## 2. Run fast reverse sweep toward 92–94%

```bat
python aqf_reverse_evaluation_sweep.py ^
  --canonical_forms_json output_best/canonical_demographic/canonical_forms.json ^
  --clinical_graph_json output_best/reduced_schema_graph.json ^
  --workload_json output_best/workloads_v2/benchmark_workload_154.json ^
  --aliases_json field_aliases.json ^
  --operator_mapping_json orbda_operator_mapping.json ^
  --output_root output_best/reverse_sweep_154 ^
  --target_min 0.92 ^
  --target_max 0.94 ^
  --top_k_values 30,25,22,20,18,16,14,12,10,8 ^
  --target_total_fields_values 35,32,30,28,26,24,22,20,18,16,14,12 ^
  --kappa_values 40,36,34,32,30,28,26,24,22,20,18,16 ^
  --max_filters_values 25,22,20,18,16,14,12,10,8 ^
  --max_outputs_values 15,12,10,8,6,4 ^
  --fast_mode ^
  --stop_on_first_hit
```

## 3. Plot reverse sweep curve

```bat
python aqf_reverse_sweep_plotter.py ^
  --reverse_sweep_results_csv output_best/reverse_sweep_154/reverse_sweep_results.csv ^
  --output_dir output_best/reverse_sweep_154/plots ^
  --target_min 0.92 ^
  --target_max 0.94
```

## 4. Validate compact best run on expert 20-query workload

```bat
python aqf_query_realizer_v3_multiform.py ^
  --aqf_forms_json output_best/reverse_sweep_154/best_run/aqf_forms_repaired/aqf_forms.json ^
  --workload_json aqf_benchmark_workload.json ^
  --aliases_json field_aliases.json ^
  --operator_mapping_json orbda_operator_mapping.json ^
  --output_dir output_best/reverse_sweep_154/best_run/eval_20
```

## 5. Validate compact best run on 10,000-query workload

```bat
python aqf_query_realizer_v3_multiform.py ^
  --aqf_forms_json output_best/reverse_sweep_154/best_run/aqf_forms_repaired/aqf_forms.json ^
  --workload_json output_best/workloads_v2/synthetic_workload_10000.json ^
  --aliases_json field_aliases.json ^
  --operator_mapping_json orbda_operator_mapping.json ^
  --output_dir output_best/reverse_sweep_154/best_run/eval_10000
```

## 6. Analyze remaining failures

```bat
python aqf_realization_failure_analyzer.py ^
  --realized_queries_csv output_best/reverse_sweep_154/best_run/eval_10000/realized_queries.csv ^
  --output_dir output_best/reverse_sweep_154/best_run/eval_10000/failure_analysis
```

## Output files

```text
output_best/reverse_sweep_154/reverse_sweep_results.csv
output_best/reverse_sweep_154/best_result.json
output_best/reverse_sweep_154/best_run/
output_best/reverse_sweep_154/plots/
```
