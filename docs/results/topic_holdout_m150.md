# Topic-Holdout Generalization

All methods receive the same test-time context: SEC comment, company response, and raw retrieved amended-filing snippets. The topic-holdout split evaluates cross-topic transfer, with held-out test examples including crypto and non-GAAP cases that are absent from the training issue-category distribution. The test set contains 125 examples from 30 review threads and 28 companies, with 30 resolved and 95 unresolved examples.

| Method | Accuracy | Macro-F1 | Resolved F1 | Unresolved F1 | Unresolved Precision | Unresolved Recall |
|---|---:|---:|---:|---:|---:|---:|
| Baseline prompt | 0.440 | 0.440 | 0.453 | 0.426 | 0.963 | 0.274 |
| MIPROv2 | 0.576 | 0.565 | 0.495 | 0.635 | 0.920 | 0.484 |
| GEPA-scalar | 0.528 | 0.524 | 0.478 | 0.569 | 0.929 | 0.411 |
| GEPA-full | **0.784** | **0.734** | **0.620** | **0.849** | 0.905 | **0.800** |

## Interpretation

This result addresses the main benchmark-level concern that the method might only work inside a curated topic bubble. GEPA-full transfers substantially better than MIPROv2 and GEPA-scalar to held-out regulatory issue areas. The gain is especially large on unresolved recall: 0.800 for GEPA-full versus 0.484 for MIPROv2 and 0.411 for GEPA-scalar.

The optimized full-feedback prompt learned topic-agnostic evidence-gap rules: identify specific SEC request elements, check amended evidence for the named detail, quantification, related-party identification, or legal/accounting analysis, and mark partial fixes as unresolved when material requested elements remain missing.

## Caveat

This is one topic-holdout split. A long benchmark paper should add multiple held-out topic configurations, but this split already provides strong evidence that full natural-language feedback learns a transferable regulatory evidence-checking policy.
