# CMS-2567 Cross-Regulatory Adaptation: GEPA Pilot

This note records the current CMS-2567 transfer/adaptation experiment for RegTrace. The purpose is not to claim that the SEC reviewer prompt transfers directly to healthcare regulation. The sharper claim is that the RegTrace pattern, context-to-feedback review optimization, can be instantiated in another regulatory setting when we expose the optimizer to domain-specific written feedback.

## Task

Input at test time:

- `deficiency_text`: CMS deficiency narrative.
- `plan_of_correction_text`: facility plan of correction.
- `ftag` and `scope_severity`: regulatory metadata available in the CMS-2567 record.

Hidden from the predictor:

- `cms_poc_adequacy_label`
- `cms_poc_missing_elements`
- `cms_poc_covered_elements`
- `cms_poc_reason`
- `cms_poc_optimizer_feedback`
- correction outcome metadata

Prediction target:

- `adequate`
- `not_adequate`

The binary label maps `adequate` to `adequate`, and both `partial` and `inadequate` to `not_adequate`. This makes the task a plan-adequacy review task, not an outcome-prediction task. The official correction outcome is not a useful target here because most plans eventually become corrected after inspection and remediation.

## Data and Split

The current benchmark uses 500 CMS-2567 plan-of-correction examples with primary LLM adjudication.

Grouped split seed: `17`

| split | rows | groups | adequate | not adequate |
| --- | ---: | ---: | ---: | ---: |
| train | 270 | 142 | 72 | 198 |
| dev | 90 | 49 | 24 | 66 |
| test | 140 | 73 | 37 | 103 |

The split is grouped by `source_document_id`, so examples from the same CMS source document do not appear across train/dev/test.

## Main Results

All rows below use the same grouped 140-example CMS test set. The direct generic baseline and all GEPA runs use `gpt-4o-mini` as the prediction backbone. GEPA runs use `gpt-4o-mini` as the reflection model, `max_metric_calls=150`, `reflection_minibatch_size=4`, and a class-balanced objective during optimization.

| method | seed/program style | feedback used in optimization | accuracy | macro-F1 | adequate F1 | not adequate F1 | prediction balance |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| Direct generic prompt | generic | none | 0.707 | 0.694 | 0.631 | 0.757 | 74 adequate / 66 not adequate |
| Minimal seed | minimal | none | 0.650 | 0.642 | 0.588 | 0.696 | 82 adequate / 58 not adequate |
| GEPA-scalar | minimal | correct/incorrect score | 0.671 | 0.663 | 0.610 | 0.716 | 81 adequate / 59 not adequate |
| GEPA-category | minimal | coarse category and label | 0.643 | 0.635 | 0.583 | 0.688 | 83 adequate / 57 not adequate |
| GEPA-full | minimal | written covered/missing/reason feedback | 0.743 | 0.723 | 0.647 | 0.798 | 65 adequate / 75 not adequate |
| Structured seed | SEC-style structured | none | 0.736 | 0.449 | 0.051 | 0.847 | 2 adequate / 138 not adequate |
| Structured GEPA-full | SEC-style structured | written covered/missing/reason feedback | 0.771 | 0.584 | 0.304 | 0.863 | 9 adequate / 131 not adequate |

## Interpretation

The user concern was correct: CMS is easier for a generic LLM prompt than SEC amended-evidence review. A direct generic prompt reaches 0.694 macro-F1 on the full grouped CMS test set, whereas the earlier strong-consensus subset looked even higher. This does not necessarily mean the CMS data is broken. It means plan-of-correction adequacy is closer to ordinary regulatory reading than SEC amended-filing evidence review.

The useful result is more specific. GEPA-full wins when we start from a lightweight CMS-appropriate reviewer. It improves the minimal seed from 0.642 to 0.723 macro-F1, beats scalar feedback by 0.059 macro-F1, and beats the direct generic prompt by 0.029 macro-F1. The gain comes mainly from improving the `not_adequate` class without destroying `adequate` recall.

The failed structured transfer is also important. The SEC-style structured reviewer is too conservative for CMS. It predicts almost everything as `not_adequate`, giving high accuracy only because the dataset is imbalanced but poor macro-F1. Full feedback partially repairs this behavior, but not enough to beat the minimal full-feedback run. This supports a clean paper claim: RegTrace is not a single transferred prompt; it is a feedback-optimized review framework whose seed policy must match the regulatory setting.

## Why Full Feedback Helps

Scalar feedback only tells the optimizer whether a prediction was correct. Category feedback adds a coarse domain bucket, but it does not explain which elements of a plan are materially covered or missing. Full feedback gives the optimizer the review logic:

- what the deficiency required,
- what the plan covered,
- which resident-specific or system-level elements remained weak,
- whether a weakness was material enough to make the plan not adequate.

That information matters in CMS because many plans contain boilerplate that sounds plausible. The model must distinguish a substantially adequate plan from a plan that merely mentions education, audit, or QAPI without tying those mechanisms back to the cited deficiency.

## What This Supports in the Main Paper

This pilot supports adding a cross-regulatory adaptation result:

1. The framework is not limited to SEC correspondence. It can be instantiated for another public regulatory corpus with a different review object.
2. Directly transferring the SEC-style prompt is not enough. Domain-specific feedback optimization is necessary.
3. Full written feedback is again the best optimization signal among scalar, category, and full feedback under the minimal CMS reviewer.

The clean wording should be:

> On CMS-2567 plans of correction, the SEC-style checklist does not transfer verbatim. However, when RegTrace is re-instantiated with CMS-specific feedback, GEPA-full improves over both a lightweight seed reviewer and scalar feedback, and it also exceeds a direct generic prompt on the grouped test set.

## Caveats

This should currently be presented as an adaptation pilot, not as a second fully validated benchmark. The 500 CMS labels are primary LLM adjudications. Earlier audit work suggests that strong `adequate` and `inadequate` labels are more stable than `partial`, but the `partial` boundary is noisier. Before making CMS a main-result benchmark, we should add either a larger independent audit or restrict the main comparison to higher-confidence examples.

The optimized result is also from one seed. It is directionally encouraging, but it should not be oversold as a fully stable effect without another seed or a small confidence interval analysis.

## Recommended Paper Use

For the ARR/main-venue version, this result is best used as a compact generalization section or appendix-backed study. The headline paper should remain RegTrace-SEC, where the data construction, amended evidence, and same-topic SEC follow-up corroboration are much stronger. CMS should be used to show that the framework idea is not a one-off SEC artifact and that full feedback remains useful in a different regulatory domain.

