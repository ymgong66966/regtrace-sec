#!/usr/bin/env python3
"""Run CMS-2567 GEPA adaptation on plan-of-correction adequacy review.

This is the cross-regulatory analogue of the SEC evidence-grounded reviewer:
the model sees a regulator deficiency narrative and a provider plan of
correction, while GEPA may receive scalar/category/full feedback during
optimization. Hidden correction metadata is never provided to the predictor.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Literal

cache_dir = Path("outputs/dspy_cache")
cache_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("DSPY_CACHE_DIR", str(cache_dir.resolve()))

import dspy


LABELS = ("adequate", "not_adequate")
FeedbackMode = Literal["scalar", "category", "full"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", default="data/cms2567_poc_gepa_splits/grouped_seed17/train.jsonl")
    parser.add_argument("--dev", default="data/cms2567_poc_gepa_splits/grouped_seed17/dev.jsonl")
    parser.add_argument("--test", default="data/cms2567_poc_gepa_splits/grouped_seed17/test.jsonl")
    parser.add_argument("--train-size", type=int, default=220)
    parser.add_argument("--dev-size", type=int, default=70)
    parser.add_argument("--model", default="openai/gpt-4o-mini")
    parser.add_argument("--reflection-model", default="openai/gpt-4o-mini")
    parser.add_argument("--task-max-tokens", type=int, default=650)
    parser.add_argument("--reflection-max-tokens", type=int, default=1500)
    parser.add_argument("--feedback-mode", choices=["scalar", "category", "full"], default="full")
    parser.add_argument("--program-style", choices=["minimal", "calibrated", "structured"], default="structured")
    parser.add_argument("--max-metric-calls", type=int, default=80)
    parser.add_argument("--reflection-minibatch-size", type=int, default=4)
    parser.add_argument(
        "--candidate-selection-strategy",
        choices=["pareto", "current_best"],
        default="pareto",
    )
    parser.add_argument("--reflect-on-perfect-subsamples", action="store_true")
    parser.add_argument("--class-balanced-metric", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--num-threads", type=int, default=3)
    parser.add_argument("--eval-num-threads", type=int, default=4)
    parser.add_argument("--skip-pre-eval", action="store_true")
    parser.add_argument("--log-dir", default="outputs/cms2567_gepa_pilot/full_m80")
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")

    train_rows = load_jsonl(Path(args.train))
    dev_rows = load_jsonl(Path(args.dev))
    test_rows = load_jsonl(Path(args.test))
    class_weights = compute_class_weights(train_rows + dev_rows) if args.class_balanced_metric else {label: 1.0 for label in LABELS}

    train_examples = to_examples(select_rows(train_rows, args.train_size, args.seed), class_weights)
    dev_examples = to_examples(select_rows(dev_rows, args.dev_size, args.seed + 1), class_weights)
    test_examples = to_examples(test_rows, class_weights)

    lm = dspy.LM(args.model, temperature=0, max_tokens=args.task_max_tokens, cache=False)
    reflection_lm = dspy.LM(args.reflection_model, temperature=0.7, max_tokens=args.reflection_max_tokens, cache=False)
    dspy.configure(lm=lm)

    student = build_cms_program(args.program_style)
    pre_dev = [] if args.skip_pre_eval else evaluate(student, dev_examples, args.feedback_mode, label="pre_dev", num_threads=args.eval_num_threads)
    pre_test = [] if args.skip_pre_eval else evaluate(student, test_examples, args.feedback_mode, label="pre_test", num_threads=args.eval_num_threads)

    optimizer = dspy.GEPA(
        metric=make_metric(args.feedback_mode),
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
    opt_dev = evaluate(optimized, dev_examples, args.feedback_mode, label="opt_dev", num_threads=args.eval_num_threads)
    opt_test = evaluate(optimized, test_examples, args.feedback_mode, label="opt_test", num_threads=args.eval_num_threads)

    result = {
        "model": args.model,
        "reflection_model": args.reflection_model,
        "program_style": args.program_style,
        "feedback_mode": args.feedback_mode,
        "class_balanced_metric": args.class_balanced_metric,
        "class_weights": class_weights,
        "train_path": args.train,
        "dev_path": args.dev,
        "test_path": args.test,
        "train_examples": len(train_examples),
        "dev_examples": len(dev_examples),
        "test_examples": len(test_examples),
        "max_metric_calls": args.max_metric_calls,
        "reflection_minibatch_size": args.reflection_minibatch_size,
        "candidate_selection_strategy": args.candidate_selection_strategy,
        "reflect_on_perfect_subsamples": args.reflect_on_perfect_subsamples,
        "task_max_tokens": args.task_max_tokens,
        "reflection_max_tokens": args.reflection_max_tokens,
        "seed": args.seed,
        "baseline_dev": summarize(pre_dev),
        "baseline_test": summarize(pre_test),
        "optimized_dev": summarize(opt_dev),
        "optimized_test": summarize(opt_test),
        "train_ids": [example.example_id for example in train_examples],
        "dev_ids": [example.example_id for example in dev_examples],
        "test_ids": [example.example_id for example in test_examples],
        "log_dir": args.log_dir,
    }
    out_dir = Path(args.log_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_dir / "baseline_dev_predictions.jsonl", pre_dev)
    write_jsonl(out_dir / "baseline_test_predictions.jsonl", pre_test)
    write_jsonl(out_dir / "optimized_dev_predictions.jsonl", opt_dev)
    write_jsonl(out_dir / "optimized_test_predictions.jsonl", opt_test)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "summary.md").write_text(render_summary(result), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def build_cms_program(style: str):
    if style == "minimal":
        class CMSPlanReviewMinimal(dspy.Signature):
            """Classify whether a CMS Plan of Correction adequately resolves the deficiency."""

            deficiency_text: str = dspy.InputField()
            plan_of_correction_text: str = dspy.InputField()
            ftag: str = dspy.InputField()
            scope_severity: str = dspy.InputField()
            label: str = dspy.OutputField(desc="Exactly one of: adequate | not_adequate.")
            reason: str = dspy.OutputField(desc="Brief explanation.")

        return dspy.ChainOfThought(CMSPlanReviewMinimal)

    if style == "calibrated":
        class CMSPlanReviewCalibrated(dspy.Signature):
            """Review a CMS-2567 Plan of Correction for substantial adequacy.

            Extract the material deficiency, then decide whether the plan
            substantially addresses it. A plan need not be perfect. Label
            not_adequate only when a material cited component is missing, the
            plan is mostly boilerplate or future intent, or the plan misses the
            central deficient practice. Do not invent requirements beyond the
            deficiency narrative.
            """

            deficiency_text: str = dspy.InputField(desc="Regulator deficiency narrative.")
            plan_of_correction_text: str = dspy.InputField(desc="Provider written plan of correction.")
            ftag: str = dspy.InputField(desc="CMS F-tag.")
            scope_severity: str = dspy.InputField(desc="CMS scope/severity code.")
            label: str = dspy.OutputField(desc="Exactly one of: adequate | not_adequate.")
            reason: str = dspy.OutputField(desc="Brief explanation grounded in the deficiency and plan.")

        return dspy.ChainOfThought(CMSPlanReviewCalibrated)

    class CMSPlanReviewStructured(dspy.Signature):
        """Structured obligation-to-response reviewer for CMS-2567 plans.

        Work in this order:
        1. Identify the material obligations in the deficiency narrative.
        2. Identify which obligations the plan visibly covers.
        3. Identify material missing or weak obligations, if any.
        4. Decide whether the plan is adequate or not_adequate.

        Calibration:
        - adequate means substantially adequate, not perfect.
        - not_adequate requires a material gap tied to the cited deficiency.
        - generic training/auditing language is insufficient when it does not
          map to the central cited risk.
        - do not invent requirements beyond the deficiency narrative.
        """

        deficiency_text: str = dspy.InputField(desc="Regulator deficiency narrative.")
        plan_of_correction_text: str = dspy.InputField(desc="Provider written plan of correction.")
        ftag: str = dspy.InputField(desc="CMS F-tag.")
        scope_severity: str = dspy.InputField(desc="CMS scope/severity code.")
        material_obligations: str = dspy.OutputField(desc="Short list of material obligations from the deficiency.")
        covered_elements: str = dspy.OutputField(desc="Plan elements that visibly address those obligations.")
        missing_or_weak_elements: str = dspy.OutputField(desc="Material obligations still missing or weak.")
        label: str = dspy.OutputField(desc="Exactly one of: adequate | not_adequate.")
        reason: str = dspy.OutputField(desc="Brief final rationale.")

    return dspy.ChainOfThought(CMSPlanReviewStructured)


def select_rows(rows: list[dict[str, Any]], n: int, seed: int) -> list[dict[str, Any]]:
    if n <= 0 or n >= len(rows):
        return list(rows)
    rng = random.Random(seed)
    by_label = {label: [row for row in rows if row["cms_poc_binary_label"] == label] for label in LABELS}
    for label_rows in by_label.values():
        rng.shuffle(label_rows)
    target_pos = min(len(by_label["adequate"]), max(1, n // 2))
    target_neg = min(len(by_label["not_adequate"]), n - target_pos)
    sample = by_label["adequate"][:target_pos] + by_label["not_adequate"][:target_neg]
    if len(sample) < n:
        used = {row["example_id"] for row in sample}
        rest = [row for row in rows if row["example_id"] not in used]
        rng.shuffle(rest)
        sample.extend(rest[: n - len(sample)])
    rng.shuffle(sample)
    return sample


def to_examples(rows: list[dict[str, Any]], class_weights: dict[str, float]) -> list[dspy.Example]:
    examples = []
    for row in rows:
        label = normalize_label(row["cms_poc_binary_label"])
        feedback = build_feedback_text(row)
        example = dspy.Example(
            example_id=row["example_id"],
            deficiency_text=compact_text(str(row.get("deficiency_text") or ""), 5600),
            plan_of_correction_text=compact_text(str(row.get("plan_of_correction_text") or ""), 4400),
            ftag=str(row.get("ftag") or ""),
            scope_severity=str(row.get("scope_severity") or ""),
            target_label=label,
            three_way_label=str(row.get("cms_poc_adequacy_label") or ""),
            feedback_category=str(row.get("ftag_group") or "other"),
            severity_band=str(row.get("severity_band") or ""),
            regulator_feedback=feedback,
            class_weight=float(class_weights.get(label, 1.0)),
        ).with_inputs("deficiency_text", "plan_of_correction_text", "ftag", "scope_severity")
        examples.append(example)
    return examples


def build_feedback_text(row: dict[str, Any]) -> str:
    label = normalize_label(row.get("cms_poc_binary_label"))
    three = str(row.get("cms_poc_adequacy_label") or "")
    covered = "; ".join(str(item) for item in row.get("cms_poc_covered_elements") or []) or "[none recorded]"
    missing = "; ".join(str(item) for item in row.get("cms_poc_missing_elements") or []) or "[none recorded]"
    reason = str(row.get("cms_poc_reason") or "")
    optimizer = str(row.get("cms_poc_optimizer_feedback") or "")
    if label == "adequate":
        return (
            f"Gold label: adequate. Three-way adequacy label: {three}. "
            f"Covered elements: {covered}. Reason: {reason} "
            "Preserve this calibration: the plan need only substantially address the central deficiency; "
            "do not over-require extra detail beyond the cited obligation."
        )
    return (
        f"Gold label: not_adequate. Three-way adequacy label: {three}. "
        f"Covered elements: {covered}. Missing or weak elements: {missing}. Reason: {reason} "
        f"Reviewer improvement feedback: {optimizer} "
        "Learn to flag material omissions tied to the deficiency narrative, not just boilerplate weakness."
    )


def make_metric(mode: FeedbackMode):
    def metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
        result = cms_metric(gold, pred, mode)
        return dspy.Prediction(score=result["score"], feedback=result["feedback"])

    return metric


def cms_metric(gold, pred, mode: FeedbackMode) -> dict[str, float | str]:
    gold_label = normalize_label(getattr(gold, "target_label", "not_adequate"))
    pred_label = normalize_label(getattr(pred, "label", "not_adequate"))
    correct = gold_label == pred_label
    weight = float(getattr(gold, "class_weight", 1.0) or 1.0)
    score = weight if correct else 0.0
    if mode == "scalar":
        feedback = f"{'Correct' if correct else 'Wrong'} (score {score:.3f})."
    elif mode == "category":
        feedback = (
            f"score {score:.3f}. Gold label: {gold_label}. Three-way label: {getattr(gold, 'three_way_label', '')}. "
            f"CMS category: {getattr(gold, 'feedback_category', 'other')}; severity: {getattr(gold, 'severity_band', '')}."
        )
    else:
        rationale = getattr(gold, "regulator_feedback", "")
        if correct:
            feedback = f"score {score:.3f}. Correct {gold_label} call. {rationale}"
        elif gold_label == "adequate":
            feedback = (
                f"score {score:.3f}. False positive. Gold is adequate. {rationale} "
                "Calibrate down: substantial adequacy is enough when the plan covers the central cited practice, "
                "at-risk residents, prevention, monitoring, and timing at a practical level."
            )
        else:
            feedback = (
                f"score {score:.3f}. False negative. Gold is not_adequate. {rationale} "
                "Calibrate up: identify the material cited deficiency component that the plan does not visibly answer."
            )
    return {"score": score, "feedback": feedback}


def evaluate(program, examples, mode: FeedbackMode, label: str, num_threads: int = 1) -> list[dict[str, Any]]:
    if not examples:
        return []
    if num_threads <= 1 or len(examples) <= 1:
        out = []
        for index, example in enumerate(examples, start=1):
            print(f"[{label}] {index}/{len(examples)} {example.example_id}", flush=True)
            out.append(run_one(program, example, mode))
        return out

    rows: list[dict[str, Any] | None] = [None] * len(examples)
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {executor.submit(run_one, program, example, mode): (index, example) for index, example in enumerate(examples)}
        done = 0
        for future in as_completed(futures):
            index, example = futures[future]
            rows[index] = future.result()
            done += 1
            print(f"[{label}] {done}/{len(examples)} {example.example_id}", flush=True)
    return [row for row in rows if row is not None]


def run_one(program, example, mode: FeedbackMode) -> dict[str, Any]:
    prediction = program(**example.inputs())
    metric = cms_metric(example, prediction, mode)
    return {
        "example_id": example.example_id,
        "gold": example.target_label,
        "pred": normalize_label(getattr(prediction, "label", "")),
        "correct": normalize_label(getattr(prediction, "label", "")) == example.target_label,
        "score": metric["score"],
        "feedback": metric["feedback"],
        "material_obligations": getattr(prediction, "material_obligations", ""),
        "covered_elements": getattr(prediction, "covered_elements", ""),
        "missing_or_weak_elements": getattr(prediction, "missing_or_weak_elements", ""),
        "reason": getattr(prediction, "reason", ""),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    gold = [row["gold"] for row in rows]
    pred = [row["pred"] for row in rows]
    return {
        "accuracy": round(sum(row["correct"] for row in rows) / len(rows), 4),
        "macro_f1": macro_f1(gold, pred),
        "label_counts": dict(Counter(gold)),
        "pred_counts": dict(Counter(pred)),
        "per_label": {label: prf(gold, pred, label) for label in LABELS},
    }


def macro_f1(gold: list[str], pred: list[str]) -> float:
    return round(sum(prf(gold, pred, label)["f1"] for label in LABELS) / len(LABELS), 4)


def prf(gold: list[str], pred: list[str], label: str) -> dict[str, float]:
    tp = sum(1 for g, p in zip(gold, pred) if g == label and p == label)
    fp = sum(1 for g, p in zip(gold, pred) if g != label and p == label)
    fn = sum(1 for g, p in zip(gold, pred) if g == label and p != label)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4), "support": gold.count(label)}


def compute_class_weights(rows: list[dict[str, Any]]) -> dict[str, float]:
    counts = Counter(normalize_label(row["cms_poc_binary_label"]) for row in rows)
    total = sum(counts.values())
    return {label: round(total / (len(LABELS) * max(counts.get(label, 1), 1)), 4) for label in LABELS}


def normalize_label(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_")
    if "not_adequate" in text or "not adequate" in text or "inadequate" in text or "partial" in text:
        return "not_adequate"
    if "adequate" in text:
        return "adequate"
    return "not_adequate"


def compact_text(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def render_summary(result: dict[str, Any]) -> str:
    lines = [
        "# CMS-2567 GEPA Pilot",
        "",
        f"- Model: `{result['model']}`",
        f"- Program style: `{result['program_style']}`",
        f"- Feedback mode: `{result['feedback_mode']}`",
        f"- Train/dev/test: {result['train_examples']}/{result['dev_examples']}/{result['test_examples']}",
        f"- Class-balanced metric: `{result['class_balanced_metric']}`",
        f"- Max metric calls: {result['max_metric_calls']}",
        "",
        "| stage | accuracy | macro-F1 | adequate F1 | not adequate F1 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name, key in [
        ("baseline dev", "baseline_dev"),
        ("optimized dev", "optimized_dev"),
        ("baseline test", "baseline_test"),
        ("optimized test", "optimized_test"),
    ]:
        summary = result.get(key) or {}
        if not summary:
            continue
        lines.append(
            f"| {name} | {summary['accuracy']:.4f} | {summary['macro_f1']:.4f} | "
            f"{summary['per_label']['adequate']['f1']:.4f} | {summary['per_label']['not_adequate']['f1']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Label Counts",
            "",
            "```json",
            json.dumps(result.get("optimized_test", {}).get("label_counts", {}), indent=2, ensure_ascii=False),
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
