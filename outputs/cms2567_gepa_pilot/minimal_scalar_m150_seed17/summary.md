# CMS-2567 GEPA Pilot

- Model: `openai/gpt-4o-mini`
- Program style: `minimal`
- Feedback mode: `scalar`
- Train/dev/test: 270/90/140
- Class-balanced metric: `True`
- Max metric calls: 150

| stage | accuracy | macro-F1 | adequate F1 | not adequate F1 |
| --- | ---: | ---: | ---: | ---: |
| optimized dev | 0.7444 | 0.7231 | 0.6462 | 0.8000 |
| optimized test | 0.6714 | 0.6631 | 0.6102 | 0.7160 |

## Label Counts

```json
{
  "not_adequate": 103,
  "adequate": 37
}
```
