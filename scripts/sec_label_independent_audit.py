#!/usr/bin/env python3
"""Independent LLM audit for RegTrace-SEC visible-evidence labels.

The auditor sees only test-time fields: SEC comment, company response, and raw
retrieved amended-filing snippets. It does not see gold labels, feedback fields,
oracle evidence summaries, missing-requirement fields, or later SEC follow-up.
"""

from __future__ import annotations

import argparse
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


LABELS = ("resolved", "unresolved")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/sec_visible_evidence_benchmark_v2/sec_visible_evidence_benchmark_v2.jsonl")
    parser.add_argument("--model", default="gpt-5.4-mini")
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--num-threads", type=int, default=4)
    parser.add_argument("--max-tokens", type=int, default=520)
    parser.add_argument("--out-dir", default="outputs/sec_label_independent_audit")
    parser.add_argument("--usage-ledger", default="outputs/openai_usage_ledger.jsonl")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--estimate-only", action="store_true")
    args = parser.parse_args()

    rows = load_jsonl(Path(args.input))
    if args.max_rows > 0:
        rows = rows[: args.max_rows]

    estimate = estimate_cost(rows, args.model, args.max_tokens)
    if args.estimate_only:
        print(json.dumps(estimate, indent=2, ensure_ascii=False))
        return 0
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")

    out_dir = Path(args.out_dir) / model_slug(args.model)
    out_dir.mkdir(parents=True, exist_ok=True)
    pred_path = out_dir / "audit_predictions.jsonl"

    completed = load_jsonl(pred_path) if args.resume and pred_path.exists() else []
    completed_ids = {row.get("example_id") for row in completed}
    remaining = [row for row in rows if row.get("example_id") not in completed_ids]
    if args.resume:
        print(f"[label_audit] resume loaded={len(completed)} remaining={len(remaining)}", flush=True)

    runner = Runner(client=OpenAI(), model=args.model, max_tokens=args.max_tokens, usage_ledger=args.usage_ledger)
    new_predictions = evaluate_rows(runner, remaining, args.num_threads)
    predictions = completed + new_predictions
    predictions.sort(key=lambda row: row.get("example_id", ""))
    write_jsonl(pred_path, predictions)

    summary = summarize(predictions)
    result = {
        "input": args.input,
        "model": args.model,
        "num_rows": len(predictions),
        "estimate": estimate,
        "summary": summary,
        "model_input_fields": ["sec_comment", "company_response", "retrieved_snippets[:3].snippet"],
        "held_out_fields": [
            "visible_evidence_resolution_label",
            "scalar_feedback",
            "category_feedback",
            "full_feedback",
            "feedback_sec_request",
            "feedback_company_action",
            "feedback_evidence_summary",
            "feedback_unmet_requirement",
            "amended_evidence_evidence_summary",
            "amended_evidence_missing_evidence",
            "real_followup_text",
        ],
    }
    (out_dir / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    write_metrics_md(out_dir / "metrics.md", result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


class Runner:
    def __init__(self, *, client: OpenAI, model: str, max_tokens: int, usage_ledger: str | None) -> None:
        self.client = client
        self.model = model
        self.max_tokens = max_tokens
        self.usage_ledger = usage_ledger

    def predict(self, row: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        request_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": build_messages(row),
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        if self.model.startswith("gpt-5"):
            request_kwargs["max_completion_tokens"] = self.max_tokens
        else:
            request_kwargs["max_tokens"] = self.max_tokens
        response = self.client.chat.completions.create(**request_kwargs)
        elapsed = time.time() - started
        usage = usage_to_dict(response.usage)
        cost = cost_for_tokens(self.model, usage["prompt_tokens"], usage["completion_tokens"])
        append_usage_record(
            self.usage_ledger,
            purpose="sec_label_independent_audit",
            model=self.model,
            usage=usage,
            estimated_cost_usd=cost,
        )
        parsed = parse_json_prediction(response.choices[0].message.content or "{}")
        pred = normalize_label(parsed.get("label", ""))
        gold = normalize_label(row.get("visible_evidence_resolution_label", ""))
        confidence = parse_float(parsed.get("confidence"))
        return {
            "example_id": row.get("example_id"),
            "gold": gold,
            "audit_label": pred,
            "agree": pred == gold,
            "confidence": confidence,
            "reason": str(parsed.get("reason", ""))[:1800],
            "visible_gap": str(parsed.get("visible_gap", ""))[:1200],
            "issue_category": row.get("issue_category"),
            "gap_type": row.get("gap_type"),
            "review_thread_id": row.get("review_thread_id"),
            "latency_sec": round(elapsed, 3),
            "usage": usage,
            "estimated_cost_usd": cost,
        }


def build_messages(row: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are an independent SEC visible-evidence auditor. "
                "Use only the SEC comment, company response, and retrieved amended-filing snippets. "
                "Do not infer from unseen filings, later SEC follow-up, or any gold label. "
                "Label resolved only if the visible snippets satisfy all material SEC request elements. "
                "Label unresolved if a material requested disclosure, quantification, exhibit, legal/accounting analysis, "
                "named item, or other requirement remains missing or only partially supported."
            ),
        },
        {
            "role": "user",
            "content": (
                f"{format_case(row)}\n\n"
                "Return JSON with exactly these keys: label, confidence, reason, visible_gap. "
                "label must be resolved or unresolved. confidence must be between 0 and 1."
            ),
        },
    ]


def format_case(row: dict[str, Any]) -> str:
    snippets = []
    for index, snippet in enumerate((row.get("retrieved_snippets") or [])[:3], start=1):
        snippets.append(
            f"[Snippet {index} | form={snippet.get('candidate_form')} | date={snippet.get('candidate_filing_date')}]\n"
            f"{str(snippet.get('snippet') or '')[:1700]}"
        )
    return "\n".join(
        [
            "SEC comment:",
            str(row.get("sec_comment", ""))[:3500],
            "",
            "Company response:",
            str(row.get("company_response", ""))[:3500],
            "",
            "Retrieved amended-filing snippets:",
            "\n\n".join(snippets) if snippets else "[none]",
        ]
    )


def estimate_cost(rows: list[dict[str, Any]], model: str, max_tokens: int) -> dict[str, Any]:
    input_tokens = output_tokens = 0
    for row in rows:
        input_tokens += 520
        input_tokens += estimate_text_tokens(str(row.get("sec_comment", ""))[:3500])
        input_tokens += estimate_text_tokens(str(row.get("company_response", ""))[:3500])
        for snippet in (row.get("retrieved_snippets") or [])[:3]:
            input_tokens += 80
            input_tokens += estimate_text_tokens(str(snippet.get("snippet") or "")[:1700])
        output_tokens += max_tokens
    return {
        "rows": len(rows),
        "model": model,
        "input_tokens_est": input_tokens,
        "output_tokens_est": output_tokens,
        "cost_usd_est": cost_for_tokens(model, input_tokens, output_tokens),
    }


def evaluate_rows(runner: Runner, rows: list[dict[str, Any]], num_threads: int) -> list[dict[str, Any]]:
    if num_threads <= 1:
        out = []
        for index, row in enumerate(rows, start=1):
            print(f"[label_audit] {index}/{len(rows)} {row.get('example_id')}", flush=True)
            out.append(runner.predict(row))
        return out

    out: list[dict[str, Any] | None] = [None] * len(rows)
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {executor.submit(runner.predict, row): (idx, row) for idx, row in enumerate(rows)}
        done = 0
        for future in as_completed(futures):
            idx, row = futures[future]
            out[idx] = future.result()
            done += 1
            print(f"[label_audit] {done}/{len(rows)} {row.get('example_id')}", flush=True)
    return [row for row in out if row is not None]


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    gold = [row["gold"] for row in rows]
    pred = [row["audit_label"] for row in rows]
    report = classification_report(gold, pred)
    agreements = [row for row in rows if row.get("agree")]
    disagreements = [row for row in rows if not row.get("agree")]
    high_conf = [row for row in rows if float(row.get("confidence") or 0) >= 0.8]
    return {
        "accuracy_agreement": report["accuracy"],
        "classification_report": report,
        "gold_counts": dict(Counter(gold)),
        "audit_label_counts": dict(Counter(pred)),
        "agreements": len(agreements),
        "disagreements": len(disagreements),
        "high_confidence_rows": len(high_conf),
        "high_confidence_agreement": round(sum(1 for row in high_conf if row.get("agree")) / len(high_conf), 4)
        if high_conf
        else None,
        "mean_confidence": round(sum(float(row.get("confidence") or 0) for row in rows) / len(rows), 4) if rows else 0,
        "cost_usd": round(sum(float(row.get("estimated_cost_usd") or 0) for row in rows), 6),
        "by_issue_category": by_group(rows, "issue_category"),
        "by_gap_type": by_group(rows, "gap_type"),
    }


def by_group(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    out = {}
    for value in sorted({str(row.get(key) or "unknown") for row in rows}):
        group = [row for row in rows if str(row.get(key) or "unknown") == value]
        if len(group) < 5:
            continue
        out[value] = {
            "n": len(group),
            "agreement": round(sum(1 for row in group if row.get("agree")) / len(group), 4),
            "gold_counts": dict(Counter(row["gold"] for row in group)),
            "audit_label_counts": dict(Counter(row["audit_label"] for row in group)),
        }
    return out


def classification_report(gold: list[str], pred: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    correct = sum(1 for g, p in zip(gold, pred) if g == p)
    for label in LABELS:
        tp = sum(1 for g, p in zip(gold, pred) if g == label and p == label)
        fp = sum(1 for g, p in zip(gold, pred) if g != label and p == label)
        fn = sum(1 for g, p in zip(gold, pred) if g == label and p != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        support = sum(1 for g in gold if g == label)
        out[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": support,
        }
    out["macro_avg"] = {"f1": round(sum(out[label]["f1"] for label in LABELS) / len(LABELS), 4)}
    out["accuracy"] = round(correct / len(gold), 4) if gold else 0.0
    return out


def write_metrics_md(path: Path, result: dict[str, Any]) -> None:
    report = result["summary"]["classification_report"]
    lines = [
        "# Independent Label Audit",
        "",
        f"Model: `{result['model']}`",
        "",
        "The auditor saw only SEC comments, company responses, and raw retrieved amended-filing snippets.",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Rows | {result['num_rows']} |",
        f"| Agreement accuracy | {report['accuracy']:.4f} |",
        f"| Macro-F1 vs benchmark label | {report['macro_avg']['f1']:.4f} |",
        f"| Resolved F1 | {report['resolved']['f1']:.4f} |",
        f"| Unresolved F1 | {report['unresolved']['f1']:.4f} |",
        f"| Mean confidence | {result['summary']['mean_confidence']:.4f} |",
        f"| Cost USD | {result['summary']['cost_usd']:.6f} |",
        "",
        "This is an independent LLM audit, not expert legal/accounting validation.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_json_prediction(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if match:
            return json.loads(match.group(0))
    return {"label": "unresolved", "confidence": 0.0, "reason": "parse failure", "visible_gap": "parse failure"}


def normalize_label(value: Any) -> str:
    text = str(value).strip().lower().replace("-", "_")
    if "unresolved" in text:
        return "unresolved"
    if "resolved" in text:
        return "resolved"
    return "unresolved"


def parse_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def usage_to_dict(usage: Any) -> dict[str, int]:
    if usage is None:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    return {
        "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
    }


def model_slug(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", model).replace("/", "__")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
