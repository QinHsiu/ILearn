"""Perception access layer: speech/handwriting as adapters, not core agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable


SourceType = Literal["text", "speech", "image"]


@dataclass(frozen=True)
class PerceptionOutput:
    text: str
    source_type: SourceType
    confidence: float = 1.0
    raw_ref: str | None = None


@runtime_checkable
class PerceptionAdapter(Protocol):
    name: str

    def transcribe(self, audio_path: str) -> PerceptionOutput: ...

    def ocr(self, image_path: str) -> PerceptionOutput: ...

    def extract(self, payload: bytes, *, source_type: SourceType) -> PerceptionOutput: ...


class TextPerceptionAdapter:
    """Passthrough adapter for existing text answers."""

    name = "text"

    def transcribe(self, audio_path: str) -> PerceptionOutput:
        raise NotImplementedError("TextPerceptionAdapter has no ASR backend")

    def ocr(self, image_path: str) -> PerceptionOutput:
        raise NotImplementedError("TextPerceptionAdapter has no OCR backend")

    def extract(self, payload: bytes, *, source_type: SourceType) -> PerceptionOutput:
        if source_type != "text":
            raise NotImplementedError(f"unsupported source_type={source_type}")
        return PerceptionOutput(
            text=payload.decode("utf-8"),
            source_type="text",
            confidence=1.0,
        )
