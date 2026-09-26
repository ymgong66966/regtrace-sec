#!/usr/bin/env python3
"""Evaluate SEC resolution/follow-up prediction with and without amended filing evidence."""

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
    parser.add_argument("--input", default="data/sec_amended_evidence_prototype_v1_test100/evidence_sample_reranked_v2.jsonl")
    parser.add_argument(
        "--target",
        choices=["regulator_followup_label", "visible_evidence_resolution_label"],
        required=True,
    )
    parser.add_argument(
        "--input-mode",
        choices=["response_only", "evidence_quote", "evidence_snippets", "evidence_summary"],
        required=True,
    )
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--num-threads", type=int, default=4)
    parser.add_argument("--max-tokens", type=int, default=320)
    parser.add_argument("--out-dir", default="outputs/sec_evidence_prompt_eval")
    parser.add_argument("--usage-ledger", default="outputs/openai_usage_ledger.jsonl")
    parser.add_argument("--estimate-only", action="store_true")
    args = parser.parse_args()

    rows = prepare_rows(load_jsonl(Path(args.input)), args.target)
    if args.max_rows > 0:
        rows = rows[: args.max_rows]

    estimate = estimate_cost(rows, args.model, args.input_mode, args.target, args.max_tokens)
    if args.estimate_only:
        print(json.dumps(estimate, indent=2, ensure_ascii=False))
        return 0
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")

    runner = Runner(
        client=OpenAI(),
        model=args.model,
        input_mode=args.input_mode,
        target=args.target,
        max_tokens=args.max_tokens,
        usage_ledger=args.usage_ledger,
    )
    predictions = evaluate_rows(runner, rows, args.num_threads)
    summary = summarize(predictions)
    result = {
        "input": args.input,
        "target": args.target,
        "input_mode": args.input_mode,
        "model": args.model,
        "num_rows": len(rows),
        "estimate": estimate,
        "summary": summary,
        "predictions": predictions,
        "model_input_fields": input_fields(args.input_mode),
    }
    out_dir = Path(args.out_dir) / args.target / args.input_mode
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    write_jsonl(out_dir / "predictions.jsonl", predictions)
    print(json.dumps({k: v for k, v in result.items() if k != "predictions"}, indent=2, ensure_ascii=False))
    return 0


class Runner:
    def __init__(
        self,
        *,
        client: OpenAI,
        model: str,
        input_mode: str,
        target: str,
        max_tokens: int,
        usage_ledger: str | None,
    ) -> None:
        self.client = client
        self.model = model
        self.input_mode = input_mode
        self.target = target
        self.max_tokens = max_tokens
        self.usage_ledger = usage_ledger

    def predict(self, row: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.build_messages(row),
            temperature=0,
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"},
        )
        elapsed = time.time() - started
        usage = usage_to_dict(response.usage)
        cost = cost_for_tokens(self.model, usage["prompt_tokens"], usage["completion_tokens"])
        append_usage_record(
            self.usage_ledger,
            purpose=f"sec_evidence_prompt_eval:{self.target}:{self.input_mode}",
            model=self.model,
            usage=usage,
            estimated_cost_usd=cost,
        )
        parsed = parse_json_prediction(response.choices[0].message.content or "{}")
        pred = normalize_label(parsed.get("label", ""))
        return {
            "example_id": row["example_id"],
            "gold": row["_target_label"],
            "pred": pred,
            "correct": pred == row["_target_label"],
            "reason": parsed.get("reason", ""),
            "raw_label": parsed.get("label", ""),
            "input_mode": self.input_mode,
            "target": self.target,
            "evidence_relevance": row.get("amended_evidence_evidence_relevance"),
            "event_label": row.get("regulator_followup_label"),
            "visible_label": row.get("visible_evidence_resolution_label"),
            "latency_sec": round(elapsed, 3),
            "usage": usage,
            "estimated_cost_usd": cost,
        }

    def build_messages(self, row: dict[str, Any]) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": system_instruction(self.target, self.input_mode)},
            {
                "role": "user",
                "content": (
                    f"{format_case(row, self.input_mode)}\n\n"
                    "Return JSON with exactly these keys: label, reason. "
                    "label must be one of: resolved, unresolved."
                ),
            },
        ]


def system_instruction(target: str, input_mode: str) -> str:
    if target == "regulator_followup_label":
        base = """You are predicting whether SEC staff will issue a same-obligation next-round follow-up after a company's response.

Label "unresolved" when the company's response is likely to leave a concrete same-obligation issue that SEC staff would continue pursuing.
Label "resolved" when the company appears to have substantively addressed the same SEC obligation such that no same-obligation follow-up is expected.

This is an event-risk task. Do not mark unresolved merely because the answer could be more detailed."""
    else:
        base = """You are evaluating visible amended-filing evidence for an SEC comment-response pair.

Label "resolved" only when the visible information shows that the company satisfied all material elements of the SEC request.
Label "unresolved" when the visible information shows a concrete unmet requirement, partial fix, missing named item, missing quantification, missing accounting/legal analysis, or no visible evidence of the claimed fix.

This is an evidence-grounded sufficiency task, not a prediction of whether SEC staff later followed up."""

    if input_mode == "response_only":
        return base + "\n\nUse only the SEC comment and company response. Do not assume unseen amended filing text."
    if input_mode == "evidence_summary":
        return base + "\n\nYou may use the provided amended-filing evidence summary. Treat it as an upper-bound setting because it is preprocessed."
    return base + "\n\nUse the SEC comment, company response, and raw amended-filing evidence. Do not infer facts beyond the visible evidence."


def format_case(row: dict[str, Any], input_mode: str) -> str:
    parts = [
        "SEC comment:",
        str(row.get("sec_comment", ""))[:3500],
        "",
        "Company response:",
        str(row.get("company_response", ""))[:3500],
    ]
    if input_mode == "evidence_quote":
        quote = str(row.get("amended_evidence_supporting_quote") or "").strip()
        parts.extend(["", "Amended filing evidence quote:", quote[:1800] if quote else "[no retrieved quote]"])
    elif input_mode == "evidence_snippets":
        snippets = row.get("retrieved_snippets") or []
        formatted = []
        for idx, snippet in enumerate(snippets[:3], start=1):
            formatted.append(
                f"[Snippet {idx} | form={snippet.get('candidate_form')} | date={snippet.get('candidate_filing_date')}]\n"
                f"{str(snippet.get('snippet') or '')[:1600]}"
            )
        parts.extend(["", "Retrieved amended-filing snippets:", "\n\n".join(formatted) if formatted else "[none]"])
    elif input_mode == "evidence_summary":
        summary = str(row.get("amended_evidence_evidence_summary") or "")
        missing = str(row.get("amended_evidence_missing_evidence") or "")
        quote = str(row.get("amended_evidence_supporting_quote") or "")
        parts.extend([
            "",
            "Preprocessed amended-filing evidence:",
            f"Quote: {quote[:1200] if quote else '[none]'}",
            f"Evidence summary: {summary[:900]}",
            f"Missing evidence note: {missing[:900]}",
        ])
    return "\n".join(parts)


def prepare_rows(rows: list[dict[str, Any]], target: str) -> list[dict[str, Any]]:
    prepared = []
    for row in rows:
        enriched = dict(row)
        visible_label = visible_label_from_row(row)
        enriched["visible_evidence_resolution_label"] = visible_label
        if target == "visible_evidence_resolution_label":
            if visible_label not in LABELS:
                continue
            enriched["_target_label"] = visible_label
        else:
            enriched["_target_label"] = normalize_label(row.get("regulator_followup_label", ""))
        prepared.append(enriched)
    return prepared


def visible_label_from_row(row: dict[str, Any]) -> str:
    if row.get("amended_evidence_sec_request_appears_satisfied") is True:
        return "resolved"
    if row.get("amended_evidence_visible_unmet_requirement") is True:
        return "unresolved"
    return "unknown"


def input_fields(input_mode: str) -> list[str]:
    fields = ["sec_comment", "company_response"]
    if input_mode == "evidence_quote":
        fields.append("amended_evidence_supporting_quote")
    elif input_mode == "evidence_snippets":
        fields.append("retrieved_snippets")
    elif input_mode == "evidence_summary":
        fields.extend([
            "amended_evidence_supporting_quote",
            "amended_evidence_evidence_summary",
            "amended_evidence_missing_evidence",
        ])
    return fields


def evaluate_rows(runner: Runner, rows: list[dict[str, Any]], num_threads: int) -> list[dict[str, Any]]:
    if num_threads <= 1:
        out = []
        for index, row in enumerate(rows, start=1):
            print(f"[{runner.target}:{runner.input_mode}] {index}/{len(rows)} {row['example_id']}", flush=True)
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
            print(f"[{runner.target}:{runner.input_mode}] {done}/{len(rows)} {row['example_id']}", flush=True)
    return [row for row in out if row is not None]


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    gold = [row["gold"] for row in rows]
    pred = [row["pred"] for row in rows]
    report = classification_report(gold, pred, LABELS)
    return {
        "accuracy": report["accuracy"],
        "classification_report": report,
        "gold_counts": dict(Counter(gold)),
        "pred_counts": dict(Counter(pred)),
        "cost_usd": round(sum(float(row.get("estimated_cost_usd") or 0) for row in rows), 6),
        "by_evidence_relevance": by_group(rows, "evidence_relevance"),
    }


def by_group(rows: list[dict[str, Any]], group_key: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row.get(group_key)), []).append(row)
    for group, group_rows in sorted(groups.items()):
        out[group] = classification_report(
            [row["gold"] for row in group_rows],
            [row["pred"] for row in group_rows],
            LABELS,
        )
    return out


def classification_report(gold: list[str], pred: list[str], labels: tuple[str, ...]) -> dict[str, Any]:
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


def estimate_cost(rows: list[dict[str, Any]], model: str, input_mode: str, target: str, max_tokens: int) -> dict[str, Any]:
    input_tokens = output_tokens = 0
    for row in rows:
        input_tokens += estimate_text_tokens(system_instruction(target, input_mode))
        input_tokens += estimate_text_tokens(format_case(row, input_mode))
        input_tokens += 80
        output_tokens += max_tokens
    return {
        "rows": len(rows),
        "model": model,
        "input_mode": input_mode,
        "target": target,
        "input_tokens_est": input_tokens,
        "output_tokens_est": output_tokens,
        "cost_usd_est": cost_for_tokens(model, input_tokens, output_tokens),
    }


def usage_to_dict(usage: Any) -> dict[str, int]:
    if usage is None:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    return {
        "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
    }


def parse_json_prediction(content: str) -> dict[str, Any]:
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
    return {"label": content[:80], "reason": content}


def normalize_label(value: Any) -> str:
    lowered = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    if "unresolved" in lowered or lowered in {"not_resolved", "followup", "follow_up", "1", "true"}:
        return "unresolved"
    return "resolved"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
