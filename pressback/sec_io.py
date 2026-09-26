from __future__ import annotations

import csv
import json
import re
from pathlib import Path


SEC_AUDIT_FIELDS = [
    "audit_decision",
    "label",
    "verified_label",
    "issue_category",
    "display_name",
    "cik",
    "review_key",
    "review_file_no",
    "review_subject",
    "upload_date",
    "response_date",
    "followup_date",
    "comment_index",
    "sec_comment",
    "company_response",
    "response_alignment_score",
    "response_alignment_method",
    "response_section_index",
    "followup_comment_text",
    "clean_followup_comment",
    "followup_topic_score",
    "embedding_similarity",
    "verifier_same_topic",
    "verifier_response_matches_comment",
    "verifier_followup_is_complete",
    "verifier_confidence",
    "verifier_failure_type",
    "verifier_reason",
    "upload_accession",
    "response_accession",
    "followup_accession",
]


def write_sec_audit_csv(jsonl_path: str | Path, csv_path: str | Path, unresolved_only: bool = False, limit: int | None = None) -> None:
    rows = [json.loads(line) for line in Path(jsonl_path).read_text(encoding="utf-8").splitlines() if line.strip()]
    if unresolved_only:
        rows = [row for row in rows if row.get("verified_label", row.get("label")) == "unresolved"]
    if limit is not None:
        rows = rows[:limit]
    destination = Path(csv_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SEC_AUDIT_FIELDS)
        writer.writeheader()
        for row in rows:
            row = dict(row)
            row["audit_decision"] = ""
            writer.writerow({field: _clean_cell(row.get(field)) for field in SEC_AUDIT_FIELDS})


def _clean_cell(value):
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip()
    return value
