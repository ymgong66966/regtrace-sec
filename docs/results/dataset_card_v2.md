# Dataset Card v2: SEC Visible-Evidence Resolution Benchmark

## Task

Given an SEC staff comment, a company response, and retrieved snippets from the amended filing, predict whether the visible amended-filing evidence resolves the material SEC request.

## Inputs

- `sec_comment`: first-round SEC request.
- `company_response`: company response that usually claims a filing revision.
- `retrieved_snippets`: raw amended-filing snippets retrieved near the referenced filing/revision.

Fields such as `gap_type`, `feedback_evidence_summary`, `amended_evidence_missing_evidence`, and `category_feedback` are training-feedback or analysis fields, not ordinary test-time inputs.

## Label

- `visible_evidence_resolution_label = resolved`: visible amended evidence covers the material SEC request.
- `visible_evidence_resolution_label = unresolved`: visible amended evidence leaves a concrete gap such as a missing named disclosure, missing quantification, missing exhibit/document, or incomplete accounting/legal analysis.

## Scale

| Quantity | Count |
|---|---:|
| Examples | 472 |
| SEC review threads | 109 |
| Companies | 95 |
| Resolved | 153 |
| Unresolved | 319 |

## Construction Pipeline

SEC comment-response pair -> revision-claim detection -> amended-filing retrieval -> snippet reranking -> LLM evidence adjudication -> label/feedback construction -> grouped/time/topic splits.

## Known Limitations

- Labels are evidence-grounded rather than legal finality labels; retrieval can miss relevant text.
- The benchmark focuses on response rows with amendment/revision claims, not all SEC comments.
- LLM adjudication should be accompanied by an audit before public release.