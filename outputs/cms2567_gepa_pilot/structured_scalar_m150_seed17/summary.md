# CMS-2567 GEPA Pilot

- Model: `openai/gpt-4o-mini`
- Program style: `structured`
- Feedback mode: `scalar`
- Train/dev/test: 270/90/140
- Class-balanced metric: `True`
- Max metric calls: 150

| stage | accuracy | macro-F1 | adequate F1 | not adequate F1 |
| --- | ---: | ---: | ---: | ---: |
| optimized dev | 0.7778 | 0.5770 | 0.2857 | 0.8684 |
| optimized test | 0.7571 | 0.5238 | 0.1905 | 0.8571 |

## Label Counts

```json
{
  "not_adequate": 103,
  "adequate": 37
}
```
