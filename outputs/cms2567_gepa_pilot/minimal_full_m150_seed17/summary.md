# CMS-2567 GEPA Pilot

- Model: `openai/gpt-4o-mini`
- Program style: `minimal`
- Feedback mode: `full`
- Train/dev/test: 270/90/140
- Class-balanced metric: `True`
- Max metric calls: 150

| stage | accuracy | macro-F1 | adequate F1 | not adequate F1 |
| --- | ---: | ---: | ---: | ---: |
| baseline dev | 0.7556 | 0.7333 | 0.6563 | 0.8103 |
| optimized dev | 0.7333 | 0.7000 | 0.6000 | 0.8000 |
| baseline test | 0.6500 | 0.6420 | 0.5882 | 0.6957 |
| optimized test | 0.7429 | 0.7225 | 0.6471 | 0.7978 |

## Label Counts

```json
{
  "not_adequate": 103,
  "adequate": 37
}
```
