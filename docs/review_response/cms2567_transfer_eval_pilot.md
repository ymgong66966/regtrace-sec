# CMS-2567 Transfer Evaluation Pilot

This note checks whether the RegTrace reviewer structure transfers to CMS-2567
before doing larger data construction or GEPA runs.

## Evaluation Set

We use the strong consensus subset from the CMS-2567 POC adjudication pilot.

Consensus policy:

- `adequate`: primary `gpt-5.4-mini` and audit `gpt-4o-mini` both label the POC adequate.
- `not_adequate`: primary `inadequate` or primary `partial` confirmed as partial/inadequate by audit.
- Borderline cases, especially primary partial but audit adequate, are excluded.

Resulting evaluation set:

| label | count |
| --- | ---: |
| adequate | 20 |
| not_adequate | 17 |
| total | 37 |

This is a small pilot, not a final benchmark result.

## Prompt Conditions

We compare four prompt structures:

1. **generic:** a short CMS adequacy prompt.
2. **regtrace_transfer:** direct transfer of the strict SEC-style obligation verifier.
3. **regtrace_calibrated:** obligation-to-response transfer with a calibrated "substantially addresses" threshold.
4. **cms_rubric:** CMS-specific calibrated rubric.

## Results

| model | prompt | accuracy | macro-F1 | adequate F1 | not-adequate F1 | behavior |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `gpt-4o-mini` | generic | 0.892 | 0.891 | 0.900 | 0.882 | balanced |
| `gpt-4o-mini` | regtrace_transfer | 0.595 | 0.547 | 0.400 | 0.694 | too strict |
| `gpt-4o-mini` | regtrace_calibrated | 0.811 | 0.796 | 0.851 | 0.741 | better, still below generic |
| `gpt-4o-mini` | cms_rubric | 0.784 | 0.763 | 0.833 | 0.692 | more adequate-leaning |
| `gpt-5.4-mini` | generic | 0.865 | 0.865 | 0.865 | 0.865 | balanced |
| `gpt-5.4-mini` | regtrace_calibrated | 0.838 | 0.828 | 0.870 | 0.786 | close, adequate-leaning |

## Interpretation

The most important finding is negative but useful: a direct SEC-style RegTrace
transfer is too skeptical for CMS POCs. It catches not-adequate cases but
over-flags adequate plans. Calibrating the transfer instruction helps
substantially, but it still does not beat a simple generic adequacy prompt on
this small consensus subset.

This changes the paper strategy:

- Do not claim that the current SEC-trained reviewer zero-shot transfers to CMS.
- Do claim that CMS-2567 is a promising cross-regulatory setting for the same
  context-to-response adequacy framework.
- The next meaningful experiment is in-domain CMS optimization or policy
  adaptation, not more zero-shot transfer prompting.

## Recommended Next Step

Build a larger consensus CMS-v0 and run a real in-domain adaptation ladder:

1. generic CMS prompt;
2. calibrated RegTrace transfer prompt;
3. few-shot CMS prompt using consensus examples;
4. CMS GEPA-scalar;
5. CMS GEPA-full using adequacy feedback.

The research question should be:

> Given a new regulatory response-review domain, can RegTrace-style feedback
> optimization adapt a reviewer policy beyond generic prompting?

That is stronger and more honest than claiming zero-shot transfer from SEC has
already won.

