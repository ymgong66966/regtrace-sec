#!/usr/bin/env python3
"""Probe CMS-2567 data for RegTrace-style response-review traces.

This script checks whether the public CMS-2567 nursing-home deficiency dataset
contains a reusable regulatory structure:

    regulator deficiency finding -> provider plan of correction -> correction status

It is a feasibility probe, not a benchmark-construction script.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import median


def nonempty(value: object) -> bool:
    if value in (None, ""):
        return False
    return str(value).strip().lower() not in {"none", "nan", "null"}


def parse_date(value: object) -> str:
    if not nonempty(value):
        return ""
    text = str(value).strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return text


def norm_tag(value: object) -> tuple[str, str]:
    text = str(value or "").strip().upper()
    match = re.search(r"F\s*-?\s*0*(\d+)", text)
    if match:
        return "F", match.group(1).zfill(4)
    if text.isdigit():
        return "F", text.zfill(4)
    return "", text


def trust(value: object) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def add_unique(items: list[str], value: object) -> None:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if text and text not in items:
        items.append(text)


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def excerpt(texts: list[str], limit: int = 900) -> str:
    return re.sub(r"\s+", " ", " ".join(texts)).strip()[:limit]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--zenodo-dir",
        default="data/cms2567/nursing_home_2567",
        help="Extracted Zenodo CMS-2567 directory.",
    )
    parser.add_argument(
        "--health-citations",
        default="data/cms2567/cms_theme/NH_HealthCitations_Aug2026.csv",
        help="CMS Provider Data Catalog health citations CSV.",
    )
    parser.add_argument("--outdir", default="data/cms2567")
    parser.add_argument(
        "--report",
        default="docs/review_response/cms2567_trace_probe.md",
    )
    parser.add_argument("--min-trust", type=float, default=0.8)
    args = parser.parse_args()

    base = Path(args.zenodo_dir)
    health_path = Path(args.health_citations)
    outdir = Path(args.outdir)
    report_path = Path(args.report)
    outdir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    deficiencies = read_csv(base / "nursing_home_deficiencies.csv")
    plans = read_csv(base / "nursing_home_plans_of_correction.csv")

    groups: dict[tuple[str, str, str, str], dict] = {}
    doc_tag_to_keys: dict[tuple[str, str], list[tuple[str, str, str, str]]] = defaultdict(list)

    for row in deficiencies:
        prefix, tag_num = norm_tag(row.get("ftag"))
        if prefix != "F":
            continue
        if not nonempty(row.get("ccn")) or not nonempty(row.get("survey_date")):
            continue
        key = (
            row["prov_source_document_id"],
            str(row["ccn"]).strip().zfill(6),
            parse_date(row["survey_date"]),
            tag_num,
        )
        if key not in groups:
            doc_tag_to_keys[(row["prov_source_document_id"], tag_num)].append(key)
        group = groups.setdefault(
            key,
            {
                "deficiency_texts": [],
                "plan_texts": [],
                "deficiency_rows": [],
                "plan_rows": [],
            },
        )
        add_unique(group["deficiency_texts"], row.get("deficiency_description"))
        group["deficiency_rows"].append(row)

    for row in plans:
        prefix, tag_num = norm_tag(row.get("ftag"))
        if prefix != "F":
            continue
        for key in doc_tag_to_keys.get((row.get("prov_source_document_id"), tag_num), []):
            group = groups[key]
            add_unique(group["plan_texts"], row.get("correction"))
            group["plan_rows"].append(row)

    paired = {
        key: group
        for key, group in groups.items()
        if group["deficiency_texts"] and group["plan_texts"]
    }

    targets = {(key[1], key[2], key[3]) for key in paired}
    outcomes: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    with health_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            key = (
                str(row.get("CMS Certification Number (CCN)", "")).strip().zfill(6),
                parse_date(row.get("Survey Date")),
                str(row.get("Deficiency Tag Number", "")).strip().zfill(4),
            )
            if key in targets:
                outcomes[key].append(row)

    matched = []
    for key, group in paired.items():
        outcome_rows = outcomes.get((key[1], key[2], key[3]), [])
        if outcome_rows:
            matched.append((key, group, outcome_rows))

    high_trust = []
    for key, group, outcome_rows in matched:
        min_def_trust = min(trust(row.get("trust_score")) for row in group["deficiency_rows"])
        min_plan_trust = min(trust(row.get("trust_score")) for row in group["plan_rows"])
        if min_def_trust >= args.min_trust and min_plan_trust >= args.min_trust:
            high_trust.append((key, group, outcome_rows))

    candidate_path = outdir / "cms2567_regtrace_candidates.jsonl"
    with candidate_path.open("w", encoding="utf-8") as handle:
        for key, group, outcome_rows in high_trust:
            first_def = group["deficiency_rows"][0]
            outcome = outcome_rows[0]
            record = {
                "source_document_id": key[0],
                "ccn": key[1],
                "survey_date": key[2],
                "ftag": f"F{key[3]}",
                "facility_name": first_def.get("facility_name"),
                "state": first_def.get("state"),
                "report_year": first_def.get("report_year"),
                "source_url": first_def.get("prov_source_url"),
                "deficiency_text": " ".join(group["deficiency_texts"]),
                "plan_of_correction_text": " ".join(group["plan_texts"]),
                "deficiency_corrected": outcome.get("Deficiency Corrected"),
                "correction_date": outcome.get("Correction Date"),
                "scope_severity": outcome.get("Scope Severity Code"),
                "cms_deficiency_category": outcome.get("Deficiency Category"),
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    outcome_counts = Counter(row[2][0].get("Deficiency Corrected") for row in matched)
    high_outcome_counts = Counter(row[2][0].get("Deficiency Corrected") for row in high_trust)
    state_counts = Counter(row[1]["deficiency_rows"][0].get("state") for row in high_trust)
    tag_counts = Counter(f"F{row[0][3]}" for row in high_trust)
    year_counts = Counter(row[1]["deficiency_rows"][0].get("report_year") for row in high_trust)
    correction_dates = [
        row[2][0].get("Correction Date") for row in matched if nonempty(row[2][0].get("Correction Date"))
    ]
    def_lens = [sum(len(text) for text in group["deficiency_texts"]) for _, group, _ in high_trust]
    plan_lens = [sum(len(text) for text in group["plan_texts"]) for _, group, _ in high_trust]

    def md_counter(counter: Counter, n: int = 14) -> str:
        lines = ["| value | count |", "| --- | ---: |"]
        for value, count in counter.most_common(n):
            lines.append(f"| {str(value).replace('|', '/')} | {count} |")
        return "\n".join(lines)

    sample_lines = []
    for i, (key, group, outcome_rows) in enumerate(high_trust[:5], start=1):
        first_def = group["deficiency_rows"][0]
        outcome = outcome_rows[0]
        sample_lines.append(
            "\n".join(
                [
                    f"### Candidate {i}: {first_def.get('facility_name')} / F{key[3]}",
                    f"- State: {first_def.get('state')}",
                    f"- Survey date: {key[2]}",
                    f"- Outcome: {outcome.get('Deficiency Corrected')}",
                    f"- Correction date: {outcome.get('Correction Date')}",
                    f"- Scope/severity: {outcome.get('Scope Severity Code')}",
                    f"- Source URL: {first_def.get('prov_source_url')}",
                    "",
                    "**Deficiency excerpt**",
                    "",
                    f"> {excerpt(group['deficiency_texts'])}",
                    "",
                    "**Plan of correction excerpt**",
                    "",
                    f"> {excerpt(group['plan_texts'])}",
                ]
            )
        )

    report = f"""# CMS-2567 RegTrace Probe

This probe checks whether CMS-2567 nursing-home Statements of Deficiencies and
Plans of Correction can support a RegTrace-style cross-regulatory extension.

## Headline

- Zenodo deficiency rows: {len(deficiencies)}
- Zenodo plan-of-correction rows: {len(plans)}
- Grouped `deficiency + plan_of_correction` pairs: {len(paired)}
- Pairs matched to CMS HealthCitations correction metadata: {len(matched)}
- Match rate among grouped pairs: {len(matched) / len(paired):.3f}
- High-trust matched pairs, min trust >= {args.min_trust}: {len(high_trust)}
- Matched pairs with non-empty correction date: {len(correction_dates)} / {len(matched)}
- Candidate JSONL: `{candidate_path}`

## Interpretation

CMS-2567 is structurally much closer to RegTrace-SEC than the FDA warning-letter
probe. It has regulator-authored deficiency narratives, provider-authored plans
of correction, provenance to public source PDFs, trust scores, and official CMS
correction-status metadata.

The main caveat is label design. In the matched subset, correction status is
heavily skewed toward `Deficient, Provider has date of correction`. This makes a
naive resolved/unresolved classification weak. The dataset is stronger for:

1. plan-of-correction adequacy review;
2. correction-delay or severity-aware adequacy prediction;
3. cross-domain testing of obligation-to-response review policies; and
4. external demonstration that RegTrace-style traces exist outside SEC filings.

It should not simply replace the SEC benchmark unless we construct task labels
that are not collapsed by the near-universal correction-date outcome.

## Outcome Distribution

{md_counter(outcome_counts)}

## High-Trust Outcome Distribution

{md_counter(high_outcome_counts)}

## High-Trust State Distribution

{md_counter(state_counts)}

## High-Trust F-Tag Distribution

{md_counter(tag_counts)}

## High-Trust Report-Year Distribution

{md_counter(year_counts)}

## Text Lengths

- Median deficiency text length, high-trust pairs: {median(def_lens) if def_lens else 'NA'}
- Median plan-of-correction text length, high-trust pairs: {median(plan_lens) if plan_lens else 'NA'}

## Samples

{chr(10).join(sample_lines)}
"""

    report_path.write_text(report, encoding="utf-8")
    print(
        json.dumps(
            {
                "deficiency_rows": len(deficiencies),
                "plan_rows": len(plans),
                "grouped_pairs": len(paired),
                "matched_to_outcome": len(matched),
                "high_trust_matched": len(high_trust),
                "candidate_path": str(candidate_path),
                "report_path": str(report_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
