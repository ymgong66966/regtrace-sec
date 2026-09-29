# CMS-2567 Transfer Evaluation

- Mode: `generic`
- Model: `gpt-5.4-mini`
- Rows: 37
- Gold counts: {'adequate': 20, 'not_adequate': 17}

| metric | value |
| --- | ---: |
| Accuracy | 0.8649 |
| Macro-F1 | 0.8649 |
| Cost USD | 0.064793 |

## Per Label

```json
{
  "adequate": {
    "precision": 0.9412,
    "recall": 0.8,
    "f1": 0.8649,
    "support": 20
  },
  "not_adequate": {
    "precision": 0.8,
    "recall": 0.9412,
    "f1": 0.8649,
    "support": 17
  }
}
```

## Prediction Counts

```json
{
  "adequate": 17,
  "not_adequate": 20
}
```
