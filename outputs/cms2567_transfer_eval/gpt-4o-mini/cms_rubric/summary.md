# CMS-2567 Transfer Evaluation

- Mode: `cms_rubric`
- Model: `gpt-4o-mini`
- Rows: 37
- Gold counts: {'adequate': 20, 'not_adequate': 17}

| metric | value |
| --- | ---: |
| Accuracy | 0.7838 |
| Macro-F1 | 0.7628 |
| Cost USD | 0.010193 |

## Per Label

```json
{
  "adequate": {
    "precision": 0.7143,
    "recall": 1.0,
    "f1": 0.8333,
    "support": 20
  },
  "not_adequate": {
    "precision": 1.0,
    "recall": 0.5294,
    "f1": 0.6923,
    "support": 17
  }
}
```

## Prediction Counts

```json
{
  "adequate": 28,
  "not_adequate": 9
}
```
