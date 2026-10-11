# Release Manifest

This file maps the manuscript claims to repository artifacts.

## Core Benchmark

- Main dataset: `data/sec_visible_evidence_benchmark_v2/sec_visible_evidence_benchmark_v2.jsonl`
- Independent-feedback variant: `data/sec_visible_evidence_benchmark_v2/sec_visible_evidence_benchmark_v2_independent_feedback.jsonl`
- Main grouped split: `data/sec_visible_evidence_benchmark_v2/splits/grouped_random_dev48_gap/fold_0/`
- Temporal split: `data/sec_visible_evidence_benchmark_v2/splits/time_train_before_2024/`
- Topic split: `data/sec_visible_evidence_benchmark_v2/splits/topic_holdout/`
- Dataset report: `data/sec_visible_evidence_benchmark_v2/reports/benchmark_v2_report.md`
- Data card: `docs/DATA_CARD.md`

## Reproducibility

- Frozen settings: `configs/main_experiment_config.yaml`
- Reproducibility notes: `docs/REPRODUCIBILITY.md`
- Environment requirements: `requirements.txt`
- Make targets: `Makefile`

## Main Results

- Main leaderboard: `docs/results/final_leaderboard_v2_dev48_gap_m150.md`
- Evidence ablation: `docs/results/evidence_ablation_table_v2.md`
- Feedback component ablation: `docs/results/feedback_component_ablation_m150.md`
- Temporal generalization: `docs/results/time_generalization_m150.md`
- Topic holdout: `docs/results/topic_holdout_m150.md`
- Bootstrap/stability: `docs/results/bootstrap_ci_grouped.csv`
- Prompt evolution: `docs/results/prompt_evolution_systematic.md`
- Full optimized prompts: `docs/results/full_optimized_prompts.md`
- Qualitative cases: `docs/results/qualitative_cases.md`

## Reviewer-Response And Soundness Analyses

- Paired follow-up analysis: `docs/review_response/followup_paired_analysis.md`
- Five-fold OOF summary: `docs/review_response/five_fold_oof_summary.csv`
- Supervised baselines: `docs/review_response/supervised_baselines_summary.md`
- Frozen encoder scorer: `docs/review_response/encoder_scorer_summary.md`
- Jev typed gate: `docs/review_response/jev_decision_gate_summary.md`
- Multi-LLM reviewer evaluation: `docs/review_response/multi_llm_reviewer_eval.md`
- Independent label audit: `docs/review_response/independent_label_audit_full.md`
- Independent-feedback ablation: `docs/review_response/independent_feedback_ablation.md`
- Human-reviewed audit sheet: `docs/review_response/sec_label_audit_sheet_80_gpt56sol_max_followup_informed.csv`

## Cross-Regulatory Adaptation

- Adaptive TraceSpec report: `docs/review_response/adaptive_trace_framework_report.md`
- CMS trace probe: `docs/review_response/cms2567_trace_probe.md`
- CMS transfer evaluation: `docs/review_response/cms2567_transfer_eval_pilot.md`
- CMS GEPA adaptation: `docs/review_response/cms2567_gepa_adaptation.md`
- FDA trace probe: `docs/review_response/fda_trace_probe.md`
- FDA contrastive experiment: `docs/review_response/fda_contrastive_experiment.md`

## Manuscript

Manuscript source files, PDFs, and rendered manuscript figures are intentionally
omitted from the anonymous review repository. The submitted PDF is handled by the
venue system; this release contains the benchmark, scripts, prompts,
predictions, and result artifacts needed to reproduce the empirical claims.

## Notes For Anonymous Release

Do not include a populated `.env` file. The tracked cost ledger
`outputs/openai_usage_ledger.jsonl` contains model usage and timestamps but no
API keys; include it only if the submission wants detailed cost accounting.
Otherwise, the summarized cost/configuration information in
`docs/REPRODUCIBILITY.md` is enough.
