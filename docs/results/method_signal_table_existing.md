# Existing Method Signal Table

These runs were produced on the earlier visible-evidence learning-curve freeze. They should be framed as method evidence, not as the final Benchmark v2 leaderboard.

| Train size | Method | Accuracy | Macro-F1 | Unresolved F1 | Unresolved Recall |
|---:|---|---:|---:|---:|---:|
| 200 | Baseline prompt | 0.466 | 0.431 | 0.291 | 0.170 |
| 200 | MIPROv2 | 0.611 | 0.602 | 0.543 | 0.386 |
| 200 | GEPA-scalar | 0.644 | 0.643 | 0.658 | 0.532 |
| 200 | GEPA-category | 0.493 | 0.474 | 0.373 | 0.234 |
| 200 | GEPA-full | 0.836 | 0.814 | 0.878 | 0.915 |
| 300 | Baseline prompt | 0.452 | 0.412 | 0.259 | 0.149 |
| 300 | MIPROv2 | 0.674 | 0.673 | 0.687 | 0.597 |
| 300 | GEPA-scalar | 0.603 | 0.602 | 0.580 | 0.425 |
| 300 | GEPA-category | 0.657 | 0.656 | 0.675 | 0.553 |
| 300 | GEPA-full | 0.753 | 0.743 | 0.795 | 0.745 |

Interpretation:

- The clearest method result remains the train=300 row: GEPA-full has the best macro-F1 and strongest unresolved detection among prompt-optimization controls.
- This table motivates rerunning a smaller, final Benchmark v2 leaderboard only after the dataset section is frozen.