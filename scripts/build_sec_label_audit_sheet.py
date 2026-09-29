#!/usr/bin/env python3
"""Build a compact human-audit sheet for RegTrace-SEC labels.

The sheet intentionally oversamples hard cases: independent-audit disagreements,
real-follow-up corroboration cases, and category/gap-type coverage. It is meant
for fast expert or author review of label validity, not for model training.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def short(text: object, limit: int = 900) -> str:
    if text is None:
        return ""
    s = " ".join(str(text).split())
    if len(s) <= limit:
        return s
    return s[: limit - 3] + "..."


def add_until(selected: list[dict], candidates: list[dict], target: int, seen: set[str]) -> None:
    for row in candidates:
        if len(selected) >= target:
            return
        example_id = row["example_id"]
        if example_id in seen:
            continue
        selected.append(row)
        seen.add(example_id)


def stratified_fill(
    selected: list[dict],
    rows: list[dict],
    target: int,
    seen: set[str],
    key: str,
    rng: random.Random,
) -> None:
    buckets: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        buckets[str(row.get(key, "unknown"))].append(row)
    for bucket_rows in buckets.values():
        rng.shuffle(bucket_rows)
    while len(selected) < target:
        grew = False
        for name in sorted(buckets):
            bucket_rows = buckets[name]
            while bucket_rows:
                row = bucket_rows.pop()
                if row["example_id"] not in seen:
                    selected.append(row)
                    seen.add(row["example_id"])
                    grew = True
                    break
            if len(selected) >= target:
                return
        if not grew:
            return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--benchmark",
        type=Path,
        default=Path("data/sec_visible_evidence_benchmark_v2/sec_visible_evidence_benchmark_v2.jsonl"),
    )
    parser.add_argument(
        "--independent-audit",
        type=Path,
        default=Path("outputs/sec_label_independent_audit/gpt-5.4-mini/audit_predictions.jsonl"),
    )
    parser.add_argument(
        "--followup-csv",
        type=Path,
        default=Path(
            "outputs/sec_visible_evidence_benchmark_v2/"
            "real_followup_corroboration_systematic/oof_full_baseline_corroboration.csv"
        ),
    )
    parser.add_argument("--output", type=Path, default=Path("docs/review_response/sec_label_audit_sheet_80.csv"))
    parser.add_argument("--n", type=int, default=80)
    parser.add_argument("--seed", type=int, default=20260928)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    rows = read_jsonl(args.benchmark)
    audit = {r["example_id"]: r for r in read_jsonl(args.independent_audit)} if args.independent_audit.exists() else {}

    followup = {}
    if args.followup_csv.exists():
        with args.followup_csv.open(newline="") as f:
            for r in csv.DictReader(f):
                followup[r["example_id"]] = r

    enriched = []
    for row in rows:
        r = dict(row)
        a = audit.get(r["example_id"], {})
        c = followup.get(r["example_id"], {})
        r["independent_audit_label"] = a.get("audit_label", "")
        r["independent_audit_agree"] = a.get("agree", "")
        r["independent_audit_confidence"] = a.get("confidence", "")
        r["independent_audit_reason"] = a.get("reason", "")
        r["followup_corroboration_label"] = c.get("judge_corroboration_label", "")
        r["followup_judge_rationale"] = c.get("judge_judge_rationale", "")
        r["gepa_full_pred"] = c.get("full_pred", "")
        r["gepa_full_correct"] = c.get("full_correct", "")
        r["baseline_pred"] = c.get("baseline_pred", "")
        r["baseline_correct"] = c.get("baseline_correct", "")
        enriched.append(r)

    selected: list[dict] = []
    seen: set[str] = set()

    disagreements = [r for r in enriched if str(r.get("independent_audit_agree")).lower() == "false"]
    rng.shuffle(disagreements)
    add_until(selected, disagreements, min(args.n, 25), seen)

    corroborated_unresolved = [
        r
        for r in enriched
        if r.get("visible_evidence_resolution_label") == "unresolved"
        and r.get("followup_corroboration_label") in {"direct_corroboration", "partial_corroboration"}
    ]
    rng.shuffle(corroborated_unresolved)
    add_until(selected, corroborated_unresolved, min(args.n, 45), seen)

    resolved_followup_controls = [
        r
        for r in enriched
        if r.get("visible_evidence_resolution_label") == "resolved" and r.get("has_real_followup")
    ]
    rng.shuffle(resolved_followup_controls)
    add_until(selected, resolved_followup_controls, min(args.n, 55), seen)

    stratified_fill(selected, enriched, min(args.n, 68), seen, "issue_category", rng)
    stratified_fill(selected, enriched, min(args.n, 76), seen, "gap_type", rng)
    stratified_fill(selected, enriched, args.n, seen, "visible_evidence_resolution_label", rng)

    out_fields = [
        "audit_id",
        "example_id",
        "review_thread_id",
        "company_name",
        "response_year",
        "issue_category",
        "gap_type",
        "visible_evidence_resolution_label",
        "independent_audit_label",
        "independent_audit_agree",
        "independent_audit_confidence",
        "has_real_followup",
        "followup_corroboration_label",
        "gepa_full_pred",
        "gepa_full_correct",
        "baseline_pred",
        "baseline_correct",
        "sec_comment",
        "company_response",
        "amended_evidence_best_snippet",
        "feedback_sec_request",
        "feedback_company_action",
        "feedback_evidence_summary",
        "feedback_unmet_requirement",
        "real_followup_text",
        "independent_audit_reason",
        "followup_judge_rationale",
        "human_label",
        "human_label_confidence",
        "evidence_sufficient",
        "human_notes",
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        for idx, row in enumerate(selected, start=1):
            out = {k: row.get(k, "") for k in out_fields}
            out["audit_id"] = idx
            for k in [
                "sec_comment",
                "company_response",
                "amended_evidence_best_snippet",
                "feedback_sec_request",
                "feedback_company_action",
                "feedback_evidence_summary",
                "feedback_unmet_requirement",
                "real_followup_text",
                "independent_audit_reason",
                "followup_judge_rationale",
            ]:
                out[k] = short(out.get(k), 1100)
            writer.writerow(out)

    by_label = defaultdict(int)
    by_issue = defaultdict(int)
    disagreements_count = 0
    for row in selected:
        by_label[row.get("visible_evidence_resolution_label", "unknown")] += 1
        by_issue[row.get("issue_category", "unknown")] += 1
        if str(row.get("independent_audit_agree")).lower() == "false":
            disagreements_count += 1
    print(f"wrote {len(selected)} rows to {args.output}")
    print("labels:", dict(sorted(by_label.items())))
    print("issues:", dict(sorted(by_issue.items())))
    print("independent-audit disagreements:", disagreements_count)


if __name__ == "__main__":
    main()
