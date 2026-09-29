# CMS-2567 Transfer Evaluation

- Mode: `regtrace_calibrated`
- Model: `gpt-5.4-mini`
- Rows: 37
- Gold counts: {'adequate': 20, 'not_adequate': 17}

| metric | value |
| --- | ---: |
| Accuracy | 0.8378 |
| Macro-F1 | 0.8276 |
| Cost USD | 0.089442 |

## Per Label

```json
{
  "adequate": {
    "precision": 0.7692,
    "recall": 1.0,
    "f1": 0.8696,
    "support": 20
  },
  "not_adequate": {
    "precision": 1.0,
    "recall": 0.6471,
    "f1": 0.7857,
    "support": 17
  }
}
```

## Prediction Counts

```json
{
  "adequate": 26,
  "not_adequate": 11
}
```
