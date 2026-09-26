# Revision Plan After FinNLP Reviews

## Diagnosis

The reviews are not rejecting the core idea. They are asking for the missing evidence chain around reproducibility, label validity, retrieval, and statistical stability. The best revision should therefore avoid adding a larger agentic story and instead make the benchmark and experiment audit trail much harder to attack.

## Must-Fix Paper Changes

1. Add a reproducibility table.

   Report the frozen prediction model and optimizer configuration in the main paper or appendix. The final grouped-split runs used `openai/gpt-4o-mini` for prediction and `openai/gpt-4o-mini` for reflection/prompt search. Prediction temperature was 0 with max 500 output tokens. Reflection/prompt-search temperature was 0.7 with max 1500 output tokens. GEPA used `max_metric_calls=150`, reflection minibatch size 4, Pareto candidate selection, `reflect_on_perfect_subsamples=True`, seed 17, and 4 evaluation threads. MIPROv2 used 8 trials, 4 candidates, max 4 labeled demos, max 4 bootstrapped demos, the same prediction model, and the same train/dev/test split.

2. Specify the retrieval pipeline.

   The amended-evidence stage started from 589 revision-claim cases. Candidate filings were selected from EDGAR company submissions around the company response date, using a window of 10 days before and 60 days after the response, with up to 8 candidate filings per row. A local lexical ranker selected top snippets, then `gpt-4o-mini` reranked/adjudicated the top 3 snippets at temperature 0. The final visible-evidence benchmark keeps 472 examples where amended evidence was available and either directly or partially relevant. The paper should print this funnel.

3. Strengthen label validity.

   The current label audit is a 60-example independent LLM audit with 49/60 agreement and mean confidence 0.897. This should be reported honestly as an LLM audit, not expert validation. The stronger external validity result is the systematic same-topic SEC follow-up analysis: among follow-up examples, unresolved labels receive direct/partial corroboration at 68.1%, resolved labels at 9.2%. Add the reviewer-requested paired analysis: on a clean 220-example follow-up subset, the visible benchmark label reaches 0.756 macro-F1 against the external follow-up reference, while GEPA-full OOF reaches 0.590 and the handwritten baseline reaches 0.460. This supports label validity more than model-win causality.

4. Fix the follow-up claim.

   The current text should not claim that GEPA-full's wins are independently corroborated beyond the unresolved base rate. Instead say: later SEC follow-up validates the benchmark labels and shows that the visible-evidence label is aligned with regulator behavior. GEPA-full still improves over the baseline in the same external-reference comparison, but this result is weaker and should be presented as secondary.

5. Address the feedback-leak concern directly.

   The paper should say that full feedback is a training-time adjudication rationale and is never present at test time. However, the reviewer is right that full feedback is closer to the label-generation rule than scalar feedback. The cleanest defense is the component ablation: removing evidence rationale or unmet-requirement text hurts macro-F1, and request/action-only feedback over-flags unresolved cases. This shows that the effect is not simply "more label text", but calibration from evidence-grounded rationales. A future stronger experiment would use independently generated feedback from a second model or human auditor.

6. Report stability.

   Add the existing five-fold out-of-fold summary as variance evidence. Across five folds, GEPA-full has mean macro-F1 0.698, MIPROv2 0.647, GEPA-scalar 0.609, GEPA-category 0.545, and baseline 0.446. The standard deviations are nontrivial, so the paper should avoid claiming that the exact grouped-split 10-point margin is deterministic. The stable claim is that full natural-language feedback is consistently competitive and usually strongest, with particularly strong temporal and topic-holdout evidence.

7. Demote or fully explain the guarded verifier.

   If the guarded verifier was designed after inspecting model errors, it should be framed as a post-hoc policy distillation or error-analysis prototype, not as the main method result. If kept in the main paper, state which split was inspected, when it was frozen, and whether the test set influenced it. Otherwise, move it to appendix.

8. Add trivial and non-optimizer baselines.

   The paper should include majority-class and random/stratified baselines. It already has zero-shot/manual/few-shot response-only baselines on an earlier response-gap dataset, but those are not the same visible-evidence benchmark. If time permits, add a cheap supervised TF-IDF/logistic baseline or document-NLI-style prompting baseline on the visible-evidence split. If not, acknowledge this as future work and include majority/stratified baselines at minimum.

9. Clarify release commitments.

   State that the release will include benchmark JSONL, split files, accession identifiers, retrieval metadata, retrieved snippets, labels, feedback fields, prompts, optimizer configs, prediction outputs for reported tables, and scripts to regenerate tables. Do not say only that such a release "should" include them.

10. Soften closed-loop/autonomous claims.

   Replace "self-improving autonomous compliance agent" with "offline reflective optimization framework for evidence-grounded regulatory review." It is fine to draw the loop as a design pattern, but the experiment evaluates offline prompt optimization, not deployed continual learning.

## Strongest Revised Story

RegTrace-SEC is a benchmark for a realistic regulatory verification problem: a company claims to have revised a filing, and the system must check whether visible amended evidence satisfies the regulator's original request. RegTrace-Agent then studies how different supervision signals shape an evidence-grounded reviewer. Full natural-language feedback is useful because it expresses the missing obligation, evidence quote, and remaining gap; scalar feedback only says the verdict was wrong. The best-supported claim is not that GEPA is always better, but that evidence-grounded written feedback teaches a transferable regulatory reading policy.

## Files Added For Revision

- `docs/sec_visible_evidence_paper_artifacts/review_response/followup_paired_analysis.md`
- `docs/sec_visible_evidence_paper_artifacts/review_response/followup_paired_analysis.json`
- `docs/sec_visible_evidence_paper_artifacts/review_response/followup_paired_metrics.csv`
- `docs/sec_visible_evidence_paper_artifacts/review_response/five_fold_oof_summary.csv`
- `scripts/sec_followup_paired_analysis.py`

