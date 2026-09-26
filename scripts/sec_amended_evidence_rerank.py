#!/usr/bin/env python3
"""LLM reranking/adjudication for amended filing evidence snippets.

The retrieval prototype finds nearby amended filings and candidate snippets.
This script asks an LLM to decide whether those snippets actually show the
disclosure/action needed to evaluate the SEC comment-response pair.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pressback.costs import cost_for_tokens, estimate_text_tokens
from pressback.openai_verifier import OPENAI_CHAT_URL, _openai_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/sec_amended_evidence_prototype_v1/evidence_sample.jsonl")
    parser.add_argument("--out-jsonl", default="data/sec_amended_evidence_prototype_v1/evidence_sample_reranked.jsonl")
    parser.add_argument("--out-csv", default="data/sec_amended_evidence_prototype_v1/evidence_sample_reranked_review.csv")
    parser.add_argument("--out-summary", default="data/sec_amended_evidence_prototype_v1/rerank_summary.json")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--estimate-only", action="store_true")
    parser.add_argument("--cost-ledger", default="outputs/openai_usage_ledger.jsonl")
    args = parser.parse_args()

    rows = load_jsonl(Path(args.input))
    rows = [row for row in rows if row.get("retrieved_snippets")]
    if args.limit > 0:
        rows = rows[: args.limit]

    estimate = estimate_cost(rows, args.model, args.top_k)
    if args.estimate_only:
        print(json.dumps(estimate, indent=2, ensure_ascii=False))
        return 0

    out_jsonl = Path(args.out_jsonl)
    completed: list[dict[str, Any]] = []
    if args.resume and out_jsonl.exists():
        completed = load_jsonl(out_jsonl)
        completed_ids = {row.get("example_id") for row in completed}
        rows = [row for row in rows if row.get("example_id") not in completed_ids]
        print(f"[amended_rerank] resume loaded={len(completed)} remaining={len(rows)}", flush=True)

    new_rows = run(rows, args.model, args.cost_ledger, args.workers, args.top_k)
    output = completed + new_rows
    output.sort(key=lambda row: row.get("example_id", ""))
    write_jsonl(out_jsonl, output)
    write_review_csv(Path(args.out_csv), output)
    summary = summarize(output, estimate)
    Path(args.out_summary).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def run(rows: list[dict[str, Any]], model: str, cost_ledger: str | None, workers: int, top_k: int) -> list[dict[str, Any]]:
    if workers <= 1:
        out = []
        for index, row in enumerate(rows, start=1):
            print(f"[amended_rerank] {index}/{len(rows)} {row.get('example_id')}", flush=True)
            out.append(adjudicate_and_enrich(row, model, cost_ledger, top_k))
        return out

    out = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(adjudicate_and_enrich, row, model, cost_ledger, top_k): (index, row)
            for index, row in enumerate(rows, start=1)
        }
        done = 0
        for future in as_completed(futures):
            index, row = futures[future]
            out.append(future.result())
            done += 1
            print(f"[amended_rerank] done {done}/{len(rows)} source_index={index} {row.get('example_id')}", flush=True)
    return out


def adjudicate_and_enrich(row: dict[str, Any], model: str, cost_ledger: str | None, top_k: int) -> dict[str, Any]:
    decision = adjudicate(row, model, cost_ledger, top_k)
    enriched = dict(row)
    enriched.update({f"amended_evidence_{key}": value for key, value in decision.items()})
    snippets = row.get("retrieved_snippets") or []
    best_index = int(decision.get("best_snippet_index") or 0)
    if best_index < 0 or best_index >= min(len(snippets), top_k):
        best_index = 0
    enriched["amended_evidence_best_snippet"] = snippets[best_index].get("snippet", "") if snippets else ""
    enriched["amended_evidence_available"] = str(decision.get("evidence_relevance")) in {
        "directly_addresses",
        "partially_addresses",
    }
    return enriched


def adjudicate(row: dict[str, Any], model: str, cost_ledger: str | None, top_k: int) -> dict[str, Any]:
    snippets = row.get("retrieved_snippets") or []
    snippet_block = "\n\n".join(
        f"[Snippet {index} | form={snippet.get('candidate_form')} | date={snippet.get('candidate_filing_date')} | accession={snippet.get('candidate_accession')}]\n"
        f"{str(snippet.get('snippet') or '')[:1800]}"
        for index, snippet in enumerate(snippets[:top_k])
    )
    prompt = f"""
You are auditing whether amended SEC filing text provides the missing evidence needed to evaluate a company's response to an SEC comment.

Inputs:
- Earlier SEC comment: what the SEC asked the company to do.
- Company response: what the company said it did or will do.
- Retrieved amended-filing snippets: text pulled from nearby filed/amended documents.

Task:
Determine whether any snippet visibly supports the company's claimed current action and whether the visible amended-filing evidence appears to satisfy the SEC request.

Important standards:
- Do not assume a response is resolved merely because the company says "we revised" or "we added disclosure." Look for visible disclosure/action in the snippet.
- If the response says the disclosure will appear in a future filing and the snippet is that later filing, treat the snippet as potential evidence.
- If snippets are boilerplate, unrelated exhibit language, signature/contact text, or only broadly similar topic text, mark them irrelevant.
- You are not deciding the final ground-truth label. You are deciding whether the retrieved filing text gives useful observable evidence for the model.
- Separate relevance from sufficiency. A snippet can directly address the same SEC obligation but still reveal an unmet requirement.

Return JSON only with:
- best_snippet_index: integer index starting at 0
- evidence_relevance: one of ["directly_addresses", "partially_addresses", "irrelevant", "no_visible_evidence"]
- obligation_matched: boolean
- company_action_supported: boolean
- sec_request_appears_satisfied: boolean
- visible_unmet_requirement: boolean
- supporting_quote: a short exact quote copied from one snippet, or "" if no exact supporting text exists
- evidence_summary: one concise sentence describing what the snippet shows
- missing_evidence: one concise sentence describing what remains unseen or insufficient
- confidence: number from 0 to 1

Quote discipline:
- supporting_quote must be copied verbatim from the snippets and must be enough to justify your decision.
- If you cannot provide a verbatim supporting_quote, set evidence_relevance="irrelevant" or "no_visible_evidence", company_action_supported=false, and sec_request_appears_satisfied=false.
- Do not infer satisfaction from generic prospectus boilerplate, broad financial statement text, or a similar topic without an exact disclosure/action matching the SEC request.
- For requests about auditor consents, filed exhibits, named parties, share/vote counts, page-specific changes, or accounting-rule thresholds, require the exact visible item. Broad related text is not enough.

Relevance and sufficiency definitions:
- evidence_relevance="directly_addresses" means the quote is about the exact SEC obligation, requested disclosure, accounting treatment, named item, or page-specific revision. It does not automatically mean the request is satisfied.
- evidence_relevance="partially_addresses" means the quote is on the same concrete topic but misses at least one required element.
- sec_request_appears_satisfied=true only when the visible quote covers all material elements of the SEC request.
- visible_unmet_requirement=true when the quote is exact-topic evidence but still lacks a requested element, keeps problematic language, omits quantification/thresholds/named items, or only shows a partial fix.
- If the SEC asked for multiple elements, all material elements must be visible before setting sec_request_appears_satisfied=true.

Earlier SEC comment:
{str(row.get("sec_comment", ""))[:3500]}

Company response:
{str(row.get("company_response", ""))[:3500]}

Retrieved amended-filing snippets:
{snippet_block}
""".strip()
    response = _openai_json(
        OPENAI_CHAT_URL,
        {
            "model": model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "You are a strict SEC amended-filing evidence auditor. Output strict JSON."},
                {"role": "user", "content": prompt},
            ],
        },
        purpose="sec_amended_evidence_rerank",
        model=model,
        cost_ledger=cost_ledger,
    )
    return json.loads(response["choices"][0]["message"]["content"])


def estimate_cost(rows: list[dict[str, Any]], model: str, top_k: int) -> dict[str, Any]:
    input_tokens = output_tokens = 0
    for row in rows:
        input_tokens += 520
        input_tokens += estimate_text_tokens(str(row.get("sec_comment", ""))[:3500])
        input_tokens += estimate_text_tokens(str(row.get("company_response", ""))[:3500])
        for snippet in (row.get("retrieved_snippets") or [])[:top_k]:
            input_tokens += 80
            input_tokens += estimate_text_tokens(str(snippet.get("snippet") or "")[:1800])
        output_tokens += 180
    return {
        "rows": len(rows),
        "model": model,
        "top_k": top_k,
        "input_tokens_est": input_tokens,
        "output_tokens_est": output_tokens,
        "cost_usd_est": cost_for_tokens(model, input_tokens, output_tokens),
    }


def summarize(rows: list[dict[str, Any]], estimate: dict[str, Any]) -> dict[str, Any]:
    return {
        "estimate": estimate,
        "rows": len(rows),
        "evidence_relevance": counts(rows, "amended_evidence_evidence_relevance"),
        "available": counts(rows, "amended_evidence_available"),
        "company_action_supported": counts(rows, "amended_evidence_company_action_supported"),
        "sec_request_appears_satisfied": counts(rows, "amended_evidence_sec_request_appears_satisfied"),
        "visible_unmet_requirement": counts(rows, "amended_evidence_visible_unmet_requirement"),
        "label_x_relevance": cross_counts(rows, "regulator_followup_label", "amended_evidence_evidence_relevance"),
    }


def counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key))
        out[value] = out.get(value, 0) + 1
    return dict(sorted(out.items(), key=lambda item: (-item[1], item[0])))


def cross_counts(rows: list[dict[str, Any]], key1: str, key2: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        value = f"{row.get(key1)}__{row.get(key2)}"
        out[value] = out.get(value, 0) + 1
    return dict(sorted(out.items(), key=lambda item: (-item[1], item[0])))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_review_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "example_id",
        "regulator_followup_label",
        "issue_category",
        "review_subject",
        "response_date",
        "best_candidate_form",
        "best_candidate_filing_date",
        "amended_evidence_evidence_relevance",
        "amended_evidence_company_action_supported",
        "amended_evidence_sec_request_appears_satisfied",
        "amended_evidence_visible_unmet_requirement",
        "amended_evidence_confidence",
        "amended_evidence_evidence_summary",
        "amended_evidence_missing_evidence",
        "amended_evidence_supporting_quote",
        "sec_comment",
        "company_response",
        "amended_evidence_best_snippet",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


if __name__ == "__main__":
    raise SystemExit(main())
