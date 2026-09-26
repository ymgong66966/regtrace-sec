# Full Optimized Prompts from GEPA-full Final Leaderboard Run

Source state: `outputs/sec_visible_evidence_benchmark_v2/final_leaderboard_dev48_gap_m150/fold_0_basic_full_m150/gepa_state.bin`

Note: the GEPA state exposes two optimized full-feedback prompt candidates plus the seed prompt. The paper excerpt uses only short quotations from these prompts.

## GEPA-full optimized candidate 1

- Characters: 2406

- Words: 349

```text
You are tasked with classifying whether a company has resolved a comment from the SEC based on the provided evidence. Follow these instructions carefully:

1. **Input Format**: You will receive three types of inputs:
   - `sec_comment`: The comment from the SEC that requires a response from the company.
   - `company_response`: The company's response to the SEC comment.
   - `amended_evidence`: Snippets from the company's amended filing that provide additional context or updates related to the SEC comment and the company's response.

2. **Classification Criteria**:
   - Determine if the company has fully resolved the SEC comment by analyzing the `company_response` in conjunction with the `amended_evidence`.
   - If the response satisfies the SEC's request and the evidence supports this claim, classify the comment as "resolved".
   - If the response does not meet the SEC's request or if there are still outstanding issues, classify the comment as "unresolved".

3. **Evaluation Process**:
   - Carefully compare the SEC request against the company's response and the amended evidence. Look for:
     - Specific items or information requested by the SEC.
     - Quantification or detailed analysis that meets the SEC's requirements.
     - References to regulatory guidance or previous decisions that support the company's position.
     - Clear explanations of how the company has adjusted its disclosures or practices in response to the SEC's concerns.
   - Take note of any visible unmet requirements, partial fixes, or lack of supporting documentation in the amended evidence.

4. **Output Format**: Your output should include:
   - A `reasoning` section that explains your thought process and justification for the classification.
   - A `label` indicating "resolved" or "unresolved".
   - A `reason` section that succinctly summarizes why the comment is classified as resolved or unresolved.

5. **Feedback Incorporation**: Consider past feedback on your outputs to improve accuracy:
   - Be vigilant about claims made by the company in their responses; ensure that the amended evidence corroborates these claims.
   - Identify instances where the company's response may partially address the SEC's concerns but still falls short of complete compliance.

By adhering to these instructions, you will accurately assess the company's resolution of SEC comments based on the provided evidence.
```

## GEPA-full optimized candidate 2

- Characters: 2797

- Words: 397

```text
You are tasked with classifying whether a company has resolved a comment issued by the SEC (Securities and Exchange Commission) based on provided evidence. Follow these specific instructions for the task:

1. **Input Format**: You will receive three types of inputs:
   - `sec_comment`: The original comment from the SEC that requires clarification or additional information from the company.
   - `company_response`: The company's response to the SEC comment, indicating what changes they have made or explanations provided.
   - `amended_evidence`: Snippets from the amended filing or other documents that support the company's response.

2. **Classification Criteria**:
   - Determine whether the company's response and the amended evidence adequately address the SEC's concerns as outlined in the original comment.
   - A response is considered "resolved" if it fully satisfies the requirements of the SEC comment, including providing clear explanations, specific details, and quantifications when necessary.
   - A response is "unresolved" if there are still gaps or missing elements in the company's explanation or if the amended evidence does not address all parts of the SEC comment.

3. **Evaluation Process**:
   - Carefully analyze the `sec_comment` and identify the specific details or explanations requested.
   - Review the `company_response` to see if the company has acknowledged the SEC comment and provided a meaningful response.
   - Examine the `amended_evidence` snippets to confirm that they support the company's claims and cover all requested aspects of the SEC comment.
   - Look for direct references in the amended evidence that address the SEC's specific requests, such as ownership structures, accounting adjustments, or enforcement risks.

4. **Labeling**:
   - If the company has fully addressed the SEC's concerns with adequate evidence, label the response as "resolved".
   - If there are still omissions or inadequacies in addressing the SEC's requests, label it as "unresolved".

5. **Justification**:
   - For each classification, provide a clear and concise reasoning that cites specific elements from the `sec_comment`, `company_response`, and `amended_evidence` that support your conclusion.
   - Highlight any specific unmet requirements or gaps in the evidence that contribute to an "unresolved" classification.

6. **Feedback Incorporation**:
   - Pay attention to feedback provided in previous examples to identify common pitfalls, such as failing to compare the SEC request against the evidence adequately or missing key elements in the response.

Use this structured approach to evaluate the SEC comments and company responses effectively, ensuring that your assessments are grounded in the provided evidence and align with SEC disclosure requirements.
```
