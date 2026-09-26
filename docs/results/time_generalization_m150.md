# Time-Split Generalization: Train Before 2024, Test on 2024-2025

All methods receive the same test-time context: SEC comment, company response, and raw retrieved amended-filing snippets. The split trains and tunes on 2022-2023 examples and evaluates on later 2024-2025 examples. The test set contains 144 examples from 53 review threads and 51 companies, with 47 resolved and 97 unresolved examples.

| Method | Accuracy | Macro-F1 | Resolved F1 | Unresolved F1 | Unresolved Precision | Unresolved Recall |
|---|---:|---:|---:|---:|---:|---:|
| Baseline prompt | 0.451 | 0.434 | 0.533 | 0.336 | 0.909 | 0.206 |
| MIPROv2 | 0.521 | 0.519 | 0.549 | 0.489 | 0.868 | 0.340 |
| GEPA-scalar | 0.653 | 0.650 | 0.621 | 0.679 | 0.898 | 0.546 |
| GEPA-full | **0.826** | **0.791** | **0.706** | **0.877** | 0.840 | **0.918** |

## Interpretation

This is the strongest current generalization result. GEPA-full improves substantially over GEPA-scalar and MIPROv2 on a temporal holdout, suggesting that full natural-language feedback is not merely fitting the grouped-random split. The learned prompt appears to transfer to later SEC review material by applying evidence-gap rules: check whether the visible amended filing satisfies each material SEC request, treat partial revision as unresolved, and avoid trusting unsupported company revision claims.

## Caveat

The development set in this first time split is small and thread-concentrated, so this table should be presented as temporal generalization evidence, not as the final stability study. A benchmark-level paper should still add grouped cross-validation or multiple temporal splits.
