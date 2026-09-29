# CMS-2567 Transfer Evaluation

- Mode: `regtrace_transfer`
- Model: `gpt-4o-mini`
- Rows: 37
- Gold counts: {'adequate': 20, 'not_adequate': 17}

| metric | value |
| --- | ---: |
| Accuracy | 0.5946 |
| Macro-F1 | 0.5470 |
| Cost USD | 0.010826 |

## Per Label

```json
{
  "adequate": {
    "precision": 1.0,
    "recall": 0.25,
    "f1": 0.4,
    "support": 20
  },
  "not_adequate": {
    "precision": 0.5312,
    "recall": 1.0,
    "f1": 0.6939,
    "support": 17
  }
}
```

## Prediction Counts

```json
{
  "not_adequate": 32,
  "adequate": 5
}
```
