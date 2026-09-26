#!/usr/bin/env python3
"""External follow-up corroboration analysis for RegTrace-SEC.

This script treats later same-topic SEC follow-up text as a noisy external
reference signal, not as the benchmark gold label. It is intended to address
the reviewer concern that method-win corroboration rates can be hard to
interpret against the base rate of unresolved examples.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any


DIRECT_LABELS = {"direct_corroboration", "partial_corroboration"}
NEGATIVE_LABELS = {"weak_or_no_corroboration"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--oof-csv",
        default="outputs/sec_visible_evidence_benchmark_v2/real_followup_corroboration_systematic/"
        "oof_full_baseline_corroboration.csv",
    )
    parser.add_argument(
        "--benchmark-jsonl",
        default="data/sec_visible_evidence_benchmark_v2/sec_visible_evidence_benchmark_v2.jsonl",
    )
    parser.add_argument(
        "--out-dir",
        default="docs/review_response",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    oof_rows = list(csv.DictReader(open(args.oof_csv, newline="", encoding="utf-8")))
    benchmark_rows = read_jsonl(Path(args.benchmark_jsonl))

    clean_rows = []
    neutral_counts = Counter()
    for row in oof_rows:
        ref = external_reference(row.get("judge_corroboration_label", ""))
        if ref is None:
            neutral_counts[row.get("judge_corroboration_label", "")] += 1
            continue
        clean_rows.append({**row, "external_followup_reference": ref})

    methods = {
        "visible_gold": [row["gold"] for row in clean_rows],
        "gepa_full_oof": [row["full_pred"] for row in clean_rows],
        "baseline_oof": [row["baseline_pred"] for row in clean_rows],
    }
    refs = [row["external_followup_reference"] for row in clean_rows]

    method_metrics = {name: classification_metrics(preds, refs) for name, preds in methods.items()}
    pairwise = {}
    for left, right in [
        ("gepa_full_oof", "baseline_oof"),
        ("gepa_full_oof", "visible_gold"),
        ("visible_gold", "baseline_oof"),
    ]:
        pairwise[f"{left}_vs_{right}"] = exact_mcnemar(methods[left], methods[right], refs)

    availability = followup_availability(benchmark_rows)

    summary = {
        "input_oof_csv": args.oof_csv,
        "benchmark_jsonl": args.benchmark_jsonl,
        "oof_rows_with_verified_followup": len(oof_rows),
        "clean_external_reference_rows": len(clean_rows),
        "external_reference_definition": {
            "unresolved": sorted(DIRECT_LABELS),
            "resolved": sorted(NEGATIVE_LABELS),
            "excluded_as_neutral": dict(neutral_counts),
        },
        "external_reference_support": dict(Counter(refs)),
        "method_metrics_against_external_reference": method_metrics,
        "paired_mcnemar_tests": pairwise,
        "followup_availability_by_visible_label": availability,
    }

    (out_dir / "followup_paired_analysis.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_metrics_csv(out_dir / "followup_paired_metrics.csv", method_metrics)
    (out_dir / "followup_paired_analysis.md").write_text(build_md(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def external_reference(label: str) -> str | None:
    if label in DIRECT_LABELS:
        return "unresolved"
    if label in NEGATIVE_LABELS:
        return "resolved"
    return None


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def classification_metrics(preds: list[str], refs: list[str]) -> dict[str, Any]:
    labels = ["resolved", "unresolved"]
    n = len(refs)
    out: dict[str, Any] = {
        "n": n,
        "accuracy": safe_div(sum(pred == ref for pred, ref in zip(preds, refs)), n),
        "support": dict(Counter(refs)),
        "pred_counts": dict(Counter(preds)),
    }
    f1s = []
    for label in labels:
        tp = sum(pred == label and ref == label for pred, ref in zip(preds, refs))
        fp = sum(pred == label and ref != label for pred, ref in zip(preds, refs))
        fn = sum(pred != label and ref == label for pred, ref in zip(preds, refs))
        precision = safe_div(tp, tp + fp)
        recall = safe_div(tp, tp + fn)
        f1 = safe_div(2 * precision * recall, precision + recall)
        f1s.append(f1)
        out[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }
    out["macro_f1"] = sum(f1s) / len(f1s)
    return out


def exact_mcnemar(left_preds: list[str], right_preds: list[str], refs: list[str]) -> dict[str, Any]:
    left_only = sum(
        left == ref and right != ref for left, right, ref in zip(left_preds, right_preds, refs)
    )
    right_only = sum(
        left != ref and right == ref for left, right, ref in zip(left_preds, right_preds, refs)
    )
    n = left_only + right_only
    if n == 0:
        p_value = 1.0
    else:
        k = min(left_only, right_only)
        p_value = min(1.0, 2 * sum(math.comb(n, i) * (0.5**n) for i in range(k + 1)))
    return {
        "left_correct_right_wrong": left_only,
        "left_wrong_right_correct": right_only,
        "discordant_pairs": n,
        "exact_two_sided_p": p_value,
    }


def followup_availability(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, Counter[str]] = {"resolved": Counter(), "unresolved": Counter()}
    for row in rows:
        label = row.get("visible_evidence_resolution_label")
        if label not in counts:
            continue
        has_followup = "yes" if row.get("has_real_followup") else "no"
        counts[label][has_followup] += 1

    table = {label: dict(counter) for label, counter in counts.items()}
    # Fisher exact two-sided p-value for [[resolved_yes, resolved_no], [unresolved_yes, unresolved_no]].
    a = counts["resolved"]["yes"]
    b = counts["resolved"]["no"]
    c = counts["unresolved"]["yes"]
    d = counts["unresolved"]["no"]
    table["fisher_exact_two_sided_p"] = fisher_exact_two_sided(a, b, c, d)
    table["resolved_followup_rate"] = safe_div(a, a + b)
    table["unresolved_followup_rate"] = safe_div(c, c + d)
    return table


def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    row1 = a + b
    row2 = c + d
    col1 = a + c
    total = row1 + row2

    def hypergeom(x: int) -> float:
        return math.comb(col1, x) * math.comb(total - col1, row1 - x) / math.comb(total, row1)

    observed = hypergeom(a)
    lo = max(0, row1 - (total - col1))
    hi = min(row1, col1)
    return min(1.0, sum(hypergeom(x) for x in range(lo, hi + 1) if hypergeom(x) <= observed + 1e-15))


def safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0


def write_metrics_csv(path: Path, metrics: dict[str, dict[str, Any]]) -> None:
    fieldnames = [
        "method",
        "n",
        "accuracy",
        "macro_f1",
        "resolved_precision",
        "resolved_recall",
        "resolved_f1",
        "unresolved_precision",
        "unresolved_recall",
        "unresolved_f1",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for method, values in metrics.items():
            writer.writerow(
                {
                    "method": method,
                    "n": values["n"],
                    "accuracy": values["accuracy"],
                    "macro_f1": values["macro_f1"],
                    "resolved_precision": values["resolved"]["precision"],
                    "resolved_recall": values["resolved"]["recall"],
                    "resolved_f1": values["resolved"]["f1"],
                    "unresolved_precision": values["unresolved"]["precision"],
                    "unresolved_recall": values["unresolved"]["recall"],
                    "unresolved_f1": values["unresolved"]["f1"],
                }
            )


def fmt(x: float) -> str:
    return f"{x:.3f}"


def build_md(summary: dict[str, Any]) -> str:
    metrics = summary["method_metrics_against_external_reference"]
    lines = [
        "# Follow-Up Paired Analysis",
        "",
        "Later same-topic SEC follow-up is used here as a noisy external reference, not as the benchmark gold label.",
        "The clean subset maps `direct_corroboration` and `partial_corroboration` to `unresolved`, maps `weak_or_no_corroboration` to `resolved`, and excludes neutral/new-requirement cases.",
        "",
        f"- OOF rows with verified follow-up: {summary['oof_rows_with_verified_followup']}",
        f"- Clean external-reference rows: {summary['clean_external_reference_rows']}",
        f"- External-reference support: `{summary['external_reference_support']}`",
        "",
        "| Method | N | Accuracy | Macro-F1 | Resolved F1 | Unresolved F1 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for method, values in metrics.items():
        lines.append(
            f"| {method} | {values['n']} | {fmt(values['accuracy'])} | {fmt(values['macro_f1'])} | "
            f"{fmt(values['resolved']['f1'])} | {fmt(values['unresolved']['f1'])} |"
        )
    lines.extend(["", "## Paired McNemar Tests", "", "| Comparison | Left correct/right wrong | Left wrong/right correct | Exact p |", "|---|---:|---:|---:|"])
    for name, values in summary["paired_mcnemar_tests"].items():
        lines.append(
            f"| {name} | {values['left_correct_right_wrong']} | {values['left_wrong_right_correct']} | "
            f"{fmt(values['exact_two_sided_p'])} |"
        )
    avail = summary["followup_availability_by_visible_label"]
    lines.extend(
        [
            "",
            "## Follow-Up Availability",
            "",
            "Follow-up availability is nearly balanced across visible labels, so the external signal is not mechanically available only for unresolved examples.",
            "",
            f"- Resolved follow-up rate: {fmt(avail['resolved_followup_rate'])}",
            f"- Unresolved follow-up rate: {fmt(avail['unresolved_followup_rate'])}",
            f"- Fisher exact p-value: {fmt(avail['fisher_exact_two_sided_p'])}",
            "",
            "## Paper Use",
            "",
            "Use this as label-validity evidence. Do not claim that GEPA-full wins are independently corroborated beyond the unresolved base rate unless the paired comparison is reported with its caveat.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
