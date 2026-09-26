#!/usr/bin/env python3
"""Summarize visible-evidence CV runs across GEPA and MIPRO controls."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path


METRIC_FIELDS = [
    "accuracy",
    "macro_f1",
    "resolved_precision",
    "resolved_recall",
    "resolved_f1",
    "unresolved_precision",
    "unresolved_recall",
    "unresolved_f1",
]


METHODS = {
    "baseline": {
        "kind": "gepa",
        "path": "fold_{fold}_basic_full_m100/dry_run_result.json",
        "system": "baseline",
    },
    "gepa_scalar": {
        "kind": "gepa",
        "path": "fold_{fold}_basic_scalar_m100/dry_run_result.json",
        "system": "optimized",
    },
    "gepa_category": {
        "kind": "gepa",
        "path": "fold_{fold}_basic_category_m100/dry_run_result.json",
        "system": "optimized",
    },
    "gepa_full": {
        "kind": "gepa",
        "path": "fold_{fold}_basic_full_m100/dry_run_result.json",
        "system": "optimized",
    },
    "mipro_v2": {
        "kind": "mipro",
        "path": "fold_{fold}_basic_mipro_t8/result.json",
        "system": "optimized_test",
    },
}


def flatten_metrics(metrics: dict) -> dict:
    report = metrics["classification_report"]
    return {
        "accuracy": float(metrics.get("accuracy", report.get("accuracy", 0.0))),
        "macro_f1": float(report["macro_avg"]["f1"]),
        "resolved_precision": float(report["resolved"]["precision"]),
        "resolved_recall": float(report["resolved"]["recall"]),
        "resolved_f1": float(report["resolved"]["f1"]),
        "unresolved_precision": float(report["unresolved"]["precision"]),
        "unresolved_recall": float(report["unresolved"]["recall"]),
        "unresolved_f1": float(report["unresolved"]["f1"]),
    }


def gepa_test_metrics(data: dict, system: str) -> tuple[str, dict]:
    if "final_eval" not in data:
        raise KeyError("GEPA result has no final_eval field")
    if len(data["final_eval"]) != 1:
        raise ValueError(f"Expected one test eval path, got {list(data['final_eval'])}")
    test_path, evals = next(iter(data["final_eval"].items()))
    return test_path, flatten_metrics(evals[system])


def mipro_test_metrics(data: dict, system: str) -> tuple[str, dict]:
    return "", flatten_metrics(data[system])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-dir",
        default="outputs/gepa_visible_evidence_cv_expanded_v1",
        type=Path,
    )
    parser.add_argument("--folds", default="0,1,2,3,4")
    parser.add_argument(
        "--out-prefix",
        default="outputs/gepa_visible_evidence_cv_expanded_v1/cv_summary_controls_m100_t8",
        type=Path,
    )
    args = parser.parse_args()

    folds = [int(x) for x in args.folds.split(",") if x.strip()]
    rows: list[dict] = []

    for method, spec in METHODS.items():
        for fold in folds:
            path = args.base_dir / spec["path"].format(fold=fold)
            if not path.exists():
                raise FileNotFoundError(path)
            data = json.loads(path.read_text())
            if spec["kind"] == "gepa":
                test_path, metrics = gepa_test_metrics(data, spec["system"])
            else:
                test_path, metrics = mipro_test_metrics(data, spec["system"])
            rows.append(
                {
                    "method": method,
                    "fold": fold,
                    "test_path": test_path,
                    **metrics,
                }
            )

    aggregate: dict[str, dict] = {}
    for method in METHODS:
        method_rows = [r for r in rows if r["method"] == method]
        aggregate[method] = {"folds": len(method_rows)}
        for field in METRIC_FIELDS:
            vals = [r[field] for r in method_rows]
            aggregate[method][f"{field}_mean"] = statistics.mean(vals)
            aggregate[method][f"{field}_std"] = statistics.pstdev(vals)

    args.out_prefix.parent.mkdir(parents=True, exist_ok=True)
    csv_path = args.out_prefix.with_suffix(".csv")
    json_path = args.out_prefix.with_suffix(".json")
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps({"rows": rows, "aggregate": aggregate}, indent=2))

    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")
    print()
    print("method, macro_f1, unresolved_f1, unresolved_recall, accuracy")
    for method, agg in aggregate.items():
        print(
            method,
            f"{agg['macro_f1_mean']:.4f} +/- {agg['macro_f1_std']:.4f}",
            f"{agg['unresolved_f1_mean']:.4f} +/- {agg['unresolved_f1_std']:.4f}",
            f"{agg['unresolved_recall_mean']:.4f} +/- {agg['unresolved_recall_std']:.4f}",
            f"{agg['accuracy_mean']:.4f} +/- {agg['accuracy_std']:.4f}",
        )


if __name__ == "__main__":
    main()
