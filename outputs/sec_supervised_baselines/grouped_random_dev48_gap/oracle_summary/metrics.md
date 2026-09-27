# Supervised Baselines

Split: `data/sec_visible_evidence_benchmark_v2/splits/grouped_random_dev48_gap/fold_0`.
Text mode: `oracle_summary`.
Train/dev/test: 285/48/139.

| Method | Accuracy | Macro-F1 | Resolved F1 | Unresolved F1 | Unresolved Precision | Unresolved Recall |
|---|---:|---:|---:|---:|---:|---:|
| Majority class | 0.691 | 0.409 | 0.000 | 0.817 | 0.691 | 1.000 |
| Random train-prior | 0.532 | 0.469 | 0.286 | 0.652 | 0.670 | 0.635 |
| TF-IDF logistic regression | 0.892 | 0.858 | 0.789 | 0.928 | 0.865 | 1.000 |

The TF-IDF model is tuned on the development set and then refit on train+dev before held-out test evaluation.