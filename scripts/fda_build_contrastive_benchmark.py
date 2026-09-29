#!/usr/bin/env python3
"""Build a minimal FDA warning-to-closeout contrastive RegTrace benchmark."""

from __future__ import annotations

import argparse
import gzip
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pairs", default="data/fda_warning_letters/fda_warning_closeout_trace_candidates.jsonl")
    parser.add_argument("--raw", default="data/fda_warning_letters/fda_warning_letters_2026-08-10.jsonl.gz")
    parser.add_argument("--out-dir", default="data/fda_warning_letters/contrastive_benchmark_v1")
    parser.add_argument("--max-pairs", type=int, default=400)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--train-frac", type=float, default=0.60)
    parser.add_argument("--dev-frac", type=float, default=0.20)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    pairs = load_jsonl(Path(args.pairs))[: args.max_pairs]
    url_to_full_text = load_full_text_map(Path(args.raw))
    examples = build_examples(pairs, url_to_full_text, rng)
    splits = grouped_split(examples, args.train_frac, args.dev_frac, rng)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_dir / "all.jsonl", examples)
    for split, rows in splits.items():
        write_jsonl(out_dir / f"{split}.jsonl", rows)

    summary = summarize(examples, splits)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    write_readme(out_dir / "README.md", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_full_text_map(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            url = row.get("source_url")
            if url:
                out[str(url)] = str(row.get("full_text") or "")
    return out


def build_examples(pairs: list[dict[str, Any]], url_to_text: dict[str, str], rng: random.Random) -> list[dict[str, Any]]:
    by_product_subject: dict[tuple[str, str], list[int]] = defaultdict(list)
    by_product: dict[str, list[int]] = defaultdict(list)
    for i, pair in enumerate(pairs):
        by_product_subject[(norm(pair.get("product")), norm(pair.get("subject")))].append(i)
        by_product[norm(pair.get("product"))].append(i)

    examples: list[dict[str, Any]] = []
    for i, pair in enumerate(pairs):
        positive = make_example(pair, pair, url_to_text, label="matched", negative_type="")
        examples.append(positive)

        candidate_indices = [
            j for j in by_product_subject[(norm(pair.get("product")), norm(pair.get("subject")))]
            if j != i and pairs[j].get("closeout_url") != pair.get("closeout_url")
        ]
        negative_type = "same_product_same_subject_wrong_closeout"
        if not candidate_indices:
            candidate_indices = [
                j for j in by_product[norm(pair.get("product"))]
                if j != i and pairs[j].get("closeout_url") != pair.get("closeout_url")
            ]
            negative_type = "same_product_wrong_closeout"
        if not candidate_indices:
            candidate_indices = [
                j for j in range(len(pairs))
                if j != i and pairs[j].get("closeout_url") != pair.get("closeout_url")
            ]
            negative_type = "different_product_wrong_closeout"
        negative_pair = pairs[rng.choice(candidate_indices)]
        examples.append(make_example(pair, negative_pair, url_to_text, label="mismatched", negative_type=negative_type))

    rng.shuffle(examples)
    return examples


def make_example(
    warning_pair: dict[str, Any],
    closeout_pair: dict[str, Any],
    url_to_text: dict[str, str],
    *,
    label: str,
    negative_type: str,
) -> dict[str, Any]:
    warning_url = str(warning_pair.get("warning_url") or "")
    closeout_url = str(closeout_pair.get("closeout_url") or "")
    warning_text = clean(url_to_text.get(warning_url) or warning_pair.get("warning_excerpt") or "")
    closeout_text = clean(url_to_text.get(closeout_url) or closeout_pair.get("closeout_excerpt") or "")
    example_id = f"fda::{stable_id(warning_url)}::{stable_id(closeout_url)}::{label}"
    matched = label == "matched"
    feedback = (
        "The closeout letter is the linked resolution evidence for this warning letter and should refer to the same firm, warning date or CMS/reference number, and corrective-action evaluation."
        if matched
        else "The candidate closeout is from a different FDA warning trace. It may share a product area, but it should not be treated as resolving this warning unless firm, reference, date, and corrective-action context align."
    )
    return {
        "example_id": example_id,
        "domain": "FDA warning-letter review",
        "task_name": "warning-to-closeout trace verification",
        "company_name": warning_pair.get("company_name"),
        "product": warning_pair.get("product"),
        "subject": warning_pair.get("subject"),
        "issuing_office": warning_pair.get("issuing_office"),
        "warning_issue_date": warning_pair.get("warning_issue_date"),
        "candidate_closeout_issue_date": closeout_pair.get("closeout_issue_date"),
        "days_to_true_closeout": warning_pair.get("days_to_closeout"),
        "warning_url": warning_url,
        "candidate_closeout_url": closeout_url,
        "true_closeout_url": warning_pair.get("closeout_url"),
        "candidate_company_name": closeout_pair.get("company_name"),
        "candidate_product": closeout_pair.get("product"),
        "candidate_subject": closeout_pair.get("subject"),
        "candidate_issuing_office": closeout_pair.get("issuing_office"),
        "warning_text": warning_text[:5200],
        "candidate_closeout_text": closeout_text[:3600],
        "fda_trace_label": label,
        "binary_label": "resolved_trace" if matched else "wrong_trace",
        "negative_type": negative_type,
        "category_feedback": "matched_trace" if matched else negative_type,
        "full_feedback": feedback,
        "group_key": warning_url,
    }


def grouped_split(
    examples: list[dict[str, Any]],
    train_frac: float,
    dev_frac: float,
    rng: random.Random,
) -> dict[str, list[dict[str, Any]]]:
    groups = sorted({row["group_key"] for row in examples})
    rng.shuffle(groups)
    n_train = int(len(groups) * train_frac)
    n_dev = int(len(groups) * dev_frac)
    train_groups = set(groups[:n_train])
    dev_groups = set(groups[n_train : n_train + n_dev])
    test_groups = set(groups[n_train + n_dev :])
    splits = {"train": [], "dev": [], "test": []}
    for row in examples:
        if row["group_key"] in train_groups:
            splits["train"].append(row)
        elif row["group_key"] in dev_groups:
            splits["dev"].append(row)
        elif row["group_key"] in test_groups:
            splits["test"].append(row)
    for rows in splits.values():
        rows.sort(key=lambda row: row["example_id"])
    return splits


def summarize(examples: list[dict[str, Any]], splits: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    return {
        "num_examples": len(examples),
        "num_warning_groups": len({row["group_key"] for row in examples}),
        "label_counts": dict(Counter(row["fda_trace_label"] for row in examples)),
        "negative_type_counts": dict(Counter(row["negative_type"] for row in examples if row["negative_type"])),
        "product_counts_top": dict(Counter(row["product"] for row in examples).most_common(12)),
        "split_sizes": {split: len(rows) for split, rows in splits.items()},
        "split_label_counts": {
            split: dict(Counter(row["fda_trace_label"] for row in rows)) for split, rows in splits.items()
        },
        "test_time_fields": ["warning_text", "candidate_closeout_text", "product", "subject", "issuing_office"],
        "hidden_fields": ["true_closeout_url", "fda_trace_label", "binary_label", "category_feedback", "full_feedback"],
        "label_definition": "matched iff the candidate closeout letter is the actual linked FDA closeout for the warning letter; mismatched iff it is a wrong closeout letter sampled as a hard negative.",
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_readme(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# FDA Contrastive RegTrace Benchmark v1",
        "",
        "This is a minimal third-domain benchmark for RegTrace. It reshapes FDA warning-letter data into a warning-to-closeout trace-verification task because public company response letters are nearly absent.",
        "",
        "## Summary",
        "",
        f"- Examples: {summary['num_examples']}",
        f"- Warning groups: {summary['num_warning_groups']}",
        f"- Split sizes: `{json.dumps(summary['split_sizes'], ensure_ascii=False)}`",
        f"- Label counts: `{json.dumps(summary['label_counts'], ensure_ascii=False)}`",
        "",
        "## Task",
        "",
        summary["label_definition"],
        "",
        "At test time, a reviewer sees only the warning text, candidate closeout text, and high-level FDA metadata. The true closeout URL and feedback fields are hidden.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def norm(value: object) -> str:
    return clean(str(value)).lower()


def stable_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", value.rstrip("/").split("/")[-1])[:80]


if __name__ == "__main__":
    main()
