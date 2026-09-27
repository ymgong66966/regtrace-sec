#!/usr/bin/env python3
"""Create split files augmented with independent feedback."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--augmented",
        default="data/sec_visible_evidence_benchmark_v2/sec_visible_evidence_benchmark_v2_independent_feedback.jsonl",
    )
    parser.add_argument(
        "--splits-root",
        default="data/sec_visible_evidence_benchmark_v2/splits",
    )
    parser.add_argument(
        "--out-root",
        default="data/sec_visible_evidence_benchmark_v2_independent_feedback/splits",
    )
    args = parser.parse_args()

    augmented = {row["example_id"]: row for row in load_jsonl(Path(args.augmented))}
    source_root = Path(args.splits_root)
    out_root = Path(args.out_root)
    written = []
    for split_file in sorted(source_root.rglob("*.jsonl")):
        rows = load_jsonl(split_file)
        merged = []
        missing = []
        for row in rows:
            example_id = row["example_id"]
            if example_id not in augmented:
                missing.append(example_id)
                continue
            merged.append(augmented[example_id])
        if missing:
            raise RuntimeError(f"{split_file} has {len(missing)} missing independent-feedback rows")
        destination = out_root / split_file.relative_to(source_root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        write_jsonl(destination, merged)
        written.append({"path": str(destination), "rows": len(merged)})

    manifest = {
        "augmented_source": args.augmented,
        "source_splits_root": args.splits_root,
        "out_root": args.out_root,
        "files": written,
    }
    (out_root.parent / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"files_written": len(written), "out_root": args.out_root}, indent=2))
    return 0


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
