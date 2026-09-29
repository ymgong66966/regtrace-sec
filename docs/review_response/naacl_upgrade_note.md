# NAACL/ARR Upgrade Note

This checkpoint keeps `paper/main_a2_context_feedback.tex` unchanged and creates a stronger main-venue draft at `paper/main_arr_naacl_regtrace.tex`.

## What Changed

1. Reframed the paper from prompt optimization to a context-to-feedback framework.
   - New title: `RegTrace-Agent: Learning Regulatory Review Policies from Context-to-Feedback Traces`.
   - Abstract now foregrounds the domain constructor, request-response-evidence roles, feedback loop, and cross-regulatory adaptation.

2. Strengthened the contribution story.
   - RegTrace is now described as trace construction, retrieval, obligation checking, feedback construction, reviewer optimization, and guarded reuse.
   - GEPA-full is positioned as the strongest reviewer-training signal inside the framework, not as the whole paper.

3. Added benchmark validation and release protocol.
   - Main text now separates test-time input fields from training-feedback-only fields.
   - It states forbidden fields clearly: gold labels, feedback fields, evidence summaries, missing-requirement fields, and later SEC follow-up text.
   - It adds the independent LLM audit, follow-up corroboration, and stratified human-audit plan.

4. Made retrieval more reproducible.
   - SEC construction now documents candidate filing selection, top-eight candidate cap, 1,800-character chunks, 250-character overlap, top-three snippets, and LLM reranking/adjudication.

5. Added human audit materials.
   - Script: `scripts/build_sec_label_audit_sheet.py`
   - Sheet: `docs/review_response/sec_label_audit_sheet_80.csv`
   - Guideline: `docs/review_response/sec_label_audit_guideline.md`

## Current Position

This version is much closer to a main NLP resource/framework paper. The strongest remaining gap is direct human or expert validation of labels. The prepared 80-row audit sheet intentionally oversamples hard cases and independent-audit disagreements so a small amount of human time gives maximal evidence.

## Recommended Next Human Step

Review 30 to 50 rows from `docs/review_response/sec_label_audit_sheet_80.csv`.

Fill:

- `human_label`
- `human_label_confidence`
- `evidence_sufficient`
- `human_notes`

The most useful rows are the independent-audit disagreements, because resolving those lets the paper report a meaningful human agreement statistic and correct obvious label noise before ARR submission.
