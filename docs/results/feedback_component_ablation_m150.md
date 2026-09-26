# Feedback Component Ablation (Grouped Benchmark v2, m=150)

All rows use the same test-time input: SEC comment, company response, and raw retrieved amended-filing snippets. Only the optimization-time feedback changes.

| Method | Optimization-time signal | Acc. | Macro-F1 | Resolved F1 | Unresolved F1 | Unresolved P | Unresolved R |
|---|---|---:|---:|---:|---:|---:|---:|
| Full feedback | Gold label + evidence relevance + supporting quote / resolution basis + visible unmet requirement | 0.784 | 0.756 | 0.674 | 0.839 | 0.867 | 0.812 |
| No evidence rationale | Removes supporting quote / evidence rationale from training feedback | 0.712 | 0.682 | 0.583 | 0.780 | 0.826 | 0.740 |
| No unmet requirement | Removes the explicit missing requirement or resolution basis from training feedback | 0.741 | 0.708 | 0.609 | 0.806 | 0.833 | 0.781 |
| Request + action only | Keeps only SEC request and company action; removes gap type, evidence, and unmet-requirement details | 0.784 | 0.724 | 0.595 | 0.853 | 0.806 | 0.906 |

For context, the scalar/category ladder on the same split is:

| Method | Optimization-time signal | Acc. | Macro-F1 | Resolved F1 | Unresolved F1 | Unresolved P | Unresolved R |
|---|---|---:|---:|---:|---:|---:|---:|
| GEPA-scalar | Scalar correctness only | 0.705 | 0.675 | 0.577 | 0.773 | 0.824 | 0.729 |
| GEPA-category | Coarse category feedback | 0.597 | 0.595 | 0.562 | 0.627 | 0.870 | 0.490 |

## Interpretation

- Full feedback has the best macro-F1, indicating the best resolved/unresolved balance.
- `request_action_only` reaches the highest unresolved recall and unresolved F1, but it lowers resolved F1. This suggests weak textual feedback can induce aggressive regulator-style skepticism, but it over-flags some actually resolved evidence-backed revisions.
- Removing evidence rationale (`no_evidence`) hurts macro-F1 and unresolved F1 relative to full feedback, showing that supporting quote/evidence grounding is useful rather than decorative.
- Removing the explicit unmet requirement (`no_unmet_requirement`) also lowers macro-F1, but less sharply than removing evidence rationale. GEPA can infer some gap rules from examples, yet full feedback gives the cleanest calibration.
- The story should therefore be framed as calibration through full natural-language feedback: not simply more recall, but better discrimination between partial disclosure and sufficient visible revision.
