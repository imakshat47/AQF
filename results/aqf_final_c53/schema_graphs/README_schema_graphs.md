# AQF Schema Graph Artifacts

This version computes cartesian-product queriability across all node pairs.
The root node `EHR Schema` is anchored at CQ=1.000. All other nodes are normalized below 1.000.

Node labels:
- `CQ`: full cartesian-product queriability adjusted against all nodes.
- `UQ`: upward containment queriability.
- `w`: initial AQF field weight for field nodes.

Edge labels:
- `rq`: relative child contribution to the parent based on CQ.

Pairwise influence CSVs:
- `weighted_schema_graph_pairwise_cartesian_queriability.csv`
- `reduced_schema_graph_pairwise_cartesian_queriability.csv`

Selected fields source: `results\aqf_final_c53\generated_forms\aqf_full\forms.json`