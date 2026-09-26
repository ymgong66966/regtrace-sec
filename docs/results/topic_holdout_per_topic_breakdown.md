# Topic-Holdout Per-Topic Breakdown

This table breaks down the topic-holdout test set by `issue_category`. The held-out test set includes crypto and non-GAAP cases that are absent from the training issue-category distribution.

| Issue category | Method | N | Accuracy | Macro-F1 | Resolved F1 | Unresolved F1 | Unresolved Precision | Unresolved Recall |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| crypto | MIPROv2 | 28 | 0.679 | 0.675 | 0.640 | 0.710 | 0.917 | 0.579 |
| crypto | GEPA-scalar | 28 | 0.679 | 0.675 | 0.640 | 0.710 | 0.917 | 0.579 |
| crypto | GEPA-full | 28 | **0.750** | **0.721** | 0.632 | **0.811** | 0.833 | **0.789** |
| non_gaap | MIPROv2 | 16 | 0.562 | 0.459 | 0.222 | 0.696 | 1.000 | 0.533 |
| non_gaap | GEPA-scalar | 16 | 0.375 | 0.333 | 0.167 | 0.500 | 1.000 | 0.333 |
| non_gaap | GEPA-full | 16 | **0.812** | **0.644** | **0.400** | **0.889** | 1.000 | **0.800** |
| other | MIPROv2 | 36 | 0.500 | 0.498 | 0.471 | 0.526 | 0.833 | 0.385 |
| other | GEPA-scalar | 36 | 0.472 | 0.472 | 0.486 | 0.457 | 0.889 | 0.308 |
| other | GEPA-full | 36 | **0.694** | **0.663** | **0.560** | **0.766** | **0.857** | **0.692** |
| revenue_recognition | MIPROv2 | 22 | 0.455 | 0.450 | 0.400 | 0.500 | 1.000 | 0.333 |
| revenue_recognition | GEPA-scalar | 22 | 0.500 | 0.491 | 0.421 | 0.560 | 1.000 | 0.389 |
| revenue_recognition | GEPA-full | 22 | **0.864** | **0.818** | **0.727** | **0.909** | 1.000 | **0.833** |
| risk_factor | MIPROv2 | 20 | 0.700 | 0.670 | 0.571 | 0.769 | **0.909** | 0.667 |
| risk_factor | GEPA-scalar | 20 | 0.550 | 0.540 | 0.471 | 0.609 | 0.875 | 0.467 |
| risk_factor | GEPA-full | 20 | **0.850** | **0.785** | **0.667** | **0.903** | 0.875 | **0.933** |
| spac_disclosure | MIPROv2 | 3 | 0.667 | 0.667 | 0.667 | 0.667 | 1.000 | 0.500 |
| spac_disclosure | GEPA-scalar | 3 | 0.667 | 0.667 | 0.667 | 0.667 | 1.000 | 0.500 |
| spac_disclosure | GEPA-full | 3 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

## Interpretation

The cross-topic gain is not driven by one topic. GEPA-full improves over MIPROv2 on every nontrivial held-out issue category in macro-F1 and unresolved F1. The largest gains appear in revenue recognition, non-GAAP, and broad other-disclosure cases, which are exactly the settings where the SEC request often contains multiple named elements and partial disclosure can be misleading.

The SPAC row has only three examples and should not be emphasized.
