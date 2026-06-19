| claim | evidence | aqf_result | comparison | interpretation |
| --- | --- | --- | --- | --- |
| Expressivity | AQF strict coverage | 90.74% | 54 benchmark queries | Shows how many benchmark requests the generated form realizes exactly. |
| Complexity reduction | AQF versus no-pruning | 44 fields, C=50 | no-pruning: 54 fields, C=60 | Shows the expressivity-complexity tradeoff imposed by candidate selection. |
| Operator awareness | Operator burden ablation | 234 operators, 0 invalid | no-operator-awareness: 484 operators, 250 invalid | Shows that operator awareness reduces interaction burden without changing coverage. |
| Ranking quality | AQF versus frequency-only | 90.74% | frequency-only: 88.89% | Shows whether structural queriability improves over simple prevalence ranking. |
| Canonical structure | AQF versus flattened form | 9 groups, 15 subgroups | flattened: 1 group, 1 subgroup | Shows that AQF preserves form context rather than only selecting fields. |
| Workload-independent selection | AQF versus random top-k trials | 90.74% | random mean: 72.04%; max: 87.04% | Shows generated ranking is stronger than arbitrary compact field selection. |
| Generalization across ORBDA categories | Category coverage | 5/6 categories at or above 90% | weakest: treatment_procedure at 37.50% | Shows where AQF generalizes and where limitations remain visible. |
