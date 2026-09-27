# Multi-LLM Reviewer Evaluation

Purpose: test whether the RegTrace reviewer structure is tied to a single frozen LLM backbone.

All runs use the same grouped held-out split:

`data/sec_visible_evidence_benchmark_v2/splits/grouped_random_dev48_gap/fold_0/test.jsonl`

All methods see only test-time fields:

- `sec_comment`
- `company_response`
- top 3 raw `retrieved_snippets`

The comparison is not prompt optimization. It evaluates two reviewer structures with two frozen LLM backbones:

- `monolithic`: one direct evidence-grounded decision prompt.
- `guarded_verifier`: obligation extraction followed by obligation-evidence checking and a guarded verdict.

## Results

| Model | Reviewer structure | Accuracy | Macro-F1 | Resolved F1 | Unresolved F1 | Cost USD |
|---|---|---:|---:|---:|---:|---:|
| `gpt-4o-mini` | monolithic | 0.6403 | 0.6380 | 0.6094 | 0.6667 | 0.052946 |
| `gpt-4o-mini` | guarded verifier | 0.8345 | 0.8076 | 0.7356 | 0.8796 | 0.057716 |
| `gpt-5.4-mini` | monolithic | 0.6187 | 0.6122 | 0.5620 | 0.6624 | 0.389326 |
| `gpt-5.4-mini` | guarded verifier | 0.7554 | 0.7321 | 0.6531 | 0.8111 | 0.420244 |

## Interpretation

The guarded reviewer improves over the monolithic prompt for both LLM backbones:

- `gpt-4o-mini`: +0.1696 macro-F1.
- `gpt-5.4-mini`: +0.1199 macro-F1.

This supports the system framing: RegTrace-Agent is not just a single tuned prompt. The obligation-evidence review structure contributes a reusable decision policy. The model comparison also shows calibration differences across backbones. `gpt-4o-mini` is stronger in this setting, while `gpt-5.4-mini` is more resolved-leaning and loses unresolved recall in the monolithic condition.

## Artifacts

- `outputs/sec_obligation_verifier_eval/grouped_random_dev48_gap__fold_0/gpt-4o-mini/monolithic/result.json`
- `outputs/sec_obligation_verifier_eval/grouped_random_dev48_gap__fold_0/gpt-4o-mini/guarded_verifier/result.json`
- `outputs/sec_obligation_verifier_eval/grouped_random_dev48_gap__fold_0/gpt-5.4-mini/monolithic/result.json`
- `outputs/sec_obligation_verifier_eval/grouped_random_dev48_gap__fold_0/gpt-5.4-mini/guarded_verifier/result.json`

