# Final Benchmark v2 Leaderboard

Split: `grouped_random_dev48_gap/fold_0`. Train/dev/test sizes are 285/48/139 examples, grouped by SEC review thread. All methods receive the same test-time inputs: SEC comment, company response, and raw retrieved amended-filing snippets. The held-out test set contains 43 resolved and 96 unresolved examples.

| Method | Accuracy | Macro-F1 | Resolved F1 | Unresolved F1 | Unresolved Precision | Unresolved Recall |
|---|---:|---:|---:|---:|---:|---:|
| Baseline prompt | 0.424 | 0.402 | 0.518 | 0.286 | 1.000 | 0.167 |
| MIPROv2 | 0.655 | 0.652 | 0.619 | 0.684 | 0.929 | 0.542 |
| GEPA-scalar | 0.705 | 0.675 | 0.577 | 0.773 | 0.824 | 0.729 |
| GEPA-category | 0.597 | 0.595 | 0.562 | 0.627 | 0.870 | 0.490 |
| GEPA-full | 0.784 | 0.756 | 0.674 | 0.839 | 0.867 | 0.812 |

Key comparison: GEPA-full is the strongest method on the frozen Benchmark v2 leaderboard, improving macro-F1 by 10.5 points over MIPROv2 and 8.1 points over GEPA-scalar. On the operationally important unresolved class, GEPA-full reaches 0.839 F1 and 0.813 recall.

Notes:

- `Baseline prompt`: Handwritten prompt; raw amended snippets at test time. Source: `outputs/sec_visible_evidence_benchmark_v2/final_leaderboard_dev48_gap_m150/fold_0_basic_mipro_t8/result.json`.
- `MIPROv2`: Scalar prompt optimization. Source: `outputs/sec_visible_evidence_benchmark_v2/final_leaderboard_dev48_gap_m150/fold_0_basic_mipro_t8/result.json`.
- `GEPA-scalar`: Reflective optimizer with correctness-only feedback. Source: `outputs/sec_visible_evidence_benchmark_v2/final_leaderboard_dev48_gap_m150/fold_0_basic_scalar_m150/dry_run_result.json`.
- `GEPA-category`: Reflective optimizer with coarse issue/gap category feedback. Source: `outputs/sec_visible_evidence_benchmark_v2/final_leaderboard_dev48_gap_m150/fold_0_basic_category_m150/dry_run_result.json`.
- `GEPA-full`: Reflective optimizer with full adjudicated natural-language feedback. Source: `outputs/sec_visible_evidence_benchmark_v2/final_leaderboard_dev48_gap_m150/fold_0_basic_full_m150/dry_run_result.json`.
