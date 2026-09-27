# Frozen Encoder Evidence Scorer

Split: `data/sec_visible_evidence_benchmark_v2/splits/grouped_random_dev48_gap/fold_0`.
Encoder: `sentence-transformers/all-MiniLM-L6-v2`.
Text mode: `evidence_snippets`.
Representation: `separate_match`.
Train/dev/test: 285/48/139.

| Method | Accuracy | Macro-F1 | Resolved F1 | Unresolved F1 | Unresolved Precision | Unresolved Recall |
|---|---:|---:|---:|---:|---:|---:|
| Frozen encoder + logistic head | 0.712 | 0.667 | 0.545 | 0.789 | 0.798 | 0.781 |

This scorer freezes the encoder and trains only a logistic decision head. It is a cheap, non-generative deployment baseline rather than a full reviewer.
