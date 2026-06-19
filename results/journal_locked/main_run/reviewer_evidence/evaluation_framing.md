# Evaluation Framing For Manuscript

The evaluation is organized around explicit research questions rather than a list of raw experiments. RQ1 evaluates expressivity using strict and partial benchmark coverage. RQ2 evaluates complexity reduction using field count and final form complexity. RQ3 evaluates operator-aware form design through an ablation that disables operator compatibility. RQ4 evaluates pruning through the no-pruning upper bound. RQ5 evaluates generalization across ORBDA workload categories.

At the current operating point, AQF realizes 90.74% of 54 benchmark queries with 44 exposed fields and final complexity 50. The no-pruning upper bound realizes 98.15%, but exposes 54 fields with final complexity 60. This directly frames AQF as an expressivity-complexity tradeoff rather than a maximum-coverage system.

Operator awareness should be interpreted as a usability mechanism, not an expressivity mechanism. In the current results, disabling operator awareness preserves strict coverage at 90.74% but increases operator count from 234 to 484 and invalid or unwanted operators from 0 to 250. This supports the claim that operator-aware classification reduces interaction burden without sacrificing query realization.

Random compact selections provide an important reviewer-facing sanity check. Across 30 random top-k trials, mean strict coverage is 72.04%, compared with AQF at 90.74%. This helps show that AQF's compact coverage is not simply due to selecting any similarly sized set of fields.

Category-level coverage should be used to show both generalization and limitations. AQF reaches at least 90% strict coverage in 5 of 6 query categories, while weaker treatment/procedure coverage should be discussed as the main remaining limitation of the current benchmark and candidate-selection setting.
