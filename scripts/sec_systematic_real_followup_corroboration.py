#!/usr/bin/env python3
"""Systematically adjudicate real SEC follow-up corroboration.

This script builds a joined analysis file from Benchmark v2, held-out method
predictions, and real next-round SEC follow-up text. It then optionally uses an
LLM judge to determine whether the follow-up corroborates the visible-evidence
gap and/or GEPA-full reasoning.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from openai import OpenAI


BENCHMARK = Path("data/sec_visible_evidence_benchmark_v2/sec_visible_evidence_benchmark_v2.jsonl")
TEST_SPLIT = Path("data/sec_visible_evidence_benchmark_v2/splits/grouped_random_dev48_gap/fold_0/test.jsonl")
OUTDIR = Path("outputs/sec_visible_evidence_benchmark_v2/real_followup_corroboration_systematic")


METHOD_SOURCES = {
    "baseline": (
        Path("outputs/sec_visible_evidence_benchmark_v2/final_leaderboard_dev48_gap_m150/fold_0_basic_full_m150/dry_run_result.json"),
        ("final_eval", "baseline"),
    ),
    "mipro": (
        Path("outputs/sec_visible_evidence_benchmark_v2/final_leaderboard_dev48_gap_m150/fold_0_basic_mipro_t8/result.json"),
        ("optimized_test",),
    ),
    "scalar": (
        Path("outputs/sec_visible_evidence_benchmark_v2/final_leaderboard_dev48_gap_m150/fold_0_basic_scalar_m150/dry_run_result.json"),
        ("final_eval", "optimized"),
    ),
    "category": (
        Path("outputs/sec_visible_evidence_benchmark_v2/final_leaderboard_dev48_gap_m150/fold_0_basic_category_m150/dry_run_result.json"),
        ("final_eval", "optimized"),
    ),
    "full": (
        Path("outputs/sec_visible_evidence_benchmark_v2/final_leaderboard_dev48_gap_m150/fold_0_basic_full_m150/dry_run_result.json"),
        ("final_eval", "optimized"),
    ),
}


SYSTEM_PROMPT = """You are an expert reviewer of SEC comment-letter follow-up behavior.

You compare:
1. the first SEC comment,
2. the company's response,
3. the visible-evidence adjudicated gap,
4. GEPA-full's model prediction/reasoning when available, and
5. the actual next-round SEC follow-up comment.

Your task is NOT to decide the original benchmark label from scratch.
Your task is to classify whether the real SEC follow-up corroborates the visible-evidence gap and/or GEPA-full's identified missing requirement.

Use exactly one corroboration_label:
- direct_corroboration: the follow-up asks for substantially the same unmet requirement identified by the visible-evidence gap or GEPA-full.
- partial_corroboration: the follow-up is clearly related and narrows, restates, or extends the same unresolved issue, but not as a one-to-one restatement.
- new_or_expanded_requirement: the follow-up is same-topic but asks for materially new information beyond the original visible-evidence gap.
- procedural_or_document_request: the follow-up mainly asks for consents, exhibits, signatures, page references, updated documents, or procedural fixes.
- weak_or_no_corroboration: the follow-up is same-topic but does not meaningfully support the visible-evidence gap or GEPA-full's reason.
- contradiction_or_label_concern: the follow-up suggests the visible-evidence label or GEPA-full reasoning may be too strict, wrong, or unsupported.

Also answer whether the follow-up corroborates GEPA-full specifically:
- yes
- partially
- no
- unavailable

Return JSON only with keys:
corroboration_label, corroborates_visible_gap, corroborates_gepa_full, shared_requirement, followup_focus, judge_rationale, label_risk.
corroborates_visible_gap must be yes, partially, no, or unclear.
corroborates_gepa_full must be yes, partially, no, or unavailable.
label_risk must be low, medium, or high."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build systematic real SEC follow-up corroboration artifacts.")
    parser.add_argument("--model", default="gpt-5-mini")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--limit", type=int, default=0, help="0 means all follow-up examples")
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--outdir", default=str(OUTDIR))
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    joined = build_joined_rows()
    write_jsonl(outdir / "real_followup_corroboration_joined.jsonl", joined)
    write_csv(outdir / "real_followup_corroboration_joined.csv", joined)

    if args.no_llm:
        summary = summarize(joined, [])
        write_outputs(outdir, joined, [], summary)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0

    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")

    judge_path = outdir / "real_followup_corroboration_judged.jsonl"
    completed = load_completed(judge_path) if args.resume else {}
    todo = [r for r in joined if r.get("has_real_followup") is True]
    if args.limit:
        todo = todo[: args.limit]
    todo = [r for r in todo if r["example_id"] not in completed]

    client = OpenAI()
    results = list(completed.values())
    mode = "a" if args.resume and judge_path.exists() else "w"
    with judge_path.open(mode, encoding="utf-8") as handle:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(judge_one, client, args.model, row): row for row in todo}
            for idx, future in enumerate(as_completed(futures), 1):
                row = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    result = {
                        "example_id": row["example_id"],
                        "error": str(exc),
                    }
                handle.write(json.dumps(result, ensure_ascii=False) + "\n")
                handle.flush()
                results.append(result)
                print(
                    f"[corroboration] {idx}/{len(todo)} {row['example_id']} -> "
                    f"{result.get('corroboration_label', result.get('error'))}",
                    flush=True,
                )

    summary = summarize(joined, results)
    write_outputs(outdir, joined, results, summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def build_joined_rows() -> list[dict[str, Any]]:
    benchmark = {r["example_id"]: r for r in read_jsonl(BENCHMARK)}
    test_ids = {r["example_id"] for r in read_jsonl(TEST_SPLIT)}
    method_rows = {name: load_method_predictions(path, selector) for name, (path, selector) in METHOD_SOURCES.items()}

    rows: list[dict[str, Any]] = []
    for eid, row in benchmark.items():
        out = {
            "example_id": eid,
            "in_main_test": eid in test_ids,
            "company_name": row.get("company_name"),
            "cik": row.get("cik"),
            "review_thread_id": row.get("review_thread_id"),
            "review_group_key": row.get("review_group_key"),
            "response_year": row.get("response_year"),
            "issue_category": row.get("issue_category"),
            "gap_type": row.get("gap_type"),
            "visible_label": row.get("visible_evidence_resolution_label"),
            "regulator_followup_label": row.get("regulator_followup_label"),
            "has_real_followup": bool(row.get("has_real_followup")),
            "real_feedback_relation": row.get("real_feedback_relation"),
            "real_feedback_gap_type": row.get("real_feedback_gap_type"),
            "sec_comment": row.get("sec_comment"),
            "company_response": row.get("company_response"),
            "feedback_sec_request": row.get("feedback_sec_request"),
            "feedback_company_action": row.get("feedback_company_action"),
            "feedback_evidence_summary": row.get("feedback_evidence_summary"),
            "feedback_unmet_requirement": row.get("feedback_unmet_requirement"),
            "feedback_supporting_quote": row.get("feedback_supporting_quote"),
            "real_followup_text": row.get("real_followup_text"),
        }
        for method, preds in method_rows.items():
            pred = preds.get(eid, {})
            out[f"{method}_pred"] = pred.get("pred")
            out[f"{method}_gold"] = pred.get("gold")
            out[f"{method}_correct"] = pred.get("pred") == pred.get("gold") if pred else None
            out[f"{method}_reason"] = pred.get("reason")
            out[f"{method}_reasoning"] = pred.get("reasoning")
        rows.append(out)
    return rows


def load_method_predictions(path: Path, selector: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if selector == ("final_eval", "baseline") or selector == ("final_eval", "optimized"):
        split_payload = next(iter(obj["final_eval"].values()))
        rows = split_payload[selector[1]]["rows"]
    elif selector == ("optimized_test",):
        rows = obj["optimized_test"]["rows"]
    else:
        raise ValueError(selector)
    return {r["example_id"]: r for r in rows}


def judge_one(client: OpenAI, model: str, row: dict[str, Any]) -> dict[str, Any]:
    user = build_user_prompt(row)
    params: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
    }
    if model.startswith(("gpt-5", "o1", "o3", "o4")):
        params["max_completion_tokens"] = 850
    else:
        params["temperature"] = 0
        params["max_tokens"] = 850
    response = client.chat.completions.create(**params)
    parsed = parse_json(response.choices[0].message.content or "{}")
    usage = getattr(response, "usage", None)
    return {
        "example_id": row["example_id"],
        "visible_label": row.get("visible_label"),
        "issue_category": row.get("issue_category"),
        "gap_type": row.get("gap_type"),
        "real_feedback_relation": row.get("real_feedback_relation"),
        "in_main_test": row.get("in_main_test"),
        "baseline_pred": row.get("baseline_pred"),
        "mipro_pred": row.get("mipro_pred"),
        "scalar_pred": row.get("scalar_pred"),
        "category_pred": row.get("category_pred"),
        "full_pred": row.get("full_pred"),
        "baseline_correct": row.get("baseline_correct"),
        "mipro_correct": row.get("mipro_correct"),
        "scalar_correct": row.get("scalar_correct"),
        "category_correct": row.get("category_correct"),
        "full_correct": row.get("full_correct"),
        "corroboration_label": normalize_label(parsed.get("corroboration_label")),
        "corroborates_visible_gap": normalize_yes(parsed.get("corroborates_visible_gap")),
        "corroborates_gepa_full": normalize_yes(parsed.get("corroborates_gepa_full"), allow_unavailable=True),
        "shared_requirement": parsed.get("shared_requirement"),
        "followup_focus": parsed.get("followup_focus"),
        "judge_rationale": parsed.get("judge_rationale"),
        "label_risk": normalize_risk(parsed.get("label_risk")),
        "prompt_tokens": getattr(usage, "prompt_tokens", None) if usage else None,
        "completion_tokens": getattr(usage, "completion_tokens", None) if usage else None,
        "total_tokens": getattr(usage, "total_tokens", None) if usage else None,
    }


def build_user_prompt(row: dict[str, Any]) -> str:
    return f"""Example ID: {row.get('example_id')}
Visible-evidence label: {row.get('visible_label')}
Issue category: {row.get('issue_category')}
Gap type: {row.get('gap_type')}
Existing follow-up relation metadata: {row.get('real_feedback_relation')}

First SEC comment:
{clip(row.get('sec_comment'), 3500)}

Company response:
{clip(row.get('company_response'), 2600)}

Visible-evidence adjudication:
- SEC request: {clip(row.get('feedback_sec_request'), 1500)}
- Company action: {clip(row.get('feedback_company_action'), 1200)}
- Evidence summary: {clip(row.get('feedback_evidence_summary'), 1600)}
- Unmet requirement: {clip(row.get('feedback_unmet_requirement'), 1600)}
- Supporting quote: {clip(row.get('feedback_supporting_quote'), 1200)}

GEPA-full prediction and reasoning:
- Prediction: {row.get('full_pred')}
- Reason: {clip(row.get('full_reason'), 1600)}
- Reasoning: {clip(row.get('full_reasoning'), 2200)}

Actual next-round SEC follow-up:
{clip(row.get('real_followup_text'), 3500)}
"""


def summarize(joined: list[dict[str, Any]], judged: list[dict[str, Any]]) -> dict[str, Any]:
    clean = [r for r in judged if not r.get("error")]
    by_id = {r["example_id"]: r for r in clean}
    followup_rows = [r for r in joined if r.get("has_real_followup") is True]
    test_followup_rows = [r for r in followup_rows if r.get("in_main_test")]

    summary: dict[str, Any] = {
        "joined_examples": len(joined),
        "verified_followup_examples": len(followup_rows),
        "judged_examples": len(clean),
        "judge_errors": len(judged) - len(clean),
        "visible_label_counts": dict(Counter(r.get("visible_label") for r in joined)),
        "followup_by_visible_label": nested_count(followup_rows, "visible_label", "real_feedback_relation"),
        "corroboration_label_counts": dict(Counter(r.get("corroboration_label") for r in clean)),
        "corroboration_by_visible_label": nested_count(clean, "visible_label", "corroboration_label"),
        "corroboration_by_gap_type": nested_count(clean, "gap_type", "corroboration_label"),
        "corroboration_by_issue_category": nested_count(clean, "issue_category", "corroboration_label"),
        "method_win_corroboration": method_win_summary(test_followup_rows, by_id),
        "token_usage": {
            "prompt_tokens": sum(int(r.get("prompt_tokens") or 0) for r in clean),
            "completion_tokens": sum(int(r.get("completion_tokens") or 0) for r in clean),
            "total_tokens": sum(int(r.get("total_tokens") or 0) for r in clean),
        },
    }
    return summary


def method_win_summary(test_rows: list[dict[str, Any]], judged_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    groups = {
        "full_correct_baseline_wrong_unresolved": lambda r: r.get("visible_label") == "unresolved"
        and r.get("full_correct") is True
        and r.get("baseline_correct") is False,
        "full_correct_mipro_wrong_unresolved": lambda r: r.get("visible_label") == "unresolved"
        and r.get("full_correct") is True
        and r.get("mipro_correct") is False,
        "full_correct_scalar_wrong_unresolved": lambda r: r.get("visible_label") == "unresolved"
        and r.get("full_correct") is True
        and r.get("scalar_correct") is False,
        "full_false_positive_resolved": lambda r: r.get("visible_label") == "resolved" and r.get("full_pred") == "unresolved",
        "full_false_negative_unresolved": lambda r: r.get("visible_label") == "unresolved" and r.get("full_pred") == "resolved",
    }
    out: dict[str, Any] = {}
    positive = {"direct_corroboration", "partial_corroboration"}
    for name, pred in groups.items():
        rows = [r for r in test_rows if pred(r)]
        judged = [judged_by_id[r["example_id"]] for r in rows if r["example_id"] in judged_by_id]
        labels = Counter(r.get("corroboration_label") for r in judged)
        out[name] = {
            "n_with_followup": len(rows),
            "n_judged": len(judged),
            "direct_or_partial": sum(labels[l] for l in positive),
            "direct_or_partial_rate": (sum(labels[l] for l in positive) / len(judged)) if judged else None,
            "labels": dict(labels),
        }
    return out


def write_outputs(outdir: Path, joined: list[dict[str, Any]], judged: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    judged_clean = [r for r in judged if not r.get("error")]
    write_csv(outdir / "real_followup_corroboration_judged.csv", judged_clean)
    (outdir / "real_followup_corroboration_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (outdir / "real_followup_corroboration_tables.md").write_text(
        build_markdown_tables(summary, joined, judged_clean), encoding="utf-8"
    )


def build_markdown_tables(summary: dict[str, Any], joined: list[dict[str, Any]], judged: list[dict[str, Any]]) -> str:
    lines = [
        "# Systematic Real SEC Follow-Up Corroboration",
        "",
        "## Headline",
        "",
        f"- Benchmark examples: {summary['joined_examples']}",
        f"- Verified same-topic follow-up examples: {summary['verified_followup_examples']}",
        f"- LLM-adjudicated follow-up examples: {summary['judged_examples']}",
        "",
        "## Corroboration Labels",
        "",
        counter_table(summary["corroboration_label_counts"], "Label"),
        "",
        "## Corroboration by Visible-Evidence Label",
        "",
        nested_table(summary["corroboration_by_visible_label"], "Visible label"),
        "",
        "## Method-Win Corroboration on Main Held-Out Test",
        "",
        method_table(summary["method_win_corroboration"]),
        "",
        "## Token Usage",
        "",
        f"- Prompt tokens: {summary['token_usage']['prompt_tokens']}",
        f"- Completion tokens: {summary['token_usage']['completion_tokens']}",
        f"- Total tokens: {summary['token_usage']['total_tokens']}",
        "",
        "## Interpretation",
        "",
        "Use `direct_corroboration` and `partial_corroboration` as the main positive corroboration signal. "
        "Use `new_or_expanded_requirement` to explain why some resolved visible-evidence examples still receive follow-up comments. "
        "Use `contradiction_or_label_concern` as an honest label-risk bucket rather than hiding difficult cases.",
        "",
    ]
    return "\n".join(lines)


def counter_table(counter: dict[str, int], name: str) -> str:
    lines = [f"| {name} | Count |", "|---|---:|"]
    for key, value in sorted(counter.items(), key=lambda kv: (-kv[1], str(kv[0]))):
        lines.append(f"| {key} | {value} |")
    return "\n".join(lines)


def nested_table(nested: dict[str, dict[str, int]], row_name: str) -> str:
    cols = sorted({c for inner in nested.values() for c in inner})
    lines = [f"| {row_name} | " + " | ".join(cols) + " | Total |", "|---" + "|---:" * (len(cols) + 1) + "|"]
    for row_key, inner in sorted(nested.items()):
        total = sum(inner.values())
        vals = [str(inner.get(c, 0)) for c in cols]
        lines.append(f"| {row_key} | " + " | ".join(vals) + f" | {total} |")
    return "\n".join(lines)


def method_table(groups: dict[str, Any]) -> str:
    lines = [
        "| Group | N with follow-up | Judged | Direct/partial | Rate | Label breakdown |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for name, row in groups.items():
        rate = row["direct_or_partial_rate"]
        rate_text = "" if rate is None else f"{rate:.3f}"
        labels = ", ".join(f"{k}={v}" for k, v in sorted(row["labels"].items()))
        lines.append(
            f"| {name} | {row['n_with_followup']} | {row['n_judged']} | "
            f"{row['direct_or_partial']} | {rate_text} | {labels} |"
        )
    return "\n".join(lines)


def nested_count(rows: list[dict[str, Any]], outer: str, inner: str) -> dict[str, dict[str, int]]:
    out: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        out[str(row.get(outer))][str(row.get(inner))] += 1
    return {k: dict(v) for k, v in out.items()}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_completed(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("example_id") and not row.get("error"):
            out[row["example_id"]] = row
    return out


def parse_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return {}
        return {}


def normalize_label(value: Any) -> str:
    allowed = {
        "direct_corroboration",
        "partial_corroboration",
        "new_or_expanded_requirement",
        "procedural_or_document_request",
        "weak_or_no_corroboration",
        "contradiction_or_label_concern",
    }
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return text if text in allowed else "weak_or_no_corroboration"


def normalize_yes(value: Any, allow_unavailable: bool = False) -> str:
    text = str(value or "").strip().lower()
    if allow_unavailable and "unavailable" in text:
        return "unavailable"
    if text.startswith("yes"):
        return "yes"
    if text.startswith("partial"):
        return "partially"
    if text.startswith("no"):
        return "no"
    return "unclear"


def normalize_risk(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if text in {"low", "medium", "high"} else "medium"


def clip(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


if __name__ == "__main__":
    raise SystemExit(main())
