#!/usr/bin/env python3
"""Build paper-ready benchmark artifacts from frozen SEC visible-evidence files."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path("docs/sec_visible_evidence_paper_artifacts")
DATA = Path("data/sec_visible_evidence_benchmark_v2")
OUT = ROOT / "benchmark_level_pack"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = read_jsonl(DATA / "sec_visible_evidence_benchmark_v2.jsonl")
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    write_dataset_tables(rows, manifest)
    write_evidence_ablation_table()
    write_method_signal_table()
    write_readiness_memo(rows, manifest)
    write_dataset_card_v2(rows, manifest)
    print(f"Wrote benchmark paper pack to {OUT}")
    return 0


def write_dataset_tables(rows: list[dict[str, Any]], manifest: dict[str, Any]) -> None:
    counts = manifest["counts"]
    lines = [
        "# Benchmark v2 Dataset Tables",
        "",
        "## Table 1. Corpus Scale",
        "",
        "| Quantity | Count |",
        "|---|---:|",
        f"| Examples | {counts['rows']} |",
        f"| SEC review threads | {counts['review_threads']} |",
        f"| Companies | {counts['companies']} |",
        f"| Resolved examples | {counts['labels'].get('resolved', 0)} |",
        f"| Unresolved examples | {counts['labels'].get('unresolved', 0)} |",
        f"| Examples with real next-round follow-up | {counts.get('real_followup', {}).get('yes', 0)} |",
        "",
        "## Table 2. Issue Categories",
        "",
        "| Issue category | Count |",
        "|---|---:|",
    ]
    for key, value in sorted(counts["issue_categories"].items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| `{key}` | {value} |")
    lines.extend([
        "",
        "## Table 3. Visible-Evidence Gap Types",
        "",
        "| Gap type | Count |",
        "|---|---:|",
    ])
    for key, value in sorted(counts["gap_types"].items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| `{key}` | {value} |")
    lines.extend([
        "",
        "## Table 4. Split Summary",
        "",
        "| Split | Train | Dev | Test | Test labels | Test threads |",
        "|---|---:|---:|---:|---|---:|",
    ])
    for split_name in ["grouped_random", "time_train_before_2024", "topic_holdout"]:
        summary_path = DATA / "splits" / split_name / "summary.json"
        if not summary_path.exists():
            continue
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        train = summary.get("train", {})
        dev = summary.get("dev", {})
        test = summary.get("test", {})
        test_labels = test.get("labels", {})
        label_text = ", ".join(f"{k}={v}" for k, v in sorted(test_labels.items()))
        lines.append(
            f"| `{split_name}` | {train.get('rows')} | {dev.get('rows')} | "
            f"{test.get('rows')} | {label_text} | {test.get('review_threads')} |"
        )
    lines.append("")
    (OUT / "dataset_tables_v2.md").write_text("\n".join(lines), encoding="utf-8")


def write_evidence_ablation_table() -> None:
    base = Path("outputs/sec_visible_evidence_benchmark_v2/evidence_ablation/visible_evidence_resolution_label")
    names = [
        ("response_only", "SEC comment + company response"),
        ("evidence_snippets", "+ raw amended-filing snippets"),
        ("evidence_summary", "+ adjudicated evidence summary (oracle upper bound)"),
    ]
    lines = [
        "# Benchmark v2 Evidence Ablation",
        "",
        "| Input condition | Accuracy | Macro-F1 | Resolved F1 | Unresolved F1 | Unresolved Recall |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, label in names:
        result_path = base / name / "result.json"
        if not result_path.exists():
            continue
        result = json.loads(result_path.read_text(encoding="utf-8"))
        s = result["summary"]
        cr = s["classification_report"]
        lines.append(
            f"| {label} | {cr['accuracy']:.3f} | {cr['macro_avg']['f1']:.3f} | "
            f"{cr['resolved']['f1']:.3f} | {cr['unresolved']['f1']:.3f} | {cr['unresolved']['recall']:.3f} |"
        )
    lines.extend([
        "",
        "Paper framing:",
        "",
        "- Response-only models over-trust company revision claims.",
        "- Raw amended-filing snippets provide a large non-oracle gain, showing that partial observability was a real bottleneck.",
        "- The adjudicated evidence-summary condition is not a deployable baseline; it is an upper bound that validates the label/feedback layer used for prompt optimization and analysis.",
    ])
    (OUT / "evidence_ablation_table_v2.md").write_text("\n".join(lines), encoding="utf-8")


def write_method_signal_table() -> None:
    rows = []
    for train in [200, 300]:
        root = Path(f"outputs/gepa_visible_evidence_learning_curve_full_v1/train_{train:03d}")
        candidates = [
            ("Baseline prompt", root / "fold_0_basic_full_m100" / "dry_run_result.json", "baseline"),
            ("MIPROv2", root / "fold_0_basic_mipro_t8" / "result.json", "optimized_test"),
            ("GEPA-scalar", root / "fold_0_basic_scalar_m100" / "dry_run_result.json", "optimized"),
            ("GEPA-category", root / "fold_0_basic_category_m100" / "dry_run_result.json", "optimized"),
            ("GEPA-full", root / "fold_0_basic_full_m100" / "dry_run_result.json", "optimized"),
        ]
        for method, path, key in candidates:
            if not path.exists():
                continue
            rows.append((train, method, metrics_from_result(path, key)))
    lines = [
        "# Existing Method Signal Table",
        "",
        "These runs were produced on the earlier visible-evidence learning-curve freeze. They should be framed as method evidence, not as the final Benchmark v2 leaderboard.",
        "",
        "| Train size | Method | Accuracy | Macro-F1 | Unresolved F1 | Unresolved Recall |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for train, method, m in rows:
        lines.append(
            f"| {train} | {method} | {m['accuracy']:.3f} | {m['macro_f1']:.3f} | "
            f"{m['unresolved_f1']:.3f} | {m['unresolved_recall']:.3f} |"
        )
    lines.extend([
        "",
        "Interpretation:",
        "",
        "- The clearest method result remains the train=300 row: GEPA-full has the best macro-F1 and strongest unresolved detection among prompt-optimization controls.",
        "- This table motivates rerunning a smaller, final Benchmark v2 leaderboard only after the dataset section is frozen.",
    ])
    (OUT / "method_signal_table_existing.md").write_text("\n".join(lines), encoding="utf-8")


def write_readiness_memo(rows: list[dict[str, Any]], manifest: dict[str, Any]) -> None:
    lines = [
        "# Benchmark-Level Paper Readiness Memo",
        "",
        "## Current Strongest Story",
        "",
        "The paper should be framed as a benchmark and method study for evidence-grounded SEC comment-response resolution. The core novelty is not just GEPA, and not just an EDGAR scrape. It is the construction of a context-to-feedback optimization setting where company responses are judged against visible amended-filing evidence, and where adjudicated gap descriptions can serve as rich natural-language feedback for reflective prompt optimization.",
        "",
        "## Results That Are Already Strong",
        "",
        "1. **Evidence matters.** On Benchmark v2, adding raw amended-filing snippets improves macro-F1 from 0.575 to 0.748 over response-only prompting.",
        "2. **The adjudication layer is meaningful.** The oracle evidence-summary condition reaches macro-F1 0.956, showing that the task becomes tractable when the model is given the exact missing-requirement summary.",
        "3. **Natural-language feedback has prior method signal.** On the earlier learning-curve freeze, GEPA-full outperformed MIPROv2, scalar GEPA, and category GEPA at train=300.",
        "4. **The dataset is now structurally credible.** Benchmark v2 has 472 examples, 109 SEC review threads, 95 companies, 7 issue categories, 8 gap types, and held-out grouped/time/topic splits.",
        "",
        "## What Not To Overclaim",
        "",
        "- Do not claim the retrieval pipeline is production-robust. Present it as a reproducible benchmark-construction and upstream evidence-retrieval component.",
        "- Do not present `evidence_summary` as a fair deployment input. It is an oracle upper bound and a feedback/adjudication artifact.",
        "- Do not treat the interrupted Benchmark v2 GEPA sanity run as a negative result. It used an inefficient optimizer-dev design and was stopped.",
        "",
        "## Highest-Value Next Experiments",
        "",
        "1. **Final Benchmark v2 leaderboard:** response-only, hard structured prompt, MIPROv2, GEPA-scalar, GEPA-category, GEPA-full on `grouped_random`, using raw evidence snippets only.",
        "2. **Generalization:** rerun the same best two or three methods on `time_train_before_2024` and `topic_holdout`.",
        "3. **Feedback component ablation:** compare full adjudicated feedback vs no evidence summary vs no missing requirement vs synthetic feedback.",
        "4. **Human/LLM audit:** small audit over 80-100 examples from Benchmark v2, focusing on label correctness and retrieval sufficiency.",
        "",
        "## Long-Paper Upgrade Path",
        "",
        "A short paper can focus on the benchmark, evidence ablation, and one method table. A long paper needs at least two of: final Benchmark v2 leaderboard, time/topic generalization, feedback component ablation, and a stronger audit section.",
        "",
    ]
    (OUT / "readiness_memo.md").write_text("\n".join(lines), encoding="utf-8")


def write_dataset_card_v2(rows: list[dict[str, Any]], manifest: dict[str, Any]) -> None:
    counts = manifest["counts"]
    lines = [
        "# Dataset Card v2: SEC Visible-Evidence Resolution Benchmark",
        "",
        "## Task",
        "",
        "Given an SEC staff comment, a company response, and retrieved snippets from the amended filing, predict whether the visible amended-filing evidence resolves the material SEC request.",
        "",
        "## Inputs",
        "",
        "- `sec_comment`: first-round SEC request.",
        "- `company_response`: company response that usually claims a filing revision.",
        "- `retrieved_snippets`: raw amended-filing snippets retrieved near the referenced filing/revision.",
        "",
        "Fields such as `gap_type`, `feedback_evidence_summary`, `amended_evidence_missing_evidence`, and `category_feedback` are training-feedback or analysis fields, not ordinary test-time inputs.",
        "",
        "## Label",
        "",
        "- `visible_evidence_resolution_label = resolved`: visible amended evidence covers the material SEC request.",
        "- `visible_evidence_resolution_label = unresolved`: visible amended evidence leaves a concrete gap such as a missing named disclosure, missing quantification, missing exhibit/document, or incomplete accounting/legal analysis.",
        "",
        "## Scale",
        "",
        "| Quantity | Count |",
        "|---|---:|",
        f"| Examples | {counts['rows']} |",
        f"| SEC review threads | {counts['review_threads']} |",
        f"| Companies | {counts['companies']} |",
        f"| Resolved | {counts['labels'].get('resolved', 0)} |",
        f"| Unresolved | {counts['labels'].get('unresolved', 0)} |",
        "",
        "## Construction Pipeline",
        "",
        "SEC comment-response pair -> revision-claim detection -> amended-filing retrieval -> snippet reranking -> LLM evidence adjudication -> label/feedback construction -> grouped/time/topic splits.",
        "",
        "## Known Limitations",
        "",
        "- Labels are evidence-grounded rather than legal finality labels; retrieval can miss relevant text.",
        "- The benchmark focuses on response rows with amendment/revision claims, not all SEC comments.",
        "- LLM adjudication should be accompanied by an audit before public release.",
    ]
    (OUT / "dataset_card_v2.md").write_text("\n".join(lines), encoding="utf-8")


def metrics_from_result(path: Path, key: str) -> dict[str, float]:
    result = json.loads(path.read_text(encoding="utf-8"))
    block = result[key]
    cr = block["classification_report"]
    return {
        "accuracy": float(cr["accuracy"]),
        "macro_f1": float(cr["macro_avg"]["f1"]),
        "unresolved_f1": float(cr["unresolved"]["f1"]),
        "unresolved_recall": float(cr["unresolved"]["recall"]),
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
