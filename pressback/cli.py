from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from .costs import estimate_verification_cost, summarize_ledger
from .dataset import freeze_sec_dataset, prepare_sec_gepa_dataset
from .evaluate import corpus_summary, evaluate_heuristic, evaluate_sec_heuristic, load_threads_jsonl
from .fool import discover_transcript_urls, write_fool_articles
from .io import write_audit_csv, write_jsonl
from .labeled_qa import export_labeled_qa_jsonl, load_labeled_qa, profile_labeled_qa
from .label import ExtractConfig, extract_corpus
from .openai_verifier import verify_pairs
from .parse import load_transcripts
from .sec import (
    build_pairs,
    download_documents,
    read_documents_jsonl,
    read_filings_jsonl,
    search_correspondence,
    write_documents_jsonl,
    write_filings_jsonl,
    write_pairs_jsonl,
)
from .sec_io import write_sec_audit_csv


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pressback")
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract = subparsers.add_parser("extract", help="extract press-back threads")
    extract.add_argument("--input", required=True, help="file or directory of transcripts")
    extract.add_argument("--output", required=True, help="JSONL output path")
    extract.add_argument("--audit", help="optional CSV audit output path")
    extract.add_argument("--audit-limit", type=int, default=200)
    extract.add_argument("--topic-threshold", type=float, default=0.22)
    extract.add_argument("--max-followup-turns", type=int)

    summarize = subparsers.add_parser("summarize", help="summarize an extracted JSONL corpus")
    summarize.add_argument("--input", required=True, help="JSONL corpus from extract")
    summarize.add_argument("--heuristic", action="store_true", help="also evaluate the heuristic floor")

    profile_labeled = subparsers.add_parser("profile-labeled", help="profile the labeled Q&A CSV")
    profile_labeled.add_argument("--input", required=True, help="labeled Q&A CSV")

    export_labeled = subparsers.add_parser("export-labeled", help="export a lean JSONL from labeled Q&A CSV")
    export_labeled.add_argument("--input", required=True, help="labeled Q&A CSV")
    export_labeled.add_argument("--output", required=True, help="lean JSONL output")
    export_labeled.add_argument("--keep-duplicates", action="store_true")

    fool = subparsers.add_parser("download-fool", help="download recent Motley Fool transcript pages")
    fool.add_argument("--pages", type=int, default=1, help="listing pages to scan")
    fool.add_argument("--limit", type=int, default=10, help="max transcript articles to download")
    fool.add_argument("--output-dir", required=True, help="directory for transcript txt files")
    fool.add_argument("--delay", type=float, default=1.0, help="polite delay between requests")

    sec_search = subparsers.add_parser("sec-search", help="search SEC UPLOAD/CORRESP metadata")
    sec_search.add_argument("--startdt", required=True)
    sec_search.add_argument("--enddt", required=True)
    sec_search.add_argument("--size", type=int, default=100)
    sec_search.add_argument("--pages", type=int, default=1)
    sec_search.add_argument("--ciks", help="optional comma-separated CIK filter")
    sec_search.add_argument("--query", help="optional SEC full-text query")
    sec_search.add_argument("--output", required=True)

    sec_download = subparsers.add_parser("sec-download", help="download SEC correspondence documents")
    sec_download.add_argument("--input", required=True, help="filings JSONL from sec-search")
    sec_download.add_argument("--output", required=True, help="documents JSONL")
    sec_download.add_argument("--limit", type=int)
    sec_download.add_argument("--delay", type=float, default=0.2)

    sec_pairs = subparsers.add_parser("sec-build-pairs", help="build SEC comment-response-followup pairs")
    sec_pairs.add_argument("--input", required=True, help="documents JSONL from sec-download")
    sec_pairs.add_argument("--output", required=True, help="pairs JSONL")
    sec_pairs.add_argument("--followup-threshold", type=float, default=0.5)
    sec_pairs.add_argument("--min-response-alignment", type=float, default=0.12)

    sec_audit = subparsers.add_parser("sec-audit", help="export SEC pairs audit CSV")
    sec_audit.add_argument("--input", required=True, help="pairs JSONL")
    sec_audit.add_argument("--output", required=True, help="audit CSV")
    sec_audit.add_argument("--unresolved-only", action="store_true")
    sec_audit.add_argument("--limit", type=int)

    sec_verify = subparsers.add_parser("sec-verify", help="verify SEC unresolved candidates with embeddings and an LLM")
    sec_verify.add_argument("--input", required=True, help="pairs JSONL from sec-build-pairs")
    sec_verify.add_argument("--output", required=True, help="verified JSONL output")
    sec_verify.add_argument("--audit", help="optional audit CSV output")
    sec_verify.add_argument("--embedding-model", default="text-embedding-3-small")
    sec_verify.add_argument("--verifier-model", default="gpt-4o-mini")
    sec_verify.add_argument("--embedding-threshold", type=float, default=0.45)
    sec_verify.add_argument("--verify-all", action="store_true", help="verify all rows with follow-up text, not only unresolved candidates")
    sec_verify.add_argument("--cost-ledger", default="outputs/openai_usage_ledger.jsonl", help="JSONL ledger for OpenAI usage/cost records")

    sec_harvest = subparsers.add_parser("sec-harvest", help="search, select active CIKs, download SEC correspondence, and build pairs")
    sec_harvest.add_argument("--startdt", required=True)
    sec_harvest.add_argument("--enddt", required=True)
    sec_harvest.add_argument("--context-startdt", help="optional wider window to fetch selected CIK histories")
    sec_harvest.add_argument("--context-enddt", help="optional wider window to fetch selected CIK histories")
    sec_harvest.add_argument("--output-prefix", required=True)
    sec_harvest.add_argument("--query", help="optional SEC full-text query for issue-targeted seed search")
    sec_harvest.add_argument("--size", type=int, default=100)
    sec_harvest.add_argument("--pages", type=int, default=5)
    sec_harvest.add_argument("--per-cik-pages", type=int, default=3)
    sec_harvest.add_argument("--top-ciks", type=int, default=50)
    sec_harvest.add_argument("--max-downloads", type=int)
    sec_harvest.add_argument("--delay", type=float, default=0.2)
    sec_harvest.add_argument("--followup-threshold", type=float, default=0.55)
    sec_harvest.add_argument("--min-response-alignment", type=float, default=0.12)

    cost_summary = subparsers.add_parser("openai-cost-summary", help="summarize local OpenAI usage/cost ledger")
    cost_summary.add_argument("--ledger", default="outputs/openai_usage_ledger.jsonl")

    cost_estimate = subparsers.add_parser("sec-cost-estimate", help="estimate OpenAI verification cost for a SEC pairs JSONL")
    cost_estimate.add_argument("--input", required=True, help="pairs JSONL")
    cost_estimate.add_argument("--verifier-model", default="gpt-4o-mini")
    cost_estimate.add_argument("--embedding-model", default="text-embedding-3-small")
    cost_estimate.add_argument("--verify-all", action="store_true")
    cost_estimate.add_argument("--batch-discount", action="store_true", help="apply OpenAI Batch API 50% discount")
    cost_estimate.add_argument("--scale-to-pairs", type=int, help="also extrapolate to this many total pairs using this file's candidate rate")

    freeze_dataset = subparsers.add_parser("sec-freeze-dataset", help="create split files, manifest, and stratified audit sheet")
    freeze_dataset.add_argument("--input", required=True, help="verified SEC dataset JSONL")
    freeze_dataset.add_argument("--output-dir", required=True)
    freeze_dataset.add_argument("--audit-size", type=int, default=100)
    freeze_dataset.add_argument("--seed", type=int, default=17)

    prepare_gepa = subparsers.add_parser("sec-prepare-gepa", help="quality-gate a frozen SEC dataset for GEPA experiments")
    prepare_gepa.add_argument("--input", required=True, help="frozen SEC all JSONL")
    prepare_gepa.add_argument("--output-dir", required=True)
    prepare_gepa.add_argument("--min-response-words", type=int, default=18)

    sec_baseline = subparsers.add_parser("sec-baseline", help="evaluate the weak SEC heuristic baseline on a GEPA-ready JSONL")
    sec_baseline.add_argument("--input", required=True)

    args = parser.parse_args(argv)
    if args.command == "extract":
        config = ExtractConfig(
            topic_threshold=args.topic_threshold,
            max_followup_turns=args.max_followup_turns,
        )
        transcripts = load_transcripts(args.input)
        threads = extract_corpus(transcripts, config)
        write_jsonl(threads, args.output)
        if args.audit:
            write_audit_csv(threads, args.audit, limit=args.audit_limit)
        _print_summary(transcripts_count=len(transcripts), threads=threads)
    elif args.command == "summarize":
        rows = load_threads_jsonl(args.input)
        print(json.dumps(corpus_summary(rows), indent=2, ensure_ascii=False))
        if args.heuristic:
            print(json.dumps(evaluate_heuristic(rows), indent=2, ensure_ascii=False))
    elif args.command == "profile-labeled":
        rows = load_labeled_qa(args.input)
        print(json.dumps(profile_labeled_qa(rows), indent=2, ensure_ascii=False))
    elif args.command == "export-labeled":
        rows = load_labeled_qa(args.input)
        export_labeled_qa_jsonl(rows, args.output, dedupe=not args.keep_duplicates)
    elif args.command == "download-fool":
        urls = discover_transcript_urls(pages=args.pages, delay=args.delay)
        articles = write_fool_articles(urls[: args.limit], args.output_dir, delay=args.delay)
        print(json.dumps({"discovered": len(urls), "downloaded": len(articles)}, indent=2))
    elif args.command == "sec-search":
        all_filings = []
        seen = set()
        total = 0
        for page in range(args.pages):
            page_total, filings = search_correspondence(
                args.startdt,
                args.enddt,
                size=args.size,
                offset=page * args.size,
                ciks=args.ciks,
                query=args.query,
            )
            total = page_total
            for filing in filings:
                if filing.accession not in seen:
                    seen.add(filing.accession)
                    all_filings.append(filing)
        write_filings_jsonl(all_filings, args.output)
        print(json.dumps({"total": total, "saved": len(all_filings), "pages": args.pages}, indent=2))
    elif args.command == "sec-download":
        filings = read_filings_jsonl(args.input)
        documents = download_documents(filings, delay=args.delay, limit=args.limit)
        write_documents_jsonl(documents, args.output)
        print(json.dumps({"downloaded": len(documents)}, indent=2))
    elif args.command == "sec-build-pairs":
        documents = read_documents_jsonl(args.input)
        pairs = build_pairs(
            documents,
            followup_threshold=args.followup_threshold,
            min_response_alignment=args.min_response_alignment,
        )
        write_pairs_jsonl(pairs, args.output)
        labels = Counter(pair.label for pair in pairs)
        cats = Counter(pair.issue_category for pair in pairs)
        print(json.dumps({"pairs": len(pairs), "labels": dict(labels), "issue_categories": dict(cats)}, indent=2))
    elif args.command == "sec-audit":
        write_sec_audit_csv(args.input, args.output, unresolved_only=args.unresolved_only, limit=args.limit)
    elif args.command == "sec-verify":
        rows = [json.loads(line) for line in Path(args.input).read_text(encoding="utf-8").splitlines() if line.strip()]
        verified = verify_pairs(
            rows,
            embedding_model=args.embedding_model,
            verifier_model=args.verifier_model,
            embedding_threshold=args.embedding_threshold,
            unresolved_only=not args.verify_all,
            cost_ledger=args.cost_ledger,
        )
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in verified), encoding="utf-8")
        if args.audit:
            write_sec_audit_csv(args.output, args.audit, unresolved_only=True)
        print(
            json.dumps(
                {
                    "rows": len(verified),
                    "original_labels": dict(Counter(row.get("label") for row in verified)),
                    "verified_labels": dict(Counter(row.get("verified_label") for row in verified)),
                    "verifier_same_topic": dict(Counter(str(row.get("verifier_same_topic")) for row in verified if "verifier_same_topic" in row)),
                },
                indent=2,
            )
        )
    elif args.command == "sec-harvest":
        print(f"[sec-harvest] seed search {args.startdt}..{args.enddt}, pages={args.pages}, size={args.size}", flush=True)
        seed_filings = _search_sec_window(args.startdt, args.enddt, size=args.size, pages=args.pages, query=args.query)
        selected = _select_active_ciks(seed_filings, top_ciks=args.top_ciks)
        print(f"[sec-harvest] seed_filings={len(seed_filings)}, selected_ciks={len(selected)}", flush=True)
        if args.context_startdt or args.context_enddt:
            context_start = args.context_startdt or args.startdt
            context_end = args.context_enddt or args.enddt
            print(f"[sec-harvest] context search {context_start}..{context_end}, per_cik_pages={args.per_cik_pages}", flush=True)
            filings = _search_selected_cik_histories(
                selected,
                context_start,
                context_end,
                size=args.size,
                pages=args.per_cik_pages,
            )
        else:
            filings = seed_filings
        filtered = [filing for filing in filings if filing.cik in selected]
        if args.max_downloads is not None:
            filtered = filtered[: args.max_downloads]

        prefix = Path(args.output_prefix)
        filings_path = prefix.with_name(prefix.name + "_filings.jsonl")
        docs_path = prefix.with_name(prefix.name + "_docs.jsonl")
        pairs_path = prefix.with_name(prefix.name + "_pairs.jsonl")
        audit_path = prefix.with_name(prefix.name + "_unresolved_audit.csv")

        write_filings_jsonl(filtered, filings_path)
        print(f"[sec-harvest] saved filings -> {filings_path} ({len(filtered)})", flush=True)
        documents = download_documents(filtered, delay=args.delay)
        write_documents_jsonl(documents, docs_path)
        print(f"[sec-harvest] saved documents -> {docs_path} ({len(documents)})", flush=True)
        pairs = build_pairs(
            documents,
            followup_threshold=args.followup_threshold,
            min_response_alignment=args.min_response_alignment,
        )
        write_pairs_jsonl(pairs, pairs_path)
        write_sec_audit_csv(pairs_path, audit_path, unresolved_only=True)
        print(
            json.dumps(
                {
                    "seed_filings": len(seed_filings),
                    "context_filings": len(filings),
                    "selected_ciks": len(selected),
                    "saved_filings": len(filtered),
                    "downloaded_docs": len(documents),
                    "pairs": len(pairs),
                    "labels": dict(Counter(pair.label for pair in pairs)),
                    "issue_categories": dict(Counter(pair.issue_category for pair in pairs)),
                    "filings": str(filings_path),
                    "documents": str(docs_path),
                    "pairs_path": str(pairs_path),
                    "audit": str(audit_path),
                },
                indent=2,
            )
        )
    elif args.command == "openai-cost-summary":
        print(json.dumps(summarize_ledger(args.ledger), indent=2, ensure_ascii=False))
    elif args.command == "sec-cost-estimate":
        rows = [json.loads(line) for line in Path(args.input).read_text(encoding="utf-8").splitlines() if line.strip()]
        estimate = estimate_verification_cost(
            rows,
            chat_model=args.verifier_model,
            embedding_model=args.embedding_model,
            unresolved_only=not args.verify_all,
            batch_discount=args.batch_discount,
        )
        if args.scale_to_pairs:
            candidate_rate = estimate["candidates"] / len(rows) if rows else 0.0
            scaled_candidates = round(args.scale_to_pairs * candidate_rate)
            per_candidate = estimate["total_cost_usd_est"] / estimate["candidates"] if estimate["candidates"] else 0.0
            estimate["scale_to_pairs"] = args.scale_to_pairs
            estimate["candidate_rate"] = candidate_rate
            estimate["scaled_candidates_est"] = scaled_candidates
            estimate["scaled_total_cost_usd_est"] = scaled_candidates * per_candidate
        print(json.dumps(estimate, indent=2, ensure_ascii=False))
    elif args.command == "sec-freeze-dataset":
        manifest = freeze_sec_dataset(args.input, args.output_dir, audit_size=args.audit_size, seed=args.seed)
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
    elif args.command == "sec-prepare-gepa":
        manifest = prepare_sec_gepa_dataset(args.input, args.output_dir, min_response_words=args.min_response_words)
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
    elif args.command == "sec-baseline":
        rows = [json.loads(line) for line in Path(args.input).read_text(encoding="utf-8").splitlines() if line.strip()]
        print(json.dumps(evaluate_sec_heuristic(rows), indent=2, ensure_ascii=False))
    return 0


def _print_summary(transcripts_count: int, threads) -> None:
    counts = Counter(thread.tier for thread in threads)
    positives = sum(1 for thread in threads if thread.press_back)
    print(f"transcripts={transcripts_count}")
    print(f"threads={len(threads)}")
    print(f"press_back={positives}")
    print(f"tiers={dict(counts)}")


def _search_sec_window(startdt: str, enddt: str, size: int, pages: int, query: str | None = None):
    filings = []
    seen = set()
    for page in range(pages):
        _, page_filings = search_correspondence(startdt, enddt, size=size, offset=page * size, query=query)
        print(f"[sec-search] page {page + 1}/{pages}: {len(page_filings)} filings", flush=True)
        for filing in page_filings:
            if filing.accession not in seen:
                seen.add(filing.accession)
                filings.append(filing)
    return sorted(filings, key=lambda filing: (filing.file_date, filing.cik, filing.form, filing.accession))


def _search_selected_cik_histories(ciks: set[str], startdt: str, enddt: str, size: int, pages: int):
    filings = []
    seen = set()
    sorted_ciks = sorted(ciks)
    for cik_index, cik in enumerate(sorted_ciks, start=1):
        padded = cik.zfill(10)
        before = len(filings)
        for page in range(pages):
            try:
                _, page_filings = search_correspondence(startdt, enddt, size=size, offset=page * size, ciks=padded)
            except Exception as exc:
                print(f"[warn] context search failed cik={cik} page={page + 1}: {exc}", flush=True)
                continue
            for filing in page_filings:
                if filing.accession not in seen:
                    seen.add(filing.accession)
                    filings.append(filing)
        print(f"[sec-context] cik {cik_index}/{len(sorted_ciks)} {cik}: +{len(filings) - before} filings", flush=True)
    return sorted(filings, key=lambda filing: (filing.file_date, filing.cik, filing.form, filing.accession))


def _select_active_ciks(filings, top_ciks: int) -> set[str]:
    by_cik: dict[str, Counter] = {}
    for filing in filings:
        by_cik.setdefault(filing.cik, Counter())[filing.form] += 1
    eligible = [
        (cik, counts["UPLOAD"] + counts["CORRESP"], counts["UPLOAD"], counts["CORRESP"])
        for cik, counts in by_cik.items()
        if counts["UPLOAD"] and counts["CORRESP"]
    ]
    eligible.sort(key=lambda row: (row[1], min(row[2], row[3])), reverse=True)
    return {cik for cik, _, _, _ in eligible[:top_ciks]}


if __name__ == "__main__":
    raise SystemExit(main())
