# CMS-2567 GEPA Pilot

- Model: `openai/gpt-4o-mini`
- Program style: `structured`
- Feedback mode: `full`
- Train/dev/test: 20/10/140
- Class-balanced metric: `True`
- Max metric calls: 8

| stage | accuracy | macro-F1 | adequate F1 | not adequate F1 |
| --- | ---: | ---: | ---: | ---: |
| baseline dev | 0.6000 | 0.5834 | 0.5000 | 0.6667 |
| optimized dev | 0.7000 | 0.6703 | 0.5714 | 0.7692 |
| baseline test | 0.7357 | 0.4489 | 0.0513 | 0.8465 |
| optimized test | 0.7286 | 0.4459 | 0.0500 | 0.8417 |

## Label Counts

```json
{
  "not_adequate": 103,
  "adequate": 37
}
```
