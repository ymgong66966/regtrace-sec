#!/usr/bin/env python3
"""Build a stratified CMS-2567 plan-of-correction adjudication sample."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/cms2567/cms2567_regtrace_candidates.jsonl")
    parser.add_argument("--output", default="outputs/cms2567_poc_adjudication/cms2567_poc_sample_120.jsonl")
    parser.add_argument("--pilot-output", default="outputs/cms2567_poc_adjudication/cms2567_poc_pilot_40.jsonl")
    parser.add_argument("--sample-size", type=int, default=120)
    parser.add_argument("--pilot-size", type=int, default=40)
    parser.add_argument("--seed", type=int, default=20260927)
    args = parser.parse_args()

    rows = load_jsonl(Path(args.input))
    enriched = [enrich(row) for row in rows if usable(row)]
    sample = stratified_sample(enriched, args.sample_size, args.seed)
    pilot = sample[: min(args.pilot_size, len(sample))]

    write_jsonl(Path(args.output), sample)
    write_jsonl(Path(args.pilot_output), pilot)

    summary = {
        "input": args.input,
        "rows_loaded": len(rows),
        "rows_usable": len(enriched),
        "sample_size": len(sample),
        "pilot_size": len(pilot),
        "seed": args.seed,
        "sample_output": args.output,
        "pilot_output": args.pilot_output,
        "sample_by_severity_band": dict(Counter(row["severity_band"] for row in sample)),
        "sample_by_report_year": dict(Counter(str(row.get("report_year")) for row in sample)),
        "sample_by_state": dict(Counter(row.get("state") for row in sample).most_common(20)),
        "sample_by_ftag_group": dict(Counter(row["ftag_group"] for row in sample).most_common(20)),
        "pilot_by_severity_band": dict(Counter(row["severity_band"] for row in pilot)),
        "pilot_by_ftag_group": dict(Counter(row["ftag_group"] for row in pilot).most_common(20)),
    }
    summary_path = Path(args.output).with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def usable(row: dict) -> bool:
    return bool(row.get("deficiency_text")) and bool(row.get("plan_of_correction_text")) and bool(row.get("ftag"))


def enrich(row: dict) -> dict:
    out = dict(row)
    stable = "|".join(
        [
            str(row.get("ccn", "")),
            str(row.get("survey_date", "")),
            str(row.get("ftag", "")),
            str(row.get("source_document_id", ""))[:12],
        ]
    )
    out["example_id"] = "cms2567_poc_" + hashlib.sha1(stable.encode("utf-8")).hexdigest()[:12]
    out["severity_band"] = severity_band(row.get("scope_severity"))
    out["ftag_group"] = ftag_group(row.get("ftag"), row.get("cms_deficiency_category"))
    out["deficiency_char_len"] = len(str(row.get("deficiency_text") or ""))
    out["poc_char_len"] = len(str(row.get("plan_of_correction_text") or ""))
    return out


def severity_band(value: object) -> str:
    text = str(value or "").strip().upper()
    if text in {"J", "K", "L"}:
        return "immediate_jeopardy"
    if text in {"G", "H", "I"}:
        return "actual_harm"
    if text in {"D", "E", "F"}:
        return "potential_harm"
    if text in {"A", "B", "C"}:
        return "low_severity"
    return "unknown"


def ftag_group(ftag: object, category: object) -> str:
    tag = str(ftag or "").upper().strip()
    if tag in {"F0880", "F0881", "F0882", "F0883"}:
        return "infection_control"
    if tag in {"F0689", "F0697", "F0684", "F0695"}:
        return "resident_care_safety"
    if tag in {"F0656", "F0657", "F0658", "F0641"}:
        return "care_planning_records"
    if tag in {"F0600", "F0602", "F0603", "F0604", "F0609"}:
        return "abuse_neglect"
    if tag in {"F0812", "F0804", "F0805", "F0809"}:
        return "food_safety"
    if tag in {"F0550", "F0551", "F0552", "F0553"}:
        return "resident_rights"
    category_text = str(category or "").lower()
    if "infection" in category_text:
        return "infection_control"
    if "food" in category_text:
        return "food_safety"
    if "resident rights" in category_text:
        return "resident_rights"
    if "abuse" in category_text or "neglect" in category_text:
        return "abuse_neglect"
    return "other"


def stratified_sample(rows: list[dict], sample_size: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        buckets[(row["severity_band"], row["ftag_group"])].append(row)
    for bucket_rows in buckets.values():
        rng.shuffle(bucket_rows)

    ordered_keys = sorted(
        buckets,
        key=lambda key: (
            ["immediate_jeopardy", "actual_harm", "potential_harm", "low_severity", "unknown"].index(key[0])
            if key[0] in ["immediate_jeopardy", "actual_harm", "potential_harm", "low_severity", "unknown"]
            else 99,
            key[1],
        ),
    )
    sample: list[dict] = []
    seen_ids: set[str] = set()
    while len(sample) < sample_size and ordered_keys:
        progressed = False
        for key in list(ordered_keys):
            bucket = buckets[key]
            while bucket:
                row = bucket.pop()
                if row["example_id"] not in seen_ids:
                    sample.append(row)
                    seen_ids.add(row["example_id"])
                    progressed = True
                    break
            if not bucket:
                ordered_keys.remove(key)
            if len(sample) >= sample_size:
                break
        if not progressed:
            break
    rng.shuffle(sample)
    return sample


if __name__ == "__main__":
    raise SystemExit(main())
