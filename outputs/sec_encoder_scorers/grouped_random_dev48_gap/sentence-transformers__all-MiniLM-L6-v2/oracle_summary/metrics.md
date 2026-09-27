# Frozen Encoder Evidence Scorer

Split: `data/sec_visible_evidence_benchmark_v2/splits/grouped_random_dev48_gap/fold_0`.
Encoder: `sentence-transformers/all-MiniLM-L6-v2`.
Text mode: `oracle_summary`.
Train/dev/test: 285/48/139.

| Method | Accuracy | Macro-F1 | Resolved F1 | Unresolved F1 | Unresolved Precision | Unresolved Recall |
|---|---:|---:|---:|---:|---:|---:|
| Frozen encoder + logistic head | 0.604 | 0.560 | 0.421 | 0.699 | 0.736 | 0.667 |

This scorer freezes the encoder and trains only a logistic decision head. It is a cheap, non-generative deployment baseline rather than a full reviewer.
