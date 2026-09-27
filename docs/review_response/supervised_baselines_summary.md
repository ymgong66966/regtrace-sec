# Non-Prompt Supervised Baselines

Split: `grouped_random_dev48_gap/fold_0`. Train/dev/test sizes are 285/48/139 examples, grouped by SEC review thread. The held-out test set has 43 resolved and 96 unresolved examples.

| Method | Input | Accuracy | Macro-F1 | Resolved F1 | Unresolved F1 | Note |
|---|---|---:|---:|---:|---:|---|
| Majority class | label prior only | 0.691 | 0.409 | 0.000 | 0.817 | Always predicts unresolved |
| Random train-prior | label prior only | 0.532 | 0.469 | 0.286 | 0.652 | Seed 17 |
| TF-IDF logistic regression | SEC comment + company response | 0.655 | 0.523 | 0.273 | 0.774 | Tuned on dev, refit on train+dev |
| TF-IDF logistic regression | + raw amended-filing snippets | 0.669 | 0.523 | 0.258 | 0.787 | Same raw evidence as prompt methods |
| TF-IDF logistic regression | + oracle evidence summary | 0.892 | 0.858 | 0.789 | 0.928 | Diagnostic upper-bound setting |

Takeaway: a lightweight supervised lexical classifier does not explain the GEPA-full result under the same raw-evidence input. Its strong oracle-summary score shows that the benchmark is learnable when evidence interpretation has already been distilled, reinforcing the paper's claim that the hard part is obligation-level evidence reading rather than label memorization.
