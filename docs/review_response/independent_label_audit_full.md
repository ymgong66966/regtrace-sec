# Full Independent Label Audit

Purpose: strengthen benchmark-label validity evidence beyond the earlier 60-example audit.

The audit model was `gpt-5.4-mini`. It saw only:

- `sec_comment`
- `company_response`
- top 3 raw `retrieved_snippets`

It did not see:

- `visible_evidence_resolution_label`
- scalar/category/full feedback
- evidence summaries or missing-requirement fields
- later SEC follow-up text

This is an independent LLM audit, not expert legal/accounting validation.

## Results

| Metric | Value |
|---|---:|
| Rows | 472 |
| Agreement accuracy | 0.7309 |
| Macro-F1 vs benchmark label | 0.7146 |
| Resolved F1 | 0.6462 |
| Unresolved F1 | 0.7829 |
| Agreements | 345 |
| Disagreements | 127 |
| Mean confidence | 0.9245 |
| High-confidence rows | 465 |
| High-confidence agreement | 0.7398 |
| Cost USD | 0.926507 |

## By Issue Category

| Issue category | N | Agreement |
|---|---:|---:|
| SPAC disclosure | 78 | 0.8205 |
| non-GAAP | 16 | 0.8125 |
| other | 183 | 0.7377 |
| revenue recognition | 75 | 0.7200 |
| crypto | 28 | 0.7143 |
| risk factor | 91 | 0.6374 |

## By Gap Type

| Gap type | N | Agreement |
|---|---:|---:|
| incomplete accounting analysis | 25 | 0.8400 |
| missing quantification | 59 | 0.8136 |
| resolved but regulator requested more detail | 38 | 0.7895 |
| resolved visible evidence | 153 | 0.7582 |
| incomplete legal or regulatory analysis | 25 | 0.7600 |
| missing exhibit or document | 29 | 0.6552 |
| missing specific disclosure | 140 | 0.6500 |

## Interpretation

The audit provides useful but bounded label-validity evidence. Agreement is meaningfully above chance on a difficult evidence-grounded task and is strongest for accounting-analysis, quantification, and SPAC-disclosure cases. Disagreements concentrate in missing-specific-disclosure and risk-factor cases, which are exactly the areas where visible evidence sufficiency is most judgment-sensitive.

For the paper, this should be framed carefully:

- It strengthens the claim that the benchmark labels are not arbitrary.
- It does not replace expert legal/accounting review.
- It complements, rather than replaces, later SEC follow-up corroboration.

## Artifacts

- `outputs/sec_label_independent_audit/gpt-5.4-mini/result.json`
- `outputs/sec_label_independent_audit/gpt-5.4-mini/metrics.md`
- `outputs/sec_label_independent_audit/gpt-5.4-mini/audit_predictions.jsonl`

