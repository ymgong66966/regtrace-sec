from __future__ import annotations

import argparse
import json
import os
import random
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

cache_dir = Path("outputs/dspy_cache")
cache_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("DSPY_CACHE_DIR", str(cache_dir.resolve()))

import dspy

from pressback.dspy_program import (
    build_sec_dspy_program,
    build_sec_expert_response_gap_program,
    build_sec_real_followup_program,
    build_sec_real_followup_risk_program,
    build_sec_real_followup_structured_risk_program,
    build_sec_visible_evidence_resolution_basic_program,
    build_sec_visible_evidence_resolution_program,
    build_sec_visible_evidence_resolution_structured_program,
)
from pressback.gepa_feedback import SecGoldExample, SecPrediction, score_sec_and_feedback


def main() -> int:
    parser = argparse.ArgumentParser(description="Tiny SEC GEPA dry run.")
    parser.add_argument("--train", default="data/gepa_ready_v1/sec_gepa_opt_train_pos3neg.jsonl")
    parser.add_argument("--dev", default="data/gepa_ready_v1/sec_gepa_quick_dev_pos3neg.jsonl")
    parser.add_argument("--train-size", type=int, default=6)
    parser.add_argument("--dev-size", type=int, default=4)
    parser.add_argument(
        "--final-eval",
        action="append",
        default=[],
        help="Optional JSONL file to evaluate after optimization. Can be repeated.",
    )
    parser.add_argument("--model", default="openai/gpt-4o-mini")
    parser.add_argument("--reflection-model", default="openai/gpt-4o-mini")
    parser.add_argument("--task-max-tokens", type=int, default=300)
    parser.add_argument("--reflection-max-tokens", type=int, default=1200)
    parser.add_argument("--feedback-mode", choices=["scalar", "category", "full"], default="full")
    parser.add_argument(
        "--task",
        choices=[
            "response_gap",
            "response_gap_expert",
            "real_followup",
            "real_followup_risk",
            "real_followup_structured_risk",
            "visible_evidence_resolution",
        ],
        default="response_gap",
        help="Task signature to optimize.",
    )
    parser.add_argument(
        "--feedback-variant",
        choices=[
            "full",
            "no_evidence",
            "no_unmet_requirement",
            "request_action_gap",
            "request_action_only",
            "real_followup",
            "hybrid_real_followup",
        ],
        default="full",
        help="Controls which response-gap rationale fields are exposed in full textual feedback.",
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
        default="expert",
        help="Initial prompt style for visible_evidence_resolution.",
    )
    parser.add_argument(
        "--label-field",
        default="target_label",
        help="Gold label field. Use response_gap_label for the adjudicated response-gap benchmark.",
    )
    parser.add_argument("--max-metric-calls", type=int, default=8)
    parser.add_argument("--reflection-minibatch-size", type=int, default=2)
    parser.add_argument(
        "--candidate-selection-strategy",
        choices=["pareto", "current_best"],
        default="current_best",
    )
    parser.add_argument(
        "--reflect-on-perfect-subsamples",
        action="store_true",
        help="Set GEPA skip_perfect_score=False so full textual feedback can still shape prompts on perfect minibatches.",
    )
    parser.add_argument("--num-threads", type=int, default=1)
    parser.add_argument("--eval-num-threads", type=int, default=1)
    parser.add_argument("--skip-pre-eval", action="store_true")
    parser.add_argument("--skip-final-baseline", action="store_true")
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument(
        "--selection",
        choices=["stratified", "hard_release_boundary"],
        default="stratified",
        help="How to sample train/dev rows before GEPA. hard_release_boundary focuses on revision/added-disclosure boundary cases.",
    )
    parser.add_argument("--log-dir", default="outputs/gepa_dry_run")
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")

    train_rows = load_jsonl(args.train)
    dev_rows = load_jsonl(args.dev)
    train_examples = to_examples(
        select_rows(train_rows, args.train_size, args.seed, args.label_field, args.selection),
        args.label_field,
        args.feedback_variant,
        args.task,
        args.evidence_input_mode,
    )
    dev_examples = to_examples(
        select_rows(dev_rows, args.dev_size, args.seed + 1, args.label_field, args.selection),
        args.label_field,
        args.feedback_variant,
        args.task,
        args.evidence_input_mode,
    )

    lm = dspy.LM(args.model, temperature=0, max_tokens=args.task_max_tokens, cache=False)
    reflection_lm = dspy.LM(args.reflection_model, temperature=0.7, max_tokens=args.reflection_max_tokens, cache=False)
    dspy.configure(lm=lm)

    if args.task == "real_followup_structured_risk":
        student = build_sec_real_followup_structured_risk_program()
    elif args.task == "visible_evidence_resolution":
        if args.visible_program_style == "structured":
            student = build_sec_visible_evidence_resolution_structured_program()
        elif args.visible_program_style == "basic":
            student = build_sec_visible_evidence_resolution_basic_program()
        else:
            student = build_sec_visible_evidence_resolution_program()
    elif args.task == "real_followup_risk":
        student = build_sec_real_followup_risk_program()
    elif args.task == "real_followup":
        student = build_sec_real_followup_program()
    elif args.task == "response_gap_expert":
        student = build_sec_expert_response_gap_program()
    else:
        student = build_sec_dspy_program()
    baseline_scores = [] if args.skip_pre_eval else evaluate(
        student,
        dev_examples,
        args.feedback_mode,
        label="pre_eval",
        num_threads=args.eval_num_threads,
    )

    optimizer = dspy.GEPA(
        metric=make_metric(args.feedback_mode, args.task),
        max_metric_calls=args.max_metric_calls,
        reflection_minibatch_size=args.reflection_minibatch_size,
        reflection_lm=reflection_lm,
        candidate_selection_strategy=args.candidate_selection_strategy,
        skip_perfect_score=not args.reflect_on_perfect_subsamples,
        log_dir=args.log_dir,
        track_stats=True,
        seed=args.seed,
        num_threads=args.num_threads,
    )
    optimized = optimizer.compile(student, trainset=train_examples, valset=dev_examples)
    optimized_scores = evaluate(
        optimized,
        dev_examples,
        args.feedback_mode,
        label="optimized_val",
        num_threads=args.eval_num_threads,
    )
    final_scores = {}
    for path in args.final_eval:
        eval_rows = load_jsonl(path)
        eval_examples = to_examples(eval_rows, args.label_field, args.feedback_variant, args.task, args.evidence_input_mode)
        baseline_summary = (
            summarize_scores(evaluate(
                student,
                eval_examples,
                args.feedback_mode,
                label=f"final_baseline:{path}",
                num_threads=args.eval_num_threads,
            ))
            if not args.skip_final_baseline
            else {}
        )
        final_scores[path] = {
            "baseline": baseline_summary,
            "optimized": summarize_scores(evaluate(
                optimized,
                eval_examples,
                args.feedback_mode,
                label=f"final_optimized:{path}",
                num_threads=args.eval_num_threads,
            )),
        }
        if args.task in {"real_followup_risk", "real_followup_structured_risk"}:
            final_scores[path]["threshold_calibrated"] = threshold_calibrated_summary(
                dev_rows=optimized_scores,
                test_rows=final_scores[path]["optimized"]["rows"],
            )

    result = {
        "model": args.model,
        "reflection_model": args.reflection_model,
        "feedback_mode": args.feedback_mode,
        "feedback_variant": args.feedback_variant,
        "task": args.task,
        "label_field": args.label_field,
        "evidence_input_mode": args.evidence_input_mode,
        "visible_program_style": args.visible_program_style,
        "task_max_tokens": args.task_max_tokens,
        "reflection_max_tokens": args.reflection_max_tokens,
        "train_examples": len(train_examples),
        "dev_examples": len(dev_examples),
        "max_metric_calls": args.max_metric_calls,
        "reflection_minibatch_size": args.reflection_minibatch_size,
        "candidate_selection_strategy": args.candidate_selection_strategy,
        "reflect_on_perfect_subsamples": args.reflect_on_perfect_subsamples,
        "eval_num_threads": args.eval_num_threads,
        "selection": args.selection,
        "baseline": summarize_scores(baseline_scores),
        "optimized": summarize_scores(optimized_scores),
        "final_eval": final_scores,
        "train_ids": [ex.example_id for ex in train_examples],
        "dev_ids": [ex.example_id for ex in dev_examples],
        "log_dir": args.log_dir,
    }
    output = Path(args.log_dir) / "dry_run_result.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


RELEASE_ACTION_RE = re.compile(
    r"\b("
    r"revis(?:e|ed|es|ing|ion|ions)|"
    r"amend(?:ed|ing|ment|ments)?|"
    r"add(?:ed|ing|itional)?|"
    r"delete(?:d|ing|ion)?|"
    r"remove(?:d|ing)?|"
    r"confirm(?:ed|ing)?|"
    r"supplement(?:ed|ing|al)?|"
    r"clarif(?:y|ied|ies|ication)|"
    r"will include|will revise|will update|will disclose"
    r")\b",
    re.IGNORECASE,
)


def select_rows(
    rows: list[dict[str, Any]],
    n: int,
    seed: int,
    label_field: str,
    strategy: str = "stratified",
) -> list[dict[str, Any]]:
    if n <= 0 or n >= len(rows):
        return list(rows)
    if strategy == "hard_release_boundary":
        return hard_release_boundary_sample(rows, n, seed, label_field)
    return stratified_sample(rows, n, seed, label_field)


def stratified_sample(rows: list[dict[str, Any]], n: int, seed: int, label_field: str) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    positives = [row for row in rows if effective_label(row, label_field) == "unresolved"]
    negatives = [row for row in rows if effective_label(row, label_field) != "unresolved"]
    rng.shuffle(positives)
    rng.shuffle(negatives)
    pos_n = min(len(positives), max(1, n // 2))
    neg_n = min(len(negatives), n - pos_n)
    sample = positives[:pos_n] + negatives[:neg_n]
    rng.shuffle(sample)
    return sample


def hard_release_boundary_sample(rows: list[dict[str, Any]], n: int, seed: int, label_field: str) -> list[dict[str, Any]]:
    """Sample cases that stress the most important SEC-followup boundary.

    Many company responses say they revised, added, deleted, confirmed, or will
    update a filing. Those action cues appear in both gold classes. This sampler
    gives GEPA more opportunities to learn when an apparent release cue is enough
    and when SEC staff still pursued the same obligation.
    """
    rng = random.Random(seed)
    positives = [row for row in rows if effective_label(row, label_field) == "unresolved"]
    negatives = [row for row in rows if effective_label(row, label_field) != "unresolved"]

    def has_release_action(row: dict[str, Any]) -> bool:
        return bool(RELEASE_ACTION_RE.search(str(row.get("company_response") or "")))

    def followup_rank(row: dict[str, Any]) -> int:
        relation = str(row.get("real_feedback_relation") or "")
        gap_type = str(row.get("real_feedback_gap_type") or "")
        if relation == "explicit_reissue":
            return 0
        if relation == "requests_missing_detail":
            return 1
        if gap_type in {"missing_specific_disclosure", "incomplete_accounting_analysis"}:
            return 2
        return 3

    def neg_rank(row: dict[str, Any]) -> int:
        # Hard negatives are cases with a visible action cue, especially when an
        # auxiliary text-only audit still found the response imperfect.
        triage = str(row.get("triage_label") or "")
        response_gap = effective_label(row, "response_gap_label")
        if response_gap == "unresolved" or triage in {"unresolved_self_contained", "external_doc_needed"}:
            return 0
        return 1

    pos_hard = [row for row in positives if has_release_action(row)]
    pos_rest = [row for row in positives if row not in pos_hard]
    neg_hard = [row for row in negatives if has_release_action(row)]
    neg_rest = [row for row in negatives if row not in neg_hard]

    rng.shuffle(pos_hard)
    rng.shuffle(pos_rest)
    rng.shuffle(neg_hard)
    rng.shuffle(neg_rest)
    pos_hard.sort(key=followup_rank)
    neg_hard.sort(key=neg_rank)

    pos_n = min(len(positives), max(1, n // 2))
    neg_n = min(len(negatives), n - pos_n)
    sample = (pos_hard + pos_rest)[:pos_n] + (neg_hard + neg_rest)[:neg_n]
    if len(sample) < n:
        used = {row.get("example_id") for row in sample}
        remainder = [row for row in rows if row.get("example_id") not in used]
        rng.shuffle(remainder)
        sample.extend(remainder[: n - len(sample)])
    rng.shuffle(sample)
    return sample


def to_examples(
    rows: list[dict[str, Any]],
    label_field: str,
    feedback_variant: str = "full",
    task: str = "response_gap",
    evidence_input_mode: str = "evidence_snippets",
) -> list[dspy.Example]:
    examples = []
    for row in rows:
        label = effective_label(row, label_field)
        fields = dict(
            example_id=row["example_id"],
            sec_comment=row["sec_comment"][:3000],
            company_response=row["company_response"][:3000],
            amended_evidence=build_amended_evidence_input(row, evidence_input_mode)[:4500],
            target_label=label,
            regulator_feedback=build_feedback_text(row, feedback_variant, task=task)[:3000],
            issue_category=row.get("issue_category") or "other",
            followup_type=(
                row.get("amended_evidence_evidence_relevance") if task == "visible_evidence_resolution" else
                row.get("real_feedback_relation")
                or row.get("real_feedback_gap_type")
                or row.get("text_gap_type")
                or row.get("verifier_failure_type")
                or "none"
            ),
            task=task,
        )
        example = dspy.Example(**fields)
        if task == "visible_evidence_resolution":
            example = example.with_inputs("sec_comment", "company_response", "amended_evidence")
        else:
            example = example.with_inputs("sec_comment", "company_response")
        examples.append(example)
    return examples


def effective_label(row: dict[str, Any], label_field: str) -> str:
    value = row.get(label_field)
    if value is None and label_field == "response_gap_label":
        value = "unresolved" if row.get("text_gap_label") == "unresolved_gap" else "resolved"
    if value is None:
        value = row.get("target_label", "resolved")
    lowered = str(value).strip().lower().replace("-", "_")
    if lowered in {"unresolved_gap", "unresolved", "not_resolved", "followup", "follow_up", "1", "true"}:
        return "unresolved"
    return "resolved"


def build_feedback_text(row: dict[str, Any], variant: str = "full", task: str = "response_gap") -> str:
    if task == "visible_evidence_resolution":
        label = effective_label(row, "visible_evidence_resolution_label")
        relevance = row.get("amended_evidence_evidence_relevance") or "[not recorded]"
        quote = compact_text(str(row.get("amended_evidence_supporting_quote") or ""), 900)
        summary = row.get("amended_evidence_evidence_summary") or "[not recorded]"
        missing = row.get("amended_evidence_missing_evidence") or "[not recorded]"
        if label == "resolved":
            return (
                f"Gold visible-evidence label: resolved. Evidence relevance: {relevance}. "
                f"Supporting quote: {quote or '[no quote]'}. Resolution basis: {summary}. "
                "Learn to require visible amended-filing evidence that covers all material elements of the SEC request."
            )
        return (
            f"Gold visible-evidence label: unresolved. Evidence relevance: {relevance}. "
            f"Supporting quote: {quote or '[no quote]'}. Visible unmet requirement: {missing}. "
            "Learn to compare the SEC request against the amended evidence and flag partial fixes, missing named items, "
            "missing quantification, omitted accounting/legal analysis, or lack of visible support."
        )

    is_real_followup_task = task in {"real_followup", "real_followup_risk", "real_followup_structured_risk"}
    event_label = effective_label(row, "regulator_followup_label") if is_real_followup_task else None

    if variant == "real_followup":
        feedback = str(row.get("real_followup_feedback") or row.get("real_feedback_text") or row.get("full_feedback") or "")
        if is_real_followup_task and event_label == "resolved":
            response_excerpt = compact_text(str(row.get("company_response") or ""), 900)
            return (
                f"{feedback} Resolution calibration: no verified same-obligation next-round SEC follow-up was "
                "observed. For the real-followup event task, treat this as resolved unless the current response "
                "plainly leaves a concrete SEC-requested item unmet. Use the company's present action as a "
                f"release cue when applicable. Company response excerpt: {response_excerpt}"
            )
        return feedback
    if variant == "hybrid_real_followup":
        if is_real_followup_task:
            real = str(row.get("real_followup_feedback") or row.get("real_feedback_text") or "").strip()
            response_excerpt = compact_text(str(row.get("company_response") or ""), 900)
            if event_label == "unresolved":
                base = build_feedback_text(row, "full", task=task)
                auxiliary = ""
                if effective_label(row, "response_gap_label") == "unresolved" and base:
                    auxiliary = f" Auxiliary text-gap analysis: {base}"
                return (
                    f"Gold event label: unresolved because SEC staff made a verified same-obligation next-round "
                    f"follow-up. Real SEC follow-up evidence: {real or '[missing real follow-up text]'} "
                    "Learn the concrete continuation cue, but do not generalize from generic caution alone."
                    f"{auxiliary}"
                )
            return (
                "Gold event label: resolved because no verified same-obligation next-round SEC follow-up was "
                "observed. This is an event label, not a requirement that the response letter reproduce the full "
                "amended filing. Calibrate down when the company makes a substantive present action such as "
                "revising, adding, deleting, confirming, quantifying, or explaining, unless the response itself "
                "plainly leaves a specific SEC-requested item unmet. Company response excerpt: "
                f"{response_excerpt}"
            )

        base = build_feedback_text(row, "full", task=task)
        real = str(row.get("real_followup_feedback") or row.get("real_feedback_text") or "").strip()
        if real and effective_label(row, "response_gap_label") == "unresolved":
            return (
                f"{base} Real SEC next-round evidence, when available: {real} "
                "Use the real follow-up text to identify the regulator's concrete unresolved obligation."
            )
        return base

    sec_request = row.get("text_gap_sec_request") or row.get("feedback_sec_request")
    response_action = row.get("text_gap_response_action") or row.get("feedback_company_action")
    gap_type = row.get("text_gap_type") or row.get("feedback_gap_type")
    current_action = row.get("text_gap_current_action") or row.get("feedback_current_action_type")
    unmet_requirement = row.get("text_gap_unmet_requirement") or row.get("feedback_unmet_requirement")
    resolution_basis = row.get("text_gap_resolution_basis") or row.get("feedback_resolution_basis")
    evidence = row.get("text_gap_evidence") or row.get("feedback_evidence")

    if sec_request or response_action:
        parts = [
            f"SEC request: {sec_request or '[not recorded]'}.",
            f"Company current action: {response_action or '[not recorded]'}.",
        ]

        if variant in {"full", "no_evidence", "no_unmet_requirement", "request_action_gap"}:
            parts.extend(
                [
                    f"Gap type: {gap_type or '[not recorded]'}.",
                    f"Current-action type: {current_action or '[not recorded]'}.",
                ]
            )

        if variant not in {"no_unmet_requirement", "request_action_gap", "request_action_only"}:
            if effective_label(row, "response_gap_label") == "unresolved":
                parts.append(f"Unmet requirement: {unmet_requirement or '[not recorded]'}.")
            else:
                parts.append(f"Resolution basis: {resolution_basis or '[not recorded]'}.")

        if variant == "full" and evidence:
            parts.append(f"Evidence: {evidence}.")
        return " ".join(parts)
    return str(row.get("full_feedback") or row.get("adjudicated_full_feedback") or row.get("regulator_feedback", ""))


def compact_text(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def build_amended_evidence_input(row: dict[str, Any], mode: str) -> str:
    if mode == "evidence_quote":
        quote = str(row.get("amended_evidence_supporting_quote") or "").strip()
        return f"Amended filing evidence quote:\n{quote if quote else '[no retrieved quote]'}"
    snippets = row.get("retrieved_snippets") or []
    formatted = []
    for index, snippet in enumerate(snippets[:3], start=1):
        formatted.append(
            f"[Snippet {index} | form={snippet.get('candidate_form')} | date={snippet.get('candidate_filing_date')}]\n"
            f"{str(snippet.get('snippet') or '')[:1400]}"
        )
    return "Retrieved amended filing snippets:\n" + ("\n\n".join(formatted) if formatted else "[none]")


def make_metric(mode: str, task: str = "response_gap"):
    def metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
        result = sec_metric(gold, pred, mode, task=task)
        return dspy.Prediction(score=result["score"], feedback=result["feedback"])

    return metric


def sec_metric(gold, pred, mode: str, task: str = "response_gap") -> dict[str, float | str]:
    actual_task = getattr(gold, "task", task)
    gold_obj = SecGoldExample(
        label=gold.target_label,
        regulator_feedback=getattr(gold, "regulator_feedback", ""),
        issue_category=getattr(gold, "issue_category", "other"),
        followup_type=getattr(gold, "followup_type", "none"),
        task=actual_task,
    )
    pred_label = getattr(pred, "label", "")
    if actual_task in {"real_followup_risk", "real_followup_structured_risk"}:
        score = parse_risk_score(getattr(pred, "risk_score", ""))
        pred_label = "unresolved" if score >= 50 else "resolved"
    pred_obj = SecPrediction(label=pred_label, reason=getattr(pred, "reason", ""))
    return score_sec_and_feedback(gold_obj, pred_obj, mode=mode)


def evaluate(program, examples, mode: str, label: str = "eval", num_threads: int = 1) -> list[dict[str, Any]]:
    if num_threads <= 1 or len(examples) <= 1:
        return evaluate_serial(program, examples, mode, label)

    total = len(examples)
    rows: list[dict[str, Any] | None] = [None] * total

    def run_one(index: int, example) -> tuple[int, dict[str, Any]]:
        prediction = program(**example.inputs())
        metric = sec_metric(example, prediction, mode)
        return index, {
            "example_id": example.example_id,
            "gold": example.target_label,
            "pred": prediction_label_for_row(example, prediction),
            "risk_score": getattr(prediction, "risk_score", ""),
            "sec_request_elements": getattr(prediction, "sec_request_elements", ""),
            "evidence_covered_elements": getattr(prediction, "evidence_covered_elements", ""),
            "missing_or_weak_elements": getattr(prediction, "missing_or_weak_elements", ""),
            "sec_obligation": getattr(prediction, "sec_obligation", ""),
            "company_action": getattr(prediction, "company_action", ""),
            "release_cue": getattr(prediction, "release_cue", ""),
            "continuation_cue": getattr(prediction, "continuation_cue", ""),
            "reason": getattr(prediction, "reason", ""),
            "reasoning": getattr(prediction, "reasoning", ""),
            "score": metric["score"],
            "feedback": metric["feedback"],
        }

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {
            executor.submit(run_one, index, example): (index, example)
            for index, example in enumerate(examples)
        }
        completed = 0
        for future in as_completed(futures):
            index, example = futures[future]
            _, row = future.result()
            rows[index] = row
            completed += 1
            print(f"[{label}] {completed}/{total} {example.example_id}", flush=True)

    return [row for row in rows if row is not None]


def evaluate_serial(program, examples, mode: str, label: str = "eval") -> list[dict[str, Any]]:
    scores = []
    total = len(examples)
    for index, example in enumerate(examples, start=1):
        print(f"[{label}] {index}/{total} {example.example_id}", flush=True)
        prediction = program(**example.inputs())
        metric = sec_metric(example, prediction, mode)
        scores.append(
            {
                "example_id": example.example_id,
                "gold": example.target_label,
                "pred": prediction_label_for_row(example, prediction),
                "risk_score": getattr(prediction, "risk_score", ""),
                "sec_request_elements": getattr(prediction, "sec_request_elements", ""),
                "evidence_covered_elements": getattr(prediction, "evidence_covered_elements", ""),
                "missing_or_weak_elements": getattr(prediction, "missing_or_weak_elements", ""),
                "sec_obligation": getattr(prediction, "sec_obligation", ""),
                "company_action": getattr(prediction, "company_action", ""),
                "release_cue": getattr(prediction, "release_cue", ""),
                "continuation_cue": getattr(prediction, "continuation_cue", ""),
                "reason": getattr(prediction, "reason", ""),
                "reasoning": getattr(prediction, "reasoning", ""),
                "score": metric["score"],
                "feedback": metric["feedback"],
            }
        )
    return scores


def summarize_scores(rows: list[dict[str, Any]]) -> dict[str, Any]:
    correct = sum(float(row["score"]) for row in rows)
    labels = {}
    for row in rows:
        labels.setdefault(row["gold"], {"support": 0, "correct": 0.0})
        labels[row["gold"]]["support"] += 1
        labels[row["gold"]]["correct"] += float(row["score"])
    class_report = classification_report(
        [str(row["gold"]).strip().lower() for row in rows],
        [normalize_prediction_label(str(row["pred"])) for row in rows],
        labels=["resolved", "unresolved"],
    )
    return {
        "accuracy": correct / len(rows) if rows else 0.0,
        "classification_report": class_report,
        "rows": rows,
        "by_gold_label": labels,
    }


def prediction_label_for_row(example, prediction) -> str:
    if getattr(example, "task", "") in {"real_followup_risk", "real_followup_structured_risk"}:
        return "unresolved" if parse_risk_score(getattr(prediction, "risk_score", "")) >= 50 else "resolved"
    return getattr(prediction, "label", "")


def parse_risk_score(value: Any) -> float:
    text = str(value).strip()
    number = ""
    seen_dot = False
    for char in text:
        if char.isdigit():
            number += char
        elif char == "." and number and not seen_dot:
            number += char
            seen_dot = True
        elif number:
            break
    if not number:
        return 50.0
    return max(0.0, min(100.0, float(number)))


def threshold_calibrated_summary(dev_rows: list[dict[str, Any]], test_rows: list[dict[str, Any]]) -> dict[str, Any]:
    best_threshold = 50
    best_macro = -1.0
    candidates = list(range(5, 100, 5))
    for threshold in candidates:
        pred = ["unresolved" if parse_risk_score(row.get("risk_score", "")) >= threshold else "resolved" for row in dev_rows]
        gold = [str(row["gold"]).strip().lower() for row in dev_rows]
        macro = classification_report(gold, pred, ["resolved", "unresolved"])["macro_avg"]["f1"]
        if macro > best_macro:
            best_macro = macro
            best_threshold = threshold

    test_pred = [
        "unresolved" if parse_risk_score(row.get("risk_score", "")) >= best_threshold else "resolved"
        for row in test_rows
    ]
    test_gold = [str(row["gold"]).strip().lower() for row in test_rows]
    return {
        "selected_threshold": best_threshold,
        "dev_macro_f1_at_threshold": best_macro,
        "test_classification_report": classification_report(test_gold, test_pred, ["resolved", "unresolved"]),
    }


def normalize_prediction_label(label: str) -> str:
    lowered = label.strip().lower().replace("-", "_")
    if "unresolved" in lowered or lowered in {"not_resolved", "followup", "follow_up", "1", "true"}:
        return "unresolved"
    return "resolved"


def classification_report(gold: list[str], pred: list[str], labels: list[str]) -> dict[str, Any]:
    report: dict[str, Any] = {}
    f1s = []
    for label in labels:
        tp = sum(1 for g, p in zip(gold, pred) if g == label and p == label)
        fp = sum(1 for g, p in zip(gold, pred) if g != label and p == label)
        fn = sum(1 for g, p in zip(gold, pred) if g == label and p != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        f1s.append(f1)
        report[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": sum(1 for g in gold if g == label),
        }
    report["macro_avg"] = {"f1": round(sum(f1s) / len(f1s), 4)}
    report["accuracy"] = round(sum(1 for g, p in zip(gold, pred) if g == p) / len(gold), 4) if gold else 0.0
    return report


if __name__ == "__main__":
    raise SystemExit(main())
