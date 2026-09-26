from __future__ import annotations

import re

from .label import topic_similarity


VAGUE_CUES = (
    "pleased",
    "excited",
    "healthy",
    "strong demand",
    "continue to",
    "long term",
    "strategic",
    "comfortable",
    "not going to comment",
    "not prepared to",
    "we do not disclose",
    "we don't disclose",
    "too early",
)

QUANT_CUES = (
    "quantify",
    "how much",
    "what percent",
    "percentage",
    "basis points",
    "margin",
    "revenue",
    "impact",
    "dollars",
    "guidance",
)


def heuristic_predict(question: str, answer: str, similarity_threshold: float = 0.16) -> str:
    """A deliberately simple non-LLM floor for responsiveness detection."""
    sim = topic_similarity(question, answer)
    lowered_answer = answer.lower()
    lowered_question = question.lower()
    asks_for_numbers = any(cue in lowered_question for cue in QUANT_CUES)
    has_number = bool(re.search(r"(\d+|percent|%|million|billion|basis point)", lowered_answer))
    vague = any(cue in lowered_answer for cue in VAGUE_CUES)
    if sim < similarity_threshold:
        return "non_responsive"
    if asks_for_numbers and not has_number:
        return "non_responsive"
    if vague and sim < similarity_threshold + 0.08:
        return "non_responsive"
    return "responsive"


def sec_heuristic_predict(sec_comment: str, company_response: str, similarity_threshold: float = 0.18) -> str:
    """A weak non-LLM floor for SEC unresolved-response detection.

    This is intentionally conservative and should be reported as a sanity-check
    baseline, not as a competitive model.
    """
    sim = topic_similarity(sec_comment, company_response)
    lowered = company_response.lower()
    terse = len(company_response.split()) < 28
    generic = any(
        cue in lowered
        for cue in (
            "acknowledges the staff's comment",
            "acknowledges the staff’s comment",
            "has revised the disclosure",
            "has revised page",
            "has updated note",
            "will revise future filings",
        )
    )
    asks_for_numbers = any(cue in sec_comment.lower() for cue in QUANT_CUES + ("quantitative", "amounts", "basis"))
    response_has_number = bool(re.search(r"(\d+|%|percent|million|billion|basis point|\\$)", company_response))
    if sim < similarity_threshold:
        return "unresolved"
    if terse and generic:
        return "unresolved"
    if asks_for_numbers and not response_has_number and sim < similarity_threshold + 0.12:
        return "unresolved"
    return "resolved"
