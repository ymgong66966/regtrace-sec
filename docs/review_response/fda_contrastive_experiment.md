# FDA Third-Domain RegTrace Experiment

## Why FDA Is a Reshape Case

The FDA warning-letter corpus does not expose the same trace structure as SEC
comment-letter review. The public snapshot has warning letters and closeout
letters, but public company response letters are almost absent. The adaptive
construction decision is therefore not to force the SEC schema. Instead,
RegTrace reshapes the domain into warning-to-closeout trace verification.

This is useful for the paper because it shows a full new-domain entry flow:

1. inspect available fields;
2. ask an LLM-assisted constructor to propose a TraceSpec;
3. pass the proposal through a utility gate;
4. reshape the task when a direct response channel is missing;
5. construct a minimal benchmark;
6. evaluate generic, strict RegTrace, and calibrated RegTrace reviewers.

## LLM-Assisted Schema Proposal

The LLM schema proposer independently returned:

| Domain | Decision |
| --- | --- |
| SEC | `go-primary-benchmark` |
| CMS | `go-cross-regulatory-adaptation` |
| FDA | `reshape-before-benchmark` |

For FDA, the proposed mapping is:

- request: `warning_excerpt`
- response: none
- evidence: `closeout_excerpt`
- label: closeout existence or delay bucket after adding controls
- feedback: closeout language describing FDA evaluation of corrective actions
- decision: reshape into warning-to-closeout tracing or contrastive verification

This matches the executable utility-gate decision.

## Benchmark Construction

We build FDA Contrastive RegTrace Benchmark v1 from 400 linked warning-closeout
pairs. Each warning receives:

- one positive candidate: its true linked FDA closeout letter;
- one hard negative: a wrong closeout letter, preferably with the same product
  and subject.

The resulting benchmark has 800 examples and grouped splits by warning URL.

| Split | N | Matched | Mismatched |
| --- | ---: | ---: | ---: |
| Train | 480 | 240 | 240 |
| Dev | 160 | 80 | 80 |
| Test | 160 | 80 | 80 |

Negative composition:

| Negative type | Count |
| --- | ---: |
| same product + same subject wrong closeout | 357 |
| same product wrong closeout | 39 |
| different product wrong closeout | 4 |

## Results

All results use the same held-out 160-example test set and `gpt-4o-mini` at
temperature 0.

| Reviewer | Accuracy | Macro-F1 | Matched F1 | Mismatched F1 | Main behavior |
| --- | ---: | ---: | ---: | ---: | --- |
| Generic | 0.919 | 0.918 | 0.912 | 0.925 | Strong baseline, but misses 13 true matches |
| RegTrace strict | 0.881 | 0.880 | 0.865 | 0.894 | Perfect on mismatches, too conservative on true closeouts |
| RegTrace calibrated | **0.950** | **0.950** | **0.947** | **0.952** | Keeps mismatch precision while recovering true closeouts |

The strict RegTrace reviewer reproduced a failure mode we also saw in SEC/CMS:
obligation-style checking can become overly skeptical if the domain-specific
document genre is not calibrated. FDA closeout letters are often short and
boilerplate-heavy, so the reviewer should not require the closeout letter to
repeat every violation from the warning letter. The calibrated reviewer keeps
the trace checks that matter, namely firm identity, CMS/reference number,
warning date, product or violation family, issuing office, and explicit
corrective-action evaluation.

## Representative Error Repair

One true matched pair involved H2 Beverages, Inc. The strict reviewer rejected
the closeout because it expected the closeout to repeat the full warning-letter
substance and treated product wording differences too harshly. The calibrated
reviewer accepted the trace because the firm identity matched, the warning date
matched, the product area aligned, and the closeout explicitly stated that FDA
evaluated corrective actions in response to that warning.

This example is valuable for the paper because it demonstrates recursive
framework behavior: the first schema-shaped reviewer is not assumed final.
Observed errors feed back into the domain rubric, producing a better reviewer
without changing the underlying dataset or hiding additional fields.

## Paper Takeaway

FDA should be presented as a third-domain minimal experiment rather than a full
benchmark equal to SEC. Its value is methodological: RegTrace can inspect a new
public regulatory corpus, decide that the SEC response-evidence schema is not
observable, reshape the task into a valid trace-verification benchmark, and
improve the reviewer through domain-calibrated feedback rules.

