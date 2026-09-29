# CMS-2567 Transfer Evaluation

- Mode: `regtrace_calibrated`
- Model: `gpt-4o-mini`
- Rows: 37
- Gold counts: {'adequate': 20, 'not_adequate': 17}

| metric | value |
| --- | ---: |
| Accuracy | 0.8108 |
| Macro-F1 | 0.7959 |
| Cost USD | 0.010051 |

## Per Label

```json
{
  "adequate": {
    "precision": 0.7407,
    "recall": 1.0,
    "f1": 0.8511,
    "support": 20
  },
  "not_adequate": {
    "precision": 1.0,
    "recall": 0.5882,
    "f1": 0.7407,
    "support": 17
  }
}
```

## Prediction Counts

```json
{
  "adequate": 27,
  "not_adequate": 10
}
```
