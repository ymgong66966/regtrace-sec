# CMS-2567 POC Adjudication Pilot

This note records the first fast iteration for turning CMS-2567 into a
RegTrace-style cross-regulatory adequacy benchmark.

## Goal

The FDA warning-letter probe did not expose public company responses. CMS-2567
does: it contains regulator-authored deficiency narratives and provider-authored
Plans of Correction (POCs). The key question is whether we can construct a
high-quality adequacy label without using the nearly always-corrected CMS
correction-status field as a shortcut.

The adjudication task is:

> Given a CMS deficiency narrative and the provider's POC, decide whether the
> POC adequately addresses the material regulatory deficiency.

The adjudicator sees only:

- deficiency narrative,
- POC text,
- F-tag,
- scope/severity,
- deficiency category.

The adjudicator does not see:

- `Deficiency Corrected`,
- `Correction Date`,
- source URL,
- any later outcome metadata.

## Sample

Starting pool:

- 2,588 high-trust CMS-2567 candidate pairs from the trace probe.

Stratified sample:

- 120 examples, stratified over severity band and F-tag group.
- 40-example pilot subset used for the first strict double-review run.

Sample files:

- `outputs/cms2567_poc_adjudication/cms2567_poc_sample_120.jsonl`
- `outputs/cms2567_poc_adjudication/cms2567_poc_pilot_40.jsonl`

## Iteration 1: strict rubric, double review on 40

Models:

- Primary: `gpt-5.4-mini`
- Audit: `gpt-4o-mini`

Result:

| signal | value |
| --- | ---: |
| rows | 40 |
| primary adequate | 1 |
| primary partial | 35 |
| primary inadequate | 4 |
| audit adequate | 6 |
| audit partial | 31 |
| audit inadequate | 3 |
| three-way agreement | 0.800 |
| binary agreement | 0.875 |

Interpretation:

The strict rubric was stable but too punitive. It treated many standard CMS POCs
as only partial because the plan could have provided more exact resident-level
or process-level detail. This is useful for finding unresolved gaps, but it
collapses the positive class and would make a weak benchmark.

## Iteration 2: calibrated rubric, primary review on 120

The calibrated rubric uses substantial adequacy rather than perfection:

- adequate if the POC substantially addresses the material deficiency;
- partial if a material cited component is still missing or vague;
- inadequate if the plan is mostly boilerplate, future intent, denial, a bare
  cross-reference, or "no plan required" without enough visible correction.

Model:

- Primary: `gpt-5.4-mini`

Result:

| label | count |
| --- | ---: |
| adequate | 28 |
| partial | 82 |
| inadequate | 10 |

By binary mapping:

| binary label | count |
| --- | ---: |
| adequate | 28 |
| not adequate | 92 |

Interpretation:

The calibrated rubric is more usable than the strict rubric. It recovers a
meaningful adequate class while still identifying many partial POCs. The
dataset remains hard because many POCs are long and superficially structured
but leave one material item underspecified.

## Iteration 3: balanced independent audit on 50

We selected a balanced audit subset from the calibrated primary labels:

- 20 primary adequate,
- 20 primary partial,
- 10 primary inadequate.

Audit model:

- `gpt-4o-mini`

Agreement:

| signal | value |
| --- | ---: |
| rows | 50 |
| three-way agreement | 0.680 |
| binary agreement | 0.740 |

Confusion, primary label by audit label:

| primary \ audit | adequate | partial | inadequate |
| --- | ---: | ---: | ---: |
| adequate | 20 | 0 | 0 |
| partial | 13 | 7 | 0 |
| inadequate | 0 | 3 | 7 |

Interpretation:

The strong labels are reliable:

- Primary `adequate` was confirmed by audit in 20/20 sampled cases.
- Primary `inadequate` was confirmed as binary not-adequate in 10/10 sampled cases.

The unstable class is `partial`. Many primary partial cases are judged adequate
by the second reviewer. This is not a failure; it tells us that `partial` is a
borderline/needs-adjudication region rather than a clean hard label.

## Recommended label policy

For a paper-grade CMS extension, do not use raw single-pass labels as gold.

Use a consensus policy:

1. **Consensus adequate:** primary adequate and audit adequate.
2. **Consensus inadequate:** primary inadequate, or primary partial confirmed as
   partial/inadequate by audit.
3. **Borderline:** primary partial but audit adequate, or any strong
   disagreement. Keep these for qualitative analysis or adjudicate with a third
   reviewer.

This gives the CMS extension a clean role:

- SEC remains the main benchmark.
- CMS-2567 becomes a cross-regulatory transfer setting for POC adequacy review.
- The framework claim becomes stronger because the same
  obligation-to-response review structure appears outside SEC correspondence.

## Next experiment

The next efficient step is not GEPA yet. It is to materialize a
consensus-labeled CMS v0:

1. Run calibrated `gpt-5.4-mini` primary review on 500 stratified examples.
2. Audit all primary adequate and primary inadequate examples with `gpt-4o-mini`.
3. Audit a stratified sample of primary partial examples.
4. Use a third strong judge only for disagreements.
5. Freeze a consensus subset for transfer experiments.

After that, run:

- generic CMS prompt,
- SEC-transferred RegTrace reviewer,
- CMS in-domain GEPA-full,
- CMS in-domain scalar/category controls if the consensus set is large enough.

