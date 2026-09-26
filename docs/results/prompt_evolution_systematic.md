# Systematic Prompt Evolution Appendix

This appendix analyzes GEPA prompt candidates extracted from saved `gepa_state.bin` files. Candidate 0 is the handwritten seed prompt; candidates 1+ are prompts proposed by GEPA reflection. Counts below report how many optimized candidates contain each regulator-style rule.

| Method | Optimized candidates | Claim alone insufficient | Visible evidence required | SEC request matching | Partial disclosure unresolved | Missing quantification / named items | Legal/accounting analysis | Avoid over-requiring |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GEPA-full | 2 | 2 | 2 | 2 | 1 | 2 | 0 | 0 |
| No evidence rationale | 2 | 2 | 2 | 0 | 2 | 2 | 1 | 0 |
| No unmet requirement | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 0 |
| Request + action only | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 0 |
| GEPA-scalar | 2 | 2 | 2 | 0 | 0 | 0 | 1 | 0 |
| GEPA-category | 2 | 2 | 2 | 0 | 0 | 0 | 2 | 0 |

## Reading the Pattern

The seed prompt is intentionally terse: `Classify whether a company resolved an SEC comment using the visible evidence.` GEPA reflection consistently expands it into a regulator-style checklist. The most useful rules are not generic prompt engineering instructions; they are domain-specific reading rules: do not accept a company revision claim unless visible amended evidence supports it; compare every named SEC request to the evidence; treat partial disclosure as unresolved; and look for missing quantification, named disclosures, exhibits, legal analysis, or accounting analysis.

The component ablation clarifies the role of feedback richness. Even weak textual feedback (`request_action_only`) induces many of these rules and yields high unresolved recall, but it over-flags resolved examples. Full feedback is better balanced because it includes both the unmet requirement for unresolved cases and the resolution basis/supporting quote for resolved cases. In other words, full feedback teaches skepticism plus calibration.

## Representative Prompt Excerpts

### GEPA-full

Rule flags: claim-insufficient=1, visible-evidence=1, request-matching=1, partial-unresolved=0, missing-items=1, avoid-overrequiring=0.

> . - Examine the `amended_evidence` snippets to confirm that they support the company's claims and cover all requested aspects of the SEC comment. - Look for direct references in the amended evidence that address the SEC's specific requests, such as ownership structures, accounting adjustments, or enforcement risks. 4. **Labeling**: - If the company has fully

### No evidence rationale

Rule flags: claim-insufficient=1, visible-evidence=1, request-matching=0, partial-unresolved=1, missing-items=1, avoid-overrequiring=0.

> s: - Pay close attention to the specific requirements outlined in the SEC comment. If the company claims to have amended the filing but the evidence does not substantiate this, classify it as unresolved. - Be aware of terms like "material terms" or "financial statements" which may indicate specific details that must be included in the amended filing. - Use the feedbac

### No unmet requirement

Rule flags: claim-insufficient=1, visible-evidence=1, request-matching=1, partial-unresolved=1, missing-items=1, avoid-overrequiring=0.

> that meet all requirements outlined in the SEC comment. The amended evidence supports the claims made in the company response. - **Unresolved**: The company has not fully addressed the SEC comment. This could be due to missing specific requested items, lack of quantification, insufficient legal or accounting analysis, or other gaps in the response or evidence. **Key

### Request + action only

Rule flags: claim-insufficient=1, visible-evidence=1, request-matching=1, partial-unresolved=1, missing-items=1, avoid-overrequiring=0.

> ompany has provided clear amendments that meet the SEC's requirements. Vague responses or claims of compliance without supporting evidence should be flagged as unresolved. 4. **Evidence Analysis**: When reviewing the amended evidence, look for: - Named items that the SEC specifically requested. - Quantitative data or disclosures that were missing or required.

### GEPA-scalar

Rule flags: claim-insufficient=1, visible-evidence=1, request-matching=0, partial-unresolved=0, missing-items=0, avoid-overrequiring=0.

> rt for the company's response. Ensure that the amended evidence aligns with the company's claims and sufficiently supports the resolution of the SEC's concerns. 4. **Classification**: After evaluating the SEC comment, the company response, and the amended evidence, classify the outcome as either: - **Resolved**: if the company has adequately addressed the SEC comm

### GEPA-category

Rule flags: claim-insufficient=1, visible-evidence=1, request-matching=0, partial-unresolved=0, missing-items=0, avoid-overrequiring=0.

> gulations. - Review the `amended_evidence` to verify if it substantiates the company's claims and aligns with SEC guidelines. 3. **Classifications**: - Your output should include: - A **label** indicating whether the SEC comment has been "resolved" or "not resolved". - A **reasoning** section that explains your classification, detailing how the compan

## Paper-Ready Takeaway

A concise wording for the paper: GEPA does not merely make the prompt longer. It turns adjudication feedback into an explicit regulatory reading policy. Scalar/category feedback can move the model toward unresolved detection, but full natural-language feedback better calibrates the boundary between unsupported revision claims and visibly sufficient amended disclosure.
