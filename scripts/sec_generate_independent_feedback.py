#!/usr/bin/env python3
"""Generate independent natural-language feedback for GEPA.

This addresses the feedback-leak concern: the feedback writer sees only the
test-time inputs plus the gold label, not the adjudication rationale fields that
were used to construct the benchmark labels.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openai import OpenAI

from pressback.costs import append_usage_record, cost_for_tokens, estimate_text_tokens


RATIONAL_FIELD_BLOCKLIST = {
    "amended_evidence_evidence_summary",
    "amended_evidence_missing_evidence",
    "amended_evidence_supporting_quote",
    "feedback_sec_request",
    "feedback_company_action",
    "feedback_evidence_summary",
    "feedback_supporting_quote",
    "feedback_unmet_requirement",
    "full_feedback",
    "category_feedback",
    "scalar_feedback",
    "real_followup_text",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="data/sec_visible_evidence_benchmark_v2/sec_visible_evidence_benchmark_v2.jsonl",
    )
    parser.add_argument(
        "--output",
        default="data/sec_visible_evidence_benchmark_v2/sec_visible_evidence_benchmark_v2_independent_feedback.jsonl",
    )
    parser.add_argument("--model", default="gpt-5.4-mini")
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--num-threads", type=int, default=4)
    parser.add_argument("--max-tokens", type=int, default=420)
    parser.add_argument("--usage-ledger", default="outputs/openai_usage_ledger.jsonl")
    parser.add_argument("--estimate-only", action="store_true")
    args = parser.parse_args()

    rows = load_jsonl(Path(args.input))
    if args.max_rows:
        rows = rows[: args.max_rows]

    estimate = estimate_cost(rows, args.model, args.max_tokens)
    if args.estimate_only:
        print(json.dumps(estimate, indent=2, ensure_ascii=False))
        return 0
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")

    client = OpenAI()
    augmented: list[dict[str, Any] | None] = [None] * len(rows)
    with ThreadPoolExecutor(max_workers=args.num_threads) as executor:
        futures = {
            executor.submit(generate_one, client, args.model, args.max_tokens, args.usage_ledger, row): (idx, row)
            for idx, row in enumerate(rows)
        }
        done = 0
        for future in as_completed(futures):
            idx, row = futures[future]
            augmented[idx] = future.result()
            done += 1
            print(f"[independent-feedback] {done}/{len(rows)} {row.get('example_id')}", flush=True)

    out = [row for row in augmented if row is not None]
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(destination, out)
    summary = {
        "input": args.input,
        "output": args.output,
        "model": args.model,
        "rows": len(out),
        "estimate": estimate,
        "field_policy": "Feedback writer saw only sec_comment, company_response, retrieved_snippets, issue metadata, and gold label.",
    }
    summary_path = destination.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def generate_one(client: OpenAI, model: str, max_tokens: int, ledger: str, row: dict[str, Any]) -> dict[str, Any]:
    started = time.time()
    request: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt()},
            {"role": "user", "content": user_prompt(row)},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    if model.startswith("gpt-5"):
        request["max_completion_tokens"] = max_tokens
    else:
        request["max_tokens"] = max_tokens
    response = client.chat.completions.create(**request)
    elapsed = time.time() - started
    usage = usage_to_dict(response.usage)
    cost = cost_for_tokens(model, usage["prompt_tokens"], usage["completion_tokens"])
    append_usage_record(
        ledger,
        purpose="sec_independent_full_feedback",
        model=model,
        usage=usage,
        estimated_cost_usd=cost,
    )
    parsed = parse_json(response.choices[0].message.content or "{}")
    feedback = compact_feedback(row, parsed)
    out = dict(row)
    out["independent_feedback_model"] = model
    out["independent_feedback_latency_sec"] = round(elapsed, 3)
    out["independent_feedback_usage"] = usage
    out["independent_sec_request_elements"] = parsed.get("sec_request_elements", "")
    out["independent_evidence_assessment"] = parsed.get("evidence_assessment", "")
    out["independent_remaining_gap"] = parsed.get("remaining_gap", "")
    out["independent_resolution_basis"] = parsed.get("resolution_basis", "")
    out["independent_full_feedback"] = feedback
    return out


def system_prompt() -> str:
    return """You are an independent SEC disclosure-review feedback writer.

Your job is to produce feedback for a prompt optimizer. You did not create the dataset label. You must use only the SEC comment, company response, raw retrieved amended-filing snippets, issue metadata, and the gold visible-evidence label.

Do not assume that a company response is true unless the raw amended-filing snippets visibly support it. Do not require information beyond the SEC's request. Do not refer to any hidden adjudication notes.

Return strict JSON with these keys:
sec_request_elements, evidence_assessment, remaining_gap, resolution_basis, optimizer_feedback."""


def user_prompt(row: dict[str, Any]) -> str:
    label = normalize_label(row.get("visible_evidence_resolution_label"))
    parts = [
        f"Gold visible-evidence label: {label}",
        f"Issue category: {row.get('issue_category') or 'other'}",
        f"Evidence relevance metadata: {row.get('amended_evidence_evidence_relevance') or 'not_provided'}",
        "",
        "SEC comment:",
        str(row.get("sec_comment") or "")[:3200],
        "",
        "Company response:",
        str(row.get("company_response") or "")[:3200],
        "",
        "Raw retrieved amended-filing snippets:",
        format_snippets(row),
        "",
        "Write concise optimizer feedback. If the gold label is unresolved, identify the concrete SEC-requested item still missing from the visible snippets. If the gold label is resolved, identify what visible evidence satisfies the material request and what not to over-require.",
    ]
    return "\n".join(parts)


def format_snippets(row: dict[str, Any]) -> str:
    snippets = []
    for index, snippet in enumerate((row.get("retrieved_snippets") or [])[:3], start=1):
        snippets.append(
            f"[Snippet {index} | form={snippet.get('candidate_form')} | date={snippet.get('candidate_filing_date')}]\n"
            f"{str(snippet.get('snippet') or '')[:1500]}"
        )
    return "\n\n".join(snippets) if snippets else "[no retrieved snippets]"


def compact_feedback(row: dict[str, Any], parsed: dict[str, Any]) -> str:
    label = normalize_label(row.get("visible_evidence_resolution_label"))
    parts = [
        f"Gold visible-evidence label: {label}.",
        f"Issue category: {row.get('issue_category') or 'other'}.",
        f"Independent SEC request elements: {parsed.get('sec_request_elements') or '[not stated]'}.",
        f"Independent evidence assessment: {parsed.get('evidence_assessment') or '[not stated]'}.",
    ]
    if label == "unresolved":
        parts.append(f"Independent remaining gap: {parsed.get('remaining_gap') or '[not stated]'}.")
    else:
        parts.append(f"Independent resolution basis: {parsed.get('resolution_basis') or '[not stated]'}.")
    if parsed.get("optimizer_feedback"):
        parts.append(f"Optimizer feedback: {parsed['optimizer_feedback']}.")
    return " ".join(parts)


def estimate_cost(rows: list[dict[str, Any]], model: str, max_tokens: int) -> dict[str, Any]:
    input_tokens = output_tokens = 0
    for row in rows:
        input_tokens += estimate_text_tokens(system_prompt())
        input_tokens += estimate_text_tokens(user_prompt(row))
        input_tokens += 80
        output_tokens += max_tokens
    return {
        "rows": len(rows),
        "model": model,
        "input_tokens_est": input_tokens,
        "output_tokens_est": output_tokens,
        "cost_usd_est": cost_for_tokens(model, input_tokens, output_tokens),
    }


def parse_json(content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", content, flags=re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    return {"optimizer_feedback": content}


def normalize_label(value: Any) -> str:
    text = str(value).strip().lower().replace("-", "_")
    if "unresolved" in text:
        return "unresolved"
    return "resolved"


def usage_to_dict(usage: Any) -> dict[str, int]:
    if usage is None:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    return {
        "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
    }


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [{key: value for key, value in row.items() if key not in RATIONAL_FIELD_BLOCKLIST} for row in rows]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
