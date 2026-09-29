# CMS-2567 POC GEPA Splits

Canonical split files for CMS-2567 plan-of-correction adequacy review.
Train/dev/test are grouped by `source_document_id` to avoid inspection-report leakage.

## Splits

- `train.jsonl`: 270 examples, 142 source-document groups, labels={'not_adequate': 198, 'adequate': 72}
- `dev.jsonl`: 90 examples, 49 source-document groups, labels={'not_adequate': 66, 'adequate': 24}
- `test.jsonl`: 140 examples, 73 source-document groups, labels={'not_adequate': 103, 'adequate': 37}

## Test-Time Inputs

Models may see `deficiency_text`, `plan_of_correction_text`, and metadata such as F-tag and severity.
They must not see adjudication feedback fields or hidden correction metadata at test time.

## Feedback Fields

`cms_poc_reason`, `cms_poc_missing_elements`, `cms_poc_covered_elements`, and `cms_poc_optimizer_feedback` are training-feedback fields for GEPA-style optimization.
