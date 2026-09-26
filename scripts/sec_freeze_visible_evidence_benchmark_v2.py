#!/usr/bin/env python3
"""Freeze a benchmark-level canonical SEC visible-evidence dataset.

This script takes the reranked amended-evidence rows and produces a cleaner
release-style dataset with explicit model-input fields, adjudication-only
feedback fields, metadata fields, and benchmark splits. It does not call any
LLM or external service.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any


VALID_LABELS = {"resolved", "unresolved"}
ELIGIBLE_RELEVANCE = {"directly_addresses", "partially_addresses"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="data/sec_amended_evidence_expanded_v1/reranked_full_v1/evidence_sample_reranked.jsonl",
    )
    parser.add_argument("--out-dir", default="data/sec_visible_evidence_benchmark_v2")
    parser.add_argument("--seed", type=int, default=29)
    parser.add_argument("--dev-frac", type=float, default=0.15)
    parser.add_argument("--test-frac", type=float, default=0.20)
    parser.add_argument("--heldout-topics", default="crypto,non_gaap")
    parser.add_argument("--time-cutoff-year", type=int, default=2024)
    args = parser.parse_args()

    in_path = Path(args.input)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    split_dir = out_dir / "splits"
    split_dir.mkdir(exist_ok=True)
    report_dir = out_dir / "reports"
    report_dir.mkdir(exist_ok=True)

    source_rows = read_jsonl(in_path)
    canonical_rows = [canonicalize(row) for row in source_rows if eligible(row)]
    canonical_rows = sorted(canonical_rows, key=lambda row: row["example_id"])

    write_jsonl(out_dir / "sec_visible_evidence_benchmark_v2.jsonl", canonical_rows)
    write_csv(out_dir / "sec_visible_evidence_benchmark_v2_review.csv", canonical_rows)

    random_splits = make_grouped_random_splits(
        canonical_rows,
        dev_frac=args.dev_frac,
        test_frac=args.test_frac,
        seed=args.seed,
    )
    write_split(split_dir / "grouped_random", random_splits)

    time_splits = make_time_splits(canonical_rows, args.time_cutoff_year)
    write_split(split_dir / f"time_train_before_{args.time_cutoff_year}", time_splits)

    heldout_topics = [x.strip() for x in args.heldout_topics.split(",") if x.strip()]
    topic_splits = make_topic_splits(canonical_rows, heldout_topics, seed=args.seed)
    write_split(split_dir / "topic_holdout", topic_splits)

    manifest = {
        "name": "SEC Visible-Evidence Resolution Benchmark v2",
        "created": date.today().isoformat(),
        "source_input": str(in_path),
        "out_dir": str(out_dir),
        "eligibility": {
            "amended_evidence_available": True,
            "label_field": "visible_evidence_resolution_label",
            "allowed_labels": sorted(VALID_LABELS),
            "allowed_evidence_relevance": sorted(ELIGIBLE_RELEVANCE),
            "revision_claim_cases": True,
        },
        "counts": summarize(canonical_rows),
        "splits": {
            "grouped_random": summarize_split(random_splits),
            f"time_train_before_{args.time_cutoff_year}": summarize_split(time_splits),
            "topic_holdout": summarize_split(topic_splits),
        },
        "fields": {
            "model_inputs": [
                "sec_comment",
                "company_response",
                "retrieved_snippets",
                "amended_evidence_best_snippet",
            ],
            "labels": [
                "visible_evidence_resolution_label",
                "event_followup_label",
                "regulator_followup_label",
            ],
            "metadata": [
                "example_id",
                "review_thread_id",
                "cik",
                "company_name",
                "review_file_no",
                "review_subject",
                "reviewed_form_family",
                "amended_form",
                "issue_category",
                "gap_type",
                "upload_year",
                "response_year",
                "amended_filing_year",
                "has_real_followup",
            ],
            "training_feedback_only": [
                "scalar_feedback",
                "category_feedback",
                "full_feedback",
                "feedback_sec_request",
                "feedback_company_action",
                "feedback_evidence_summary",
                "feedback_unmet_requirement",
                "real_followup_text",
            ],
        },
        "notes": [
            "This is a retrieval-conditioned benchmark. It evaluates reasoning over retrieved amended evidence, not end-to-end EDGAR retrieval recall.",
            "Gold adjudication and feedback fields must not be included in test-time prompts.",
            "Primary leakage control should use review_thread_id, not only response accession.",
        ],
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (report_dir / "benchmark_v2_report.md").write_text(build_report(manifest, canonical_rows), encoding="utf-8")
    write_counter_tables(report_dir, canonical_rows)

    print(json.dumps(manifest["counts"], indent=2, ensure_ascii=False))
    print(f"Wrote benchmark v2 to {out_dir}")
    print(f"Report: {report_dir / 'benchmark_v2_report.md'}")
    return 0


def eligible(row: dict[str, Any]) -> bool:
    if row.get("amended_evidence_available") is not True:
        return False
    if visible_label(row) not in VALID_LABELS:
        return False
    if str(row.get("amended_evidence_evidence_relevance") or "") not in ELIGIBLE_RELEVANCE:
        return False
    return True


def canonicalize(row: dict[str, Any]) -> dict[str, Any]:
    retrieved = row.get("retrieved_snippets") or []
    best_snippet = str(row.get("amended_evidence_best_snippet") or "")
    review_thread_id = str(row.get("review_key") or row.get("group_key") or f"{row.get('cik')}:file:{row.get('review_file_no')}")
    issue_category = normalize_category(row.get("issue_category") or row.get("harvest_topic") or "other")
    label = visible_label(row)
    gap_type = infer_gap_type(row, label)
    company_name = parse_company_name(str(row.get("display_name") or ""))
    amended_form = str(row.get("best_candidate_form") or "")
    reviewed_forms = row.get("target_forms_from_subject") or []
    reviewed_form_family = form_family(reviewed_forms[0] if reviewed_forms else amended_form or row.get("review_subject"))
    response_date = str(row.get("response_date") or "")
    upload_date = str(row.get("upload_date") or "")
    amended_date = str(row.get("best_candidate_filing_date") or "")
    full_feedback = build_visible_full_feedback(row, label, gap_type)

    return {
        "example_id": str(row.get("example_id") or ""),
        "review_thread_id": review_thread_id,
        "review_group_key": str(row.get("group_key") or review_thread_id),
        "cik": str(row.get("cik") or ""),
        "company_name": company_name,
        "display_name": str(row.get("display_name") or ""),
        "review_file_no": str(row.get("review_file_no") or ""),
        "review_subject": str(row.get("review_subject") or ""),
        "reviewed_form_family": reviewed_form_family,
        "target_forms_from_subject": reviewed_forms,
        "amended_form": amended_form,
        "amended_form_family": form_family(amended_form),
        "upload_accession": str(row.get("upload_accession") or ""),
        "upload_date": upload_date,
        "upload_year": year_from_date(upload_date),
        "response_accession": str(row.get("response_accession") or ""),
        "response_date": response_date,
        "response_year": year_from_date(response_date),
        "amended_accession": str(row.get("best_candidate_accession") or ""),
        "amended_filing_date": amended_date,
        "amended_filing_year": year_from_date(amended_date),
        "followup_accession": str(row.get("followup_accession") or ""),
        "followup_date": str(row.get("followup_date") or ""),
        "has_real_followup": bool(str(row.get("real_followup_text") or "").strip()),
        "issue_category": issue_category,
        "harvest_topic": normalize_category(row.get("harvest_topic") or ""),
        "gap_type": gap_type,
        "real_feedback_relation": str(row.get("real_feedback_relation") or ""),
        "real_feedback_gap_type": str(row.get("real_feedback_gap_type") or ""),
        "source_kind": str(row.get("source_kind") or ""),
        "resource_source": str(row.get("resource_source") or ""),
        "revision_claim_detected": bool(row.get("revision_claim_detected")),
        "page_refs": row.get("page_refs") or [],
        "amendment_refs": row.get("amendment_refs") or [],
        "sec_comment": clean_text(row.get("sec_comment")),
        "company_response": clean_text(row.get("company_response")),
        "retrieved_snippets": [
            {
                "rank": index + 1,
                "chunk_index": snippet.get("chunk_index"),
                "score": snippet.get("score"),
                "matched_terms": snippet.get("matched_terms") or [],
                "snippet": clean_text(snippet.get("snippet")),
            }
            for index, snippet in enumerate(retrieved[:5])
        ],
        "amended_evidence_best_snippet": clean_text(best_snippet),
        "amended_evidence_best_snippet_index": row.get("amended_evidence_best_snippet_index"),
        "amended_evidence_evidence_relevance": str(row.get("amended_evidence_evidence_relevance") or ""),
        "amended_evidence_evidence_summary": clean_text(row.get("amended_evidence_evidence_summary")),
        "amended_evidence_missing_evidence": clean_text(row.get("amended_evidence_missing_evidence")),
        "amended_evidence_supporting_quote": clean_text(row.get("amended_evidence_supporting_quote")),
        "amended_evidence_confidence": row.get("amended_evidence_confidence"),
        "amended_evidence_obligation_matched": row.get("amended_evidence_obligation_matched"),
        "amended_evidence_company_action_supported": row.get("amended_evidence_company_action_supported"),
        "amended_evidence_sec_request_appears_satisfied": row.get("amended_evidence_sec_request_appears_satisfied"),
        "amended_evidence_visible_unmet_requirement": row.get("amended_evidence_visible_unmet_requirement"),
        "visible_evidence_resolution_label": label,
        "event_followup_label": normalize_label(row.get("event_followup_label")),
        "regulator_followup_label": normalize_label(row.get("regulator_followup_label")),
        "feedback_sec_request": clean_text(row.get("sec_comment")),
        "feedback_company_action": clean_text(row.get("company_response")),
        "feedback_evidence_summary": clean_text(row.get("amended_evidence_evidence_summary")),
        "feedback_supporting_quote": clean_text(row.get("amended_evidence_supporting_quote")),
        "feedback_unmet_requirement": clean_text(row.get("amended_evidence_missing_evidence") or row.get("real_feedback_summary")),
        "real_followup_text": clean_text(row.get("real_followup_text")),
        "scalar_feedback": f"gold_label={label}",
        "category_feedback": f"issue_category={issue_category}; gap_type={gap_type}; evidence_relevance={row.get('amended_evidence_evidence_relevance')}",
        "full_feedback": full_feedback,
    }


def build_visible_full_feedback(row: dict[str, Any], label: str, gap_type: str) -> str:
    pieces = [
        f"Gold visible-evidence label: {label}.",
        f"Issue category: {normalize_category(row.get('issue_category') or row.get('harvest_topic') or 'other')}.",
        f"Gap type: {gap_type}.",
        f"SEC request: {clean_text(row.get('sec_comment'))}",
        f"Company response/action: {clean_text(row.get('company_response'))}",
        f"Visible amended evidence summary: {clean_text(row.get('amended_evidence_evidence_summary'))}",
    ]
    quote = clean_text(row.get("amended_evidence_supporting_quote"))
    if quote:
        pieces.append(f"Supporting quote: {quote}")
    unmet = clean_text(row.get("amended_evidence_missing_evidence") or row.get("real_feedback_summary"))
    if unmet:
        pieces.append(f"Remaining unmet requirement or caveat: {unmet}")
    if clean_text(row.get("real_followup_text")):
        pieces.append(f"Later same-topic SEC follow-up, for analysis only: {clean_text(row.get('real_followup_text'))}")
    return " ".join(piece for piece in pieces if piece.strip())


def visible_label(row: dict[str, Any]) -> str:
    if normalize_label(row.get("visible_evidence_resolution_label")) in VALID_LABELS:
        return normalize_label(row.get("visible_evidence_resolution_label"))
    if row.get("amended_evidence_sec_request_appears_satisfied") is True:
        return "resolved"
    if row.get("amended_evidence_visible_unmet_requirement") is True:
        return "unresolved"
    return "unknown"


def normalize_label(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_")
    if text in VALID_LABELS:
        return text
    return "unknown"


def infer_gap_type(row: dict[str, Any], label: str) -> str:
    if label == "resolved":
        return "resolved_visible_evidence"
    real_gap = normalize_category(row.get("real_feedback_gap_type") or "")
    if real_gap and real_gap not in {"resolved_no_followup", "unknown", "other"}:
        return real_gap
    missing = " ".join(
        clean_text(row.get(key)).lower()
        for key in [
            "amended_evidence_missing_evidence",
            "amended_evidence_visible_unmet_requirement",
            "real_feedback_summary",
            "sec_comment",
        ]
    )
    if any(term in missing for term in ["quantif", "number", "amount", "percentage", "rate", "calculation"]):
        return "missing_quantification"
    if any(term in missing for term in ["exhibit", "consent", "agreement", "document", "file"]):
        return "missing_exhibit_or_document"
    if any(term in missing for term in ["accounting", "asc ", "gaap", "non-gaap", "non gaap", "analysis"]):
        return "incomplete_accounting_analysis"
    if any(term in missing for term in ["legal", "regulation", "rule ", "item ", "securities"]):
        return "incomplete_legal_or_regulatory_analysis"
    if any(term in missing for term in ["specific", "detail", "disclose", "disclosure", "clarify", "describe"]):
        return "missing_specific_disclosure"
    return "visible_evidence_gap"


def form_family(value: Any) -> str:
    text = str(value or "").upper()
    if "S-4" in text or "F-4" in text:
        return "registration_merger_spac"
    if "S-1" in text or "F-1" in text:
        return "registration_ipo"
    if "10-K" in text or "20-F" in text:
        return "annual_report"
    if "10-Q" in text:
        return "quarterly_report"
    if "8-K" in text or "6-K" in text:
        return "current_report"
    if "DEF" in text or "PREM" in text or "PRER" in text or "PROXY" in text:
        return "proxy"
    if not text:
        return "unknown"
    return "other"


def parse_company_name(display_name: str) -> str:
    if not display_name:
        return ""
    return re.sub(r"\s+\(.*$", "", display_name).strip()


def normalize_category(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "unknown"


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def year_from_date(value: str) -> int | None:
    match = re.match(r"(\d{4})", str(value or ""))
    return int(match.group(1)) if match else None


def make_grouped_random_splits(rows: list[dict[str, Any]], dev_frac: float, test_frac: float, seed: int) -> dict[str, list[dict[str, Any]]]:
    grouped_rows = group_rows(rows)
    train_target = len(rows) * (1.0 - dev_frac - test_frac)
    dev_target = len(rows) * dev_frac
    test_target = len(rows) * test_frac
    assigned = assign_groups_to_splits(
        grouped_rows,
        targets={"train": train_target, "dev": dev_target, "test": test_target},
        seed=seed,
    )
    return {
        "train": flatten_groups(assigned["train"]),
        "dev": flatten_groups(assigned["dev"]),
        "test": flatten_groups(assigned["test"]),
    }


def assign_groups_to_splits(
    groups: dict[str, list[dict[str, Any]]],
    targets: dict[str, float],
    seed: int,
) -> dict[str, list[tuple[str, list[dict[str, Any]]]]]:
    rng = random.Random(seed)
    items = list(groups.items())
    rng.shuffle(items)
    items.sort(key=lambda item: (-len(item[1]), item[0]))
    assigned: dict[str, list[tuple[str, list[dict[str, Any]]]]] = {name: [] for name in targets}
    target_labels = {
        split: {
            "resolved": count_label_all(groups, "resolved") * target / sum(targets.values()),
            "unresolved": count_label_all(groups, "unresolved") * target / sum(targets.values()),
        }
        for split, target in targets.items()
    }
    for key, group_rows in items:
        best_split = min(
            targets,
            key=lambda split: assignment_cost(assigned[split], group_rows, targets[split], target_labels[split]),
        )
        assigned[best_split].append((key, group_rows))
    return assigned


def assignment_cost(
    current_groups: list[tuple[str, list[dict[str, Any]]]],
    candidate_rows: list[dict[str, Any]],
    target_size: float,
    target_labels: dict[str, float],
) -> float:
    current_rows = [row for _, rows in current_groups for row in rows]
    after = current_rows + candidate_rows
    size_delta = len(after) - target_size
    if size_delta > 0:
        size_cost = 3.0 * size_delta / max(target_size, 1.0)
    else:
        size_cost = abs(size_delta) / max(target_size, 1.0)
    label_cost = 0.0
    for label, target in target_labels.items():
        label_cost += abs(sum(row["visible_evidence_resolution_label"] == label for row in after) - target) / max(target, 1.0)
    # Avoid splits with only a couple of giant threads when a smaller split can
    # absorb the group nearly as well.
    group_count_cost = 1.0 / max(len(current_groups) + 1, 1)
    return size_cost + 0.5 * label_cost + 0.05 * group_count_cost


def count_label_all(groups: dict[str, list[dict[str, Any]]], label: str) -> int:
    return sum(row["visible_evidence_resolution_label"] == label for rows in groups.values() for row in rows)


def make_time_splits(rows: list[dict[str, Any]], cutoff_year: int) -> dict[str, list[dict[str, Any]]]:
    pre_cutoff = []
    test = []
    for row in rows:
        year = row.get("response_year") or row.get("upload_year") or row.get("amended_filing_year") or 0
        if year < cutoff_year:
            pre_cutoff.append(row)
        else:
            test.append(row)
    grouped_pre = group_rows(pre_cutoff)
    assigned = assign_groups_to_splits(
        grouped_pre,
        targets={"train": len(pre_cutoff) * 0.85, "dev": len(pre_cutoff) * 0.15},
        seed=41,
    )
    train = flatten_groups(assigned["train"])
    dev = flatten_groups(assigned["dev"])
    return {
        "train": sorted(train, key=lambda row: row["example_id"]),
        "dev": sorted(dev, key=lambda row: row["example_id"]),
        "test": sorted(test, key=lambda row: row["example_id"]),
    }


def make_topic_splits(rows: list[dict[str, Any]], heldout_topics: list[str], seed: int) -> dict[str, list[dict[str, Any]]]:
    heldout = {normalize_category(topic) for topic in heldout_topics}
    test = [row for row in rows if row["issue_category"] in heldout or row["harvest_topic"] in heldout]
    remaining = [row for row in rows if row not in test]
    grouped_rows = group_rows(remaining)
    groups = stratified_group_order(grouped_rows, seed)
    dev_groups, train_groups = take_groups(groups, max(1, round(len(remaining) * 0.15)))
    return {
        "train": flatten_groups(train_groups),
        "dev": flatten_groups(dev_groups),
        "test": sorted(test, key=lambda row: row["example_id"]),
    }


def group_rows(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        out[row["review_thread_id"]].append(row)
    return out


def stratified_group_order(groups: dict[str, list[dict[str, Any]]], seed: int) -> list[tuple[str, list[dict[str, Any]]]]:
    rng = random.Random(seed)
    buckets: dict[str, list[tuple[str, list[dict[str, Any]]]]] = defaultdict(list)
    for key, rows in groups.items():
        labels = Counter(row["visible_evidence_resolution_label"] for row in rows)
        majority = "unresolved" if labels["unresolved"] >= labels["resolved"] else "resolved"
        buckets[majority].append((key, rows))
    for bucket in buckets.values():
        rng.shuffle(bucket)
        bucket.sort(key=lambda item: (-len(item[1]), item[0]))
    ordered: list[tuple[str, list[dict[str, Any]]]] = []
    while buckets["unresolved"] or buckets["resolved"]:
        for label in ["unresolved", "resolved"]:
            if buckets[label]:
                ordered.append(buckets[label].pop(0))
    return ordered


def take_groups(groups: list[tuple[str, list[dict[str, Any]]]], target_size: int) -> tuple[list[tuple[str, list[dict[str, Any]]]], list[tuple[str, list[dict[str, Any]]]]]:
    taken: list[tuple[str, list[dict[str, Any]]]] = []
    remaining = list(groups)
    while sum(len(rows) for _, rows in taken) < target_size and remaining:
        taken.append(remaining.pop(0))
    return taken, remaining


def flatten_groups(groups: list[tuple[str, list[dict[str, Any]]]]) -> list[dict[str, Any]]:
    return sorted([row for _, rows in groups for row in rows], key=lambda row: row["example_id"])


def write_split(path: Path, split: dict[str, list[dict[str, Any]]]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    fold_dir = path / "fold_0"
    fold_dir.mkdir(exist_ok=True)
    for name, rows in split.items():
        write_jsonl(path / f"{name}.jsonl", rows)
        write_jsonl(fold_dir / f"{name}.jsonl", rows)
    (path / "summary.json").write_text(json.dumps(summarize_split(split), indent=2, ensure_ascii=False), encoding="utf-8")


def summarize_split(split: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    return {name: summarize(rows) for name, rows in split.items()}


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "rows": len(rows),
        "review_threads": len({row["review_thread_id"] for row in rows}),
        "companies": len({row["cik"] for row in rows if row["cik"]}),
        "labels": dict(Counter(row["visible_evidence_resolution_label"] for row in rows)),
        "issue_categories": dict(Counter(row["issue_category"] for row in rows)),
        "gap_types": dict(Counter(row["gap_type"] for row in rows)),
        "amended_form_families": dict(Counter(row["amended_form_family"] for row in rows)),
        "reviewed_form_families": dict(Counter(row["reviewed_form_family"] for row in rows)),
        "evidence_relevance": dict(Counter(row["amended_evidence_evidence_relevance"] for row in rows)),
        "response_years": dict(sorted(Counter(row["response_year"] for row in rows).items())),
        "real_followup": dict(Counter("yes" if row["has_real_followup"] else "no" for row in rows)),
    }


def build_report(manifest: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    counts = manifest["counts"]
    lines = [
        "# SEC Visible-Evidence Benchmark v2 Report",
        "",
        "## Scope",
        "",
        "This benchmark contains revision-claim SEC comment-response examples with retrieved amended-filing evidence. It is retrieval-conditioned: examples are included only when amended evidence is available and directly or partially relevant.",
        "",
        "## Headline Counts",
        "",
        f"- Rows: {counts['rows']}",
        f"- Review threads: {counts['review_threads']}",
        f"- Companies: {counts['companies']}",
        f"- Labels: `{json.dumps(counts['labels'], ensure_ascii=False)}`",
        f"- Real same-topic follow-up available: `{json.dumps(counts['real_followup'], ensure_ascii=False)}`",
        "",
        "## Recommended Splits",
        "",
        "- `splits/grouped_random`: main benchmark split grouped by SEC review thread.",
        "- `splits/time_train_before_2024`: temporal generalization split.",
        "- `splits/topic_holdout`: topic generalization split with crypto/non-GAAP held out by default.",
        "",
        "## Top Issue Categories",
        "",
        markdown_counter(counts["issue_categories"]),
        "",
        "## Top Gap Types",
        "",
        markdown_counter(counts["gap_types"]),
        "",
        "## Amended Form Families",
        "",
        markdown_counter(counts["amended_form_families"]),
        "",
        "## Label by Issue Category",
        "",
        markdown_nested(label_by(rows, "issue_category")),
        "",
        "## Label by Gap Type",
        "",
        markdown_nested(label_by(rows, "gap_type")),
        "",
        "## Split Summaries",
        "",
    ]
    for name, split_summary in manifest["splits"].items():
        lines.append(f"### {name}")
        lines.append("")
        for split_name, summary in split_summary.items():
            lines.append(f"- `{split_name}`: rows={summary['rows']}, review_threads={summary['review_threads']}, labels=`{json.dumps(summary['labels'], ensure_ascii=False)}`")
        lines.append("")
    return "\n".join(lines) + "\n"


def label_by(rows: list[dict[str, Any]], field: str) -> dict[str, Counter]:
    out: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        out[str(row.get(field) or "unknown")][row["visible_evidence_resolution_label"]] += 1
    return dict(sorted(out.items(), key=lambda item: (-sum(item[1].values()), item[0])))


def markdown_counter(counter: dict[str, int], top_n: int = 20) -> str:
    lines = ["| value | count |", "|---|---:|"]
    for key, value in Counter(counter).most_common(top_n):
        lines.append(f"| {key} | {value} |")
    return "\n".join(lines)


def markdown_nested(nested: dict[str, Counter], top_n: int = 30) -> str:
    lines = ["| value | resolved | unresolved | total |", "|---|---:|---:|---:|"]
    for key, counter in list(nested.items())[:top_n]:
        resolved = counter.get("resolved", 0)
        unresolved = counter.get("unresolved", 0)
        lines.append(f"| {key} | {resolved} | {unresolved} | {resolved + unresolved} |")
    return "\n".join(lines)


def write_counter_tables(report_dir: Path, rows: list[dict[str, Any]]) -> None:
    for field in ["issue_category", "gap_type", "amended_form_family", "reviewed_form_family", "response_year", "real_feedback_relation"]:
        path = report_dir / f"by_{field}.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=[field, "resolved", "unresolved", "total"])
            writer.writeheader()
            nested = label_by(rows, field)
            for key, counter in nested.items():
                resolved = counter.get("resolved", 0)
                unresolved = counter.get("unresolved", 0)
                writer.writerow({field: key, "resolved": resolved, "unresolved": unresolved, "total": resolved + unresolved})


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = [
        "example_id",
        "visible_evidence_resolution_label",
        "issue_category",
        "gap_type",
        "review_thread_id",
        "cik",
        "company_name",
        "review_file_no",
        "review_subject",
        "reviewed_form_family",
        "amended_form",
        "response_date",
        "has_real_followup",
        "amended_evidence_evidence_relevance",
        "sec_comment",
        "company_response",
        "amended_evidence_best_snippet",
        "feedback_evidence_summary",
        "feedback_unmet_requirement",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
