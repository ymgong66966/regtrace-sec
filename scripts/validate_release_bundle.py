"""Lightweight checks for the anonymous review release bundle."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = [
    "README.md",
    "Makefile",
    "requirements.txt",
    "LICENSES.md",
    ".env.example",
    "configs/main_experiment_config.yaml",
    "docs/ANONYMIZATION.md",
    "docs/RELEASE_MANIFEST.md",
    "docs/DATA_CARD.md",
    "docs/REPRODUCIBILITY.md",
    "docs/results/final_leaderboard_v2_dev48_gap_m150.md",
    "docs/results/evidence_ablation_table_v2.md",
    "docs/results/prompt_evolution_systematic.md",
    "docs/review_response/followup_paired_analysis.md",
    "docs/review_response/independent_label_audit_full.md",
    "docs/review_response/sec_label_audit_sheet_80_gpt56sol_max_followup_informed.csv",
    "data/sec_visible_evidence_benchmark_v2/sec_visible_evidence_benchmark_v2.jsonl",
    "data/sec_visible_evidence_benchmark_v2/splits/grouped_random_dev48_gap/fold_0/train.jsonl",
    "data/sec_visible_evidence_benchmark_v2/splits/grouped_random_dev48_gap/fold_0/dev.jsonl",
    "data/sec_visible_evidence_benchmark_v2/splits/grouped_random_dev48_gap/fold_0/test.jsonl",
]

SCAN_DIRS = [
    "README.md",
    "LICENSES.md",
    "Makefile",
    "configs",
    "docs",
    "pressback",
    "regtrace_framework",
    "scripts",
]

SENSITIVE_PATTERNS = [
    re.compile("/" + "Users/"),
    re.compile("xyx" + "g025", re.IGNORECASE),
    re.compile("ym" + "gong", re.IGNORECASE),
    re.compile(r"github\.com[:/]" + "ym" + "gong", re.IGNORECASE),
    re.compile(r"OPENAI_API_KEY\s*=\s*\S+"),
    re.compile(r"JEV_API_KEY\s*=\s*\S+"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
]

ALLOWLIST = {
    ".env.example",
}


def iter_scan_files() -> list[Path]:
    files: list[Path] = []
    for item in SCAN_DIRS:
        path = ROOT / item
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(
                p
                for p in path.rglob("*")
                if p.is_file()
                and p.suffix.lower()
                in {".md", ".tex", ".bib", ".py", ".yaml", ".yml", ".txt", ".csv", ".json"}
            )
    return files


def main() -> int:
    errors: list[str] = []

    for rel in REQUIRED_PATHS:
        if not (ROOT / rel).exists():
            errors.append(f"missing required artifact: {rel}")

    env_file = ROOT / ".env"
    if env_file.exists():
        print("note: .env exists locally and is ignored; do not commit it")

    for path in iter_scan_files():
        rel = path.relative_to(ROOT).as_posix()
        if rel in ALLOWLIST:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            errors.append(f"could not read {rel}: {exc}")
            continue
        for pattern in SENSITIVE_PATTERNS:
            if pattern.search(text):
                errors.append(f"possible identifying or secret pattern in {rel}: {pattern.pattern}")

    if errors:
        print("release-check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("release-check passed")
    print(f"checked {len(REQUIRED_PATHS)} required artifacts and {len(iter_scan_files())} text files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
