# Benchmark v2 Dataset Tables

## Table 1. Corpus Scale

| Quantity | Count |
|---|---:|
| Examples | 472 |
| SEC review threads | 109 |
| Companies | 95 |
| Resolved examples | 153 |
| Unresolved examples | 319 |
| Examples with real next-round follow-up | 236 |

## Table 2. Issue Categories

| Issue category | Count |
|---|---:|
| `other` | 183 |
| `risk_factor` | 91 |
| `spac_disclosure` | 78 |
| `revenue_recognition` | 75 |
| `crypto` | 28 |
| `non_gaap` | 16 |
| `cybersecurity` | 1 |

## Table 3. Visible-Evidence Gap Types

| Gap type | Count |
|---|---:|
| `resolved_visible_evidence` | 153 |
| `missing_specific_disclosure` | 140 |
| `missing_quantification` | 59 |
| `resolved_but_regulator_requested_more_detail` | 38 |
| `missing_exhibit_or_document` | 29 |
| `incomplete_accounting_analysis` | 25 |
| `incomplete_legal_or_regulatory_analysis` | 25 |
| `visible_evidence_gap` | 3 |

## Table 4. Split Summary

| Split | Train | Dev | Test | Test labels | Test threads |
|---|---:|---:|---:|---|---:|
| `grouped_random` | 229 | 104 | 139 | resolved=43, unresolved=96 | 11 |
| `time_train_before_2024` | 264 | 64 | 144 | resolved=47, unresolved=97 | 53 |
| `topic_holdout` | 279 | 68 | 125 | resolved=30, unresolved=95 | 30 |
