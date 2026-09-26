from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dspy

from pressback.dspy_program import (
    build_sec_dspy_program,
    build_sec_visible_evidence_resolution_basic_program,
    build_sec_visible_evidence_resolution_program,
    build_sec_visible_evidence_resolution_structured_program,
)
from scripts.sec_gepa_dry_run import (
    evaluate,
    load_jsonl,
    select_rows,
    summarize_scores,
    to_examples,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DSPy MIPROv2 scalar optimizer on an SEC benchmark.")
    parser.add_argument("--train", default="data/sec_response_gap_canonical_v1/sec_response_gap_train.jsonl")
    parser.add_argument("--dev", default="data/sec_response_gap_canonical_v1/sec_response_gap_dev.jsonl")
    parser.add_argument("--test", default="data/sec_response_gap_canonical_v1/sec_response_gap_test.jsonl")
    parser.add_argument(
        "--task",
        choices=["response_gap", "visible_evidence_resolution"],
        default="response_gap",
        help="Task signature to optimize.",
    )
    parser.add_argument(
        "--label-field",
        default="response_gap_label",
        help="Gold label field.",
    )
    parser.add_argument(
        "--feedback-variant",
        default="full",
        help="Feedback/rationale field variant passed through to examples.",
    )
    parser.add_argument(
        "--evidence-input-mode",
        choices=["evidence_snippets", "evidence_quote"],
        default="evidence_snippets",
        help="Input format for visible_evidence_resolution.",
    )
    parser.add_argument(
        "--visible-program-style",
        choices=["expert", "basic", "structured"],
        default="basic",
        help="Initial prompt style for visible_evidence_resolution.",
    )
    parser.add_argument("--train-size", type=int, default=296)
    parser.add_argument("--dev-size", type=int, default=92)
    parser.add_argument("--test-size", type=int, default=0, help="0 means all test examples.")
    parser.add_argument("--model", default="openai/gpt-4o-mini")
    parser.add_argument("--prompt-model", default="")
    parser.add_argument("--task-max-tokens", type=int, default=600)
    parser.add_argument("--prompt-max-tokens", type=int, default=1200)
    parser.add_argument("--num-trials", type=int, default=12)
    parser.add_argument("--num-candidates", type=int, default=6)
    parser.add_argument("--max-labeled-demos", type=int, default=4)
    parser.add_argument("--max-bootstrapped-demos", type=int, default=4)
    parser.add_argument("--num-threads", type=int, default=1)
    parser.add_argument("--eval-num-threads", type=int, default=1)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument(
        "--selection",
        choices=["stratified", "hard_release_boundary"],
        default="stratified",
        help="How to sample rows before optimization.",
    )
    parser.add_argument("--skip-pre-eval", action="store_true")
    parser.add_argument("--skip-test-baseline", action="store_true")
    parser.add_argument("--log-dir", default="outputs/sec_mipro_response_gap")
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")

    train_rows = select_rows(load_jsonl(args.train), args.train_size, args.seed, args.label_field, args.selection)
    dev_rows = select_rows(load_jsonl(args.dev), args.dev_size, args.seed + 1, args.label_field, args.selection)
    test_rows = load_jsonl(args.test)
    if args.test_size > 0:
        test_rows = select_rows(test_rows, args.test_size, args.seed + 2, args.label_field, args.selection)
    train_examples = to_examples(
        train_rows,
        args.label_field,
        args.feedback_variant,
        args.task,
        args.evidence_input_mode,
    )
    dev_examples = to_examples(
        dev_rows,
        args.label_field,
        args.feedback_variant,
        args.task,
        args.evidence_input_mode,
    )
    test_examples = to_examples(
        test_rows,
        args.label_field,
        args.feedback_variant,
        args.task,
        args.evidence_input_mode,
    )

    task_lm = dspy.LM(args.model, temperature=0, max_tokens=args.task_max_tokens, cache=False)
    prompt_lm = dspy.LM(
        args.prompt_model or args.model,
        temperature=0.7,
        max_tokens=args.prompt_max_tokens,
        cache=False,
    )
    dspy.configure(lm=task_lm)

    if args.task == "visible_evidence_resolution":
        if args.visible_program_style == "structured":
            student = build_sec_visible_evidence_resolution_structured_program()
        elif args.visible_program_style == "expert":
            student = build_sec_visible_evidence_resolution_program()
        else:
            student = build_sec_visible_evidence_resolution_basic_program()
    else:
        student = build_sec_dspy_program()
    pre_eval = [] if args.skip_pre_eval else evaluate(
        student,
        dev_examples,
        "scalar",
        label="mipro_pre_eval",
        num_threads=args.eval_num_threads,
    )

    optimizer = dspy.MIPROv2(
        metric=scalar_metric,
        prompt_model=prompt_lm,
        task_model=task_lm,
        max_labeled_demos=args.max_labeled_demos,
        max_bootstrapped_demos=args.max_bootstrapped_demos,
        auto=None,
        num_candidates=args.num_candidates,
        num_threads=args.num_threads,
        seed=args.seed,
        log_dir=args.log_dir,
        track_stats=True,
    )
    optimized = optimizer.compile(
        student,
        trainset=train_examples,
        valset=dev_examples,
        num_trials=args.num_trials,
        minibatch=True,
        minibatch_size=min(35, len(dev_examples)),
        requires_permission_to_run=False,
    )

    optimized_dev = evaluate(
        optimized,
        dev_examples,
        "scalar",
        label="mipro_optimized_dev",
        num_threads=args.eval_num_threads,
    )
    test_baseline = (
        {}
        if args.skip_test_baseline
        else summarize_scores(evaluate(
            student,
            test_examples,
            "scalar",
            label="mipro_test_baseline",
            num_threads=args.eval_num_threads,
        ))
    )
    optimized_test = summarize_scores(evaluate(
        optimized,
        test_examples,
        "scalar",
        label="mipro_optimized_test",
        num_threads=args.eval_num_threads,
    ))

    result = {
        "optimizer": "MIPROv2",
        "feedback": "scalar_exact_match",
        "model": args.model,
        "prompt_model": args.prompt_model or args.model,
        "task": args.task,
        "label_field": args.label_field,
        "evidence_input_mode": args.evidence_input_mode,
        "visible_program_style": args.visible_program_style,
        "train_examples": len(train_examples),
        "dev_examples": len(dev_examples),
        "test_examples": len(test_examples),
        "test_size_arg": args.test_size,
        "num_trials": args.num_trials,
        "num_candidates": args.num_candidates,
        "max_labeled_demos": args.max_labeled_demos,
        "max_bootstrapped_demos": args.max_bootstrapped_demos,
        "pre_eval": summarize_scores(pre_eval),
        "optimized_dev": summarize_scores(optimized_dev),
        "test_baseline": test_baseline,
        "optimized_test": optimized_test,
        "train_ids": [ex.example_id for ex in train_examples],
        "dev_ids": [ex.example_id for ex in dev_examples],
    }
    output = Path(args.log_dir) / "result.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def scalar_metric(gold: Any, pred: Any, trace: Any = None, pred_name: Any = None, pred_trace: Any = None) -> float:
    gold_label = normalize_label(getattr(gold, "target_label", ""))
    pred_label = normalize_label(getattr(pred, "label", ""))
    return 1.0 if gold_label == pred_label else 0.0


def normalize_label(value: str) -> str:
    lowered = str(value).strip().lower().replace("-", "_")
    if "unresolved" in lowered or lowered in {"not_resolved", "follow_up", "followup", "1", "true"}:
        return "unresolved"
    return "resolved"


if __name__ == "__main__":
    raise SystemExit(main())
