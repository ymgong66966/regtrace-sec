# CMS-2567 GEPA Pilot

- Model: `openai/gpt-4o-mini`
- Program style: `structured`
- Feedback mode: `category`
- Train/dev/test: 270/90/140
- Class-balanced metric: `True`
- Max metric calls: 150

| stage | accuracy | macro-F1 | adequate F1 | not adequate F1 |
| --- | ---: | ---: | ---: | ---: |
| optimized dev | 0.8000 | 0.6400 | 0.4000 | 0.8800 |
| optimized test | 0.7500 | 0.4787 | 0.1026 | 0.8548 |

## Label Counts

```json
{
  "not_adequate": 103,
  "adequate": 37
}
```
