#!/usr/bin/env python3
"""Run non-prompt supervised baselines for RegTrace-SEC.

The goal is reviewer-facing reproducibility: compare prompt-optimization methods
against a simple supervised classifier that receives the same test-time fields.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support
from sklearn.pipeline import Pipeline


LABELS = ("resolved", "unresolved")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--split-dir",
        default="data/sec_visible_evidence_benchmark_v2/splits/grouped_random_dev48_gap/fold_0",
    )
    parser.add_argument(
        "--text-mode",
        choices=["response_only", "evidence_snippets", "oracle_summary"],
        default="evidence_snippets",
    )
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--out-dir", default="outputs/sec_supervised_baselines")
    args = parser.parse_args()

    split_dir = Path(args.split_dir)
    train = load_jsonl(split_dir / "train.jsonl")
    dev = load_jsonl(split_dir / "dev.jsonl")
    test = load_jsonl(split_dir / "test.jsonl")

    tuned = tune_logreg(train, dev, args.text_mode, args.seed)
    final_train = train + dev
    model = build_model(tuned["C"], tuned["ngram_range"], args.seed)
    model.fit([format_case(row, args.text_mode) for row in final_train], labels(final_train))
    pred = list(model.predict([format_case(row, args.text_mode) for row in test]))

    majority_label = Counter(labels(train)).most_common(1)[0][0]
    majority_pred = [majority_label] * len(test)
    random_pred = random_prior_predictions(train, len(test), args.seed)

    rows = [
        metric_row("Majority class", labels(test), majority_pred, args.text_mode, {"majority_label": majority_label}),
        metric_row("Random train-prior", labels(test), random_pred, args.text_mode, {"seed": args.seed}),
        metric_row(
            "TF-IDF logistic regression",
            labels(test),
            pred,
            args.text_mode,
            {
                "C": tuned["C"],
                "ngram_range": list(tuned["ngram_range"]),
                "dev_macro_f1": tuned["dev_macro_f1"],
            },
        ),
    ]

    out_dir = Path(args.out_dir) / split_dir.parent.name / args.text_mode
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "split_dir": str(split_dir),
        "text_mode": args.text_mode,
        "seed": args.seed,
        "train_size": len(train),
        "dev_size": len(dev),
        "test_size": len(test),
        "train_label_counts": dict(Counter(labels(train))),
        "dev_label_counts": dict(Counter(labels(dev))),
        "test_label_counts": dict(Counter(labels(test))),
        "tuned_logreg": tuned,
        "metrics": rows,
        "model_input_fields": input_fields(args.text_mode),
    }
    (out_dir / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    write_metrics_csv(out_dir / "metrics.csv", rows)
    write_metrics_md(out_dir / "metrics.md", result)
    write_predictions(out_dir / "tfidf_logreg_predictions.jsonl", test, pred)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def tune_logreg(train: list[dict[str, Any]], dev: list[dict[str, Any]], text_mode: str, seed: int) -> dict[str, Any]:
    best: dict[str, Any] | None = None
    for c_value in [0.1, 0.3, 1.0, 3.0, 10.0]:
        for ngram_range in [(1, 1), (1, 2)]:
            model = build_model(c_value, ngram_range, seed)
            model.fit([format_case(row, text_mode) for row in train], labels(train))
            pred = list(model.predict([format_case(row, text_mode) for row in dev]))
            macro = f1_score(labels(dev), pred, labels=list(LABELS), average="macro", zero_division=0)
            candidate = {"C": c_value, "ngram_range": ngram_range, "dev_macro_f1": macro}
            if best is None or macro > best["dev_macro_f1"]:
                best = candidate
    assert best is not None
    return best


def build_model(c_value: float, ngram_range: tuple[int, int], seed: int) -> Pipeline:
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    strip_accents="unicode",
                    max_features=50000,
                    min_df=2,
                    ngram_range=ngram_range,
                    sublinear_tf=True,
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    C=c_value,
                    class_weight="balanced",
                    max_iter=2000,
                    random_state=seed,
                    solver="liblinear",
                ),
            ),
        ]
    )


def format_case(row: dict[str, Any], text_mode: str) -> str:
    parts = [
        "SEC COMMENT\n" + str(row.get("sec_comment") or ""),
        "COMPANY RESPONSE\n" + str(row.get("company_response") or ""),
    ]
    if text_mode == "evidence_snippets":
        snippets = []
        for index, snippet in enumerate((row.get("retrieved_snippets") or [])[:3], start=1):
            snippets.append(f"SNIPPET {index}\n{snippet.get('snippet') or ''}")
        parts.append("RETRIEVED AMENDED FILING SNIPPETS\n" + "\n\n".join(snippets))
    elif text_mode == "oracle_summary":
        parts.extend(
            [
                "SUPPORTING QUOTE\n" + str(row.get("amended_evidence_supporting_quote") or ""),
                "EVIDENCE SUMMARY\n" + str(row.get("amended_evidence_evidence_summary") or ""),
                "MISSING EVIDENCE NOTE\n" + str(row.get("amended_evidence_missing_evidence") or ""),
            ]
        )
    return "\n\n".join(parts)


def input_fields(text_mode: str) -> list[str]:
    fields = ["sec_comment", "company_response"]
    if text_mode == "evidence_snippets":
        fields.append("retrieved_snippets[:3].snippet")
    elif text_mode == "oracle_summary":
        fields.extend(
            [
                "amended_evidence_supporting_quote",
                "amended_evidence_evidence_summary",
                "amended_evidence_missing_evidence",
            ]
        )
    return fields


def labels(rows: list[dict[str, Any]]) -> list[str]:
    return [normalize_label(row.get("visible_evidence_resolution_label")) for row in rows]


def normalize_label(value: Any) -> str:
    text = str(value).strip().lower().replace("-", "_")
    if "unresolved" in text:
        return "unresolved"
    return "resolved"


def random_prior_predictions(train: list[dict[str, Any]], n: int, seed: int) -> list[str]:
    rng = random.Random(seed)
    counts = Counter(labels(train))
    total = sum(counts.values())
    unresolved_prob = counts["unresolved"] / total if total else 0.5
    return ["unresolved" if rng.random() < unresolved_prob else "resolved" for _ in range(n)]


def metric_row(
    method: str,
    gold: list[str],
    pred: list[str],
    text_mode: str,
    extra: dict[str, Any],
) -> dict[str, Any]:
    precision, recall, f1, support = precision_recall_fscore_support(
        gold,
        pred,
        labels=list(LABELS),
        zero_division=0,
    )
    return {
        "method": method,
        "text_mode": text_mode,
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
        "extra": extra,
    }


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_predictions(path: Path, rows: list[dict[str, Any]], pred: list[str]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row, label in zip(rows, pred):
            handle.write(
                json.dumps(
                    {
                        "example_id": row.get("example_id"),
                        "gold": normalize_label(row.get("visible_evidence_resolution_label")),
                        "pred": label,
                        "issue_category": row.get("issue_category"),
                        "review_group_key": row.get("review_group_key"),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


def write_metrics_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [key for key in rows[0].keys() if key != "extra"] + ["extra_json"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            out = {key: value for key, value in row.items() if key != "extra"}
            out["extra_json"] = json.dumps(row["extra"], ensure_ascii=False)
            writer.writerow(out)


def write_metrics_md(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Supervised Baselines",
        "",
        f"Split: `{result['split_dir']}`.",
        f"Text mode: `{result['text_mode']}`.",
        f"Train/dev/test: {result['train_size']}/{result['dev_size']}/{result['test_size']}.",
        "",
        "| Method | Accuracy | Macro-F1 | Resolved F1 | Unresolved F1 | Unresolved Precision | Unresolved Recall |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["metrics"]:
        lines.append(
            "| {method} | {accuracy:.3f} | {macro_f1:.3f} | {resolved_f1:.3f} | {unresolved_f1:.3f} | {unresolved_precision:.3f} | {unresolved_recall:.3f} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "The TF-IDF model is tuned on the development set and then refit on train+dev before held-out test evaluation.",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
