#!/usr/bin/env python3
"""Build grouped CMS-2567 adequacy-review splits for prompt optimization.

The input sample contains the visible regulator deficiency and provider Plan of
Correction. The adjudication file contains the label and natural-language
feedback. This script joins them into a canonical benchmark format and creates
grouped train/dev/test splits by source CMS-2567 document.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="outputs/cms2567_poc_adjudication/cms2567_poc_sample_500.jsonl")
    parser.add_argument("--adjudications", default="outputs/cms2567_poc_adjudication/sample_500_calibrated_primary/adjudications.jsonl")
    parser.add_argument("--out-dir", default="data/cms2567_poc_gepa_splits/grouped_seed17")
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--test-frac", type=float, default=0.28)
    parser.add_argument("--dev-frac", type=float, default=0.18)
    args = parser.parse_args()

    source_rows = {row["example_id"]: row for row in load_jsonl(Path(args.source))}
    adjudication_rows = {row["example_id"]: row for row in load_jsonl(Path(args.adjudications))}
    rows = build_rows(source_rows, adjudication_rows)
    splits = grouped_split(rows, args.seed, args.dev_frac, args.test_frac)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_dir / "all.jsonl", rows)
    for name, split_rows in splits.items():
        write_jsonl(out_dir / f"{name}.jsonl", split_rows)

    summary = {
        "source": args.source,
        "adjudications": args.adjudications,
        "seed": args.seed,
        "num_rows": len(rows),
        "num_groups": len({row["source_document_id"] for row in rows}),
        "splits": {name: summarize(split_rows) for name, split_rows in splits.items()},
        "label_policy": {
            "gold_label": "cms_poc_binary_label",
            "binary_mapping": {"adequate": "adequate", "partial": "not_adequate", "inadequate": "not_adequate"},
            "test_time_fields": [
                "deficiency_text",
                "plan_of_correction_text",
                "ftag",
                "scope_severity",
                "severity_band",
                "ftag_group",
                "cms_deficiency_category",
            ],
            "feedback_only_fields": [
                "cms_poc_adequacy_label",
                "cms_poc_missing_elements",
                "cms_poc_covered_elements",
                "cms_poc_reason",
                "cms_poc_optimizer_feedback",
            ],
            "hidden_outcome_metadata": ["deficiency_corrected", "correction_date", "days_to_correction", "source_url"],
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "README.md").write_text(render_readme(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def build_rows(source_rows: dict[str, dict[str, Any]], adjudication_rows: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for example_id, adjudication in adjudication_rows.items():
        if example_id not in source_rows:
            continue
        source = source_rows[example_id]
        three_way = normalize_three(adjudication.get("primary_label"))
        binary = "adequate" if three_way == "adequate" else "not_adequate"
        rows.append(
            {
                "example_id": example_id,
                "source_document_id": source.get("source_document_id"),
                "ccn": source.get("ccn"),
                "facility_name": source.get("facility_name"),
                "state": source.get("state"),
                "report_year": source.get("report_year"),
                "survey_date": source.get("survey_date"),
                "ftag": source.get("ftag"),
                "ftag_group": source.get("ftag_group"),
                "scope_severity": source.get("scope_severity"),
                "severity_band": source.get("severity_band"),
                "cms_deficiency_category": source.get("cms_deficiency_category"),
                "deficiency_text": source.get("deficiency_text"),
                "plan_of_correction_text": source.get("plan_of_correction_text"),
                "cms_poc_adequacy_label": three_way,
                "cms_poc_binary_label": binary,
                "cms_poc_confidence": adjudication.get("primary_confidence"),
                "cms_poc_missing_elements": adjudication.get("primary_missing_elements") or [],
                "cms_poc_covered_elements": adjudication.get("primary_covered_elements") or [],
                "cms_poc_reason": adjudication.get("primary_reason") or "",
                "cms_poc_optimizer_feedback": adjudication.get("primary_optimizer_feedback") or "",
                "deficiency_corrected": source.get("deficiency_corrected"),
                "correction_date": source.get("correction_date"),
                "days_to_correction": adjudication.get("days_to_correction"),
                "source_url": source.get("source_url"),
            }
        )
    rows.sort(key=lambda row: row["example_id"])
    return rows


def grouped_split(rows: list[dict[str, Any]], seed: int, dev_frac: float, test_frac: float) -> dict[str, list[dict[str, Any]]]:
    rng = random.Random(seed)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row["source_document_id"])].append(row)

    group_items = list(groups.items())
    rng.shuffle(group_items)
    group_items.sort(key=lambda item: group_score(item[1]), reverse=True)

    total = len(rows)
    target = {
        "test": round(total * test_frac),
        "dev": round(total * dev_frac),
        "train": total - round(total * test_frac) - round(total * dev_frac),
    }
    splits: dict[str, list[dict[str, Any]]] = {"train": [], "dev": [], "test": []}

    for _, group_rows in group_items:
        name = choose_split(splits, target, group_rows)
        splits[name].extend(group_rows)

    for split_rows in splits.values():
        split_rows.sort(key=lambda row: row["example_id"])
    return splits


def group_score(rows: list[dict[str, Any]]) -> tuple[int, int]:
    adequate = sum(row["cms_poc_binary_label"] == "adequate" for row in rows)
    not_adequate = len(rows) - adequate
    # Mixed groups are placed first so the greedy splitter can distribute them.
    return (min(adequate, not_adequate), len(rows))


def choose_split(
    splits: dict[str, list[dict[str, Any]]],
    target: dict[str, int],
    group_rows: list[dict[str, Any]],
) -> str:
    best_name = "train"
    best_score: tuple[float, float] | None = None
    for name in ("test", "dev", "train"):
        projected_size = len(splits[name]) + len(group_rows)
        current_size = len(splits[name])
        # Fill the most under-filled split first. Using absolute distance to the
        # target is bad early in a greedy pass because tiny dev/test targets look
        # "closer" than train and swallow the corpus.
        fill_ratio = projected_size / max(target[name], 1)
        overflow = max(0, projected_size - target[name]) / max(target[name], 1)
        projected = splits[name] + group_rows
        label_counts = Counter(row["cms_poc_binary_label"] for row in projected)
        adequate_rate = label_counts.get("adequate", 0) / max(len(projected), 1)
        # Match the corpus adequate rate (0.266 for the current 500-label pool).
        label_error = abs(adequate_rate - 0.266)
        score = (fill_ratio + 10 * overflow + 0.2 * label_error, current_size / max(target[name], 1))
        if best_score is None or score < best_score:
            best_score = score
            best_name = name
    return best_name


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "rows": len(rows),
        "groups": len({row["source_document_id"] for row in rows}),
        "binary_label_counts": dict(Counter(row["cms_poc_binary_label"] for row in rows)),
        "three_way_label_counts": dict(Counter(row["cms_poc_adequacy_label"] for row in rows)),
        "ftag_group_counts": dict(Counter(row["ftag_group"] for row in rows)),
        "severity_band_counts": dict(Counter(row["severity_band"] for row in rows)),
    }


def render_readme(summary: dict[str, Any]) -> str:
    split_lines = []
    for name, split in summary["splits"].items():
        split_lines.append(
            f"- `{name}.jsonl`: {split['rows']} examples, {split['groups']} source-document groups, "
            f"labels={split['binary_label_counts']}"
        )
    return "\n".join(
        [
            "# CMS-2567 POC GEPA Splits",
            "",
            "Canonical split files for CMS-2567 plan-of-correction adequacy review.",
            "Train/dev/test are grouped by `source_document_id` to avoid inspection-report leakage.",
            "",
            "## Splits",
            "",
            *split_lines,
            "",
            "## Test-Time Inputs",
            "",
            "Models may see `deficiency_text`, `plan_of_correction_text`, and metadata such as F-tag and severity.",
            "They must not see adjudication feedback fields or hidden correction metadata at test time.",
            "",
            "## Feedback Fields",
            "",
            "`cms_poc_reason`, `cms_poc_missing_elements`, `cms_poc_covered_elements`, and "
            "`cms_poc_optimizer_feedback` are training-feedback fields for GEPA-style optimization.",
            "",
        ]
    )


def normalize_three(value: Any) -> str:
    text = str(value or "").strip().lower()
    if "inadequate" in text:
        return "inadequate"
    if "partial" in text:
        return "partial"
    if "adequate" in text:
        return "adequate"
    return "partial"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
