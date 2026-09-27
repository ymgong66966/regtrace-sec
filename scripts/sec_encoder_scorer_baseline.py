#!/usr/bin/env python3
"""Run a frozen-encoder evidence scorer for RegTrace-SEC.

This baseline represents a cheap deployment component: encode the review context
with a local sentence encoder, then train a small linear decision head. It does
not generate tokens at inference time.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline


LABELS = ("resolved", "unresolved")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--split-dir",
        default="data/sec_visible_evidence_benchmark_v2/splits/grouped_random_dev48_gap/fold_0",
    )
    parser.add_argument(
        "--model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="SentenceTransformer model name or local path. Prefer cached/local models.",
    )
    parser.add_argument(
        "--text-mode",
        choices=["response_only", "evidence_snippets", "best_snippet", "oracle_summary"],
        default="evidence_snippets",
    )
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument(
        "--representation",
        choices=["joint", "separate_match"],
        default="separate_match",
        help="joint encodes the full case once; separate_match encodes request/response/evidence separately and adds matching features.",
    )
    parser.add_argument("--out-dir", default="outputs/sec_encoder_scorers")
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    split_dir = Path(args.split_dir)
    train = load_jsonl(split_dir / "train.jsonl")
    dev = load_jsonl(split_dir / "dev.jsonl")
    test = load_jsonl(split_dir / "test.jsonl")

    encoder = SentenceTransformer(args.model, local_files_only=True)

    x_train = encode_rows(encoder, train, args.text_mode, args.batch_size, args.representation)
    x_dev = encode_rows(encoder, dev, args.text_mode, args.batch_size, args.representation)
    x_test = encode_rows(encoder, test, args.text_mode, args.batch_size, args.representation)

    y_train = labels(train)
    y_dev = labels(dev)
    y_test = labels(test)

    tuned = tune_head(x_train, y_train, x_dev, y_dev, args.seed)
    final_head = build_head(tuned["C"], args.seed)
    final_head.fit(np.vstack([x_train, x_dev]), y_train + y_dev)
    pred = list(final_head.predict(x_test))
    proba = final_head.predict_proba(x_test)
    unresolved_index = list(final_head.classes_).index("unresolved")

    rows = [
        metric_row(
            "Frozen encoder + logistic head",
            y_test,
            pred,
            args.text_mode,
            {
                "encoder": args.model,
                "embedding_dim": int(x_test.shape[1]),
                "representation": args.representation,
                "C": tuned["C"],
                "dev_macro_f1": tuned["dev_macro_f1"],
                "no_generation_at_inference": True,
            },
        )
    ]

    out_dir = Path(args.out_dir) / split_dir.parent.name / slug_model(args.model) / args.representation / args.text_mode
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "split_dir": str(split_dir),
        "model": args.model,
        "text_mode": args.text_mode,
        "representation": args.representation,
        "seed": args.seed,
        "train_size": len(train),
        "dev_size": len(dev),
        "test_size": len(test),
        "train_label_counts": dict(Counter(y_train)),
        "dev_label_counts": dict(Counter(y_dev)),
        "test_label_counts": dict(Counter(y_test)),
        "tuned_head": tuned,
        "metrics": rows,
        "model_input_fields": input_fields(args.text_mode),
        "notes": "Frozen sentence encoder with a trained logistic scoring head; no text generation at inference time.",
    }
    (out_dir / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    write_metrics_csv(out_dir / "metrics.csv", rows)
    write_metrics_md(out_dir / "metrics.md", result)
    write_predictions(out_dir / "predictions.jsonl", test, pred, proba[:, unresolved_index])
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def tune_head(
    x_train: np.ndarray,
    y_train: list[str],
    x_dev: np.ndarray,
    y_dev: list[str],
    seed: int,
) -> dict[str, Any]:
    best: dict[str, Any] | None = None
    for c_value in [0.03, 0.1, 0.3, 1.0, 3.0, 10.0]:
        head = build_head(c_value, seed)
        head.fit(x_train, y_train)
        pred = list(head.predict(x_dev))
        macro = f1_score(y_dev, pred, labels=list(LABELS), average="macro", zero_division=0)
        candidate = {"C": c_value, "dev_macro_f1": macro}
        if best is None or macro > best["dev_macro_f1"]:
            best = candidate
    assert best is not None
    return best


def build_head(c_value: float, seed: int) -> Pipeline:
    return Pipeline(
        [
            ("scale", StandardScaler()),
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


def encode_rows(
    encoder: SentenceTransformer,
    rows: list[dict[str, Any]],
    text_mode: str,
    batch_size: int,
    representation: str,
) -> np.ndarray:
    if representation == "separate_match":
        requests = encoder.encode(
            [str(row.get("sec_comment") or "") for row in rows],
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        responses = encoder.encode(
            [str(row.get("company_response") or "") for row in rows],
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        evidence = encoder.encode(
            [format_evidence(row, text_mode) for row in rows],
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.concatenate(
            [
                requests,
                responses,
                evidence,
                np.abs(requests - evidence),
                requests * evidence,
            ],
            axis=1,
        )
    texts = [format_case(row, text_mode) for row in rows]
    return encoder.encode(
        texts,
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )


def format_case(row: dict[str, Any], text_mode: str) -> str:
    parts = [
        "SEC request: " + str(row.get("sec_comment") or ""),
        "Company response: " + str(row.get("company_response") or ""),
    ]
    if text_mode == "evidence_snippets":
        snippets = []
        for index, snippet in enumerate((row.get("retrieved_snippets") or [])[:3], start=1):
            snippets.append(f"Evidence snippet {index}: {snippet.get('snippet') or ''}")
        parts.append("Retrieved amended filing evidence: " + " ".join(snippets))
    elif text_mode == "best_snippet":
        parts.append("Best amended filing evidence: " + str(row.get("amended_evidence_best_snippet") or ""))
    elif text_mode == "oracle_summary":
        parts.extend(
            [
                "Supporting quote: " + str(row.get("amended_evidence_supporting_quote") or ""),
                "Evidence summary: " + str(row.get("amended_evidence_evidence_summary") or ""),
                "Missing evidence note: " + str(row.get("amended_evidence_missing_evidence") or ""),
            ]
        )
    return "\n".join(parts)


def format_evidence(row: dict[str, Any], text_mode: str) -> str:
    if text_mode == "response_only":
        return str(row.get("company_response") or "")
    if text_mode == "evidence_snippets":
        snippets = []
        for index, snippet in enumerate((row.get("retrieved_snippets") or [])[:3], start=1):
            snippets.append(f"Evidence snippet {index}: {snippet.get('snippet') or ''}")
        return "\n".join(snippets)
    if text_mode == "best_snippet":
        return str(row.get("amended_evidence_best_snippet") or "")
    if text_mode == "oracle_summary":
        return "\n".join(
            [
                "Supporting quote: " + str(row.get("amended_evidence_supporting_quote") or ""),
                "Evidence summary: " + str(row.get("amended_evidence_evidence_summary") or ""),
                "Missing evidence note: " + str(row.get("amended_evidence_missing_evidence") or ""),
            ]
        )
    raise ValueError(f"Unknown text mode: {text_mode}")


def input_fields(text_mode: str) -> list[str]:
    fields = ["sec_comment", "company_response"]
    if text_mode == "evidence_snippets":
        fields.append("retrieved_snippets[:3].snippet")
    elif text_mode == "best_snippet":
        fields.append("amended_evidence_best_snippet")
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


def write_predictions(
    path: Path,
    rows: list[dict[str, Any]],
    pred: list[str],
    unresolved_probability: np.ndarray,
) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row, label, score in zip(rows, pred, unresolved_probability):
            handle.write(
                json.dumps(
                    {
                        "example_id": row.get("example_id"),
                        "gold": normalize_label(row.get("visible_evidence_resolution_label")),
                        "pred": label,
                        "unresolved_probability": float(score),
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
        "# Frozen Encoder Evidence Scorer",
        "",
        f"Split: `{result['split_dir']}`.",
        f"Encoder: `{result['model']}`.",
        f"Text mode: `{result['text_mode']}`.",
        f"Representation: `{result['representation']}`.",
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
            "This scorer freezes the encoder and trains only a logistic decision head. It is a cheap, non-generative deployment baseline rather than a full reviewer.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def slug_model(model: str) -> str:
    return model.replace("/", "__").replace(":", "_")


if __name__ == "__main__":
    raise SystemExit(main())
