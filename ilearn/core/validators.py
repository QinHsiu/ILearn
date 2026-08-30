"""Request payload validation helpers."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
_XSS_RE = re.compile(r"<script|javascript:|onclick=", re.IGNORECASE)


class QuestionSubmission(BaseModel):
    """Single question answer submission checks."""

    question_id: str = Field(..., min_length=1, max_length=80)
    answer: str = Field(..., max_length=1000)
    time_spent: float = Field(default=0.0, ge=0, le=3600)
    hint_used: bool = False
    hint_count: int = Field(default=0, ge=0, le=5)

    @field_validator("question_id")
    @classmethod
    def validate_question_id(cls, value: str) -> str:
        if not _ID_RE.match(value):
            raise ValueError("question_id must be alphanumeric")
        return value

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, value: str) -> str:
        if _XSS_RE.search(value):
            raise ValueError("invalid characters in answer")
        return value


class StudentProfileUpdate(BaseModel):
    """Optional student profile patch validation."""

    nickname: str | None = Field(default=None, min_length=1, max_length=20)
    grade: int | None = Field(default=None, ge=1, le=12)
    region: str | None = Field(default=None, min_length=2, max_length=20)
    interests: list[str] = Field(default_factory=list)

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, value: str | None) -> str | None:
        if value and re.search(r'[<>"/]', value):
            raise ValueError("nickname contains invalid characters")
        return value


def validate_submit_answers(answers: dict[str, Any]) -> dict[str, str]:
    """Validate a submit map; empty answers are allowed for API compatibility."""
    cleaned: dict[str, str] = {}
    for question_id, answer in answers.items():
        text = "" if answer is None else str(answer)
        item = QuestionSubmission(question_id=str(question_id), answer=text)
        cleaned[item.question_id] = item.answer
    return cleaned
