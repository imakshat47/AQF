| formula | design_intuition | why_not_simpler | evaluation_link |
| --- | --- | --- | --- |
| LU(v) = cov(v) * div(v) | A field is useful only when it is both present and discriminative. | A weighted sum can let high coverage compensate for near-zero diversity, or vice versa. | Supports field ranking and compact form selection. |
| SC(u,v) = lambda*CC(u,v) + (1-lambda)*CO(u,v) | Query usefulness depends on both containment context and empirical co-occurrence. | Structure-only ignores data support; co-occurrence-only can miss clinically meaningful hierarchy. | Supports category-level generalization and canonical context preservation. |
| Q(v) = LU(v) + mu*sum SC(u,v)*LU(u) | Fields embedded near other useful fields are stronger form candidates. | Local scoring alone cannot capture clinically coherent query neighborhoods. | Supports AQF versus frequency-only and random top-k comparisons. |
| C(F) = |E_F| + eta*depth(F) | Usability cost grows with both number of fields and navigational depth. | Field count alone misses the cost of deeply nested form structures. | Supports complexity reduction and pruning ablations. |
