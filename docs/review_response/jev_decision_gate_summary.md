# Jev Typed Decision Gate

Purpose: evaluate Jev as a non-generative decision gate inside RegTrace-Agent.

Endpoint used: `https://thejevai.com/v1/systemone`.

Split: `grouped_random_dev48_gap/fold_0` held-out test set.

Rows: 139 predictions, 0 errors.

Input: SEC comment, company response, and top 3 raw retrieved amended-filing snippets.

Question type: `choice` with options `resolved` and `unresolved`.

| Method | Accuracy | Macro-F1 | Resolved F1 | Unresolved F1 | Unresolved Precision | Unresolved Recall |
|---|---:|---:|---:|---:|---:|---:|
| Jev typed decision gate | 0.799 | 0.722 | 0.576 | 0.868 | 0.793 | 0.958 |

Usage:

- Requests: 139
- Input tokens: 284,402
- Output tokens: 5,074

Interpretation:

- Jev is a strong non-generative triage component: it reaches high unresolved recall (`0.958`) and macro-F1 (`0.722`) without generating rationales.
- It is stronger than the frozen local encoder scorer (`0.667`) and lexical TF-IDF raw-evidence baseline (`0.523`).
- It still trails GEPA-full (`0.756` macro-F1), mainly because it is very aggressive on unresolved decisions and has lower resolved F1 (`0.576`).
- This supports the system framing: use Jev or frozen scorers as cheap first-pass gates, and route difficult or high-impact cases to the full feedback-trained reviewer / guarded verifier.

Source artifacts:

- `outputs/sec_jev_eval/grouped_random_dev48_gap/fold_0/result.json`
- `outputs/sec_jev_eval/grouped_random_dev48_gap/fold_0/metrics.md`
- `outputs/sec_jev_eval/grouped_random_dev48_gap/fold_0/predictions.jsonl`
