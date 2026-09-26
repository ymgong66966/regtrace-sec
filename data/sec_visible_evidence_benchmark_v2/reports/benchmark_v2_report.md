# SEC Visible-Evidence Benchmark v2 Report

## Scope

This benchmark contains revision-claim SEC comment-response examples with retrieved amended-filing evidence. It is retrieval-conditioned: examples are included only when amended evidence is available and directly or partially relevant.

## Headline Counts

- Rows: 472
- Review threads: 109
- Companies: 95
- Labels: `{"resolved": 153, "unresolved": 319}`
- Real same-topic follow-up available: `{"no": 236, "yes": 236}`

## Recommended Splits

- `splits/grouped_random`: main benchmark split grouped by SEC review thread.
- `splits/time_train_before_2024`: temporal generalization split.
- `splits/topic_holdout`: topic generalization split with crypto/non-GAAP held out by default.

## Top Issue Categories

| value | count |
|---|---:|
| other | 183 |
| risk_factor | 91 |
| spac_disclosure | 78 |
| revenue_recognition | 75 |
| crypto | 28 |
| non_gaap | 16 |
| cybersecurity | 1 |

## Top Gap Types

| value | count |
|---|---:|
| resolved_visible_evidence | 153 |
| missing_specific_disclosure | 140 |
| missing_quantification | 59 |
| resolved_but_regulator_requested_more_detail | 38 |
| missing_exhibit_or_document | 29 |
| incomplete_legal_or_regulatory_analysis | 25 |
| incomplete_accounting_analysis | 25 |
| visible_evidence_gap | 3 |

## Amended Form Families

| value | count |
|---|---:|
| registration_merger_spac | 184 |
| registration_ipo | 118 |
| other | 71 |
| quarterly_report | 42 |
| annual_report | 32 |
| proxy | 17 |
| current_report | 8 |

## Label by Issue Category

| value | resolved | unresolved | total |
|---|---:|---:|---:|
| other | 64 | 119 | 183 |
| risk_factor | 35 | 56 | 91 |
| spac_disclosure | 24 | 54 | 78 |
| revenue_recognition | 20 | 55 | 75 |
| crypto | 9 | 19 | 28 |
| non_gaap | 1 | 15 | 16 |
| cybersecurity | 0 | 1 | 1 |

## Label by Gap Type

| value | resolved | unresolved | total |
|---|---:|---:|---:|
| resolved_visible_evidence | 153 | 0 | 153 |
| missing_specific_disclosure | 0 | 140 | 140 |
| missing_quantification | 0 | 59 | 59 |
| resolved_but_regulator_requested_more_detail | 0 | 38 | 38 |
| missing_exhibit_or_document | 0 | 29 | 29 |
| incomplete_accounting_analysis | 0 | 25 | 25 |
| incomplete_legal_or_regulatory_analysis | 0 | 25 | 25 |
| visible_evidence_gap | 0 | 3 | 3 |

## Split Summaries

### grouped_random

- `train`: rows=229, review_threads=93, labels=`{"resolved": 89, "unresolved": 140}`
- `dev`: rows=104, review_threads=5, labels=`{"resolved": 21, "unresolved": 83}`
- `test`: rows=139, review_threads=11, labels=`{"resolved": 43, "unresolved": 96}`

### time_train_before_2024

- `train`: rows=264, review_threads=62, labels=`{"resolved": 89, "unresolved": 175}`
- `dev`: rows=64, review_threads=3, labels=`{"resolved": 17, "unresolved": 47}`
- `test`: rows=144, review_threads=53, labels=`{"unresolved": 97, "resolved": 47}`

### topic_holdout

- `train`: rows=279, review_threads=84, labels=`{"resolved": 103, "unresolved": 176}`
- `dev`: rows=68, review_threads=3, labels=`{"resolved": 20, "unresolved": 48}`
- `test`: rows=125, review_threads=30, labels=`{"unresolved": 95, "resolved": 30}`

