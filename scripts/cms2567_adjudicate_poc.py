#!/usr/bin/env python3
"""LLM adjudication pilot for CMS-2567 plan-of-correction adequacy."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openai import OpenAI

from pressback.costs import append_usage_record, cost_for_tokens, estimate_text_tokens


LABELS = ("adequate", "partial", "inadequate")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="outputs/cms2567_poc_adjudication/cms2567_poc_pilot_40.jsonl")
    parser.add_argument("--out-dir", default="outputs/cms2567_poc_adjudication/pilot_40")
    parser.add_argument("--model", default="gpt-5.4-mini")
    parser.add_argument("--audit-model", default="gpt-4o-mini")
    parser.add_argument("--rubric-version", choices=["strict", "calibrated"], default="strict")
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--num-threads", type=int, default=3)
    parser.add_argument("--max-tokens", type=int, default=760)
    parser.add_argument("--usage-ledger", default="outputs/openai_usage_ledger.jsonl")
    parser.add_argument("--estimate-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    rows = load_jsonl(Path(args.input))
    if args.max_rows:
        rows = rows[: args.max_rows]

    estimate = estimate_cost(rows, args.model, args.audit_model, args.max_tokens, args.rubric_version)
    if args.estimate_only:
        print(json.dumps(estimate, indent=2, ensure_ascii=False))
        return 0
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pred_path = out_dir / "adjudications.jsonl"
    completed = load_jsonl(pred_path) if args.resume and pred_path.exists() else []
    completed_ids = {row.get("example_id") for row in completed}
    remaining = [row for row in rows if row.get("example_id") not in completed_ids]
    if args.resume:
        print(f"[cms-poc] resume loaded={len(completed)} remaining={len(remaining)}", flush=True)

    runner = Runner(
        client=OpenAI(),
        model=args.model,
        audit_model=args.audit_model,
        max_tokens=args.max_tokens,
        usage_ledger=args.usage_ledger,
        rubric_version=args.rubric_version,
    )
    new_predictions = evaluate_rows(runner, remaining, args.num_threads)
    predictions = completed + new_predictions
    predictions.sort(key=lambda row: row.get("example_id", ""))
    write_jsonl(pred_path, predictions)

    result = {
        "input": args.input,
        "model": args.model,
        "audit_model": args.audit_model,
        "rubric_version": args.rubric_version,
        "num_rows": len(predictions),
        "estimate": estimate,
        "summary": summarize(predictions),
        "label_policy": {
            "test_time_fields": ["deficiency_text", "plan_of_correction_text", "ftag", "scope_severity"],
            "hidden_from_adjudicator": ["deficiency_corrected", "correction_date", "source_url"],
            "primary_label": "cms_poc_adequacy_label",
            "binary_mapping": {"adequate": "adequate", "partial": "not_adequate", "inadequate": "not_adequate"},
        },
    }
    (out_dir / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(out_dir / "summary.md", result, predictions)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


class Runner:
    def __init__(
        self,
        *,
        client: OpenAI,
        model: str,
        audit_model: str,
        max_tokens: int,
        usage_ledger: str | None,
        rubric_version: str,
    ) -> None:
        self.client = client
        self.model = model
        self.audit_model = audit_model
        self.max_tokens = max_tokens
        self.usage_ledger = usage_ledger
        self.rubric_version = rubric_version

    def predict(self, row: dict[str, Any]) -> dict[str, Any]:
        primary = self.call_model(row, self.model, role="primary")
        audit = self.call_model(row, self.audit_model, role="audit") if self.audit_model else {}
        primary_label = normalize_label(primary.get("adequacy_label"))
        audit_label = normalize_label(audit.get("adequacy_label")) if audit else ""
        out = {
            "example_id": row.get("example_id"),
            "facility_name": row.get("facility_name"),
            "state": row.get("state"),
            "report_year": row.get("report_year"),
            "ftag": row.get("ftag"),
            "ftag_group": row.get("ftag_group"),
            "scope_severity": row.get("scope_severity"),
            "severity_band": row.get("severity_band"),
            "cms_deficiency_category": row.get("cms_deficiency_category"),
            "survey_date": row.get("survey_date"),
            "deficiency_corrected": row.get("deficiency_corrected"),
            "correction_date": row.get("correction_date"),
            "days_to_correction": days_between(row.get("survey_date"), row.get("correction_date")),
            "primary_label": primary_label,
            "primary_binary": binary_label(primary_label),
            "primary_confidence": parse_float(primary.get("confidence")),
            "primary_missing_elements": primary.get("missing_elements", []),
            "primary_covered_elements": primary.get("covered_elements", []),
            "primary_reason": str(primary.get("reason", ""))[:2000],
            "primary_optimizer_feedback": str(primary.get("optimizer_feedback", ""))[:2200],
            "audit_label": audit_label,
            "audit_binary": binary_label(audit_label) if audit_label else "",
            "audit_confidence": parse_float(audit.get("confidence")) if audit else None,
            "audit_reason": str(audit.get("reason", ""))[:1600] if audit else "",
            "three_way_agree": primary_label == audit_label if audit_label else None,
            "binary_agree": binary_label(primary_label) == binary_label(audit_label) if audit_label else None,
            "input_excerpt": {
                "deficiency": str(row.get("deficiency_text") or "")[:900],
                "plan_of_correction": str(row.get("plan_of_correction_text") or "")[:900],
            },
        }
        return out

    def call_model(self, row: dict[str, Any], model: str, role: str) -> dict[str, Any]:
        started = time.time()
        request: dict[str, Any] = {
            "model": model,
            "messages": build_messages(row, role, self.rubric_version),
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        if model.startswith("gpt-5"):
            request["max_completion_tokens"] = self.max_tokens
        else:
            request["max_tokens"] = self.max_tokens
        response = self.client.chat.completions.create(**request)
        usage = usage_to_dict(response.usage)
        cost = cost_for_tokens(model, usage["prompt_tokens"], usage["completion_tokens"])
        append_usage_record(
            self.usage_ledger,
            purpose=f"cms2567_poc_{role}_adjudication",
            model=model,
            usage=usage,
            estimated_cost_usd=cost,
        )
        parsed = parse_json(response.choices[0].message.content or "{}")
        parsed["_latency_sec"] = round(time.time() - started, 3)
        parsed["_usage"] = usage
        parsed["_estimated_cost_usd"] = cost
        return parsed


def build_messages(row: dict[str, Any], role: str, rubric_version: str) -> list[dict[str, str]]:
    stance = (
        "Be careful not to reward length or boilerplate. A plan can be long and still inadequate if it does not address the cited facts."
        if role == "primary"
        else "Act as an independent second reviewer. Look for both false negatives and false positives in adequacy judgments."
    )
    if rubric_version == "calibrated":
        rubric = (
            "Rubric:\n"
            "- adequate: the plan substantially addresses the material cited deficiency. It need not be perfect or include every conceivable detail. It should visibly cover the main resident-specific correction where applicable, the affected or at-risk population, a systemic prevention step such as education/policy/process change, some monitoring/audit/QAPI or responsible follow-up, and a concrete timing/completion basis.\n"
            "- partial: the plan contains meaningful corrective content but leaves one or more material cited deficiency components unaddressed, treats a specific harm only generically, lacks a meaningful monitoring/follow-up mechanism, or is too vague to determine whether the material risk is controlled.\n"
            "- inadequate: the plan is mostly boilerplate, future intent, denial, a bare cross-reference, or 'no plan required' without enough visible corrective action; or it misses the central cited deficient practice.\n\n"
            "Calibration rule: do not downgrade to partial merely because the plan could be more detailed. Downgrade only for a material gap tied to the deficiency narrative."
        )
    else:
        rubric = (
            "Rubric:\n"
            "- adequate: the plan specifically addresses the cited deficient practice and material resident harm/risk; includes immediate action for affected residents when applicable; identifies other residents at risk; describes systemic prevention or policy/training/process changes; includes monitoring/audit or responsible follow-up; and gives a concrete timing/completion basis.\n"
            "- partial: the plan addresses some material requirements but leaves a meaningful gap, is too generic for part of the cited deficiency, lacks monitoring/timeline/responsibility, or only partially covers affected residents/systemic prevention.\n"
            "- inadequate: the plan is mostly boilerplate, future intent, denial, or missing the central cited obligation/harm; or it lacks enough concrete corrective action to judge adequacy."
        )
    return [
        {
            "role": "system",
            "content": (
                "You are a CMS-2567 plan-of-correction adequacy reviewer. "
                "Judge only whether the provider's written plan of correction adequately responds to the regulator's deficiency narrative. "
                "Do not use or infer from later correction status, revisit results, or hidden metadata. "
                "Use the plan text itself as visible evidence. "
                f"{stance}\n\n"
                f"{rubric}"
            ),
        },
        {
            "role": "user",
            "content": (
                f"{format_case(row)}\n\n"
                "Return strict JSON with these keys: adequacy_label, confidence, covered_elements, missing_elements, reason, optimizer_feedback. "
                "adequacy_label must be adequate, partial, or inadequate. confidence must be 0 to 1. "
                "covered_elements and missing_elements should be short arrays of strings."
            ),
        },
    ]


def format_case(row: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"F-tag: {row.get('ftag')}",
            f"Scope/severity: {row.get('scope_severity')}",
            f"Deficiency category: {row.get('cms_deficiency_category')}",
            "",
            "Regulator deficiency narrative:",
            str(row.get("deficiency_text") or "")[:5200],
            "",
            "Provider plan of correction:",
            str(row.get("plan_of_correction_text") or "")[:4200],
        ]
    )


def estimate_cost(
    rows: list[dict[str, Any]],
    model: str,
    audit_model: str,
    max_tokens: int,
    rubric_version: str,
) -> dict[str, Any]:
    estimates = []
    for active_model, role in [(model, "primary"), (audit_model, "audit")]:
        if not active_model:
            continue
        input_tokens = output_tokens = 0
        for row in rows:
            messages = build_messages(row, role, rubric_version)
            input_tokens += sum(estimate_text_tokens(message["content"]) for message in messages) + 80
            output_tokens += max_tokens
        estimates.append(
            {
                "model": active_model,
                "role": role,
                "input_tokens_est": input_tokens,
                "output_tokens_est": output_tokens,
                "cost_usd_est": cost_for_tokens(active_model, input_tokens, output_tokens),
            }
        )
    return {
        "rows": len(rows),
        "calls": len(rows) * len(estimates),
        "by_model": estimates,
        "total_cost_usd_est": round(sum(item["cost_usd_est"] for item in estimates), 6),
    }


def evaluate_rows(runner: Runner, rows: list[dict[str, Any]], num_threads: int) -> list[dict[str, Any]]:
    if num_threads <= 1:
        out = []
        for index, row in enumerate(rows, start=1):
            print(f"[cms-poc] {index}/{len(rows)} {row.get('example_id')}", flush=True)
            out.append(runner.predict(row))
        return out

    out: list[dict[str, Any] | None] = [None] * len(rows)
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {executor.submit(runner.predict, row): (index, row) for index, row in enumerate(rows)}
        done = 0
        for future in as_completed(futures):
            index, row = futures[future]
            out[index] = future.result()
            done += 1
            print(f"[cms-poc] {done}/{len(rows)} {row.get('example_id')}", flush=True)
    return [row for row in out if row is not None]


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    primary_counts = Counter(row.get("primary_label") for row in rows)
    audit_counts = Counter(row.get("audit_label") for row in rows if row.get("audit_label"))
    binary_agree_rows = [row for row in rows if row.get("binary_agree") is not None]
    three_agree_rows = [row for row in rows if row.get("three_way_agree") is not None]
    days_by_binary: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        days = row.get("days_to_correction")
        if isinstance(days, int) and days >= 0:
            days_by_binary[row.get("primary_binary", "")].append(days)
    return {
        "primary_label_counts": dict(primary_counts),
        "audit_label_counts": dict(audit_counts),
        "primary_binary_counts": dict(Counter(row.get("primary_binary") for row in rows)),
        "binary_agreement": ratio(sum(1 for row in binary_agree_rows if row.get("binary_agree")), len(binary_agree_rows)),
        "three_way_agreement": ratio(sum(1 for row in three_agree_rows if row.get("three_way_agree")), len(three_agree_rows)),
        "mean_primary_confidence": round(sum(float(row.get("primary_confidence") or 0) for row in rows) / len(rows), 4)
        if rows
        else None,
        "median_days_to_correction_by_primary_binary": {
            key: median_int(values) for key, values in sorted(days_by_binary.items()) if values
        },
        "by_severity_band": grouped_counts(rows, "severity_band"),
        "by_ftag_group": grouped_counts(rows, "ftag_group"),
    }


def grouped_counts(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, int]]:
    out: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        out[str(row.get(key) or "unknown")][str(row.get("primary_label") or "unknown")] += 1
    return {group: dict(counts) for group, counts in sorted(out.items())}


def write_report(path: Path, result: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    summary = result["summary"]
    examples = []
    for row in rows[:8]:
        examples.append(
            "\n".join(
                [
                    f"### {row['example_id']} / {row.get('ftag')} / {row.get('primary_label')}",
                    f"- Facility: {row.get('facility_name')}",
                    f"- Severity: {row.get('scope_severity')} ({row.get('severity_band')})",
                    f"- Primary vs audit: {row.get('primary_label')} / {row.get('audit_label')} (binary agree={row.get('binary_agree')})",
                    f"- Hidden correction metadata: {row.get('deficiency_corrected')} / {row.get('correction_date')}",
                    f"- Reason: {row.get('primary_reason')}",
                    "",
                    "**Deficiency excerpt**",
                    "",
                    f"> {row['input_excerpt']['deficiency']}",
                    "",
                    "**Plan excerpt**",
                    "",
                    f"> {row['input_excerpt']['plan_of_correction']}",
                ]
            )
        )
    text = f"""# CMS-2567 POC Adjudication Pilot

This pilot adjudicates plan-of-correction adequacy from visible text only. The
adjudicators do not see correction status or correction date; those fields are
used only for later sanity checks.

## Setup

- Input: `{result['input']}`
- Primary model: `{result['model']}`
- Audit model: `{result['audit_model']}`
- Rubric version: `{result['rubric_version']}`
- Rows: {result['num_rows']}
- Estimated cost before run: {result['estimate']['total_cost_usd_est']:.6f} USD

## Label Distribution

- Primary labels: {summary['primary_label_counts']}
- Audit labels: {summary['audit_label_counts']}
- Primary binary labels: {summary['primary_binary_counts']}
- Binary primary/audit agreement: {summary['binary_agreement']}
- Three-way primary/audit agreement: {summary['three_way_agreement']}
- Mean primary confidence: {summary['mean_primary_confidence']}
- Median days to correction by primary binary: {summary['median_days_to_correction_by_primary_binary']}

## By Severity Band

```json
{json.dumps(summary['by_severity_band'], indent=2, ensure_ascii=False)}
```

## By F-Tag Group

```json
{json.dumps(summary['by_ftag_group'], indent=2, ensure_ascii=False)}
```

## Sample Adjudications

{chr(10).join(examples)}
"""
    path.write_text(text, encoding="utf-8")


def binary_label(label: str) -> str:
    return "adequate" if label == "adequate" else "not_adequate"


def normalize_label(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_")
    if "inadequate" in text:
        return "inadequate"
    if "partial" in text or "partially" in text:
        return "partial"
    if "adequate" in text:
        return "adequate"
    return "partial"


def parse_float(value: Any) -> float | None:
    try:
        parsed = float(value)
        if parsed < 0:
            return 0.0
        if parsed > 1:
            return 1.0
        return parsed
    except Exception:
        return None


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
    return {"adequacy_label": "partial", "reason": content}


def days_between(start: Any, end: Any) -> int | None:
    if not start or not end:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            s = datetime.strptime(str(start), fmt)
            break
        except ValueError:
            s = None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            e = datetime.strptime(str(end), fmt)
            break
        except ValueError:
            e = None
    if not s or not e:
        return None
    return (e - s).days


def median_int(values: list[int]) -> int:
    if not values:
        return 0
    sorted_values = sorted(values)
    return int(sorted_values[len(sorted_values) // 2])


def ratio(num: int, den: int) -> float | None:
    if den == 0:
        return None
    return round(num / den, 4)


def usage_to_dict(usage: Any) -> dict[str, int]:
    if usage is None:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    return {
        "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
    }


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
