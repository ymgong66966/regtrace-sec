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

## Limitations

This is a visible-evidence benchmark. If retrieval misses a relevant amended snippet, the label may not reflect the complete amended filing. Labels are LLM-adjudicated and supported by independent LLM audit and later SEC follow-up corroboration, but they are not a substitute for expert legal or accounting review.

The dataset should be used for research on evidence-grounded regulatory-review assistance, not for autonomous legal compliance decisions.

