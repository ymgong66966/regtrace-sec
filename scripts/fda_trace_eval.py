#!/usr/bin/env python3
"""Evaluate FDA warning-to-closeout trace verification prompts."""

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


MODES = ("generic", "regtrace_schema", "regtrace_calibrated")
LABELS = ("matched", "mismatched")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/fda_warning_letters/contrastive_benchmark_v1/test.jsonl")
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--max-tokens", type=int, default=420)
    parser.add_argument("--num-threads", type=int, default=4)
    parser.add_argument("--out-dir", default="outputs/fda_contrastive_eval")
    parser.add_argument("--usage-ledger", default="outputs/openai_usage_ledger.jsonl")
    parser.add_argument("--estimate-only", action="store_true")
    args = parser.parse_args()

    load_env_file(Path(".env"))
    rows = load_jsonl(Path(args.input))
    estimate = estimate_cost(rows, args.mode, args.model, args.max_tokens)
    if args.estimate_only:
        print(json.dumps(estimate, indent=2, ensure_ascii=False))
        return 0
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")

    runner = Runner(client=OpenAI(), model=args.model, mode=args.mode, max_tokens=args.max_tokens, usage_ledger=args.usage_ledger)
    predictions = evaluate_rows(runner, rows, args.num_threads)
    result = {
        "input": args.input,
        "mode": args.mode,
        "model": args.model,
        "num_rows": len(rows),
        "gold_counts": dict(Counter(row["fda_trace_label"] for row in rows)),
        "estimate": estimate,
        "summary": summarize(predictions),
    }
    out_dir = Path(args.out_dir) / model_slug(args.model) / args.mode
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_dir / "predictions.jsonl", predictions)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    write_summary(out_dir / "summary.md", result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


class Runner:
    def __init__(self, *, client: OpenAI, model: str, mode: str, max_tokens: int, usage_ledger: str | None) -> None:
        self.client = client
        self.model = model
        self.mode = mode
        self.max_tokens = max_tokens
        self.usage_ledger = usage_ledger

    def predict(self, row: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        request: dict[str, Any] = {
            "model": self.model,
            "messages": build_messages(row, self.mode),
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        if self.model.startswith("gpt-5"):
            request["max_completion_tokens"] = self.max_tokens
        else:
            request["max_tokens"] = self.max_tokens
        response = self.client.chat.completions.create(**request)
        usage = usage_to_dict(response.usage)
        cost = cost_for_tokens(self.model, usage["prompt_tokens"], usage["completion_tokens"])
        append_usage_record(
            self.usage_ledger,
            purpose=f"fda_trace_eval:{self.mode}",
            model=self.model,
            usage=usage,
            estimated_cost_usd=cost,
        )
        parsed = parse_json(response.choices[0].message.content or "{}")
        pred = normalize_label(parsed.get("label"))
        gold = normalize_label(row.get("fda_trace_label"))
        return {
            "example_id": row["example_id"],
            "gold": gold,
            "pred": pred,
            "correct": pred == gold,
            "mode": self.mode,
            "product": row.get("product"),
            "subject": row.get("subject"),
            "negative_type": row.get("negative_type"),
            "company_name": row.get("company_name"),
            "candidate_company_name": row.get("candidate_company_name"),
            "reason": str(parsed.get("reason", ""))[:1500],
            "alignment_signals": parsed.get("alignment_signals", []) if isinstance(parsed.get("alignment_signals"), list) else [],
            "latency_sec": round(time.time() - started, 3),
            "usage": usage,
            "estimated_cost_usd": cost,
        }


def build_messages(row: dict[str, Any], mode: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": system_prompt(mode)},
        {
            "role": "user",
            "content": (
                f"{format_case(row)}\n\n"
                "Return strict JSON with keys: label, reason, alignment_signals. "
                "label must be matched or mismatched."
            ),
        },
    ]


def system_prompt(mode: str) -> str:
    if mode == "generic":
        return (
            "You are given an FDA warning letter and a candidate FDA closeout letter. "
            "Decide whether the closeout letter corresponds to and resolves the warning letter. "
            "Return matched if they are the same regulatory trace, otherwise mismatched."
        )
    if mode == "regtrace_calibrated":
        return (
            "You are a RegTrace reviewer for FDA warning-to-closeout traces. "
            "Use only the visible warning letter, candidate closeout letter, and high-level FDA metadata. "
            "Return matched when the candidate closeout is visibly the resolution letter for the same FDA warning trace. "
            "Strong matching signals include the same firm or recipient, same CMS/reference number, explicit mention of the same warning-letter date, same product or violation family, and closeout language saying FDA evaluated corrective actions in response to that warning. "
            "Do not require the closeout letter to repeat every violation from the warning letter; FDA closeout letters are often short boilerplate. "
            "Return mismatched when the candidate closeout appears to concern a different firm, different warning date, different reference/CMS number, or only shares a broad product area."
        )
    return (
        "You are a RegTrace reviewer for FDA warning-to-closeout traces. "
        "Use only the visible warning letter, candidate closeout letter, and high-level FDA metadata. "
        "Do not assume that a closeout letter is correct merely because it uses similar FDA boilerplate or the same product area. "
        "Check trace alignment in this order: firm or recipient identity, CMS/reference number or warning date, product/violation family, issuing office, and whether the closeout says FDA evaluated corrective actions for the same warning. "
        "Return matched only when the candidate closeout is visibly the resolution evidence for this warning. "
        "Return mismatched when it appears to be a different firm, different warning, different reference number, or merely a similar regulatory template."
    )


def format_case(row: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Warning company: {row.get('company_name')}",
            f"Warning product: {row.get('product')}",
            f"Warning subject: {row.get('subject')}",
            f"Warning issuing office: {row.get('issuing_office')}",
            f"Warning issue date: {row.get('warning_issue_date')}",
            "",
            "FDA warning letter:",
            str(row.get("warning_text") or "")[:5200],
            "",
            f"Candidate closeout company: {row.get('candidate_company_name')}",
            f"Candidate closeout product: {row.get('candidate_product')}",
            f"Candidate closeout subject: {row.get('candidate_subject')}",
            f"Candidate closeout issuing office: {row.get('candidate_issuing_office')}",
            f"Candidate closeout date: {row.get('candidate_closeout_issue_date')}",
            "",
            "Candidate FDA closeout letter:",
            str(row.get("candidate_closeout_text") or "")[:3600],
        ]
    )


def evaluate_rows(runner: Runner, rows: list[dict[str, Any]], num_threads: int) -> list[dict[str, Any]]:
    predictions: list[tuple[int, dict[str, Any]]] = []
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {executor.submit(runner.predict, row): i for i, row in enumerate(rows)}
        for future in as_completed(futures):
            predictions.append((futures[future], future.result()))
    return [row for _, row in sorted(predictions, key=lambda item: item[0])]


def summarize(predictions: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(predictions)
    correct = sum(1 for row in predictions if row["correct"])
    per_label: dict[str, dict[str, float]] = {}
    f1s = []
    for label in LABELS:
        tp = sum(1 for row in predictions if row["gold"] == label and row["pred"] == label)
        fp = sum(1 for row in predictions if row["gold"] != label and row["pred"] == label)
        fn = sum(1 for row in predictions if row["gold"] == label and row["pred"] != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        f1s.append(f1)
        per_label[label] = {"precision": precision, "recall": recall, "f1": f1, "support": tp + fn}
    return {
        "accuracy": correct / total if total else 0.0,
        "macro_f1": sum(f1s) / len(f1s) if f1s else 0.0,
        "per_label": per_label,
        "pred_counts": dict(Counter(row["pred"] for row in predictions)),
        "confusion": confusion(predictions),
    }


def confusion(predictions: list[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(f"{row['gold']}->{row['pred']}" for row in predictions))


def estimate_cost(rows: list[dict[str, Any]], mode: str, model: str, max_tokens: int) -> dict[str, Any]:
    prompt_tokens = 0
    for row in rows:
        prompt_tokens += estimate_text_tokens(system_prompt(mode))
        prompt_tokens += estimate_text_tokens(format_case(row))
        prompt_tokens += 80
    completion_tokens = len(rows) * max_tokens
    return {
        "rows": len(rows),
        "mode": mode,
        "model": model,
        "estimated_prompt_tokens": prompt_tokens,
        "estimated_completion_tokens": completion_tokens,
        "estimated_cost_usd": cost_for_tokens(model, prompt_tokens, completion_tokens),
    }


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_summary(path: Path, result: dict[str, Any]) -> None:
    s = result["summary"]
    lines = [
        f"# FDA Trace Eval: {result['mode']}",
        "",
        f"- Model: `{result['model']}`",
        f"- Rows: {result['num_rows']}",
        f"- Accuracy: {s['accuracy']:.3f}",
        f"- Macro-F1: {s['macro_f1']:.3f}",
        f"- Confusion: `{json.dumps(s['confusion'], ensure_ascii=False)}`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def parse_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        return {}


def normalize_label(value: object) -> str:
    text = str(value or "").strip().lower()
    if "mis" in text or "wrong" in text or "not" in text:
        return "mismatched"
    if "match" in text or "resolved_trace" in text:
        return "matched"
    return text if text in LABELS else "mismatched"


def usage_to_dict(usage: Any) -> dict[str, int]:
    return {
        "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
    }


def model_slug(model: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", model)


if __name__ == "__main__":
    raise SystemExit(main())
