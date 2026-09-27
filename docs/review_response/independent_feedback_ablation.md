# Independent-Feedback GEPA Ablation

Purpose: address the feedback-leak concern. In the main GEPA-full condition, the optimizer receives structured natural-language feedback derived from the benchmark adjudication fields. To test whether the gain depends on those exact adjudication rationales, we generated a second feedback source with `gpt-5.4-mini`.

The independent feedback writer saw only:

- `sec_comment`
- `company_response`
- raw `retrieved_snippets`
- issue metadata
- the gold visible-evidence label

It did not see the original adjudication rationale fields such as `feedback_evidence_summary`, `feedback_unmet_requirement`, `amended_evidence_evidence_summary`, `amended_evidence_missing_evidence`, `full_feedback`, or later SEC follow-up text.

## Configuration

Split: `grouped_random_dev48_gap/fold_0`.

Train/dev/test: 285/48/139.

GEPA configuration matches the main full-feedback run:

- predictor model: `openai/gpt-4o-mini`
- reflection model: `openai/gpt-4o-mini`
- task max tokens: 500
- reflection max tokens: 1500
- max metric calls: 150
- reflection minibatch size: 4
- candidate selection: Pareto
- feedback mode: full
- feedback variant: `independent_full`

Independent feedback generation cost recorded in the local ledger: 474 calls, about `$1.30`, including a 2-row smoke test.

## Result

| Method | Feedback source | Accuracy | Macro-F1 | Resolved F1 | Unresolved F1 | Unresolved Precision | Unresolved Recall |
|---|---|---:|---:|---:|---:|---:|---:|
| Initial prompt | none | 0.417 | 0.393 | 0.515 | 0.270 | 1.000 | 0.156 |
| GEPA-full | original adjudication feedback | 0.784 | 0.756 | 0.674 | 0.839 | 0.867 | 0.812 |
| GEPA-independent-full | independent GPT-5.4-mini feedback | 0.770 | 0.750 | 0.680 | 0.820 | 0.890 | 0.760 |

Takeaway: the full-feedback result survives when the natural-language feedback is written by a model that did not produce the original adjudication rationale. This substantially weakens the feedback-leak objection. The independent-feedback run is slightly lower on unresolved recall than the original GEPA-full run, but its macro-F1 is within 0.006 of the headline result.

Source artifact: `outputs/sec_visible_evidence_benchmark_v2/independent_feedback_ablation/fold_0_basic_independent_full_m150/dry_run_result.json`.
