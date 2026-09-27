#!/usr/bin/env python3
"""Evaluate obligation-guided SEC visible-evidence review modes."""

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
MODES = ("monolithic", "obligation_guided", "guarded_verifier")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="data/sec_visible_evidence_benchmark_v2/splits/grouped_random_dev48_gap/fold_0/test.jsonl",
    )
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--num-threads", type=int, default=4)
    parser.add_argument("--max-tokens", type=int, default=700)
    parser.add_argument("--out-dir", default="outputs/sec_obligation_verifier_eval")
    parser.add_argument("--usage-ledger", default="outputs/openai_usage_ledger.jsonl")
    parser.add_argument("--estimate-only", action="store_true")
    args = parser.parse_args()

    rows = prepare_rows(load_jsonl(Path(args.input)))
    if args.max_rows > 0:
        rows = rows[: args.max_rows]

    estimate = estimate_cost(rows, args.model, args.mode, args.max_tokens)
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
        "split_name": split_name(Path(args.input)),
        "mode": args.mode,
        "model": args.model,
        "num_rows": len(rows),
        "estimate": estimate,
        "summary": summary,
        "predictions": predictions,
        "model_input_fields": ["sec_comment", "company_response", "retrieved_snippets"],
    }
    out_dir = Path(args.out_dir) / split_name(Path(args.input)) / model_slug(args.model) / args.mode
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
        request_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": build_messages(row, self.mode),
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
            purpose=f"sec_obligation_verifier_eval:{self.mode}",
            model=self.model,
            usage=usage,
            estimated_cost_usd=cost,
        )
        parsed = parse_json_prediction(response.choices[0].message.content or "{}")
        pred = normalize_label(parsed.get("label", ""))
        obligations = parsed.get("obligations", [])
        if not isinstance(obligations, list):
            obligations = []
        return {
            "example_id": row["example_id"],
            "gold": row["_target_label"],
            "pred": pred,
            "correct": pred == row["_target_label"],
            "reason": str(parsed.get("reason", ""))[:2000],
            "raw_label": parsed.get("label", ""),
            "mode": self.mode,
            "issue_category": row.get("issue_category"),
            "gap_type": row.get("gap_type"),
            "evidence_relevance": row.get("amended_evidence_evidence_relevance"),
            "obligations": obligations[:8],
            "num_obligations": len(obligations),
            "latency_sec": round(elapsed, 3),
            "usage": usage,
            "estimated_cost_usd": cost,
        }


def build_messages(row: dict[str, Any], mode: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": system_instruction(mode)},
        {
            "role": "user",
            "content": (
                f"{format_case(row)}\n\n"
                "Return valid JSON. Required keys: label, reason, obligations. "
                "label must be resolved or unresolved. obligations should be a list; "
                "each item may include request, status, evidence, and gap."
            ),
        },
    ]


def model_slug(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", model).replace("/", "__")


def split_name(path: Path) -> str:
    parts = path.parts
    if "splits" in parts:
        index = parts.index("splits")
        remainder = parts[index + 1 : -1]
        return "__".join(remainder)
    return path.parent.name


def system_instruction(mode: str) -> str:
    base = """You are an autonomous evidence-grounded compliance reviewer.

Your task is to decide whether visible amended-filing evidence resolves the SEC staff request.
Use only the SEC comment, company response, and retrieved amended-filing snippets.
Do not trust a company statement such as "revised accordingly" unless the visible evidence supports it.
Do not require disclosures beyond what the SEC actually requested."""

    if mode == "monolithic":
        return base + """

Make one careful evidence-grounded decision.
Label "resolved" if the visible evidence satisfies the material request.
Label "unresolved" if a material requested item, quantification, exhibit, legal analysis, accounting analysis, or explanation remains missing."""

    if mode == "obligation_guided":
        return base + """

First identify the material obligations in the SEC comment. Then compare the response and evidence against those obligations.
The obligations are a reading aid, not a reason to invent new requirements.
Label "resolved" only when the visible evidence satisfies the material obligations."""

    return base + """

Use a guarded review policy:
1. Extract the material obligations in the SEC comment.
2. For each obligation, decide whether the visible evidence satisfies it.
3. Cite or summarize the visible evidence supporting each satisfied obligation.
4. Mark an obligation missing if the company response promises a revision but the retrieved evidence does not show the requested disclosure.
5. Output "resolved" only if every material obligation is visibly satisfied.
6. Output "unresolved" if any material obligation is missing, only partially addressed, or unsupported by visible evidence.

Keep the obligations focused on what the SEC actually requested."""


def format_case(row: dict[str, Any]) -> str:
    snippets = row.get("retrieved_snippets") or []
    formatted = []
    for idx, snippet in enumerate(snippets[:3], start=1):
        formatted.append(
            f"[Snippet {idx}]\n{str(snippet.get('snippet') or '')[:1800]}"
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
            "\n\n".join(formatted) if formatted else "[none]",
        ]
    )


def prepare_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prepared = []
    for row in rows:
        label = normalize_label(row.get("visible_evidence_resolution_label", ""))
        if label not in LABELS:
            continue
        enriched = dict(row)
        enriched["_target_label"] = label
        prepared.append(enriched)
    return prepared


def evaluate_rows(runner: Runner, rows: list[dict[str, Any]], num_threads: int) -> list[dict[str, Any]]:
    if num_threads <= 1:
        out = []
        for index, row in enumerate(rows, start=1):
            print(f"[{runner.mode}] {index}/{len(rows)} {row['example_id']}", flush=True)
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
            print(f"[{runner.mode}] {done}/{len(rows)} {row['example_id']}", flush=True)
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
        "avg_obligations": round(sum(int(row.get("num_obligations") or 0) for row in rows) / len(rows), 3) if rows else 0.0,
        "by_issue_category": by_group(rows, "issue_category"),
        "by_gap_type": by_group(rows, "gap_type"),
    }


def by_group(rows: list[dict[str, Any]], group_key: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row.get(group_key)), []).append(row)
    for group, group_rows in sorted(groups.items()):
        if len(group_rows) < 3:
            continue
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


def estimate_cost(rows: list[dict[str, Any]], model: str, mode: str, max_tokens: int) -> dict[str, Any]:
    input_tokens = output_tokens = 0
    for row in rows:
        for message in build_messages(row, mode):
            input_tokens += estimate_text_tokens(message["content"])
        input_tokens += 100
        output_tokens += max_tokens
    return {
        "rows": len(rows),
        "model": model,
        "mode": mode,
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
    return {"label": content[:80], "reason": content, "obligations": []}


def normalize_label(value: Any) -> str:
    lowered = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    if "unresolved" in lowered or "partial" in lowered or "insufficient" in lowered:
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
