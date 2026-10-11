#!/usr/bin/env python3
"""Model-as-expert audit for the 80-row RegTrace-SEC audit sheet.

This script fills the human-audit columns in a copy of the CSV. The model does
not see the benchmark label, prior independent audit label, GEPA predictions,
baseline predictions, generated feedback fields, or later SEC follow-up. It
audits the visible-evidence question directly from:

  SEC request + company response + retrieved amended evidence snippet.

That makes the resulting audit useful as an independent label-quality check.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openai import OpenAI

from pressback.costs import append_usage_record, cost_for_tokens, estimate_text_tokens


LABELS = ("resolved", "unresolved", "unclear")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="docs/review_response/sec_label_audit_sheet_80.csv")
    parser.add_argument("--output-csv", default="")
    parser.add_argument("--out-dir", default="outputs/sec_label_audit_sheet_gpt56sol_max")
    parser.add_argument("--usage-ledger", default="outputs/openai_usage_ledger.jsonl")
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--reasoning-effort", default="max", choices=["low", "medium", "high", "xhigh", "max"])
    parser.add_argument("--max-output-tokens", type=int, default=1800)
    parser.add_argument("--num-threads", type=int, default=2)
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument(
        "--include-followup-reference",
        action="store_true",
        help="Allow the auditor to use later same-topic SEC follow-up text as external corroboration.",
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--estimate-only", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input)
    rows, fieldnames = load_csv(input_path)
    if args.max_rows > 0:
        rows = rows[: args.max_rows]

    estimate = estimate_cost(
        rows,
        args.model,
        args.max_output_tokens,
        include_followup_reference=args.include_followup_reference,
    )
    if args.estimate_only:
        print(json.dumps(estimate, indent=2, ensure_ascii=False))
        return 0

    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    prediction_path = out_dir / "audit_predictions.jsonl"
    output_csv = Path(args.output_csv) if args.output_csv else input_path.with_name(
        input_path.stem + f"_{slug(args.model)}_{args.reasoning_effort}_audited.csv"
    )

    if not args.resume and prediction_path.exists():
        prediction_path.unlink()
    completed = load_jsonl(prediction_path) if args.resume and prediction_path.exists() else []
    completed_by_id = {str(row.get("audit_id") or row.get("example_id")): row for row in completed}
    remaining = [row for row in rows if row_id(row) not in completed_by_id]
    if args.resume:
        print(f"[audit-sheet] resume completed={len(completed_by_id)} remaining={len(remaining)}", flush=True)

    runner = Runner(
        client=OpenAI(),
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        max_output_tokens=args.max_output_tokens,
        usage_ledger=args.usage_ledger,
        include_followup_reference=args.include_followup_reference,
    )
    new_predictions = evaluate_rows(runner, remaining, args.num_threads, checkpoint_path=prediction_path)
    all_predictions = completed + new_predictions
    all_predictions.sort(key=lambda row: str(row.get("audit_id") or row.get("example_id") or ""))
    write_jsonl(prediction_path, all_predictions)

    predictions_by_id = {str(row.get("audit_id") or row.get("example_id")): row for row in all_predictions}
    audited_rows = []
    for row in rows:
        prediction = predictions_by_id.get(row_id(row), {})
        audited = dict(row)
        audited["human_label"] = prediction.get("audit_label", "")
        audited["human_label_confidence"] = prediction.get("confidence_level", "")
        audited["evidence_sufficient"] = prediction.get("evidence_sufficient", "")
        audited["human_notes"] = prediction.get("audit_notes", "")
        audited["auditor_model"] = args.model
        audited["auditor_reasoning_effort"] = args.reasoning_effort
        audited["auditor_confidence_score"] = str(prediction.get("confidence_score", ""))
        audited["auditor_visible_gap"] = prediction.get("visible_gap", "")
        audited_rows.append(audited)

    extra_fields = [
        "auditor_model",
        "auditor_reasoning_effort",
        "auditor_confidence_score",
        "auditor_visible_gap",
    ]
    write_csv(output_csv, audited_rows, fieldnames + [name for name in extra_fields if name not in fieldnames])

    summary = summarize(rows, all_predictions)
    result = {
        "input_csv": str(input_path),
        "output_csv": str(output_csv),
        "prediction_jsonl": str(prediction_path),
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "include_followup_reference": args.include_followup_reference,
        "estimate": estimate,
        "summary": summary,
        "blind_input_fields": ["sec_comment", "company_response", "amended_evidence_best_snippet"],
        "withheld_fields": [
            "visible_evidence_resolution_label",
            "independent_audit_label",
            "gepa_full_pred",
            "baseline_pred",
            "feedback_sec_request",
            "feedback_company_action",
            "feedback_evidence_summary",
            "feedback_unmet_requirement",
            "real_followup_text",
            "followup_corroboration_label",
        ],
    }
    if args.include_followup_reference:
        result["audit_input_fields"] = [
            "sec_comment",
            "company_response",
            "amended_evidence_best_snippet",
            "real_followup_text",
            "followup_corroboration_label",
        ]
    (out_dir / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    write_summary_md(out_dir / "summary.md", result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


class Runner:
    def __init__(
        self,
        *,
        client: OpenAI,
        model: str,
        reasoning_effort: str,
        max_output_tokens: int,
        usage_ledger: str | None,
        include_followup_reference: bool,
    ) -> None:
        self.client = client
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.max_output_tokens = max_output_tokens
        self.usage_ledger = usage_ledger
        self.include_followup_reference = include_followup_reference

    def predict(self, row: dict[str, str]) -> dict[str, Any]:
        started = time.time()
        response = self.client.responses.create(
            model=self.model,
            instructions=system_prompt(include_followup_reference=self.include_followup_reference),
            input=user_prompt(row, include_followup_reference=self.include_followup_reference),
            reasoning={"effort": self.reasoning_effort},
            max_output_tokens=self.max_output_tokens,
            text={"format": {"type": "json_object"}},
        )
        elapsed = time.time() - started
        usage = responses_usage_to_dict(response.usage)
        cost = cost_for_tokens(self.model, usage["input_tokens"], usage["output_tokens"])
        append_usage_record(
            self.usage_ledger,
            purpose="sec_audit_sheet_model_as_expert",
            model=self.model,
            usage=usage,
            estimated_cost_usd=cost,
        )
        parsed = parse_json(response.output_text or "{}")
        label = normalize_label(parsed.get("human_label") or parsed.get("label"))
        evidence_sufficient = normalize_evidence(parsed.get("evidence_sufficient"))
        confidence_score = parse_float(parsed.get("confidence_score") or parsed.get("confidence"))
        confidence_level = normalize_confidence(parsed.get("human_label_confidence"), confidence_score)
        return {
            "audit_id": row.get("audit_id"),
            "example_id": row.get("example_id"),
            "review_thread_id": row.get("review_thread_id"),
            "issue_category": row.get("issue_category"),
            "gap_type": row.get("gap_type"),
            "benchmark_label": row.get("visible_evidence_resolution_label"),
            "audit_label": label,
            "confidence_level": confidence_level,
            "confidence_score": confidence_score,
            "evidence_sufficient": evidence_sufficient,
            "audit_notes": one_line(parsed.get("human_notes") or parsed.get("reason"), 900),
            "visible_gap": one_line(parsed.get("visible_gap"), 900),
            "material_sec_request": one_line(parsed.get("material_sec_request"), 700),
            "visible_company_action": one_line(parsed.get("visible_company_action"), 700),
            "usage": usage,
            "estimated_cost_usd": cost,
            "latency_sec": round(elapsed, 3),
        }


def system_prompt(*, include_followup_reference: bool) -> str:
    if include_followup_reference:
        return (
            "You are a senior SEC disclosure-review auditor performing a follow-up-informed benchmark audit. "
            "You may use four sources: the SEC's initial comment, the company response, the retrieved amended-filing "
            "evidence snippet, and later same-topic SEC follow-up when provided. The later follow-up is not a perfect "
            "gold label, but it is strong external regulatory corroboration when it directly reissues, narrows, or "
            "repeats the same material requirement.\n\n"
            "Use these labels:\n"
            "- resolved: the visible evidence substantially satisfies the material SEC request, and any later follow-up "
            "does not directly reissue the same unmet requirement.\n"
            "- unresolved: the visible evidence misses a material requested item, or a later same-topic SEC follow-up "
            "directly or partially corroborates that the same material issue remained open.\n"
            "- unclear: reserve this for genuinely indeterminate cases where the evidence is incomplete and there is "
            "no direct or partial same-topic follow-up to disambiguate.\n\n"
            "Calibration: if followup_corroboration_label is direct_corroboration or partial_corroboration and the "
            "follow-up text asks for the same substance, prefer unresolved over unclear. If there is no follow-up, do "
            "not treat absence as proof of resolution; judge from the visible evidence. Do not over-require beyond the "
            "initial SEC request. Return only valid json."
        )
    return (
        "You are a senior SEC disclosure-review auditor performing a blind quality audit of a benchmark label. "
        "You must judge only from the runtime-visible materials supplied to you: the SEC comment, the company's "
        "response, and the retrieved amended-filing evidence snippet. Do not assume unseen amended pages, later SEC "
        "letters, benchmark labels, prior model rationales, or generated feedback fields. The audit question is: "
        "does the visible amended evidence substantially show that the company resolved the material SEC request?\n\n"
        "Use these labels:\n"
        "- resolved: the visible amended evidence substantially satisfies all material parts of the SEC request.\n"
        "- unresolved: the visible evidence affirmatively shows that a material requested item remains missing, "
        "partial, unsupported, unquantified, or analytically incomplete.\n"
        "- unclear: the company claims a revision or separate filing, but the visible evidence snippet is not enough "
        "to verify resolution or non-resolution.\n\n"
        "Set evidence_sufficient consistently with the label: yes for resolved, no for unresolved, and partial for "
        "unclear. If the evidence is only partial but still substantially satisfies the material request, choose "
        "resolved and evidence_sufficient=yes; explain the immaterial caveat in human_notes.\n\n"
        "Important calibration: do not mark a row unresolved merely because the company response itself is short. "
        "If the visible amended evidence supplies the requested substance, mark resolved. Conversely, do not mark "
        "resolved merely because the company says it revised the filing; the visible evidence must show the substance. "
        "Return only valid json."
    )


def user_prompt(row: dict[str, str], *, include_followup_reference: bool) -> str:
    prompt = (
        "Audit this SEC visible-evidence case and return json with exactly these keys: "
        "human_label, human_label_confidence, confidence_score, evidence_sufficient, "
        "material_sec_request, visible_company_action, visible_gap, human_notes.\n\n"
        f"Audit ID: {row.get('audit_id')}\n"
        f"Issue category: {row.get('issue_category')}\n\n"
        "SEC comment:\n"
        f"{clip(row.get('sec_comment', ''), 5000)}\n\n"
        "Company response:\n"
        f"{clip(row.get('company_response', ''), 5000)}\n\n"
        "Visible amended-filing evidence snippet:\n"
        f"{clip(row.get('amended_evidence_best_snippet', ''), 7000)}\n\n"
    )
    if include_followup_reference:
        prompt += (
            "Later SEC follow-up metadata and text, for external corroboration:\n"
            f"has_real_followup: {row.get('has_real_followup')}\n"
            f"followup_corroboration_label: {row.get('followup_corroboration_label')}\n"
            "real_followup_text:\n"
            f"{clip(row.get('real_followup_text', ''), 3500)}\n\n"
        )
    return prompt + "Remember: output valid json only."


def estimate_cost(
    rows: list[dict[str, str]],
    model: str,
    max_output_tokens: int,
    *,
    include_followup_reference: bool,
) -> dict[str, Any]:
    input_tokens = 0
    for row in rows:
        input_tokens += 650
        input_tokens += estimate_text_tokens(row.get("sec_comment", "")[:5000])
        input_tokens += estimate_text_tokens(row.get("company_response", "")[:5000])
        input_tokens += estimate_text_tokens(row.get("amended_evidence_best_snippet", "")[:7000])
        if include_followup_reference:
            input_tokens += 180
            input_tokens += estimate_text_tokens(row.get("real_followup_text", "")[:3500])
    output_tokens = len(rows) * max_output_tokens
    return {
        "rows": len(rows),
        "model": model,
        "input_tokens_est": input_tokens,
        "output_tokens_upper_bound": output_tokens,
        "cost_usd_upper_bound_est": cost_for_tokens(model, input_tokens, output_tokens),
    }


def evaluate_rows(
    runner: Runner,
    rows: list[dict[str, str]],
    num_threads: int,
    *,
    checkpoint_path: Path | None = None,
) -> list[dict[str, Any]]:
    if num_threads <= 1:
        out = []
        for index, row in enumerate(rows, start=1):
            print(f"[audit-sheet] {index}/{len(rows)} {row_id(row)}", flush=True)
            prediction = runner.predict(row)
            out.append(prediction)
            append_jsonl(checkpoint_path, prediction)
        return out

    out: list[dict[str, Any] | None] = [None] * len(rows)
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {executor.submit(runner.predict, row): (idx, row) for idx, row in enumerate(rows)}
        done = 0
        for future in as_completed(futures):
            idx, row = futures[future]
            prediction = future.result()
            out[idx] = prediction
            append_jsonl(checkpoint_path, prediction)
            done += 1
            print(f"[audit-sheet] {done}/{len(rows)} {row_id(row)}", flush=True)
    return [row for row in out if row is not None]


def summarize(source_rows: list[dict[str, str]], predictions: list[dict[str, Any]]) -> dict[str, Any]:
    source_by_id = {row_id(row): row for row in source_rows}
    counts = Counter(row.get("audit_label") for row in predictions)
    evidence_counts = Counter(row.get("evidence_sufficient") for row in predictions)
    confidence_counts = Counter(row.get("confidence_level") for row in predictions)
    benchmark_pairs = []
    for pred in predictions:
        source = source_by_id.get(str(pred.get("audit_id") or pred.get("example_id")), {})
        gold = normalize_binary_label(source.get("visible_evidence_resolution_label"))
        audit = pred.get("audit_label")
        if gold and audit in {"resolved", "unresolved"}:
            benchmark_pairs.append((gold, audit))
    return {
        "rows": len(predictions),
        "audit_label_counts": dict(counts),
        "evidence_sufficient_counts": dict(evidence_counts),
        "confidence_counts": dict(confidence_counts),
        "mean_confidence_score": round(
            sum(float(row.get("confidence_score") or 0) for row in predictions) / len(predictions), 4
        )
        if predictions
        else 0,
        "estimated_cost_usd": round(sum(float(row.get("estimated_cost_usd") or 0) for row in predictions), 6),
        "binary_agreement_excluding_unclear": binary_report(benchmark_pairs),
        "by_issue_category": grouped_counts(predictions, "issue_category"),
        "by_gap_type": grouped_counts(predictions, "gap_type"),
    }


def binary_report(pairs: list[tuple[str, str]]) -> dict[str, Any]:
    if not pairs:
        return {}
    correct = sum(1 for gold, pred in pairs if gold == pred)
    out: dict[str, Any] = {"n": len(pairs), "accuracy": round(correct / len(pairs), 4)}
    for label in ("resolved", "unresolved"):
        tp = sum(1 for gold, pred in pairs if gold == label and pred == label)
        fp = sum(1 for gold, pred in pairs if gold != label and pred == label)
        fn = sum(1 for gold, pred in pairs if gold == label and pred != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        out[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": sum(1 for gold, _ in pairs if gold == label),
        }
    out["macro_f1"] = round((out["resolved"]["f1"] + out["unresolved"]["f1"]) / 2, 4)
    return out


def grouped_counts(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    out = {}
    for value in sorted({str(row.get(key) or "unknown") for row in rows}):
        group = [row for row in rows if str(row.get(key) or "unknown") == value]
        if len(group) < 3:
            continue
        out[value] = {"n": len(group), "labels": dict(Counter(row.get("audit_label") for row in group))}
    return out


def write_summary_md(path: Path, result: dict[str, Any]) -> None:
    summary = result["summary"]
    report = summary.get("binary_agreement_excluding_unclear") or {}
    followup_mode = bool(result.get("include_followup_reference"))
    title = "GPT-5.6-Sol Follow-up-Informed Model-as-Expert Audit" if followup_mode else "GPT-5.6-Sol Blind Model-as-Expert Audit"
    input_note = (
        "The auditor could use later same-topic SEC follow-up as external corroboration, but did not see benchmark labels, prior audit labels, GEPA/baseline predictions, or generated feedback fields."
        if followup_mode
        else "The auditor was blind to benchmark labels, prior audit labels, GEPA/baseline predictions, generated feedback fields, and later SEC follow-up."
    )
    lines = [
        f"# {title}",
        "",
        f"Model: `{result['model']}`",
        f"Reasoning effort: `{result['reasoning_effort']}`",
        "",
        input_note,
        "",
        "| Item | Value |",
        "|---|---:|",
        f"| Rows | {summary['rows']} |",
        f"| Estimated actual cost USD | {summary['estimated_cost_usd']:.6f} |",
        f"| Mean confidence score | {summary['mean_confidence_score']:.4f} |",
        f"| Unclear labels | {summary['audit_label_counts'].get('unclear', 0)} |",
    ]
    if report:
        lines.extend(
            [
                f"| Binary agreement rows, excluding unclear | {report['n']} |",
                f"| Agreement accuracy vs benchmark | {report['accuracy']:.4f} |",
                f"| Macro-F1 vs benchmark | {report['macro_f1']:.4f} |",
            ]
        )
    lines.extend(
        [
            "",
            "## Audit Label Counts",
            "",
            "```json",
            json.dumps(summary["audit_label_counts"], indent=2, ensure_ascii=False),
            "```",
            "",
            "## Evidence Sufficiency Counts",
            "",
            "```json",
            json.dumps(summary["evidence_sufficient_counts"], indent=2, ensure_ascii=False),
            "```",
            "",
            "This is still model-assisted validation, not licensed legal or accounting expert review.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def load_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def append_jsonl(path: Path | None, row: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if match:
            return json.loads(match.group(0))
    return {
        "human_label": "unclear",
        "human_label_confidence": "low",
        "confidence_score": 0.0,
        "evidence_sufficient": "partial",
        "human_notes": "Parse failure.",
        "visible_gap": "Parse failure.",
    }


def responses_usage_to_dict(usage: Any) -> dict[str, int]:
    if usage is None:
        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    return {
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
    }


def normalize_label(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_")
    if "unclear" in text or "cannot" in text or "insufficient" in text:
        return "unclear"
    if "unresolved" in text:
        return "unresolved"
    if "resolved" in text:
        return "resolved"
    return "unclear"


def normalize_binary_label(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_")
    if "unresolved" in text:
        return "unresolved"
    if "resolved" in text:
        return "resolved"
    return ""


def normalize_evidence(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"yes", "no", "partial"}:
        return text
    if "yes" in text or "sufficient" in text:
        return "yes"
    if "no" in text or "missing" in text:
        return "no"
    return "partial"


def normalize_confidence(value: Any, score: float) -> str:
    text = str(value or "").strip().lower()
    if text in {"high", "medium", "low"}:
        return text
    if score >= 0.8:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


def parse_float(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def clip(text: str, limit: int) -> str:
    text = str(text or "")
    return text if len(text) <= limit else text[:limit] + "\n[truncated]"


def one_line(value: Any, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]


def row_id(row: dict[str, Any]) -> str:
    return str(row.get("audit_id") or row.get("example_id") or "")


def slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).replace("/", "__")


if __name__ == "__main__":
    raise SystemExit(main())
