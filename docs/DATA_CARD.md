# Data Card

## Dataset

RegTrace-SEC Visible-Evidence Benchmark v2.

## Source

The examples are derived from public SEC EDGAR comment-letter correspondence and amended filings. The dataset includes SEC comments, company responses, accession identifiers, retrieved amended-filing snippets, visible-evidence labels, structured feedback fields, and split metadata.

## Task

Given:

- an SEC comment,
- a company response,
- retrieved amended-filing snippets,

predict whether the visible amended evidence resolves the SEC request.

Labels:

- `resolved`: the visible amended evidence substantially satisfies the material SEC request.
- `unresolved`: the visible amended evidence leaves a material requested item, quantification, exhibit, legal analysis, accounting analysis, or disclosure gap unresolved.

## Scale

- Rows: 472
- SEC review threads: 109
- Companies: 95
- Labels: 153 resolved, 319 unresolved

## Issue Categories

- other: 183
- risk factor: 91
- SPAC disclosure: 78
- revenue recognition: 75
- crypto: 28
- non-GAAP: 16
- cybersecurity: 1

## Important Fields

Model input fields:

- `sec_comment`
- `company_response`
- `retrieved_snippets`
- `amended_evidence_best_snippet`

Label fields:

- `visible_evidence_resolution_label`
- `event_followup_label`
- `regulator_followup_label`

Training-feedback and analysis fields:

- `scalar_feedback`
- `category_feedback`
- `full_feedback`
- `feedback_sec_request`
- `feedback_company_action`
- `feedback_evidence_summary`
- `feedback_unmet_requirement`
- `real_followup_text`

The feedback fields must not be included in test-time prompts.

## Evidence Retrieval and Inclusion

The visible-evidence benchmark is retrieval-conditioned. The evidence pipeline starts from revision-claim SEC comment-response cases, searches nearby amended filings, ranks candidate snippets, and keeps only examples whose retrieved amended evidence is directly or partially relevant.

Pipeline summary:

- Start from 589 revision-claim candidate cases.
- Select EDGAR amended-filing candidates around the company response date.
- Use a 10-day-before to 60-day-after response-date window.
- Keep up to 8 candidate filings per row.
- Apply local lexical snippet ranking.
- Use `gpt-4o-mini` at temperature 0 to rerank/adjudicate the top 3 snippets.
- Freeze 472 examples where amended evidence is available and directly or partially relevant.

This means the benchmark evaluates visible-evidence reasoning over retrieved snippets. It does not claim complete end-to-end retrieval recall over every possible amended filing.

## Label Audit Evidence

The benchmark labels are visible-evidence judgments. They are supported by three audit signals:

- Full independent LLM audit: `gpt-5.4-mini` sees only test-time fields for all 472 examples and reaches 0.7309 agreement accuracy and 0.7146 macro-F1 against the released labels.
- Same-topic SEC follow-up corroboration: later SEC follow-up is used as noisy external behavioral evidence, not as the gold label.
- Paired follow-up analysis: on a clean 220-example follow-up subset, the visible benchmark label reaches 0.756 macro-F1 against the external follow-up reference.

These checks strengthen label validity, but they do not replace expert legal or accounting review.

## Limitations

This is a visible-evidence benchmark. If retrieval misses a relevant amended snippet, the label may not reflect the complete amended filing. Labels are LLM-adjudicated and supported by independent LLM audit and later SEC follow-up corroboration, but they are not a substitute for expert legal or accounting review.

The dataset should be used for research on evidence-grounded regulatory-review assistance, not for autonomous legal compliance decisions.
