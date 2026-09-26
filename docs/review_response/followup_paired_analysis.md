# Follow-Up Paired Analysis

Later same-topic SEC follow-up is used here as a noisy external reference, not as the benchmark gold label.
The clean subset maps `direct_corroboration` and `partial_corroboration` to `unresolved`, maps `weak_or_no_corroboration` to `resolved`, and excludes neutral/new-requirement cases.

- OOF rows with verified follow-up: 236
- Clean external-reference rows: 220
- External-reference support: `{'unresolved': 116, 'resolved': 104}`

| Method | N | Accuracy | Macro-F1 | Resolved F1 | Unresolved F1 |
|---|---:|---:|---:|---:|---:|
| visible_gold | 220 | 0.768 | 0.756 | 0.702 | 0.810 |
| gepa_full_oof | 220 | 0.591 | 0.590 | 0.605 | 0.575 |
| baseline_oof | 220 | 0.523 | 0.460 | 0.644 | 0.276 |

## Paired McNemar Tests

| Comparison | Left correct/right wrong | Left wrong/right correct | Exact p |
|---|---:|---:|---:|
| gepa_full_oof_vs_baseline_oof | 42 | 27 | 0.091 |
| gepa_full_oof_vs_visible_gold | 22 | 61 | 0.000 |
| visible_gold_vs_baseline_oof | 90 | 36 | 0.000 |

## Follow-Up Availability

Follow-up availability is nearly balanced across visible labels, so the external signal is not mechanically available only for unresolved examples.

- Resolved follow-up rate: 0.497
- Unresolved follow-up rate: 0.502
- Fisher exact p-value: 1.000

## Paper Use

Use this as label-validity evidence. Do not claim that GEPA-full wins are independently corroborated beyond the unresolved base rate unless the paired comparison is reported with its caveat.
