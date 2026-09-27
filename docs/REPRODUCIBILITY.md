# Reproducibility Notes

## Frozen Model Configuration

Main prompt-optimization experiments used:

- Prediction model: `openai/gpt-4o-mini`
- Reflection / prompt-search model: `openai/gpt-4o-mini`
- Prediction temperature: 0
- Prediction max tokens: 500
- Reflection temperature: 0.7
- Reflection max tokens: 1500
- DSPy cache disabled during runs

The saved artifacts record OpenAI model aliases rather than dated model snapshots. This should be stated as a limitation if exact provider-side snapshots are unavailable.

## Main Split

The main grouped split is `data/sec_visible_evidence_benchmark_v2/splits/grouped_random_dev48_gap/fold_0`.

- Train: 285 examples
- Dev: 48 examples
- Test: 139 examples
- Test support: 43 resolved, 96 unresolved
- Grouping unit: SEC review thread

## GEPA Runs

Shared settings:

- Task: `visible_evidence_resolution`
- Label field: `visible_evidence_resolution_label`
- Test-time evidence input: raw retrieved amended-filing snippets
- Initial program style: `basic`
- Selection: stratified
- Seed: 17
- `max_metric_calls`: 150
- Reflection minibatch size: 4
- Candidate selection: Pareto
- Reflect on perfect subsamples: true
- Evaluation threads: 4

Feedback modes:

- `GEPA-scalar`: correctness-only feedback.
- `GEPA-category`: coarse issue/gap category feedback.
- `GEPA-full`: gold label plus evidence relevance, supporting quote or resolution basis, and visible unmet requirement.
- `GEPA-independent-full`: gold label plus independently written natural-language feedback from `gpt-5.4-mini`. The feedback writer saw only the SEC comment, company response, raw retrieved snippets, issue metadata, and gold visible-evidence label; it did not see the original adjudication rationale fields.

Independent-feedback ablation result on the grouped split:

- GEPA-full with original adjudication feedback: 0.756 macro-F1
- GEPA-independent-full: 0.750 macro-F1

This ablation directly tests whether the full-feedback result depends on reusing the same rationale fields that produced the benchmark labels.

## MIPROv2 Run

- Prediction model: `openai/gpt-4o-mini`
- Prompt model: `openai/gpt-4o-mini`
- Prediction temperature: 0
- Prompt-model temperature: 0.7
- Prediction max tokens: 500
- Prompt max tokens: 1500
- Number of trials: 8
- Number of candidates: 4
- Max labeled demos: 4
- Max bootstrapped demos: 4
- Seed: 17

## Retrieval Pipeline

The benchmark is retrieval-conditioned.

1. Start from 589 revision-claim examples.
2. Select candidate amended filings from EDGAR company submissions around the response date.
3. Candidate window: 10 days before to 60 days after the company response.
4. Keep up to 8 candidate filings per row.
5. Rank local filing chunks with a lexical scorer.
6. Pass the top 3 snippets to an LLM reranker/adjudicator.
7. Keep examples whose evidence is available and directly or partially relevant.

Rerank/adjudication settings:

- Model: `gpt-4o-mini`
- Temperature: 0
- Top snippets judged: 3

Retrieval funnel:

- 589 revision-claim cases
- 588 cases with candidate filings/snippets
- 472 cases retained in the visible-evidence benchmark
- Evidence relevance: 303 directly addresses, 169 partially addresses, 72 irrelevant, 44 no visible evidence

## Label Audit And Follow-Up Corroboration

Independent LLM audit:

- Rows audited: 60
- Audit model: `gpt-5.4-mini`
- Agreement: 49/60
- Mean confidence: 0.897

External follow-up analysis:

- Verified same-topic follow-up examples: 236
- Clean external-reference subset: 220
- External reference maps direct/partial corroboration to unresolved and weak/no corroboration to resolved.
- Visible benchmark label vs external reference: 0.756 macro-F1
- GEPA-full OOF vs external reference: 0.590 macro-F1
- Baseline OOF vs external reference: 0.460 macro-F1

## Variance Evidence

Five-fold OOF summary is in `docs/review_response/five_fold_oof_summary.csv`.

Mean macro-F1 across folds:

- Baseline: 0.446
- MIPROv2: 0.647
- GEPA-scalar: 0.609
- GEPA-category: 0.545
- GEPA-full: 0.698

The standard deviations are nontrivial, so the paper should report this as stability evidence rather than as a claim of deterministic margins.

## Non-Prompt Supervised Baselines

A lightweight TF-IDF logistic-regression baseline is included to address the non-prompt-optimization baseline concern.

Grouped split test macro-F1:

- Majority unresolved: 0.409
- Random train-prior: 0.469
- TF-IDF logistic regression, response-only: 0.523
- TF-IDF logistic regression, raw amended-filing snippets: 0.523
- TF-IDF logistic regression, oracle evidence summary: 0.858

The raw-snippet result shows that a simple lexical supervised classifier does not explain the GEPA-full gain. The oracle-summary result is diagnostic: once evidence interpretation is distilled, the task becomes much easier.
