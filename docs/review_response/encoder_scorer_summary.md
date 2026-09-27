# Frozen Encoder Evidence Scorer

Purpose: test whether RegTrace-Agent can support a cheap, non-generative scoring component, rather than only a prompt-optimized reviewer.

Split: `grouped_random_dev48_gap/fold_0`.

Encoder: `sentence-transformers/all-MiniLM-L6-v2`, loaded from local cache.

Representation: `separate_match`.

The scorer separately embeds:

- SEC request,
- company response,
- evidence text,

then trains a logistic head over `[request, response, evidence, |request-evidence|, request*evidence]`. At inference time it outputs a probability and binary decision; it does not generate text.

| Input | Accuracy | Macro-F1 | Resolved F1 | Unresolved F1 | Note |
|---|---:|---:|---:|---:|---|
| response only | 0.612 | 0.574 | 0.449 | 0.700 | no amended evidence |
| raw amended-filing snippets | 0.712 | 0.667 | 0.545 | 0.789 | deployable scorer setting |
| oracle evidence summary | 0.647 | 0.608 | 0.484 | 0.732 | diagnostic, not deployable |

Interpretation:

- The raw-snippet encoder scorer substantially improves over TF-IDF raw snippets (`0.523` macro-F1).
- It is close to GEPA-scalar (`0.675`) and above MIPROv2 (`0.652`) on the grouped split, but still below GEPA-full (`0.756`).
- This supports the system framing: RegTrace-Agent can produce both a full natural-language reviewer and cheaper scoring heads for triage.
- The oracle-summary result is not strong because the frozen sentence encoder compresses the whole summary into one vector; lexical TF-IDF benefits more from explicit words such as "missing" and "satisfies". This is a useful reminder that cheap scorers need task-specific representation, not just more label-like text.

Source artifacts:

- `outputs/sec_encoder_scorers/grouped_random_dev48_gap/sentence-transformers__all-MiniLM-L6-v2/separate_match/response_only/result.json`
- `outputs/sec_encoder_scorers/grouped_random_dev48_gap/sentence-transformers__all-MiniLM-L6-v2/separate_match/evidence_snippets/result.json`
- `outputs/sec_encoder_scorers/grouped_random_dev48_gap/sentence-transformers__all-MiniLM-L6-v2/separate_match/oracle_summary/result.json`
