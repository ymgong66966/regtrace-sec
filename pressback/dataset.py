from __future__ import annotations

import csv
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .sec_io import SEC_AUDIT_FIELDS, _clean_cell


def freeze_sec_dataset(
    input_path: str | Path,
    output_dir: str | Path,
    audit_size: int = 100,
    seed: int = 17,
) -> dict[str, Any]:
    rows = read_jsonl(input_path)
    rows = dedupe_rows(rows)
    assign_splits(rows, seed=seed)

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    write_jsonl(rows, output / "sec_frozen_all.jsonl")
    for split in ("train", "dev", "test"):
        write_jsonl([row for row in rows if row["split"] == split], output / f"sec_frozen_{split}.jsonl")

    audit_rows = stratified_audit_sample(rows, audit_size=audit_size, seed=seed)
    write_audit_csv(audit_rows, output / "sec_frozen_audit_100.csv")
    manifest = dataset_manifest(rows, audit_rows)
    (output / "sec_frozen_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def prepare_sec_gepa_dataset(
    input_path: str | Path,
    output_dir: str | Path,
    min_response_words: int = 18,
) -> dict[str, Any]:
    rows = read_jsonl(input_path)
    prepared: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for row in rows:
        decision = assess_sec_row_quality(row, min_response_words=min_response_words)
        quality = {
            "quality_decision": decision["decision"],
            "quality_reasons": decision["reasons"],
        }
        if decision["decision"] == "exclude":
            excluded.append({**row, **quality})
            continue
        example = build_sec_gepa_example(row)
        example.update(quality)
        prepared.append(example)
        if decision["decision"] == "warn":
            warnings.append(example)

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    write_jsonl(prepared, output / "sec_gepa_all.jsonl")
    for split in ("train", "dev", "test"):
        write_jsonl([row for row in prepared if row.get("split") == split], output / f"sec_gepa_{split}.jsonl")
    write_jsonl(excluded, output / "sec_gepa_excluded.jsonl")
    write_gepa_audit_csv(prepared, output / "sec_gepa_quality_audit.csv")
    write_gepa_audit_csv(excluded, output / "sec_gepa_excluded.csv")

    manifest = gepa_manifest(prepared, excluded, warnings)
    (output / "sec_gepa_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    write_gepa_readme(output, manifest)
    return manifest


def assess_sec_row_quality(row: dict[str, Any], min_response_words: int = 18) -> dict[str, Any]:
    reasons: list[str] = []
    label = row.get("verified_label", row.get("label"))
    sec_comment = normalized_text(row.get("sec_comment"))
    response = normalized_text(row.get("company_response"))
    clean_followup = normalized_text(row.get("clean_followup_comment"))
    raw_followup = normalized_text(row.get("followup_comment_text"))

    if not sec_comment or not response:
        reasons.append("missing_sec_comment_or_company_response")
    if label == "unresolved" and not clean_followup:
        reasons.append("unresolved_without_clean_followup")
    if row.get("verifier_response_matches_comment") is False:
        reasons.append("verifier_says_response_does_not_match_comment")
    if row.get("verifier_followup_is_complete") is False and raw_followup:
        reasons.append("verifier_says_followup_is_incomplete")

    heading = response_comment_heading(response)
    comment_index = str(row.get("comment_index") or "").strip()
    if heading and comment_index and heading != comment_index and response.lower().startswith("comment "):
        reasons.append(f"response_comment_heading_mismatch:{heading}!={comment_index}")

    hard_prefixes = ("response letter", "funds.", "clarify how ", "the platform,")
    if response.lower().startswith(hard_prefixes):
        reasons.append("response_starts_mid_sentence_or_inside_comment")

    if len(response.split()) < min_response_words:
        reasons.append("very_short_company_response")

    hard = {
        "missing_sec_comment_or_company_response",
        "unresolved_without_clean_followup",
        "verifier_says_response_does_not_match_comment",
        "verifier_says_followup_is_incomplete",
    }
    if any(reason in hard or reason.startswith("response_comment_heading_mismatch") for reason in reasons):
        return {"decision": "exclude", "reasons": reasons}
    if reasons:
        return {"decision": "warn", "reasons": reasons}
    return {"decision": "keep", "reasons": []}


def build_sec_gepa_example(row: dict[str, Any]) -> dict[str, Any]:
    label = row.get("verified_label", row.get("label", "resolved"))
    target_label = "unresolved" if label == "unresolved" else "resolved"
    followup = normalized_text(row.get("clean_followup_comment")) if target_label == "unresolved" else ""
    example_id = sec_example_id(row)
    return {
        "example_id": example_id,
        "split": row.get("split"),
        "group_key": row.get("group_key"),
        "target_label": target_label,
        "issue_category": row.get("issue_category"),
        "sec_comment": normalized_text(row.get("sec_comment")),
        "company_response": normalized_text(row.get("company_response")),
        "regulator_feedback": followup,
        "category_feedback": category_feedback(row),
        "scalar_feedback": f"gold_label={target_label}",
        "display_name": row.get("display_name"),
        "cik": row.get("cik"),
        "review_key": row.get("review_key"),
        "review_file_no": row.get("review_file_no"),
        "review_subject": row.get("review_subject"),
        "upload_date": row.get("upload_date"),
        "response_date": row.get("response_date"),
        "followup_date": row.get("followup_date"),
        "comment_index": row.get("comment_index"),
        "upload_accession": row.get("upload_accession"),
        "response_accession": row.get("response_accession"),
        "followup_accession": row.get("followup_accession"),
        "embedding_similarity": row.get("embedding_similarity"),
        "verifier_confidence": row.get("verifier_confidence"),
        "verifier_failure_type": row.get("verifier_failure_type"),
        "verifier_reason": row.get("verifier_reason"),
        "source_verified_label": row.get("verified_label"),
        "source_label": row.get("label"),
        "dataset_source": row.get("dataset_source"),
    }


def sec_example_id(row: dict[str, Any]) -> str:
    parts = [
        str(row.get("upload_accession") or "no-upload"),
        str(row.get("response_accession") or "no-response"),
        str(row.get("comment_index") or "no-comment"),
    ]
    return "::".join(parts)


def category_feedback(row: dict[str, Any]) -> str:
    category = row.get("issue_category") or "other"
    failure_type = row.get("verifier_failure_type") or ""
    if row.get("verified_label") == "unresolved" and failure_type:
        return f"issue_category={category}; followup_type={failure_type}"
    return f"issue_category={category}"


def response_comment_heading(text: str) -> str | None:
    match = re.search(r"\bComment\s+(\d+)\b", text, re.IGNORECASE)
    return match.group(1) if match else None


def normalized_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(rows: list[dict[str, Any]], path: str | Path) -> None:
    Path(path).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = {}
    for row in rows:
        key = (row.get("upload_accession"), row.get("response_accession"), row.get("comment_index"))
        by_key[key] = dict(row)
    return list(by_key.values())


def assign_splits(rows: list[dict[str, Any]], seed: int = 17) -> None:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[group_key(row)].append(row)

    rng = random.Random(seed)
    split_targets = {"train": 0.70, "dev": 0.15, "test": 0.15}
    row_targets = {split: len(rows) * target for split, target in split_targets.items()}
    total_cat = Counter(row.get("issue_category") for row in rows if row.get("verified_label") == "unresolved")
    cat_targets = {
        split: {category: count * target for category, count in total_cat.items()}
        for split, target in split_targets.items()
    }

    group_items = list(groups.items())
    rng.shuffle(group_items)
    group_items.sort(key=lambda item: (sum(group_category_counts(item[1]).values()), len(item[1])), reverse=True)

    split_rows = Counter()
    split_cats: dict[str, Counter] = {split: Counter() for split in split_targets}
    split_assignments: dict[str, str] = {}
    for key, group_rows in group_items:
        split = choose_capacity_split(group_rows, split_rows, split_cats, row_targets, cat_targets)
        split_assignments[key] = split
        split_rows[split] += len(group_rows)
        split_cats[split].update(group_category_counts(group_rows))

    for key, group_rows in groups.items():
        split = split_assignments[key]
        for row in group_rows:
            row["split"] = split
            row["group_key"] = key


def choose_capacity_split(
    group_rows: list[dict[str, Any]],
    split_rows: Counter,
    split_cats: dict[str, Counter],
    row_targets: dict[str, float],
    cat_targets: dict[str, dict[str, float]],
) -> str:
    group_cats = group_category_counts(group_rows)
    best_split = "train"
    best_score = float("-inf")
    for split in row_targets:
        row_need = row_targets[split] - split_rows[split]
        row_score = row_need / max(row_targets[split], 1.0)
        cat_score = 0.0
        for category, count in group_cats.items():
            target = cat_targets[split].get(category, 0.0)
            need = target - split_cats[split][category]
            cat_score += count * (need / max(target, 1.0))
        overfill_penalty = max(0.0, (split_rows[split] + len(group_rows)) - row_targets[split]) / max(row_targets[split], 1.0)
        score = row_score + (3.0 * cat_score) - overfill_penalty
        if score > best_score:
            best_score = score
            best_split = split
    return best_split


def group_category_counts(rows: list[dict[str, Any]]) -> Counter:
    return Counter(row.get("issue_category") for row in rows if row.get("verified_label") == "unresolved")


def group_key(row: dict[str, Any]) -> str:
    review_key = row.get("review_key")
    if review_key:
        return str(review_key)
    file_no = row.get("review_file_no")
    if file_no:
        return f"{row.get('cik')}:file:{file_no}"
    return f"{row.get('cik')}:upload:{row.get('upload_accession')}"


def group_has_positive(rows: list[dict[str, Any]]) -> bool:
    return any(row.get("verified_label") == "unresolved" for row in rows)


def stratified_audit_sample(rows: list[dict[str, Any]], audit_size: int, seed: int = 17) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    positives = [row for row in rows if row.get("verified_label") == "unresolved"]
    negatives = [row for row in rows if row.get("verified_label") != "unresolved"]

    selected: list[dict[str, Any]] = []
    selected.extend(sample_by_category(positives, min(len(positives), audit_size // 2), rng))
    selected.extend(sample_by_category(negatives, audit_size - len(selected), rng))
    rng.shuffle(selected)
    return selected[:audit_size]


def sample_by_category(rows: list[dict[str, Any]], n: int, rng: random.Random) -> list[dict[str, Any]]:
    if n <= 0 or not rows:
        return []
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_category[str(row.get("issue_category", "other"))].append(row)

    selected: list[dict[str, Any]] = []
    categories = sorted(by_category)
    per_category = max(1, n // max(len(categories), 1))
    for category in categories:
        bucket = list(by_category[category])
        rng.shuffle(bucket)
        selected.extend(bucket[:per_category])

    if len(selected) < n:
        remaining = [row for row in rows if row not in selected]
        rng.shuffle(remaining)
        selected.extend(remaining[: n - len(selected)])
    return selected[:n]


def write_audit_csv(rows: list[dict[str, Any]], path: str | Path) -> None:
    fields = ["audit_decision", "split", "group_key"] + [field for field in SEC_AUDIT_FIELDS if field != "audit_decision"]
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            out = dict(row)
            out["audit_decision"] = ""
            writer.writerow({field: _clean_cell(out.get(field)) for field in fields})


def dataset_manifest(rows: list[dict[str, Any]], audit_rows: list[dict[str, Any]]) -> dict[str, Any]:
    split_counts = {
        split: {
            "rows": sum(1 for row in rows if row.get("split") == split),
            "unresolved": sum(1 for row in rows if row.get("split") == split and row.get("verified_label") == "unresolved"),
            "groups": len({row.get("group_key") for row in rows if row.get("split") == split}),
        }
        for split in ("train", "dev", "test")
    }
    group_to_splits: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        group_to_splits[str(row.get("group_key"))].add(str(row.get("split")))
    leaked_groups = {group: sorted(splits) for group, splits in group_to_splits.items() if len(splits) > 1}
    return {
        "rows": len(rows),
        "verified_labels": dict(Counter(row.get("verified_label") for row in rows)),
        "verified_unresolved_issue_categories": dict(Counter(row.get("issue_category") for row in rows if row.get("verified_label") == "unresolved")),
        "splits": split_counts,
        "unique_groups": len(group_to_splits),
        "leaked_groups": leaked_groups,
        "audit_rows": len(audit_rows),
        "audit_verified_labels": dict(Counter(row.get("verified_label") for row in audit_rows)),
        "audit_issue_categories": dict(Counter(row.get("issue_category") for row in audit_rows)),
    }


def gepa_manifest(prepared: list[dict[str, Any]], excluded: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> dict[str, Any]:
    group_to_splits: dict[str, set[str]] = defaultdict(set)
    for row in prepared:
        group_to_splits[str(row.get("group_key"))].add(str(row.get("split")))
    leaked_groups = {group: sorted(splits) for group, splits in group_to_splits.items() if len(splits) > 1}
    return {
        "prepared_rows": len(prepared),
        "excluded_rows": len(excluded),
        "warning_rows": len(warnings),
        "target_labels": dict(Counter(row.get("target_label") for row in prepared)),
        "excluded_source_labels": dict(Counter(row.get("verified_label", row.get("label")) for row in excluded)),
        "issue_categories": dict(Counter(row.get("issue_category") for row in prepared)),
        "positive_issue_categories": dict(Counter(row.get("issue_category") for row in prepared if row.get("target_label") == "unresolved")),
        "splits": {
            split: {
                "rows": sum(1 for row in prepared if row.get("split") == split),
                "unresolved": sum(1 for row in prepared if row.get("split") == split and row.get("target_label") == "unresolved"),
                "groups": len({row.get("group_key") for row in prepared if row.get("split") == split}),
            }
            for split in ("train", "dev", "test")
        },
        "excluded_reasons": dict(Counter(reason for row in excluded for reason in row.get("quality_reasons", []))),
        "warning_reasons": dict(Counter(reason for row in warnings for reason in row.get("quality_reasons", []))),
        "unique_groups": len(group_to_splits),
        "leaked_groups": leaked_groups,
    }


def write_gepa_audit_csv(rows: list[dict[str, Any]], path: str | Path) -> None:
    fields = [
        "example_id",
        "quality_decision",
        "quality_reasons",
        "split",
        "target_label",
        "issue_category",
        "display_name",
        "comment_index",
        "sec_comment",
        "company_response",
        "regulator_feedback",
        "category_feedback",
        "verifier_reason",
        "upload_accession",
        "response_accession",
        "followup_accession",
    ]
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            out = dict(row)
            out["quality_reasons"] = "; ".join(out.get("quality_reasons", []))
            writer.writerow({field: _clean_cell(out.get(field)) for field in fields})


def write_gepa_readme(output: Path, manifest: dict[str, Any]) -> None:
    text = f"""# SEC GEPA-ready dataset

This directory is generated from the frozen SEC comment-letter dataset after
conservative quality gating for the GEPA experiments.

Files:

- `sec_gepa_train.jsonl`, `sec_gepa_dev.jsonl`, `sec_gepa_test.jsonl`: model-ready examples.
- `sec_gepa_all.jsonl`: all retained examples.
- `sec_gepa_excluded.jsonl` / `sec_gepa_excluded.csv`: rows removed before experiments.
- `sec_gepa_quality_audit.csv`: retained examples plus quality warnings.
- `sec_gepa_manifest.json`: counts and split diagnostics.

Task:

Given `sec_comment` and `company_response`, predict `target_label`:

- `resolved`: no accepted same-topic next-round SEC follow-up.
- `unresolved`: a same-topic next-round SEC follow-up was verified.

Feedback fields:

- `scalar_feedback`: label-only feedback.
- `category_feedback`: issue category and, when available, verifier follow-up type.
- `regulator_feedback`: cleaned real SEC follow-up text for unresolved examples.

Quality policy:

Rows are excluded when the response is missing, the unresolved row lacks cleaned
follow-up text, the verifier judged the response/comment alignment false, the
follow-up was incomplete/truncated, or the response begins with a numbered SEC
comment heading that mismatches the row's `comment_index`.

Current counts:

```json
{json.dumps(manifest, indent=2, ensure_ascii=False)}
```
"""
    (output / "README.md").write_text(text, encoding="utf-8")
