# ARR Upgrade Notes

This file tracks additions made after the pre-ARR checkpoint:

- Checkpoint commit: `c5f36db`
- Checkpoint tag: `checkpoint/pre-arr-upgrade-20260927`

## Main Reviewer Concerns Addressed

### Reproducibility

Added or clarified:

- exact prediction and reflection models,
- optimizer budgets,
- grouped split paths,
- non-generative scorer configuration,
- Jev endpoint and token usage,
- output directories for each reported run,
- model-specific output paths for multi-LLM verifier runs.

### Retrieval Details

The evidence pipeline is documented as:

1. start from 589 revision-claim candidate cases;
2. select EDGAR candidate amended filings around the company response date;
3. use a 10-day-before to 60-day-after filing window;
4. keep up to 8 candidate filings per row;
5. lexical rank candidate snippets;
6. ask `gpt-4o-mini` at temperature 0 to rerank/adjudicate the top 3 snippets;
7. keep 472 examples whose amended evidence is directly or partially relevant.

The benchmark is therefore retrieval-conditioned. It evaluates evidence-grounded reasoning over retrieved snippets, not complete end-to-end filing-retrieval recall.

### Label Validity

Evidence now includes:

- full independent LLM audit over all 472 examples with `gpt-5.4-mini`;
- later SEC same-topic follow-up corroboration;
- paired external-reference analysis on the clean 220-example follow-up subset;
- independent-feedback GEPA ablation, where the feedback writer did not see the original adjudication rationales.

### Multi-LLM Evaluation

New runs compare monolithic vs guarded verifier prompts under two backbones:

- `gpt-4o-mini`
- `gpt-5.4-mini`

The guarded reviewer improves over monolithic prompting for both models, supporting the claim that RegTrace-Agent's obligation-evidence structure contributes beyond a single tuned prompt.

### Release Package

The anonymized release should include:

- benchmark JSONL,
- split files,
- accession identifiers,
- retrieval metadata,
- raw retrieved snippets,
- labels,
- feedback fields,
- prompts,
- optimizer configs,
- prediction outputs,
- scripts to regenerate the main tables,
- data card and reproducibility notes.

## Potential External Dataset Extensions

The current paper should remain centered on RegTrace-SEC. Other public regulatory traces are better framed as future extension points unless we have time to build a second benchmark.

Promising candidates:

- FDA Warning Letters: public FDA site has warning letters with response/closeout filters and thousands of entries.
- Hugging Face `tim-a-wood/fda-warning-letters`: a public scrape of FDA warning letters with response-letter fields.
- openFDA Complete Response Letters: public endpoint for FDA complete response letters.
- Commercial SEC comment-letter products such as Audit Analytics, sec-api.io, or Obscura can help scale thread reconstruction, but licensing may limit anonymous release.

Recommendation: do not expand the main benchmark before ARR October unless the current SEC package is fully cleaned. Use these as discussion/future work, not core results.

