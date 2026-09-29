# RegTrace 结果图说明

这组图不是把所有表格都可视化，而是挑最能支撑论文主线的结果。核心 story 是：

> RegTrace 把监管审查变成 request-response-evidence-feedback trace；证据让任务成立，full natural-language feedback 让 reviewer 学到监管式 gap reasoning，这个机制能跨时间、跨主题、跨监管领域适配。

## Figure 1: Evidence Ablation

文件：

- `paper/figures/result_1_evidence_ablation.pdf`
- `paper/figures/result_1_evidence_ablation.png`

这张图讲：只看 company response 不够，因为公司经常只说“we revised the disclosure”。加入 amended filing snippets 以后，macro-F1 从 0.575 到 0.748，说明这个任务真正的核心不是判断 response 语气，而是检查 revised artifact 里有没有真的补上。

为什么重要：它证明 RegTrace-SEC 不是普通 text classification，也不是 response-only compliance classification，而是 evidence-grounded review。

## Figure 2: Feedback Ladder

文件：

- `paper/figures/result_2_feedback_ladder.pdf`
- `paper/figures/result_2_feedback_ladder.png`

这张图讲：在同样的 test-time evidence 下，full natural-language feedback 是最好的 reviewer-training signal。GEPA-full macro-F1 0.756，高于 MIPROv2 的 0.652 和 GEPA-scalar 的 0.675。

为什么重要：这是方法贡献的主图。它说明优势不是因为 GEPA-full 看到了更多 test-time evidence，而是因为 optimization-time feedback 更有信息量：它告诉模型“SEC 要什么、公司做了什么、证据支持什么、还缺什么”。

## Figure 3: Temporal and Topic Generalization

文件：

- `paper/figures/result_3_generalization.pdf`
- `paper/figures/result_3_generalization.png`

这张图讲：GEPA-full 不只是某个 random split 上赢。它在 2024-2025 temporal holdout 上 macro-F1 0.791，在 topic holdout 上 0.734，也超过 baseline、MIPROv2 和 scalar GEPA。

为什么重要：这回应 reviewer 对“curated bubble”的担心。它说明 learned review policy 有一定跨时间和跨 issue category 的泛化能力。

## Figure 4: Cross-Domain Adaptation

文件：

- `paper/figures/result_4_cross_domain_adaptation.pdf`
- `paper/figures/result_4_cross_domain_adaptation.png`

这张图分成 CMS 和 FDA 两边。

CMS 讲：同样的 context-to-feedback 机制可以迁移到 CMS Plan of Correction，但不能直接复制 SEC checklist。用 CMS-specific written POC feedback 后，GEPA-full 达到 0.723 macro-F1，高于 generic prompt 和 scalar/category controls。

FDA 讲：constructor 不应该强行把所有数据集套成 SEC-style response adequacy。FDA 公开数据缺少 company response channel，所以 framework reshapes 成 warning-to-closeout trace verification。校准后 macro-F1 从 strict RegTrace 的 0.880 到 0.950。

为什么重要：这张图把文章从“一个 SEC dataset”推向“一个 adaptive regulatory review framework”。

## Figure 5: Label Validation and Follow-Up Corroboration

文件：

- `paper/figures/result_5_label_validation.pdf`
- `paper/figures/result_5_label_validation.png`

左图讲：在有 verified same-topic follow-up 的样本中，unresolved labels 有 68.1% 被后续 SEC follow-up 直接或部分佐证，而 resolved labels 只有 9.2%。这说明 visible-evidence label 和真实监管行为有很强一致性。

右图讲：follow-up 更适合作为 label validity evidence，而不是主 gold label。benchmark label 对 noisy follow-up reference 的 macro-F1 是 0.756，高于 OOF GEPA-full 的 0.590 和 handwritten baseline 的 0.460。

为什么重要：这直接回应 reviewer 对 LLM-adjudicated labels 的质疑。它不是专家人工审查的替代，但它是很强的外部行为信号。

## Contact Sheet

文件：

- `paper/figures/result_figures_contact_sheet.png`

这是五张图的快速预览，方便检查整体视觉风格。

## 我建议放进正文的图

正文优先级：

1. `result_2_feedback_ladder`: 主方法结果。
2. `result_1_evidence_ablation`: 证明任务定义成立。
3. `result_5_label_validation`: 回应 label validity。
4. `result_4_cross_domain_adaptation`: 如果走 NAACL/ARR main-venue framework story，这张很关键。

`result_3_generalization` 可以放正文或 appendix。如果篇幅紧，正文用一句话报数字，把图放 appendix。
