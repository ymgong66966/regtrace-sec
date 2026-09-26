from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from .schema import Role, Transcript, TranscriptTurn


ROLE_SPEAKER_LINE = re.compile(
    r"^\s*(?P<role>analyst|executive|operator|management|manager|ceo|cfo)"
    r"(?:\s*-\s*(?P<speaker>[^:]{1,80}))?\s*:\s*(?P<text>.+?)\s*$",
    re.IGNORECASE,
)
SPEAKER_LINE = re.compile(r"^\s*(?P<speaker>[^:]{1,80})\s*:\s*(?P<text>.+?)\s*$")

ANALYST_HINTS = (
    "analyst",
    "research",
    "securities",
    "capital",
    "markets",
    "bank",
    "morgan",
    "goldman",
    "jpmorgan",
    "barclays",
    "ubs",
    "wells",
)
EXECUTIVE_HINTS = (
    "ceo",
    "cfo",
    "coo",
    "chief",
    "president",
    "officer",
    "executive",
    "management",
    "director",
)
OPERATOR_HINTS = ("operator", "moderator", "conference")


def infer_role(speaker: str, text: str = "", explicit_role: str | None = None) -> Role:
    explicit = (explicit_role or "").lower()
    if "operator" in explicit:
        return "operator"
    if explicit in {"analyst"}:
        return "analyst"
    if explicit in {"executive", "management", "manager", "ceo", "cfo"}:
        return "executive"
    speaker_joined = " ".join(part.lower() for part in (explicit_role or "", speaker))
    text_head = text[:100].lower()
    if any(hint in speaker_joined for hint in OPERATOR_HINTS):
        return "operator"
    if any(hint in speaker_joined for hint in ANALYST_HINTS):
        return "analyst"
    if any(hint in speaker_joined for hint in EXECUTIVE_HINTS):
        return "executive"
    if "question and answer session" in text_head or "question queue" in text_head:
        return "operator"
    return "unknown"


def load_transcripts(path: str | Path) -> list[Transcript]:
    source = Path(path)
    if source.is_dir():
        transcripts: list[Transcript] = []
        for child in sorted(source.iterdir()):
            if child.suffix.lower() in {".txt", ".csv", ".jsonl", ".json"}:
                transcripts.extend(load_transcripts(child))
        return transcripts
    if source.suffix.lower() == ".csv":
        return _load_csv(source)
    if source.suffix.lower() in {".jsonl", ".json"}:
        return _load_jsonl(source)
    return [_load_text(source)]


def _load_csv(path: Path) -> list[Transcript]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    turns = [_row_to_turn(row, i, path.stem) for i, row in enumerate(rows)]
    return _group_turns(turns)


def _load_jsonl(path: Path) -> list[Transcript]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        first = handle.read(1)
        handle.seek(0)
        if first == "[":
            rows = json.load(handle)
        else:
            rows = [json.loads(line) for line in handle if line.strip()]
    turns = [_row_to_turn(row, i, path.stem) for i, row in enumerate(rows)]
    return _group_turns(turns)


def _load_text(path: Path) -> Transcript:
    turns: list[TranscriptTurn] = []
    fallback_index = 0
    pending_speaker: str | None = None
    pending_role: Role | None = None
    raw_lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    analyst_names = _extract_analyst_names(raw_lines)
    with path.open(encoding="utf-8") as handle:
        for raw_line in raw_lines:
            text = raw_line.strip()
            if not text:
                continue
            role_match = ROLE_SPEAKER_LINE.match(text)
            match = SPEAKER_LINE.match(text)
            if role_match:
                prefix = role_match.group("role") or ""
                speaker = (role_match.group("speaker") or prefix or "Unknown").strip()
                body = role_match.group("text").strip()
                role = infer_role(speaker=speaker, text=body, explicit_role=prefix)
            elif match:
                speaker = (match.group("speaker") or "Unknown").strip()
                body = match.group("text").strip()
                explicit = "analyst" if _speaker_in_set(speaker, analyst_names) else None
                role = infer_role(speaker=speaker, text=body, explicit_role=explicit)
            elif _looks_like_speaker_line(text):
                pending_speaker = text
                explicit = "analyst" if _speaker_in_set(text, analyst_names) else None
                pending_role = infer_role(text, explicit_role=explicit)
                continue
            elif pending_speaker:
                speaker = pending_speaker
                body = text
                role = pending_role or infer_role(speaker, body)
                if role == "unknown":
                    role = infer_role(speaker, body)
                pending_speaker = None
                pending_role = None
            else:
                speaker = "Unknown"
                body = text
                role = infer_role(speaker, body)
            turns.append(
                TranscriptTurn(
                    transcript_id=path.stem,
                    turn_index=fallback_index,
                    speaker=speaker,
                    role=role,
                    text=body,
                )
            )
            fallback_index += 1
    return Transcript(transcript_id=path.stem, turns=turns)


def _looks_like_speaker_line(text: str) -> bool:
    if ":" in text or len(text.split()) > 6:
        return False
    lowered = text.lower()
    if lowered in {"operator", "moderator"}:
        return True
    return bool(re.match(r"^[A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){0,4}$", text))


def _extract_analyst_names(lines: list[str]) -> set[str]:
    names: set[str] = {"Analyst"}
    patterns = [
        r"(?:next|first|last)?\s*question (?:comes|is) from (?P<name>.+?)(?: with | from |\.|$)",
        r"line (?:is )?(?:now )?(?:live|open).*?(?P<name>[A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){1,4})",
    ]
    for line in lines:
        lowered = line.lower()
        if "question" not in lowered and "line" not in lowered:
            continue
        for pattern in patterns:
            match = re.search(pattern, line, flags=re.IGNORECASE)
            if match:
                name = _clean_name(match.group("name"))
                if name:
                    names.add(name)
    return names


def _speaker_in_set(speaker: str, names: set[str]) -> bool:
    normalized = _clean_name(speaker).lower()
    return any(normalized == _clean_name(name).lower() for name in names)


def _clean_name(name: str) -> str:
    cleaned = re.sub(r"\b(your|our|the|next|first|last|question|comes|from|with|line|is|now|live)\b", " ", name, flags=re.IGNORECASE)
    cleaned = re.sub(r"[^A-Za-z.' -]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,-")
    if len(cleaned.split()) > 5:
        cleaned = " ".join(cleaned.split()[:5])
    return cleaned


def _row_to_turn(row: dict, fallback_index: int, fallback_id: str) -> TranscriptTurn:
    transcript_id = _first(row, "transcript_id", "call_id", "id", default=fallback_id)
    speaker = _first(row, "speaker", "speaker_name", "participant", "name", default="Unknown")
    text = _first(row, "text", "content", "utterance", "body", "transcript", default="")
    explicit_role = _first(row, "role", "speaker_role", "participant_type", default=None)
    raw_index = _first(row, "turn_index", "index", "sequence", default=None)
    try:
        turn_index = int(raw_index) if raw_index is not None else fallback_index
    except ValueError:
        turn_index = fallback_index
    role = infer_role(speaker=speaker, text=text, explicit_role=explicit_role)
    return TranscriptTurn(
        transcript_id=str(transcript_id),
        turn_index=turn_index,
        speaker=str(speaker),
        role=role,
        text=str(text).strip(),
        ticker=_first(row, "ticker", "symbol", default=None),
        date=_first(row, "date", "call_date", "event_date", default=None),
        company=_first(row, "company", "company_name", default=None),
        raw=dict(row),
    )


def _group_turns(turns: Iterable[TranscriptTurn]) -> list[Transcript]:
    grouped: dict[str, list[TranscriptTurn]] = defaultdict(list)
    for turn in turns:
        if turn.text:
            grouped[turn.transcript_id].append(turn)
    transcripts = []
    for transcript_id, group in grouped.items():
        ordered = sorted(group, key=lambda turn: turn.turn_index)
        first = ordered[0] if ordered else None
        transcripts.append(
            Transcript(
                transcript_id=transcript_id,
                turns=ordered,
                ticker=first.ticker if first else None,
                date=first.date if first else None,
                company=first.company if first else None,
            )
        )
    return transcripts


def _first(row: dict, *keys: str, default: str | None = None) -> str | None:
    lowered = {str(key).lower(): value for key, value in row.items()}
    for key in keys:
        value = lowered.get(key.lower())
        if value not in (None, ""):
            return str(value)
    return default
