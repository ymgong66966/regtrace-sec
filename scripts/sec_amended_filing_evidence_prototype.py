#!/usr/bin/env python3
"""Prototype amended-filing evidence retrieval for SEC follow-up prediction.

The goal is to test whether we can recover external amended-filing evidence
when a company response says it revised, added, deleted, or amended disclosure.
This script intentionally uses no OpenAI calls: it fetches SEC company
submissions, downloads nearby candidate filings, and ranks text chunks with a
local lexical scorer.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pressback.sec import ARCHIVES, USER_AGENT, decode_document, normalize_text


SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik10}.json"
REQUEST_USER_AGENT = os.environ.get("SEC_USER_AGENT") or USER_AGENT

RELEASE_ACTION_RE = re.compile(
    r"\b("
    r"revis(?:e|ed|es|ing|ion|ions)|"
    r"amend(?:ed|ing|ment|ments)?|"
    r"add(?:ed|ing|itional)?|"
    r"delete(?:d|ing|ion)?|"
    r"remove(?:d|ing)?|"
    r"confirm(?:ed|ing)?|"
    r"supplement(?:ed|ing|al)?|"
    r"clarif(?:y|ied|ies|ication)|"
    r"filed|furnished|included|updated|will include|will revise|will update|will disclose"
    r")\b",
    re.IGNORECASE,
)

PAGE_RE = re.compile(r"\bpages?\s+([0-9][0-9,\-– and]*)", re.IGNORECASE)
AMENDMENT_RE = re.compile(r"\bAmendment\s+No\.?\s*([0-9]+)", re.IGNORECASE)

TARGET_FORM_RE = re.compile(
    r"\b("
    r"10-K|10-Q|8-K|S-1|S-3|S-4|F-1|F-3|F-4|20-F|40-F|"
    r"PREM14A|PREC14A|PRER14A|DEFM14A|DEF 14A|PRE 14A|Schedule 14A"
    r")\b",
    re.IGNORECASE,
)

STOPWORDS = {
    "the", "and", "for", "that", "with", "this", "from", "your", "you", "are", "our",
    "has", "have", "will", "were", "was", "been", "into", "page", "pages", "please",
    "revise", "revised", "disclosure", "disclosures", "company", "staff", "comment",
    "response", "form", "filing", "filings", "amendment", "registration", "statement",
    "securities", "commission", "regulation", "item", "also", "such", "any", "not",
    "may", "its", "their", "there", "these", "those", "include", "including",
}

AMENDMENT_FORMS = {
    "10-K/A", "10-Q/A", "8-K/A", "S-1/A", "S-3/A", "S-4/A", "F-1/A", "F-3/A", "F-4/A",
    "20-F/A", "40-F/A", "PREM14A", "PREC14A", "PRER14A", "DEFM14A", "DEF 14A",
    "DEFA14A", "PRE 14A", "PRER14C", "DEFR14A",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/sec_multiround_followup_v3/sec_multiround_balanced_test.jsonl")
    parser.add_argument("--out-dir", default="data/sec_amended_evidence_prototype_v1")
    parser.add_argument("--sample-size", type=int, default=120)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--window-before-days", type=int, default=7)
    parser.add_argument("--window-after-days", type=int, default=45)
    parser.add_argument("--max-candidates-per-row", type=int, default=8)
    parser.add_argument("--top-snippets", type=int, default=3)
    parser.add_argument("--delay", type=float, default=0.12)
    parser.add_argument("--cache-dir", default="data/sec_amended_evidence_prototype_v1/cache")
    parser.add_argument("--resume", action="store_true", help="Append to an existing evidence_sample.jsonl and skip completed example_ids.")
    parser.add_argument(
        "--sec-user-agent",
        default=os.environ.get("SEC_USER_AGENT") or USER_AGENT,
        help="SEC-compliant User-Agent, preferably including a contact email.",
    )
    args = parser.parse_args()

    global REQUEST_USER_AGENT
    REQUEST_USER_AGENT = args.sec_user_agent

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    rows = load_jsonl(Path(args.input))
    selected = select_rows(rows, args.sample_size, args.seed)
    out_jsonl = out_dir / "evidence_sample.jsonl"
    completed_rows: list[dict[str, Any]] = []
    completed_ids: set[str] = set()
    if args.resume and out_jsonl.exists():
        completed_rows = load_jsonl(out_jsonl)
        completed_ids = {str(row.get("example_id")) for row in completed_rows}
        selected = [row for row in selected if str(row.get("example_id")) not in completed_ids]
        print(f"[evidence] resume completed={len(completed_rows)} remaining={len(selected)}", flush=True)
    elif out_jsonl.exists():
        out_jsonl.unlink()

    output_rows = []
    with out_jsonl.open("a", encoding="utf-8") as stream:
        for index, row in enumerate(selected, start=1):
            print(f"[evidence] {index}/{len(selected)} {row.get('example_id')}", flush=True)
            evidence = retrieve_evidence_for_row(row, args, cache_dir)
            enriched = {**row, **evidence}
            output_rows.append(enriched)
            stream.write(json.dumps(enriched, ensure_ascii=False) + "\n")
            stream.flush()

    all_rows = completed_rows + output_rows
    stats = summarize_rows(all_rows)

    # Rewrite the JSONL in stable order after a successful pass. During a run,
    # the same file is also a streaming checkpoint.
    all_rows.sort(key=lambda row: str(row.get("example_id", "")))
    write_jsonl(out_jsonl, all_rows)

    out_csv = out_dir / "evidence_sample_review.csv"
    write_review_csv(out_csv, all_rows)
    manifest = {
        "input": args.input,
        "sample_size": len(all_rows),
        "completed_this_run": len(output_rows),
        "settings": vars(args),
        "stats": dict(stats),
        "label_counts": dict(Counter(row.get("regulator_followup_label") for row in all_rows)),
        "issue_category_counts": dict(Counter(row.get("issue_category") for row in all_rows)),
        "outputs": {
            "jsonl": str(out_jsonl),
            "review_csv": str(out_csv),
        },
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


def summarize_rows(rows: list[dict[str, Any]]) -> Counter:
    stats = Counter()
    for row in rows:
        stats["rows"] += 1
        if row_needs_external_evidence(row):
            stats["revision_claim_rows"] += 1
        if row.get("candidate_filings"):
            stats["rows_with_candidate_filings"] += 1
        if row.get("retrieved_snippets"):
            stats["rows_with_snippets"] += 1
        if row.get("best_candidate_score", 0) > 0:
            stats["rows_with_positive_score"] += 1
    return stats


def select_rows(rows: list[dict[str, Any]], sample_size: int, seed: int) -> list[dict[str, Any]]:
    if sample_size <= 0 or sample_size >= len(rows):
        return list(rows)
    import random

    rng = random.Random(seed)
    revision = [row for row in rows if row_needs_external_evidence(row)]
    rest = [row for row in rows if row not in revision]
    positives = [row for row in revision if row.get("regulator_followup_label") == "unresolved"]
    negatives = [row for row in revision if row.get("regulator_followup_label") != "unresolved"]
    rng.shuffle(positives)
    rng.shuffle(negatives)
    rng.shuffle(rest)
    half = sample_size // 2
    sample = positives[:half] + negatives[: sample_size - half]
    if len(sample) < sample_size:
        used = {row.get("example_id") for row in sample}
        sample.extend([row for row in rest if row.get("example_id") not in used][: sample_size - len(sample)])
    rng.shuffle(sample)
    return sample


def row_needs_external_evidence(row: dict[str, Any]) -> bool:
    response = str(row.get("company_response") or "")
    return bool(RELEASE_ACTION_RE.search(response) or PAGE_RE.search(response) or AMENDMENT_RE.search(response))


def retrieve_evidence_for_row(row: dict[str, Any], args: argparse.Namespace, cache_dir: Path) -> dict[str, Any]:
    cik = str(row.get("cik") or "").lstrip("0")
    response_date = parse_date(str(row.get("response_date") or ""))
    if not cik or response_date is None:
        return empty_evidence("missing_cik_or_response_date")

    try:
        filings = get_company_filings(cik, cache_dir)
    except Exception as exc:
        return empty_evidence(f"submissions_fetch_failed: {type(exc).__name__}: {exc}")

    candidates = candidate_filings(row, filings, response_date, args.window_before_days, args.window_after_days)
    candidates = candidates[: args.max_candidates_per_row]
    ranked_candidates = []
    snippets = []
    for candidate in candidates:
        try:
            text = fetch_filing_text(cik, candidate, cache_dir)
            time.sleep(args.delay)
        except Exception as exc:
            ranked_candidates.append({**candidate, "fetch_error": f"{type(exc).__name__}: {exc}", "score": 0.0})
            continue
        chunk_scores = rank_chunks(row, text)
        score = chunk_scores[0]["score"] if chunk_scores else 0.0
        ranked_candidates.append({**candidate, "score": score, "text_chars": len(text)})
        for chunk in chunk_scores[: args.top_snippets]:
            snippets.append({**chunk, "candidate_accession": candidate["accessionNumber"], "candidate_form": candidate["form"], "candidate_filing_date": candidate["filingDate"], "candidate_primary_document": candidate["primaryDocument"]})

    ranked_candidates.sort(key=lambda item: (float(item.get("score") or 0), item.get("filingDate", "")), reverse=True)
    snippets.sort(key=lambda item: float(item.get("score") or 0), reverse=True)
    top_snippets = snippets[: args.top_snippets]
    return {
        "revision_claim_detected": row_needs_external_evidence(row),
        "page_refs": extract_page_refs(str(row.get("company_response") or "")),
        "amendment_refs": extract_amendment_refs(str(row.get("company_response") or "")),
        "target_forms_from_subject": extract_target_forms(str(row.get("review_subject") or "")),
        "candidate_filings": ranked_candidates,
        "retrieved_snippets": top_snippets,
        "best_candidate_score": ranked_candidates[0]["score"] if ranked_candidates else 0.0,
        "best_candidate_form": ranked_candidates[0]["form"] if ranked_candidates else "",
        "best_candidate_accession": ranked_candidates[0]["accessionNumber"] if ranked_candidates else "",
        "best_candidate_filing_date": ranked_candidates[0]["filingDate"] if ranked_candidates else "",
        "evidence_status": "ok" if top_snippets else "no_snippet",
    }


def empty_evidence(reason: str) -> dict[str, Any]:
    return {
        "revision_claim_detected": False,
        "page_refs": [],
        "amendment_refs": [],
        "target_forms_from_subject": [],
        "candidate_filings": [],
        "retrieved_snippets": [],
        "best_candidate_score": 0.0,
        "best_candidate_form": "",
        "best_candidate_accession": "",
        "best_candidate_filing_date": "",
        "evidence_status": reason,
    }


def get_company_filings(cik: str, cache_dir: Path) -> list[dict[str, Any]]:
    cik10 = cik.zfill(10)
    path = cache_dir / f"CIK{cik10}.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = fetch_json(SUBMISSIONS_URL.format(cik10=cik10))
        path.write_text(json.dumps(data), encoding="utf-8")
    recent = data.get("filings", {}).get("recent", {})
    keys = ["accessionNumber", "filingDate", "reportDate", "acceptanceDateTime", "form", "primaryDocument", "primaryDocDescription"]
    filings = []
    for i, accession in enumerate(recent.get("accessionNumber", [])):
        item = {key: (recent.get(key, [""] * len(recent.get("accessionNumber", [])))[i] if i < len(recent.get(key, [])) else "") for key in keys}
        item["accessionNumber"] = accession
        filings.append(item)
    return filings


def candidate_filings(
    row: dict[str, Any],
    filings: list[dict[str, Any]],
    response_date: date,
    before_days: int,
    after_days: int,
) -> list[dict[str, Any]]:
    start = response_date - timedelta(days=before_days)
    end = response_date + timedelta(days=after_days)
    target_forms = set(extract_target_forms(str(row.get("review_subject") or "")))
    response_acc = str(row.get("response_accession") or "")
    candidates = []
    for filing in filings:
        filing_date = parse_date(str(filing.get("filingDate") or ""))
        if filing_date is None or filing_date < start or filing_date > end:
            continue
        accession = str(filing.get("accessionNumber") or "")
        if accession == response_acc:
            continue
        form = normalize_form(str(filing.get("form") or ""))
        if form in {"UPLOAD", "CORRESP"}:
            continue
        score = candidate_metadata_score(row, filing, response_date, target_forms)
        if score <= 0:
            continue
        candidates.append({**filing, "metadata_score": score})
    candidates.sort(key=lambda item: (item["metadata_score"], item.get("filingDate", "")), reverse=True)
    return candidates


def candidate_metadata_score(row: dict[str, Any], filing: dict[str, Any], response_date: date, target_forms: set[str]) -> float:
    form = normalize_form(str(filing.get("form") or ""))
    filing_date = parse_date(str(filing.get("filingDate") or "")) or response_date
    score = 0.0
    if form in AMENDMENT_FORMS or form.endswith("/A"):
        score += 3.0
    if target_forms and any(forms_compatible(form, target) for target in target_forms):
        score += 2.0
    if not target_forms and form in AMENDMENT_FORMS:
        score += 1.0
    days = abs((filing_date - response_date).days)
    score += max(0.0, 2.0 - days / 14.0)
    primary = str(filing.get("primaryDocument") or "").lower()
    if primary.endswith((".htm", ".html", ".txt")):
        score += 0.5
    subject = str(row.get("review_subject") or "").lower()
    desc = str(filing.get("primaryDocDescription") or "").lower()
    if desc and any(token in desc for token in salient_tokens(subject, limit=8)):
        score += 0.5
    return score


def forms_compatible(form: str, target: str) -> bool:
    form = normalize_form(form)
    target = normalize_form(target)
    if form == target or form == f"{target}/A":
        return True
    if target == "SCHEDULE 14A":
        return form in {"PREM14A", "PREC14A", "PRER14A", "DEFM14A", "DEF 14A", "DEFA14A", "PRE 14A"}
    if target == "8-K":
        return form in {"8-K", "8-K/A"}
    return False


def fetch_filing_text(cik: str, filing: dict[str, Any], cache_dir: Path) -> str:
    accession = str(filing["accessionNumber"])
    primary = str(filing.get("primaryDocument") or "")
    if not primary:
        return ""
    accession_nodash = accession.replace("-", "")
    path = cache_dir / f"{cik}_{accession_nodash}_{safe_name(primary)}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8", errors="ignore")
    url = f"{ARCHIVES}/{str(cik).lstrip('0')}/{accession_nodash}/{primary}"
    raw = fetch_bytes(url)
    text = decode_document(raw, primary)
    path.write_text(text, encoding="utf-8")
    return text


def rank_chunks(row: dict[str, Any], text: str) -> list[dict[str, Any]]:
    clean = normalize_text(text)
    if not clean:
        return []
    query_text = " ".join([
        str(row.get("sec_comment") or ""),
        str(row.get("company_response") or ""),
        str(row.get("review_subject") or ""),
    ])
    terms = salient_tokens(query_text, limit=60)
    if not terms:
        return []
    term_counts = Counter(terms)
    chunks = make_chunks(clean)
    scored = []
    for idx, chunk in enumerate(chunks):
        lowered = chunk.lower()
        score = 0.0
        matched = []
        for term, weight in term_counts.items():
            if term in lowered:
                score += 1.0 + math.log1p(weight)
                matched.append(term)
        # Boost chunks that look like amended disclosure rather than boilerplate.
        if re.search(r"\b(revised|amended|added|deleted|risk factor|management['’]s discussion|note \\d+|non-gaap|revenue|liquidity|custody)\b", lowered):
            score += 1.0
        if score > 0:
            scored.append({
                "chunk_index": idx,
                "score": round(score, 4),
                "matched_terms": matched[:20],
                "snippet": chunk[:2200],
            })
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored


def make_chunks(text: str, size: int = 1800, overlap: int = 250) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


def salient_tokens(text: str, limit: int = 50) -> list[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9\\-]{2,}", text.lower())
    filtered = [token for token in tokens if token not in STOPWORDS and len(token) > 2]
    counts = Counter(filtered)
    # Prefer domain terms, but keep this deterministic and local.
    ranked = sorted(counts.items(), key=lambda item: (domain_boost(item[0]), item[1], len(item[0])), reverse=True)
    return [token for token, _ in ranked[:limit]]


def domain_boost(token: str) -> int:
    domain = {
        "revenue", "recognition", "non-gaap", "adjusted", "ebitda", "custody", "bitcoin",
        "crypto", "risk", "factor", "liquidity", "agreement", "material", "related",
        "party", "beneficial", "ownership", "shares", "proxy", "business", "combination",
        "audit", "consent", "accounting", "policy", "quantification", "cash", "flow",
    }
    return 1 if token in domain else 0


def extract_page_refs(text: str) -> list[str]:
    refs = []
    for match in PAGE_RE.finditer(text):
        refs.append(match.group(1).strip())
    return refs[:10]


def extract_amendment_refs(text: str) -> list[str]:
    return [match.group(1) for match in AMENDMENT_RE.finditer(text)][:10]


def extract_target_forms(text: str) -> list[str]:
    forms = []
    for match in TARGET_FORM_RE.finditer(text):
        forms.append(normalize_form(match.group(1)))
    # Preserve order and uniqueness.
    seen = set()
    unique = []
    for form in forms:
        if form not in seen:
            seen.add(form)
            unique.append(form)
    return unique


def normalize_form(form: str) -> str:
    clean = re.sub(r"\s+", " ", form.upper()).strip()
    if clean == "SCHEDULE 14A":
        return clean
    if clean == "PRE 14A":
        return clean
    return clean


def parse_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def fetch_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers=request_headers("application/json,text/plain,*/*"))
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers=request_headers("text/html,application/xhtml+xml,text/plain,*/*"))
    with urllib.request.urlopen(req, timeout=45) as response:
        return response.read()


def request_headers(accept: str) -> dict[str, str]:
    return {
        "User-Agent": REQUEST_USER_AGENT,
        "Accept": accept,
        "Accept-Encoding": "identity",
        "Accept-Language": "en-US,en;q=0.9",
    }


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name)[:120]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_review_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    import csv

    fields = [
        "example_id",
        "regulator_followup_label",
        "issue_category",
        "review_subject",
        "response_date",
        "revision_claim_detected",
        "page_refs",
        "amendment_refs",
        "best_candidate_form",
        "best_candidate_filing_date",
        "best_candidate_accession",
        "best_candidate_score",
        "evidence_status",
        "sec_comment",
        "company_response",
        "top_snippet",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            snippets = row.get("retrieved_snippets") or []
            writer.writerow({
                "example_id": row.get("example_id", ""),
                "regulator_followup_label": row.get("regulator_followup_label", ""),
                "issue_category": row.get("issue_category", ""),
                "review_subject": row.get("review_subject", ""),
                "response_date": row.get("response_date", ""),
                "revision_claim_detected": row.get("revision_claim_detected", ""),
                "page_refs": "; ".join(row.get("page_refs") or []),
                "amendment_refs": "; ".join(row.get("amendment_refs") or []),
                "best_candidate_form": row.get("best_candidate_form", ""),
                "best_candidate_filing_date": row.get("best_candidate_filing_date", ""),
                "best_candidate_accession": row.get("best_candidate_accession", ""),
                "best_candidate_score": row.get("best_candidate_score", ""),
                "evidence_status": row.get("evidence_status", ""),
                "sec_comment": row.get("sec_comment", ""),
                "company_response": row.get("company_response", ""),
                "top_snippet": snippets[0].get("snippet", "") if snippets else "",
            })


if __name__ == "__main__":
    raise SystemExit(main())
