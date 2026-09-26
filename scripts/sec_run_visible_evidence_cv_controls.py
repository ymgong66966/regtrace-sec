from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime


def main() -> int:
    parser = argparse.ArgumentParser(description="Run visible-evidence CV controls.")
    parser.add_argument("--folds", nargs="+", type=int, default=[0, 1, 2, 3, 4])
    parser.add_argument(
        "--controls",
        nargs="+",
        choices=["gepa_scalar", "gepa_category", "gepa_full", "mipro"],
        default=["gepa_scalar", "gepa_category"],
    )
    parser.add_argument("--split-root", default="data/sec_visible_evidence_cv_expanded_v1")
    parser.add_argument("--out-root", default="outputs/gepa_visible_evidence_cv_expanded_v1")
    parser.add_argument("--model", default="openai/gpt-4o-mini")
    parser.add_argument("--max-metric-calls", type=int, default=100)
    parser.add_argument("--mipro-trials", type=int, default=8)
    parser.add_argument("--mipro-candidates", type=int, default=4)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument(
        "--capture-logs",
        action="store_true",
        help="Write each subprocess stdout/stderr to a log file and print compact progress.",
    )
    args = parser.parse_args()

    for control in args.controls:
        for fold in args.folds:
            run_control(args, control, fold)
    return 0


def run_control(args: argparse.Namespace, control: str, fold: int) -> None:
    split_root = Path(args.split_root)
    train = split_root / f"fold_{fold}" / "train.jsonl"
    dev = split_root / f"fold_{fold}" / "dev.jsonl"
    test = split_root / f"fold_{fold}" / "test.jsonl"
    if control.startswith("gepa_"):
        mode = control.removeprefix("gepa_")
        log_dir = Path(args.out_root) / f"fold_{fold}_basic_{mode}_m{args.max_metric_calls}"
        output = log_dir / "dry_run_result.json"
        command = [
            sys.executable,
            "scripts/sec_gepa_dry_run.py",
            "--task",
            "visible_evidence_resolution",
            "--visible-program-style",
            "basic",
            "--train",
            str(train),
            "--dev",
            str(dev),
            "--final-eval",
            str(test),
            "--label-field",
            "visible_evidence_resolution_label",
            "--feedback-mode",
            mode,
            "--feedback-variant",
            "full",
            "--evidence-input-mode",
            "evidence_snippets",
            "--train-size",
            "0",
            "--dev-size",
            "0",
            "--max-metric-calls",
            str(args.max_metric_calls),
            "--reflection-minibatch-size",
            "4",
            "--candidate-selection-strategy",
            "pareto",
            "--reflect-on-perfect-subsamples",
            "--task-max-tokens",
            "500",
            "--reflection-max-tokens",
            "1500",
            "--num-threads",
            "2",
            "--eval-num-threads",
            "4",
            "--log-dir",
            str(log_dir),
        ]
    else:
        log_dir = Path(args.out_root) / f"fold_{fold}_basic_mipro_t{args.mipro_trials}"
        output = log_dir / "result.json"
        command = [
            sys.executable,
            "scripts/sec_mipro_run.py",
            "--task",
            "visible_evidence_resolution",
            "--visible-program-style",
            "basic",
            "--train",
            str(train),
            "--dev",
            str(dev),
            "--test",
            str(test),
            "--label-field",
            "visible_evidence_resolution_label",
            "--feedback-variant",
            "full",
            "--evidence-input-mode",
            "evidence_snippets",
            "--train-size",
            "0",
            "--dev-size",
            "0",
            "--test-size",
            "0",
            "--model",
            args.model,
            "--task-max-tokens",
            "500",
            "--prompt-max-tokens",
            "1500",
            "--num-trials",
            str(args.mipro_trials),
            "--num-candidates",
            str(args.mipro_candidates),
            "--max-labeled-demos",
            "4",
            "--max-bootstrapped-demos",
            "4",
            "--num-threads",
            "2",
            "--eval-num-threads",
            "4",
            "--log-dir",
            str(log_dir),
        ]

    if args.skip_existing and output.exists():
        print(f"[skip] {control} fold {fold}: {output}", flush=True)
        return

    print(f"[run] {control} fold {fold}", flush=True)
    print(" ".join(command), flush=True)
    if args.capture_logs:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "run.log"
        start = datetime.now()
        with log_path.open("w", encoding="utf-8") as handle:
            handle.write(f"START {start.isoformat()}\n")
            handle.write("COMMAND " + " ".join(command) + "\n\n")
            handle.flush()
            result = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT)
            end = datetime.now()
            handle.write(f"\nEND {end.isoformat()}\n")
            handle.write(f"RETURN_CODE {result.returncode}\n")
        if result.returncode != 0:
            print(f"[fail] {control} fold {fold}: see {log_path}", flush=True)
            raise subprocess.CalledProcessError(result.returncode, command)
        print(f"[done] {control} fold {fold}: {output} ({end - start})", flush=True)
    else:
        subprocess.run(command, check=True)


if __name__ == "__main__":
    raise SystemExit(main())
