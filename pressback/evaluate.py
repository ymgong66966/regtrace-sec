from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .baselines import heuristic_predict, sec_heuristic_predict


def load_threads_jsonl(path: str | Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def corpus_summary(rows: list[dict]) -> dict:
    tiers = Counter(row.get("tier", "none") for row in rows)
    labels = Counter(row.get("label") for row in rows)
    transcripts = {row.get("transcript_id") for row in rows}
    return {
        "transcripts": len(transcripts),
        "threads": len(rows),
        "labels": dict(labels),
        "tiers": dict(tiers),
        "press_back_rate": labels.get("non_responsive", 0) / len(rows) if rows else 0.0,
    }


def evaluate_heuristic(rows: list[dict]) -> dict:
    gold = [row["label"] for row in rows]
    pred = [heuristic_predict(row["question"], row["answer"]) for row in rows]
    return classification_report(gold, pred)


def evaluate_sec_heuristic(rows: list[dict]) -> dict:
    gold = [row["target_label"] for row in rows]
    pred = [sec_heuristic_predict(row["sec_comment"], row["company_response"]) for row in rows]
    return classification_report(gold, pred, labels=["resolved", "unresolved"])


def classification_report(gold: list[str], pred: list[str], labels: list[str] | None = None) -> dict:
    labels = labels or ["responsive", "non_responsive"]
    report: dict[str, dict[str, float]] = {}
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
