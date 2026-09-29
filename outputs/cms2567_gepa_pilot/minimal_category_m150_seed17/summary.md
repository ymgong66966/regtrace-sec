# CMS-2567 GEPA Pilot

- Model: `openai/gpt-4o-mini`
- Program style: `minimal`
- Feedback mode: `category`
- Train/dev/test: 270/90/140
- Class-balanced metric: `True`
- Max metric calls: 150

| stage | accuracy | macro-F1 | adequate F1 | not adequate F1 |
| --- | ---: | ---: | ---: | ---: |
| optimized dev | 0.7000 | 0.6827 | 0.6087 | 0.7568 |
| optimized test | 0.6429 | 0.6354 | 0.5833 | 0.6875 |

## Label Counts

```json
{
  "not_adequate": 103,
  "adequate": 37
}
```
