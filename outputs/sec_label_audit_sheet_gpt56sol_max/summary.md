# GPT-5.6-Sol Model-as-Expert Audit

Model: `gpt-5.6-sol`
Reasoning effort: `max`

The auditor was blind to benchmark labels, prior audit labels, GEPA/baseline predictions, generated feedback fields, and later SEC follow-up.

| Item | Value |
|---|---:|
| Rows | 80 |
| Estimated actual cost USD | 1.741040 |
| Mean confidence score | 0.8970 |
| Unclear labels | 60 |
| Binary agreement rows, excluding unclear | 20 |
| Agreement accuracy vs benchmark | 0.5000 |
| Macro-F1 vs benchmark | 0.4506 |

## Audit Label Counts

```json
{
  "resolved": 8,
  "unclear": 60,
  "unresolved": 12
}
```

## Evidence Sufficiency Counts

```json
{
  "yes": 8,
  "partial": 60,
  "no": 12
}
```

This is still model-assisted validation, not licensed legal or accounting expert review.
