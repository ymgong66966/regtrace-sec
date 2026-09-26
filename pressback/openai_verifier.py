from __future__ import annotations

import json
import math
import os
import time
import urllib.request
from typing import Any

from .costs import append_usage_record, cost_for_tokens


OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_EMBED_URL = "https://api.openai.com/v1/embeddings"


def verify_pairs(
    rows: list[dict[str, Any]],
    embedding_model: str = "text-embedding-3-small",
    verifier_model: str = "gpt-4o-mini",
    embedding_threshold: float = 0.45,
    unresolved_only: bool = True,
    cost_ledger: str | None = "outputs/openai_usage_ledger.jsonl",
) -> list[dict[str, Any]]:
    verified = []
    for row in rows:
        enriched = dict(row)
        should_verify = bool(row.get("followup_comment_text")) and (not unresolved_only or row.get("label") == "unresolved")
        if not should_verify:
            enriched.setdefault("verified_label", row.get("label", "resolved"))
            verified.append(enriched)
            continue

        decision = verify_same_topic(
            row.get("sec_comment", ""),
            row.get("company_response", ""),
            row.get("followup_comment_text", ""),
            model=verifier_model,
            cost_ledger=cost_ledger,
        )
        clean_followup = str(decision.get("clean_followup_comment") or row.get("followup_comment_text", "")).strip()
        similarity = embedding_similarity(
            row.get("sec_comment", ""),
            clean_followup,
            model=embedding_model,
            cost_ledger=cost_ledger,
        )
        same_topic = bool(decision.get("same_topic"))
        response_matches = bool(decision.get("response_matches_comment", True))
        followup_complete = bool(decision.get("followup_is_complete", True))
        accepted = similarity >= embedding_threshold and same_topic and response_matches and followup_complete and _has_minimum_content(row)
        enriched.update(
            {
                "embedding_similarity": similarity,
                "clean_followup_comment": clean_followup,
                "verifier_same_topic": same_topic,
                "verifier_response_matches_comment": response_matches,
                "verifier_followup_is_complete": followup_complete,
                "verifier_confidence": decision.get("confidence"),
                "verifier_failure_type": decision.get("failure_type"),
                "verifier_reason": decision.get("reason"),
                "verified_label": "unresolved" if accepted else "resolved",
            }
        )
        verified.append(enriched)
    return verified


def embedding_similarity(left: str, right: str, model: str = "text-embedding-3-small", cost_ledger: str | None = None) -> float:
    left_embedding, right_embedding = embed_texts([left, right], model=model, cost_ledger=cost_ledger)
    return cosine(left_embedding, right_embedding)


def embed_texts(texts: list[str], model: str = "text-embedding-3-small", cost_ledger: str | None = None) -> list[list[float]]:
    response = _openai_json(
        OPENAI_EMBED_URL,
        {
            "model": model,
            "input": [text[:12000] for text in texts],
        },
        purpose="embedding",
        model=model,
        cost_ledger=cost_ledger,
    )
    return [item["embedding"] for item in sorted(response["data"], key=lambda item: item["index"])]


def verify_same_topic(
    sec_comment: str,
    company_response: str,
    followup_comment: str,
    model: str = "gpt-4o-mini",
    cost_ledger: str | None = None,
) -> dict[str, Any]:
    prompt = f"""
You are auditing SEC comment-letter review threads.

Decide whether the later SEC comment is a same-topic follow-up showing that the company's response did not fully resolve the earlier SEC comment.

Return JSON only with:
- same_topic: boolean
- response_matches_comment: boolean
- followup_is_complete: boolean
- clean_followup_comment: string
- confidence: number between 0 and 1
- failure_type: one of ["explicit_reissue", "same_disclosure_gap", "same_accounting_issue", "new_issue", "generic_admin", "truncated_followup", "unclear"]
- reason: one concise sentence

Use a strict standard. Mark same_topic=true when the later comment explicitly reissues or narrows the earlier comment, asks for the same disclosure/accounting fix, or critiques the company's response to that same issue. Mark same_topic=false when it is merely in the same filing, same broad risk area, same staff letter, contact/signature text, or a new issue.

Set response_matches_comment=true if the company response is about the same disclosure/accounting/legal issue as the earlier SEC comment, even if the response is incomplete, inadequate, or later criticized by the SEC. This field is an alignment check, not a quality check. Set it false only if the response is a mere extension request, generic correspondence, blank/truncated text, or appears to answer a different numbered comment.

Set followup_is_complete=true only if the later SEC comment is a complete, interpretable staff comment. Set it false if the later comment appears truncated, ends mid-phrase, contains mostly contact/signature/page-footer boilerplate, or is too fragmentary to support a label. If followup_is_complete=false, use failure_type="truncated_followup".

For clean_followup_comment, rewrite only the later SEC comment by removing signature blocks, staff contact information, page headers/footers, EDGAR artifacts, and unrelated trailing boilerplate. Do not add facts. If the later comment is truncated or not interpretable, return the best cleaned fragment and set followup_is_complete=false.

Earlier SEC comment:
{sec_comment[:4000]}

Company response:
{company_response[:4000]}

Later SEC comment:
{followup_comment[:4000]}
""".strip()
    response = _openai_json(
        OPENAI_CHAT_URL,
        {
            "model": model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "You are a careful SEC disclosure-review auditor. Output strict JSON."},
                {"role": "user", "content": prompt},
            ],
        },
        purpose="sec_followup_verifier",
        model=model,
        cost_ledger=cost_ledger,
    )
    content = response["choices"][0]["message"]["content"]
    return json.loads(content)


def cosine(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


def _has_minimum_content(row: dict[str, Any]) -> bool:
    sec_comment = str(row.get("sec_comment", ""))
    company_response = str(row.get("company_response", ""))
    return len(sec_comment.split()) >= 12 and len(company_response.split()) >= 8


def _openai_json(
    url: str,
    payload: dict[str, Any],
    purpose: str,
    model: str,
    cost_ledger: str | None = None,
) -> dict[str, Any]:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    last_error: Exception | None = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                data = json.loads(response.read().decode("utf-8"))
            break
        except Exception as exc:
            last_error = exc
            if attempt == 4:
                raise
            time.sleep(1.0 * (2**attempt))
    else:
        raise last_error or RuntimeError("OpenAI request failed")
    usage = data.get("usage") or {}
    if usage:
        input_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or usage.get("total_tokens") or 0)
        output_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        try:
            estimated_cost = cost_for_tokens(model, input_tokens, output_tokens)
        except KeyError:
            estimated_cost = 0.0
        append_usage_record(
            cost_ledger,
            purpose=purpose,
            model=model,
            usage=usage,
            estimated_cost_usd=estimated_cost,
        )
    return data
