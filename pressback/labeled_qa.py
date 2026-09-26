from __future__ import annotations

import csv
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


KEEP_COLUMNS = [
    "uid",
    "question",
    "answer",
    "rasiah_label",
    "bavelas_label",
    "bull_subtype",
    "cosine_similarity",
    "question_tense",
    "answer_tense",
    "answer_sentiment",
]


def load_labeled_qa(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def profile_labeled_qa(rows: list[dict[str, str]]) -> dict[str, Any]:
    uid_counts = Counter(row["uid"] for row in rows)
    duplicates = {uid: count for uid, count in uid_counts.items() if count > 1}
    q_lens = [len(row["question"].split()) for row in rows]
    a_lens = [len(row["answer"].split()) for row in rows]
    cosine_by_label: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        try:
            cosine_by_label[row["rasiah_label"]].append(float(row["cosine_similarity"]))
        except (KeyError, ValueError):
            pass
    return {
        "rows": len(rows),
        "unique_uid": len(uid_counts),
        "duplicate_uid_count": len(duplicates),
        "duplicate_extra_rows": sum(count - 1 for count in duplicates.values()),
        "rasiah_label": dict(Counter(row["rasiah_label"] for row in rows)),
        "bavelas_label": dict(Counter(row["bavelas_label"] for row in rows)),
        "bull_subtype": dict(Counter(row["bull_subtype"] for row in rows).most_common()),
        "question_tense": dict(Counter(row["question_tense"] for row in rows)),
        "answer_tense": dict(Counter(row["answer_tense"] for row in rows)),
        "answer_sentiment": dict(Counter(row["answer_sentiment"] for row in rows)),
        "question_words": _length_stats(q_lens),
        "answer_words": _length_stats(a_lens),
        "cosine_by_rasiah": {
            label: _float_stats(values) for label, values in sorted(cosine_by_label.items())
        },
        "embedding_strings_are_truncated": _embedding_strings_are_truncated(rows),
        "label_consistency": _label_consistency(rows),
    }


def export_labeled_qa_jsonl(rows: list[dict[str, str]], path: str | Path, dedupe: bool = True) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    with destination.open("w", encoding="utf-8") as handle:
        for row in rows:
            uid = row["uid"]
            if dedupe and uid in seen:
                continue
            seen.add(uid)
            lean = {column: row.get(column, "") for column in KEEP_COLUMNS}
            lean["label"] = "responsive" if row.get("rasiah_label") == "direct" else "non_responsive"
            handle.write(json.dumps(lean, ensure_ascii=False) + "\n")


def _length_stats(values: list[int]) -> dict[str, float]:
    if not values:
        return {}
    quartiles = statistics.quantiles(values, n=4)
    return {
        "min": min(values),
        "p25": quartiles[0],
        "median": statistics.median(values),
        "p75": quartiles[2],
        "max": max(values),
        "mean": round(statistics.mean(values), 2),
    }


def _float_stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {}
    return {
        "n": len(values),
        "mean": round(statistics.mean(values), 4),
        "median": round(statistics.median(values), 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


def _embedding_strings_are_truncated(rows: list[dict[str, str]]) -> bool:
    if not rows:
        return False
    sample = rows[0].get("question_embedding", "")
    numeric_count = len(re.findall(r"[-+]?\d*\.\d+(?:[eE][-+]?\d+)?|[-+]?\d+", sample))
    return "..." in sample or numeric_count < 1536


def _label_consistency(rows: list[dict[str, str]]) -> dict[str, int]:
    direct_with_subtype = 0
    evasive_without_subtype = 0
    for row in rows:
        direct = row.get("rasiah_label") == "direct"
        has_subtype = row.get("bavelas_label") != "—" and row.get("bull_subtype") != "—"
        if direct and has_subtype:
            direct_with_subtype += 1
        if not direct and not has_subtype:
            evasive_without_subtype += 1
    return {
        "direct_with_evasion_subtype": direct_with_subtype,
        "evasive_without_subtype": evasive_without_subtype,
    }

