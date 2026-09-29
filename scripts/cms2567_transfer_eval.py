#!/usr/bin/env python3
"""Evaluate RegTrace-style transfer prompts on CMS-2567 POC adequacy labels."""

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


MODES = ("generic", "regtrace_transfer", "regtrace_calibrated", "cms_rubric")
LABELS = ("adequate", "not_adequate")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="outputs/cms2567_poc_adjudication/calibrated_audit_balanced_50_input.jsonl")
    parser.add_argument("--primary", default="outputs/cms2567_poc_adjudication/sample_120_calibrated_primary/adjudications.jsonl")
    parser.add_argument("--audit", default="outputs/cms2567_poc_adjudication/calibrated_audit_balanced_50_gpt4omini/adjudications.jsonl")
    parser.add_argument(
        "--benchmark",
        default="",
        help="Optional canonical benchmark JSONL with cms_poc_binary_label. If set, ignores --input/--primary/--audit.",
    )
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--max-tokens", type=int, default=520)
    parser.add_argument("--num-threads", type=int, default=4)
    parser.add_argument("--out-dir", default="outputs/cms2567_transfer_eval")
    parser.add_argument("--usage-ledger", default="outputs/openai_usage_ledger.jsonl")
    parser.add_argument("--estimate-only", action="store_true")
    args = parser.parse_args()

    rows = build_benchmark_rows(Path(args.benchmark)) if args.benchmark else build_consensus_rows(
        Path(args.input),
        Path(args.primary),
        Path(args.audit),
    )
    estimate = estimate_cost(rows, args.mode, args.model, args.max_tokens)
    if args.estimate_only:
        print(json.dumps(estimate, indent=2, ensure_ascii=False))
        return 0
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")

    runner = Runner(
        client=OpenAI(),
        model=args.model,
        mode=args.mode,
        max_tokens=args.max_tokens,
        usage_ledger=args.usage_ledger,
    )
    predictions = evaluate_rows(runner, rows, args.num_threads)
    summary = summarize(predictions)
    result = {
        "input": args.input,
        "benchmark": args.benchmark,
        "primary": args.primary,
        "audit": args.audit,
        "mode": args.mode,
        "model": args.model,
        "num_rows": len(rows),
        "gold_counts": dict(Counter(row["_gold_binary"] for row in rows)),
        "estimate": estimate,
        "summary": summary,
    }
    out_dir = Path(args.out_dir) / model_slug(args.model) / args.mode
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_dir / "predictions.jsonl", predictions)
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
        mode: str,
        max_tokens: int,
        usage_ledger: str | None,
    ) -> None:
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
        elapsed = time.time() - started
        usage = usage_to_dict(response.usage)
        cost = cost_for_tokens(self.model, usage["prompt_tokens"], usage["completion_tokens"])
        append_usage_record(
            self.usage_ledger,
            purpose=f"cms2567_transfer_eval:{self.mode}",
            model=self.model,
            usage=usage,
            estimated_cost_usd=cost,
        )
        parsed = parse_json(response.choices[0].message.content or "{}")
        pred = normalize_binary(parsed.get("label"))
        return {
            "example_id": row["example_id"],
            "gold": row["_gold_binary"],
            "pred": pred,
            "correct": pred == row["_gold_binary"],
            "mode": self.mode,
            "ftag": row.get("ftag"),
            "severity_band": row.get("severity_band"),
            "ftag_group": row.get("ftag_group"),
            "primary_label": row.get("_primary_label"),
            "audit_label": row.get("_audit_label"),
            "reason": str(parsed.get("reason", ""))[:1800],
            "obligations": parsed.get("obligations", []) if isinstance(parsed.get("obligations"), list) else [],
            "missing_elements": parsed.get("missing_elements", [])
            if isinstance(parsed.get("missing_elements"), list)
            else [],
            "latency_sec": round(elapsed, 3),
            "usage": usage,
            "estimated_cost_usd": cost,
        }


def build_consensus_rows(input_path: Path, primary_path: Path, audit_path: Path) -> list[dict[str, Any]]:
    source = {row["example_id"]: row for row in load_jsonl(input_path)}
    primary = {row["example_id"]: row for row in load_jsonl(primary_path)}
    audit = {row["example_id"]: row for row in load_jsonl(audit_path)}
    rows: list[dict[str, Any]] = []
    for example_id, audit_row in audit.items():
        if example_id not in source or example_id not in primary:
            continue
        primary_label = normalize_three(primary[example_id].get("primary_label"))
        audit_label = normalize_three(audit_row.get("primary_label"))
        gold: str | None = None
        if primary_label == "adequate" and audit_label == "adequate":
            gold = "adequate"
        elif primary_label == "inadequate" and audit_label in {"partial", "inadequate"}:
            gold = "not_adequate"
        elif primary_label == "partial" and audit_label in {"partial", "inadequate"}:
            gold = "not_adequate"
        if gold is None:
            continue
        row = dict(source[example_id])
        row["_gold_binary"] = gold
        row["_primary_label"] = primary_label
        row["_audit_label"] = audit_label
        rows.append(row)
    rows.sort(key=lambda row: row["example_id"])
    return rows


def build_benchmark_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in load_jsonl(path):
        out = dict(row)
        out["_gold_binary"] = normalize_binary(row.get("cms_poc_binary_label"))
        out["_primary_label"] = row.get("cms_poc_adequacy_label", "")
        out["_audit_label"] = ""
        rows.append(out)
    rows.sort(key=lambda row: row["example_id"])
    return rows


def build_messages(row: dict[str, Any], mode: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": system_prompt(mode)},
        {
            "role": "user",
            "content": (
                f"{format_case(row)}\n\n"
                "Return strict JSON with keys: label, reason, obligations, missing_elements. "
                "label must be adequate or not_adequate."
            ),
        },
    ]


def system_prompt(mode: str) -> str:
    if mode == "generic":
        return (
            "You are reviewing a CMS-2567 nursing-home Plan of Correction. "
            "Decide whether the plan adequately responds to the cited deficiency. "
            "Use only the deficiency narrative and the plan text. "
            "Return adequate if the plan is a sufficient response, otherwise not_adequate."
        )
    if mode == "cms_rubric":
        return (
            "You are a CMS-2567 plan-of-correction adequacy reviewer. "
            "Use only the deficiency narrative and the provider's plan text. "
            "Label adequate if the plan substantially addresses the material deficiency; it need not be perfect. "
            "It should visibly cover the main resident-specific correction where applicable, the affected or at-risk population, "
            "a systemic prevention step such as education/policy/process change, monitoring/audit/QAPI or responsible follow-up, "
            "and a concrete timing/completion basis. "
            "Label not_adequate if a material cited component is missing, the plan is only boilerplate or future intent, "
            "or the plan misses the central deficient practice. "
            "Do not downgrade merely because more detail would be helpful; downgrade only for material gaps."
        )
    if mode == "regtrace_calibrated":
        return (
            "You are applying a RegTrace obligation-to-response review policy in a new regulatory domain. "
            "Transfer the structure, not the SEC-specific skepticism threshold. "
            "First extract the material obligations in the deficiency narrative. Then compare the Plan of Correction to those obligations. "
            "A plan is adequate if it substantially addresses the central deficiency, even if it is not perfect. "
            "Look for a visible chain: cited deficient practice -> resident-specific or immediate correction where applicable -> at-risk population -> systemic prevention -> monitoring or responsible follow-up -> timing/completion basis. "
            "Label not_adequate only when a central material obligation is missing, the plan is mostly boilerplate/future intent, "
            "or the plan fails to map corrective actions to the main cited risk. "
            "Do not downgrade merely because the plan could include more detail. Do not invent requirements beyond the deficiency narrative."
        )
    return (
        "You are applying a RegTrace obligation-to-response review policy learned from evidence-grounded regulatory review. "
        "This policy is domain-general: first extract the material obligations in the regulator's deficiency narrative, "
        "then compare the organization's response against those obligations. "
        "Do not reward length, boilerplate, or a promise to improve unless the plan visibly addresses the obligation. "
        "Do not invent requirements beyond the deficiency narrative. "
        "Label adequate only when the plan visibly satisfies the material obligations at a substantive level. "
        "Label not_adequate if any central obligation is missing, only partially addressed, unsupported, or replaced by generic training/auditing language. "
        "Distinguish a plan that sounds compliant from one that actually maps deficiency -> corrective action -> systemic prevention -> monitoring."
    )


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


def estimate_cost(rows: list[dict[str, Any]], mode: str, model: str, max_tokens: int) -> dict[str, Any]:
    input_tokens = output_tokens = 0
    for row in rows:
        input_tokens += sum(estimate_text_tokens(message["content"]) for message in build_messages(row, mode)) + 80
        output_tokens += max_tokens
    return {
        "rows": len(rows),
        "model": model,
        "mode": mode,
        "input_tokens_est": input_tokens,
        "output_tokens_est": output_tokens,
        "cost_usd_est": cost_for_tokens(model, input_tokens, output_tokens),
    }


def evaluate_rows(runner: Runner, rows: list[dict[str, Any]], num_threads: int) -> list[dict[str, Any]]:
    if num_threads <= 1:
        predictions = []
        for index, row in enumerate(rows, start=1):
            print(f"[cms-transfer] {runner.mode} {index}/{len(rows)} {row['example_id']}", flush=True)
            predictions.append(runner.predict(row))
        return predictions
    predictions: list[dict[str, Any] | None] = [None] * len(rows)
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {executor.submit(runner.predict, row): (index, row) for index, row in enumerate(rows)}
        done = 0
        for future in as_completed(futures):
            index, row = futures[future]
            predictions[index] = future.result()
            done += 1
            print(f"[cms-transfer] {runner.mode} {done}/{len(rows)} {row['example_id']}", flush=True)
    return [row for row in predictions if row is not None]


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    gold = [row["gold"] for row in rows]
    pred = [row["pred"] for row in rows]
    return {
        "accuracy": ratio(sum(1 for row in rows if row["correct"]), len(rows)),
        "macro_f1": macro_f1(gold, pred),
        "label_counts": dict(Counter(gold)),
        "pred_counts": dict(Counter(pred)),
        "per_label": {label: prf(gold, pred, label) for label in LABELS},
        "cost_usd": round(sum(float(row.get("estimated_cost_usd") or 0) for row in rows), 6),
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


def write_summary_md(path: Path, result: dict[str, Any]) -> None:
    summary = result["summary"]
    text = f"""# CMS-2567 Transfer Evaluation

- Mode: `{result['mode']}`
- Model: `{result['model']}`
- Rows: {result['num_rows']}
- Gold counts: {result['gold_counts']}

| metric | value |
| --- | ---: |
| Accuracy | {summary['accuracy']:.4f} |
| Macro-F1 | {summary['macro_f1']:.4f} |
| Cost USD | {summary['cost_usd']:.6f} |

## Per Label

```json
{json.dumps(summary['per_label'], indent=2, ensure_ascii=False)}
```

## Prediction Counts

```json
{json.dumps(summary['pred_counts'], indent=2, ensure_ascii=False)}
```
"""
    path.write_text(text, encoding="utf-8")


def normalize_three(value: Any) -> str:
    text = str(value or "").strip().lower()
    if "inadequate" in text:
        return "inadequate"
    if "partial" in text:
        return "partial"
    if "adequate" in text:
        return "adequate"
    return "partial"


def normalize_binary(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_")
    if "not_adequate" in text or "not adequate" in text or "inadequate" in text or "partial" in text:
        return "not_adequate"
    if "adequate" in text:
        return "adequate"
    return "not_adequate"


def ratio(num: int, den: int) -> float:
    return round(num / den, 4) if den else 0.0


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
    return {"label": "not_adequate", "reason": content}


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
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
