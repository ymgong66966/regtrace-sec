# RegTrace-SEC Label Audit Guideline

This sheet is for checking whether the released visible-evidence label is reasonable, not for judging legal liability or accounting correctness.

For each row, read:

1. `sec_comment`: what the SEC asked the company to add, explain, remove, quantify, or file.
2. `company_response`: what the company claimed it did.
3. `amended_evidence_best_snippet`: what we can visibly see in the amended filing or retrieved evidence.
4. `feedback_unmet_requirement`, `independent_audit_reason`, and `real_followup_text`: use these as hints, but do not blindly trust them.

Fill the blank columns:

- `human_label`: write `resolved`, `unresolved`, or `unclear`.
- `human_label_confidence`: write `high`, `medium`, or `low`.
- `evidence_sufficient`: write `yes`, `no`, or `partial`.
- `human_notes`: one short sentence explaining the key reason.

Decision rule:

- Mark `resolved` if the visible amended evidence substantially addresses the material SEC request.
- Mark `unresolved` if the visible evidence still misses a named disclosure, number, exhibit, legal/accounting analysis, table, contrast, or other material item requested by the SEC.
- Mark `unclear` if the company says it revised or separately filed something, but the visible evidence in the row is not enough to confirm either way.

Important: do not mark a case unresolved merely because the company response itself is short. If the amended evidence visibly supplies the requested information, the row can be resolved. Conversely, do not mark a case resolved merely because the company says it revised the filing; the visible evidence should show the substance of the fix.
