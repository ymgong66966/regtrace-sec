# CMS-2567 Transfer Evaluation

- Mode: `generic`
- Model: `gpt-4o-mini`
- Rows: 140
- Gold counts: {'not_adequate': 103, 'adequate': 37}

| metric | value |
| --- | ---: |
| Accuracy | 0.7071 |
| Macro-F1 | 0.6940 |
| Cost USD | 0.035342 |

## Per Label

```json
{
  "adequate": {
    "precision": 0.473,
    "recall": 0.9459,
    "f1": 0.6306,
    "support": 37
  },
  "not_adequate": {
    "precision": 0.9697,
    "recall": 0.6214,
    "f1": 0.7574,
    "support": 103
  }
}
```

## Prediction Counts

```json
{
  "not_adequate": 66,
  "adequate": 74
}
```
