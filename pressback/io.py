from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from .schema import PressBackThread


AUDIT_FIELDS = [
    "audit_decision",
    "transcript_id",
    "ticker",
    "date",
    "analyst",
    "question_turn_index",
    "question",
    "answer",
    "press_back",
    "tier",
    "follow_up_analyst",
    "follow_up_turn_index",
    "follow_up_text",
    "topic_score",
]


def write_jsonl(threads: list[PressBackThread], path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        for thread in threads:
            handle.write(json.dumps(thread.to_json(), ensure_ascii=False) + "\n")


def write_audit_csv(threads: list[PressBackThread], path: str | Path, limit: int | None = None) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    selected = threads if limit is None else threads[:limit]
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_FIELDS)
        writer.writeheader()
        for thread in selected:
            row = thread.to_json()
            row["audit_decision"] = ""
            writer.writerow({field: _clean_cell(row.get(field)) for field in AUDIT_FIELDS})


def _clean_cell(value):
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip()
    return value
