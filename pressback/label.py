from __future__ import annotations

import re
from dataclasses import dataclass

from .schema import PressBackThread, Transcript, TranscriptTurn


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "can",
    "could",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "our",
    "that",
    "the",
    "this",
    "to",
    "was",
    "we",
    "what",
    "with",
    "would",
    "you",
    "your",
}

FOLLOW_UP_CUES = (
    "follow up",
    "following up",
    "just to clarify",
    "to clarify",
    "on that",
    "on the same",
    "back to",
    "circle back",
    "coming back",
    "press",
    "understand",
    "specifically",
    "can you quantify",
    "could you quantify",
    "can you give us",
    "could you give us",
    "more detail",
    "color on",
)


@dataclass(frozen=True)
class ExtractConfig:
    topic_threshold: float = 0.22
    same_analyst_threshold: float = 0.24
    cross_analyst_threshold: float = 0.5
    max_followup_turns: int | None = None
    require_interrogative: bool = True
    require_followup_cue_or_question: bool = True
    min_question_tokens: int = 4


def extract_threads(transcript: Transcript, config: ExtractConfig | None = None) -> list[PressBackThread]:
    config = config or ExtractConfig()
    turns = transcript.turns
    threads: list[PressBackThread] = []
    i = 0
    while i < len(turns):
        turn = turns[i]
        if not _is_analyst_question(turn, config):
            i += 1
            continue
        answer_turns: list[TranscriptTurn] = []
        j = i + 1
        while j < len(turns) and turns[j].role != "analyst":
            if turns[j].role == "executive" or turns[j].role == "unknown":
                answer_turns.append(turns[j])
            j += 1
        if not answer_turns:
            i += 1
            continue
        match = _find_followup(turn, turns, j, config)
        answer = "\n".join(answer_turn.text for answer_turn in answer_turns).strip()
        executive_speakers = sorted({answer_turn.speaker for answer_turn in answer_turns})
        tier = "none"
        if match is not None:
            followup_turn, score = match
            tier = "same_analyst" if _same_speaker(turn.speaker, followup_turn.speaker) else "cross_analyst"
        else:
            followup_turn, score = None, None
        threads.append(
            PressBackThread(
                transcript_id=transcript.transcript_id,
                question_turn_index=turn.turn_index,
                answer_end_turn_index=answer_turns[-1].turn_index,
                analyst=turn.speaker,
                executive_speakers=executive_speakers,
                question=turn.text,
                answer=answer,
                press_back=followup_turn is not None,
                tier=tier,
                follow_up_turn_index=followup_turn.turn_index if followup_turn else None,
                follow_up_analyst=followup_turn.speaker if followup_turn else None,
                follow_up_text=followup_turn.text if followup_turn else None,
                topic_score=score,
                ticker=transcript.ticker or turn.ticker,
                date=transcript.date or turn.date,
                company=transcript.company or turn.company,
            )
        )
        i = j
    return threads


def extract_corpus(transcripts: list[Transcript], config: ExtractConfig | None = None) -> list[PressBackThread]:
    threads: list[PressBackThread] = []
    for transcript in transcripts:
        threads.extend(extract_threads(transcript, config))
    return threads


def topic_similarity(left: str, right: str) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = len(left_tokens & right_tokens)
    # Short analyst questions often share a compact set of accounting terms but
    # differ in filler words. Overlap coefficient is a better high-recall first
    # pass than Jaccard; the audit gate later decides the threshold.
    return overlap / min(len(left_tokens), len(right_tokens))


def is_followup_like(text: str) -> bool:
    lowered = text.lower()
    return "?" in text or any(cue in lowered for cue in FOLLOW_UP_CUES)


def _find_followup(
    question: TranscriptTurn,
    turns: list[TranscriptTurn],
    start_index: int,
    config: ExtractConfig,
) -> tuple[TranscriptTurn, float] | None:
    end = len(turns)
    if config.max_followup_turns is not None:
        end = min(end, start_index + config.max_followup_turns)
    best: tuple[TranscriptTurn, float] | None = None
    crossed_to_new_analyst = False
    for turn in turns[start_index:end]:
        if turn.role != "analyst":
            continue
        if config.require_followup_cue_or_question and not is_followup_like(turn.text):
            continue
        same_analyst = _same_speaker(question.speaker, turn.speaker)
        if not same_analyst:
            crossed_to_new_analyst = True
        score = topic_similarity(question.text, turn.text)
        has_explicit_cue = any(cue in turn.text.lower() for cue in FOLLOW_UP_CUES)
        cue_bonus = 0.08 if has_explicit_cue else 0.0
        adjusted = min(score + cue_bonus, 1.0)
        threshold = config.same_analyst_threshold if same_analyst else config.cross_analyst_threshold
        if not same_analyst and not has_explicit_cue:
            continue
        if same_analyst and crossed_to_new_analyst:
            continue
        if adjusted >= threshold and adjusted >= config.topic_threshold and (best is None or adjusted > best[1]):
            best = (turn, adjusted)
    return best


def _is_analyst_question(turn: TranscriptTurn, config: ExtractConfig) -> bool:
    if turn.role != "analyst":
        return False
    if len(_tokens(turn.text)) < config.min_question_tokens:
        return False
    return not config.require_interrogative or is_followup_like(turn.text)


def _tokens(text: str) -> set[str]:
    tokens = set(re.findall(r"[a-zA-Z][a-zA-Z0-9_'-]{2,}", text.lower()))
    return {token for token in tokens if token not in STOPWORDS}


def _same_speaker(left: str, right: str) -> bool:
    if left.strip().lower() in {"analyst", "unknown"} or right.strip().lower() in {"analyst", "unknown"}:
        return False
    return re.sub(r"\W+", "", left.lower()) == re.sub(r"\W+", "", right.lower())
