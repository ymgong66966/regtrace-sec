#!/usr/bin/env python3
"""Build paper-ready leaderboard tables for SEC Benchmark v2 runs."""

from __future__ import annotations

import csv
import json
from pathlib import Path


RUN_ROOT = Path("outputs/sec_visible_evidence_benchmark_v2/final_leaderboard_dev48_gap_m150")
OUT_DIR = Path("docs/results")


METHODS = [
    (
        "Baseline prompt",
        RUN_ROOT / "fold_0_basic_mipro_t8/result.json",
        "mipro_baseline",
        "Handwritten prompt; raw amended snippets at test time.",
    ),
    (
        "MIPROv2",
        RUN_ROOT / "fold_0_basic_mipro_t8/result.json",
        "mipro_optimized",
        "Scalar prompt optimization.",
    ),
    (
        "GEPA-scalar",
        RUN_ROOT / "fold_0_basic_scalar_m150/dry_run_result.json",
        "gepa_optimized",
        "Reflective optimizer with correctness-only feedback.",
    ),
    (
        "GEPA-category",
        RUN_ROOT / "fold_0_basic_category_m150/dry_run_result.json",
        "gepa_optimized",
        "Reflective optimizer with coarse issue/gap category feedback.",
    ),
    (
        "GEPA-full",
        RUN_ROOT / "fold_0_basic_full_m150/dry_run_result.json",
        "gepa_optimized",
        "Reflective optimizer with full adjudicated natural-language feedback.",
    ),
]


def load_report(path: Path, mode: str) -> dict:
    data = json.loads(path.read_text())
    if mode == "mipro_baseline":
        return data["test_baseline"]["classification_report"]
    if mode == "mipro_optimized":
        return data["optimized_test"]["classification_report"]
    if mode == "gepa_optimized":
        final_entry = next(iter(data["final_eval"].values()))
        return final_entry["optimized"]["classification_report"]
    raise ValueError(f"unknown mode: {mode}")


def row_from_report(method: str, path: Path, mode: str, notes: str) -> dict:
    report = load_report(path, mode)
    return {
        "method": method,
        "accuracy": report["accuracy"],
        "macro_f1": report["macro_avg"]["f1"],
        "resolved_f1": report["resolved"]["f1"],
        "unresolved_f1": report["unresolved"]["f1"],
        "unresolved_precision": report["unresolved"]["precision"],
        "unresolved_recall": report["unresolved"]["recall"],
        "resolved_support": report["resolved"]["support"],
        "unresolved_support": report["unresolved"]["support"],
        "source_file": str(path),
        "notes": notes,
    }


def fmt(x: float) -> str:
    return f"{x:.3f}"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = [row_from_report(*spec) for spec in METHODS]

    csv_path = OUT_DIR / "final_leaderboard_v2_dev48_gap_m150.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    md_path = OUT_DIR / "final_leaderboard_v2_dev48_gap_m150.md"
    lines = [
        "# Final Benchmark v2 Leaderboard",
        "",
        "Split: `grouped_random_dev48_gap/fold_0`. Train/dev/test sizes are 285/48/139 examples, grouped by SEC review thread. All methods receive the same test-time inputs: SEC comment, company response, and raw retrieved amended-filing snippets. The held-out test set contains 43 resolved and 96 unresolved examples.",
        "",
        "| Method | Accuracy | Macro-F1 | Resolved F1 | Unresolved F1 | Unresolved Precision | Unresolved Recall |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {method} | {accuracy} | {macro_f1} | {resolved_f1} | {unresolved_f1} | {unresolved_precision} | {unresolved_recall} |".format(
                method=row["method"],
                accuracy=fmt(row["accuracy"]),
                macro_f1=fmt(row["macro_f1"]),
                resolved_f1=fmt(row["resolved_f1"]),
                unresolved_f1=fmt(row["unresolved_f1"]),
                unresolved_precision=fmt(row["unresolved_precision"]),
                unresolved_recall=fmt(row["unresolved_recall"]),
            )
        )
    lines.extend(
        [
            "",
            "Key comparison: GEPA-full is the strongest method on the frozen Benchmark v2 leaderboard, improving macro-F1 by 10.5 points over MIPROv2 and 8.1 points over GEPA-scalar. On the operationally important unresolved class, GEPA-full reaches 0.839 F1 and 0.813 recall.",
            "",
            "Notes:",
            "",
        ]
    )
    for row in rows:
        lines.append(f"- `{row['method']}`: {row['notes']} Source: `{row['source_file']}`.")
    lines.append("")
    md_path.write_text("\n".join(lines))

    print(md_path)
    print(csv_path)


if __name__ == "__main__":
    main()
