#!/usr/bin/env python3
"""Probe FDA warning-letter data for regulatory trace candidates.

The goal is not to create labels. It summarizes whether public FDA warning
letters expose enough request/response/outcome structure to support a
RegTrace-style extension.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import median


def nonempty(value: object) -> bool:
    if value in (None, "", [], {}):
        return False
    return str(value).strip().lower() not in {"none", "null", "nan"}


def parse_date(value: object) -> datetime | None:
    if not nonempty(value):
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def compact_excerpt(text: object, limit: int = 900) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    return cleaned[:limit]


def load_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def is_closeout_row(row: dict) -> bool:
    text = str(row.get("full_text") or "").lstrip().upper()
    return text.startswith("CLOSEOUT LETTER")


def is_warning_row(row: dict) -> bool:
    text = str(row.get("full_text") or "").lstrip().upper()
    return text.startswith("WARNING LETTER")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="data/fda_warning_letters/fda_warning_letters_2026-08-10.jsonl.gz",
    )
    parser.add_argument("--outdir", default="data/fda_warning_letters")
    parser.add_argument(
        "--report",
        default="docs/review_response/fda_trace_probe.md",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    outdir = Path(args.outdir)
    report_path = Path(args.report)
    outdir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    rows = load_rows(input_path)
    url_to_row = {row.get("source_url"): row for row in rows if row.get("source_url")}

    warning_rows = [row for row in rows if is_warning_row(row)]
    closeout_rows = [row for row in rows if is_closeout_row(row)]
    response_rows = [row for row in rows if nonempty(row.get("response_letter"))]
    linked_warning_rows = [
        row for row in warning_rows if nonempty(row.get("closeout_letter"))
    ]

    pairs: list[dict] = []
    missing_closeout_text = 0
    for warning in linked_warning_rows:
        closeout_url = warning.get("closeout_letter")
        closeout = url_to_row.get(closeout_url)
        if not closeout:
            missing_closeout_text += 1
            continue
        warning_date = parse_date(warning.get("issue_date"))
        closeout_date = parse_date(closeout.get("issue_date"))
        days_to_closeout = None
        if warning_date and closeout_date:
            days_to_closeout = (closeout_date - warning_date).days
        pairs.append(
            {
                "company_name": warning.get("company_name"),
                "product": warning.get("product"),
                "subject": warning.get("subject"),
                "issuing_office": warning.get("issuing_office"),
                "warning_issue_date": warning.get("issue_date"),
                "closeout_issue_date": closeout.get("issue_date"),
                "days_to_closeout": days_to_closeout,
                "warning_url": warning.get("source_url"),
                "closeout_url": closeout_url,
                "warning_text_len": len(str(warning.get("full_text") or "")),
                "closeout_text_len": len(str(closeout.get("full_text") or "")),
                "warning_excerpt": compact_excerpt(warning.get("full_text")),
                "closeout_excerpt": compact_excerpt(closeout.get("full_text")),
            }
        )

    candidate_path = outdir / "fda_warning_closeout_trace_candidates.jsonl"
    with candidate_path.open("w", encoding="utf-8") as handle:
        for pair in pairs:
            handle.write(json.dumps(pair, ensure_ascii=False) + "\n")

    product_counts = Counter(pair["product"] for pair in pairs)
    office_counts = Counter(pair["issuing_office"] for pair in pairs)
    subject_counts = Counter(pair["subject"] for pair in pairs if nonempty(pair["subject"]))
    year_counts = Counter(str(pair["warning_issue_date"])[:4] for pair in pairs)
    delays = [
        pair["days_to_closeout"]
        for pair in pairs
        if isinstance(pair.get("days_to_closeout"), int)
        and pair["days_to_closeout"] >= 0
    ]

    def md_counter(counter: Counter, n: int = 12) -> str:
        lines = ["| value | count |", "| --- | ---: |"]
        for value, count in counter.most_common(n):
            lines.append(f"| {str(value).replace('|', '/')} | {count} |")
        return "\n".join(lines)

    sample_lines = []
    for i, pair in enumerate(pairs[:5], start=1):
        sample_lines.append(
            "\n".join(
                [
                    f"### Candidate {i}: {pair['company_name']}",
                    f"- Product: {pair['product']}",
                    f"- Subject: {pair['subject']}",
                    f"- Warning date: {pair['warning_issue_date']}",
                    f"- Closeout date: {pair['closeout_issue_date']}",
                    f"- Days to closeout: {pair['days_to_closeout']}",
                    f"- Warning URL: {pair['warning_url']}",
                    f"- Closeout URL: {pair['closeout_url']}",
                    "",
                    "**Warning excerpt**",
                    "",
                    f"> {pair['warning_excerpt']}",
                    "",
                    "**Closeout excerpt**",
                    "",
                    f"> {pair['closeout_excerpt']}",
                ]
            )
        )

    report = f"""# FDA Warning-Letter Trace Probe

This probe checks whether the public FDA warning-letter corpus can support a
RegTrace-style cross-regulatory extension. It is a data-structure probe, not a
labeling experiment.

## Headline

- Total records: {len(rows)}
- Warning-letter rows: {len(warning_rows)}
- Closeout-letter rows: {len(closeout_rows)}
- Rows with a public `response_letter` field: {len(response_rows)}
- Warning rows linking to a closeout letter: {len(linked_warning_rows)}
- Linked warning-closeout pairs with closeout text in the corpus: {len(pairs)}
- Linked closeout URLs missing from corpus: {missing_closeout_text}
- Candidate JSONL: `{candidate_path}`

## Interpretation

The FDA data is promising as a cross-domain regulatory trace resource, but it
does not mirror the SEC task one-to-one. Public warning letters frequently link
to later closeout letters, while public company response letters are almost
absent in this snapshot. The strongest near-term FDA task is therefore not
`request + company response + amended evidence -> resolved`. It is closer to:

1. `warning letter -> closeout/outcome trace` for studying regulatory-resolution
   language and time-to-closeout;
2. `warning letter + closeout letter -> deficiency-resolution verification`,
   possibly with contrastive negatives; or
3. positive-unlabeled prediction of whether a warning letter eventually receives
   a public closeout letter.

For the current ARR paper, this supports the broader claim that RegTrace-style
context-to-feedback review can generalize beyond SEC correspondence, but it
should be framed as an extension/probe unless we build FDA-specific labels.

## Delay

- Pairs with parseable nonnegative delay: {len(delays)}
- Median days to closeout: {median(delays) if delays else 'NA'}
- Min days to closeout: {min(delays) if delays else 'NA'}
- Max days to closeout: {max(delays) if delays else 'NA'}

## Warning Year Distribution

{md_counter(year_counts)}

## Product Distribution for Linked Pairs

{md_counter(product_counts)}

## Issuing Office Distribution for Linked Pairs

{md_counter(office_counts)}

## Subject Distribution for Linked Pairs

{md_counter(subject_counts)}

## Samples

{chr(10).join(sample_lines)}
"""

    report_path.write_text(report, encoding="utf-8")

    print(
        json.dumps(
            {
                "records": len(rows),
                "warning_rows": len(warning_rows),
                "closeout_rows": len(closeout_rows),
                "response_rows": len(response_rows),
                "linked_warning_rows": len(linked_warning_rows),
                "paired_traces": len(pairs),
                "candidate_path": str(candidate_path),
                "report_path": str(report_path),
                "median_days_to_closeout": median(delays) if delays else None,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
