# CMS-2567 Transfer Evaluation

- Mode: `generic`
- Model: `gpt-4o-mini`
- Rows: 37
- Gold counts: {'adequate': 20, 'not_adequate': 17}

| metric | value |
| --- | ---: |
| Accuracy | 0.8919 |
| Macro-F1 | 0.8912 |
| Cost USD | 0.009583 |

## Per Label

```json
{
  "adequate": {
    "precision": 0.9,
    "recall": 0.9,
    "f1": 0.9,
    "support": 20
  },
  "not_adequate": {
    "precision": 0.8824,
    "recall": 0.8824,
    "f1": 0.8824,
    "support": 17
  }
}
```

## Prediction Counts

```json
{
  "adequate": 20,
  "not_adequate": 17
}
```
