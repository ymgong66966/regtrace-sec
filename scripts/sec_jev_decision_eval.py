#!/usr/bin/env python3
"""Evaluate Jev/System One as a typed RegTrace decision gate.

Jev is used as a non-generative decision component: given a SEC comment, company
response, and retrieved amended-filing evidence, it returns a typed choice with
probabilities rather than free-form text.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support


LABELS = ("resolved", "unresolved")
DEFAULT_ENDPOINT = "https://api.typesafe.ai/v1/systemone"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--split-path",
        default="data/sec_visible_evidence_benchmark_v2/splits/grouped_random_dev48_gap/fold_0/test.jsonl",
    )
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--model", default="jev-latest")
    parser.add_argument("--endpoint", default=os.environ.get("JEV_API_URL", DEFAULT_ENDPOINT))
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--sleep", type=float, default=0.1)
    parser.add_argument("--max-snippets", type=int, default=3)
    parser.add_argument("--out-dir", default="outputs/sec_jev_eval")
    args = parser.parse_args()

    load_env_file(Path(args.env_file))
    api_key = os.environ.get("JEV_API_KEY") or os.environ.get("TYPESAFE_API_KEY")
    if not api_key:
        raise SystemExit("Missing JEV_API_KEY or TYPESAFE_API_KEY in environment/.env")

    rows = load_jsonl(Path(args.split_path))
    subset = rows[args.offset : args.offset + args.limit] if args.limit else rows[args.offset :]
    predictions = []
    errors = []
    usage = {"input_tokens": 0, "output_tokens": 0, "requests": 0}

    out_dir = Path(args.out_dir) / Path(args.split_path).parent.parent.name / Path(args.split_path).parent.name
    out_dir.mkdir(parents=True, exist_ok=True)

    for index, row in enumerate(subset, start=args.offset):
        payload = build_payload(row, args.model, args.max_snippets)
        try:
            response = post_json(args.endpoint, api_key, payload)
            parsed = parse_response(response)
            gold = normalize_label(row.get("visible_evidence_resolution_label"))
            predictions.append(
                {
                    "row_index": index,
                    "example_id": row.get("example_id"),
                    "gold": gold,
                    "pred": parsed["pred"],
                    "resolved_probability": parsed.get("resolved_probability"),
                    "unresolved_probability": parsed.get("unresolved_probability"),
                    "confidence": parsed.get("confidence"),
                    "raw_answer": parsed.get("raw_answer"),
                    "usage": extract_usage(response),
                    "issue_category": row.get("issue_category"),
                    "review_group_key": row.get("review_group_key"),
                }
            )
            add_usage(usage, extract_usage(response))
        except Exception as exc:  # noqa: BLE001
            errors.append(
                {
                    "row_index": index,
                    "example_id": row.get("example_id"),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
        time.sleep(args.sleep)

    metrics = compute_metrics(predictions)
    result = {
        "split_path": args.split_path,
        "offset": args.offset,
        "limit": args.limit,
        "model": args.model,
        "endpoint": scrub_endpoint(args.endpoint),
        "max_snippets": args.max_snippets,
        "num_predictions": len(predictions),
        "num_errors": len(errors),
        "metrics": metrics,
        "usage": usage,
        "notes": "Jev/System One typed decision gate. No key is written to artifacts.",
    }

    (out_dir / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    write_jsonl(out_dir / "predictions.jsonl", predictions)
    write_jsonl(out_dir / "errors.jsonl", errors)
    write_metrics_csv(out_dir / "metrics.csv", metrics)
    write_metrics_md(out_dir / "metrics.md", result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not errors else 2


def build_payload(row: dict[str, Any], model: str, max_snippets: int) -> dict[str, Any]:
    snippets = []
    for index, snippet in enumerate((row.get("retrieved_snippets") or [])[:max_snippets], start=1):
        snippets.append(
            {
                "rank": index,
                "snippet": snippet.get("snippet") or "",
            }
        )
    state = {
        "sec_comment": row.get("sec_comment") or "",
        "company_response": row.get("company_response") or "",
        "retrieved_amended_filing_snippets": snippets,
    }
    return {
        "model": model,
        "state": state,
        "questions": {
            "resolution": {
                "type": "choice",
                "instructions": (
                    "Decide whether the company response and visible amended-filing evidence resolve "
                    "the SEC comment. Choose resolved only if the visible evidence satisfies all material "
                    "SEC request elements. Choose unresolved if a named disclosure, quantification, exhibit, "
                    "legal/accounting analysis, or other material requested item remains missing or only "
                    "partially addressed. Do not treat a company claim that it revised the filing as sufficient "
                    "unless the visible evidence supports the requested change."
                ),
                "criteria": {
                    "resolved": "The visible amended-filing evidence satisfies the material SEC request.",
                    "unresolved": "The visible amended-filing evidence leaves a material SEC request unmet.",
                },
            }
        },
    }


def post_json(endpoint: str, api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "RegTraceJevEval/0.1 (+https://github.com/ymgong66966/regtrace-sec)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body[:1000]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"URL error: {exc.reason}") from exc


def parse_response(response: dict[str, Any]) -> dict[str, Any]:
    response_root = response
    if isinstance(response.get("data"), dict) and isinstance(response["data"].get("result"), dict):
        response_root = response["data"]["result"]
    answer = (response_root.get("answers") or {}).get("resolution")
    if not isinstance(answer, dict):
        raise ValueError(f"Missing answers.resolution in response: {response}")
    choice = normalize_label(answer.get("choice"))
    probabilities = answer.get("probabilities") or {}
    return {
        "pred": choice,
        "resolved_probability": normalize_probability(probabilities.get("resolved")),
        "unresolved_probability": normalize_probability(probabilities.get("unresolved")),
        "confidence": normalize_probability(answer.get("confidence")),
        "raw_answer": answer,
    }


def compute_metrics(predictions: list[dict[str, Any]]) -> dict[str, Any]:
    if not predictions:
        return {}
    gold = [row["gold"] for row in predictions]
    pred = [row["pred"] for row in predictions]
    precision, recall, f1, support = precision_recall_fscore_support(
        gold,
        pred,
        labels=list(LABELS),
        zero_division=0,
    )
    return {
        "accuracy": accuracy_score(gold, pred),
        "macro_f1": f1_score(gold, pred, labels=list(LABELS), average="macro", zero_division=0),
        "resolved_precision": precision[0],
        "resolved_recall": recall[0],
        "resolved_f1": f1[0],
        "resolved_support": int(support[0]),
        "unresolved_precision": precision[1],
        "unresolved_recall": recall[1],
        "unresolved_f1": f1[1],
        "unresolved_support": int(support[1]),
    }


def normalize_label(value: Any) -> str:
    text = str(value).strip().lower().replace("-", "_")
    if "unresolved" in text:
        return "unresolved"
    return "resolved"


def normalize_probability(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def add_usage(total: dict[str, int], usage: Any) -> None:
    if not isinstance(usage, dict):
        return
    total["requests"] += 1
    for key in ["input_tokens", "output_tokens"]:
        try:
            total[key] += int(usage.get(key) or 0)
        except (TypeError, ValueError):
            pass


def extract_usage(response: dict[str, Any]) -> Any:
    if isinstance(response.get("usage"), dict):
        return response.get("usage")
    if isinstance(response.get("data"), dict):
        result = response["data"].get("result")
        if isinstance(result, dict) and isinstance(result.get("usage"), dict):
            return result.get("usage")
    return None


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_metrics_csv(path: Path, metrics: dict[str, Any]) -> None:
    if not metrics:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(metrics.keys()))
        writer.writeheader()
        writer.writerow(metrics)


def write_metrics_md(path: Path, result: dict[str, Any]) -> None:
    metrics = result.get("metrics") or {}
    lines = [
        "# Jev Typed Decision Gate",
        "",
        f"Split path: `{result['split_path']}`.",
        f"Model: `{result['model']}`.",
        f"Endpoint: `{result['endpoint']}`.",
        f"Rows evaluated: {result['num_predictions']} predictions, {result['num_errors']} errors.",
        "",
    ]
    if metrics:
        lines.extend(
            [
                "| Accuracy | Macro-F1 | Resolved F1 | Unresolved F1 | Unresolved Precision | Unresolved Recall |",
                "|---:|---:|---:|---:|---:|---:|",
                "| {accuracy:.3f} | {macro_f1:.3f} | {resolved_f1:.3f} | {unresolved_f1:.3f} | {unresolved_precision:.3f} | {unresolved_recall:.3f} |".format(
                    **metrics
                ),
                "",
            ]
        )
    lines.append(f"Usage: `{json.dumps(result['usage'], ensure_ascii=False)}`.")
    lines.append("")
    lines.append("Jev returns typed decisions rather than generated rationales, making it a candidate high-throughput triage gate.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def scrub_endpoint(endpoint: str) -> str:
    return endpoint.split("?")[0]


if __name__ == "__main__":
    raise SystemExit(main())
