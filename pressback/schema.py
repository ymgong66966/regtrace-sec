from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


Role = Literal["analyst", "executive", "operator", "unknown"]


@dataclass(frozen=True)
class TranscriptTurn:
    transcript_id: str
    turn_index: int
    speaker: str
    role: Role
    text: str
    ticker: str | None = None
    date: str | None = None
    company: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Transcript:
    transcript_id: str
    turns: list[TranscriptTurn]
    ticker: str | None = None
    date: str | None = None
    company: str | None = None


@dataclass(frozen=True)
class PressBackThread:
    transcript_id: str
    question_turn_index: int
    answer_end_turn_index: int
    analyst: str
    executive_speakers: list[str]
    question: str
    answer: str
    press_back: bool
    tier: Literal["none", "same_analyst", "cross_analyst"]
    follow_up_turn_index: int | None = None
    follow_up_analyst: str | None = None
    follow_up_text: str | None = None
    topic_score: float | None = None
    ticker: str | None = None
    date: str | None = None
    company: str | None = None

    @property
    def label(self) -> str:
        return "non_responsive" if self.press_back else "responsive"

    def to_json(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["label"] = self.label
        return payload

