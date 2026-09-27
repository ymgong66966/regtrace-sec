.PHONY: followup-paired leaderboard supervised-baselines encoder-scorers multi-llm-reviewer-eval label-audit-estimate label-audit-full jev-smoke independent-feedback-estimate materialize-independent-feedback independent-gepa-ablation fda-trace-probe cms2567-trace-probe cms2567-poc-sample cms2567-poc-estimate paper

followup-paired:
	PYTHONPATH=. python scripts/sec_followup_paired_analysis.py

leaderboard:
	PYTHONPATH=. python scripts/sec_build_final_leaderboard_artifact.py

supervised-baselines:
	PYTHONPATH=. python scripts/sec_supervised_baselines.py --text-mode response_only
	PYTHONPATH=. python scripts/sec_supervised_baselines.py --text-mode evidence_snippets
	PYTHONPATH=. python scripts/sec_supervised_baselines.py --text-mode oracle_summary

encoder-scorers:
	PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python scripts/sec_encoder_scorer_baseline.py --representation separate_match --text-mode response_only
	PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python scripts/sec_encoder_scorer_baseline.py --representation separate_match --text-mode evidence_snippets
	PYTHONPATH=. HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python scripts/sec_encoder_scorer_baseline.py --representation separate_match --text-mode oracle_summary

multi-llm-reviewer-eval:
	PYTHONPATH=. python scripts/sec_obligation_verifier_eval.py --mode monolithic --model gpt-4o-mini
	PYTHONPATH=. python scripts/sec_obligation_verifier_eval.py --mode guarded_verifier --model gpt-4o-mini
	PYTHONPATH=. python scripts/sec_obligation_verifier_eval.py --mode monolithic --model gpt-5.4-mini
	PYTHONPATH=. python scripts/sec_obligation_verifier_eval.py --mode guarded_verifier --model gpt-5.4-mini

label-audit-estimate:
	PYTHONPATH=. python scripts/sec_label_independent_audit.py --model gpt-5.4-mini --estimate-only

label-audit-full:
	PYTHONPATH=. python scripts/sec_label_independent_audit.py --model gpt-5.4-mini --resume

jev-smoke:
	PYTHONPATH=. python scripts/sec_jev_decision_eval.py --limit 3 --sleep 0.2 --endpoint https://thejevai.com/v1/systemone

independent-feedback-estimate:
	PYTHONPATH=. python scripts/sec_generate_independent_feedback.py --estimate-only --model gpt-5.4-mini

materialize-independent-feedback:
	PYTHONPATH=. python scripts/sec_materialize_independent_feedback_splits.py

independent-gepa-ablation:
	PYTHONPATH=. python scripts/sec_gepa_dry_run.py --task visible_evidence_resolution --visible-program-style basic --label-field visible_evidence_resolution_label --evidence-input-mode evidence_snippets --feedback-mode full --feedback-variant independent_full --train data/sec_visible_evidence_benchmark_v2_independent_feedback/splits/grouped_random_dev48_gap/fold_0/train.jsonl --dev data/sec_visible_evidence_benchmark_v2_independent_feedback/splits/grouped_random_dev48_gap/fold_0/dev.jsonl --final-eval data/sec_visible_evidence_benchmark_v2_independent_feedback/splits/grouped_random_dev48_gap/fold_0/test.jsonl --train-size 285 --dev-size 48 --model openai/gpt-4o-mini --reflection-model openai/gpt-4o-mini --task-max-tokens 500 --reflection-max-tokens 1500 --max-metric-calls 150 --reflection-minibatch-size 4 --candidate-selection-strategy pareto --reflect-on-perfect-subsamples --num-threads 4 --eval-num-threads 4 --log-dir outputs/sec_visible_evidence_benchmark_v2/independent_feedback_ablation/fold_0_basic_independent_full_m150

fda-trace-probe:
	PYTHONPATH=. python scripts/fda_warning_letter_probe.py

cms2567-trace-probe:
	PYTHONPATH=. python scripts/cms2567_trace_probe.py

cms2567-poc-sample:
	PYTHONPATH=. python scripts/cms2567_build_poc_sample.py

cms2567-poc-estimate:
	PYTHONPATH=. python scripts/cms2567_adjudicate_poc.py --estimate-only

paper:
	cd paper && pdflatex main_8page_v2.tex && bibtex main_8page_v2 && pdflatex main_8page_v2.tex && pdflatex main_8page_v2.tex
