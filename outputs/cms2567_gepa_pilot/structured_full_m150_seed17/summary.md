# CMS-2567 GEPA Pilot

- Model: `openai/gpt-4o-mini`
- Program style: `structured`
- Feedback mode: `full`
- Train/dev/test: 270/90/140
- Class-balanced metric: `True`
- Max metric calls: 150

| stage | accuracy | macro-F1 | adequate F1 | not adequate F1 |
| --- | ---: | ---: | ---: | ---: |
| baseline dev | 0.7444 | 0.4989 | 0.1481 | 0.8497 |
| optimized dev | 0.8111 | 0.6846 | 0.4848 | 0.8844 |
| baseline test | 0.7357 | 0.4489 | 0.0513 | 0.8465 |
| optimized test | 0.7714 | 0.5837 | 0.3043 | 0.8632 |

## Label Counts

```json
{
  "not_adequate": 103,
  "adequate": 37
}
```
