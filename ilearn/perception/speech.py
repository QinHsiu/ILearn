"""Speech assessment adapter — ASR as perception, not a core Agent."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ilearn.perception.adapter import PerceptionAdapter, PerceptionOutput, SourceType

TranscribeFn = Callable[[str], PerceptionOutput]


class SpeechAssessmentAdapter:
    """Replaceable speech→text adapter for English oral / spoken answers.

    Does not alter the session state machine. PracticeAgent consumes
    ``PerceptionOutput`` via ``grade_perception_outputs``.
    """

    name = "speech"

    def __init__(self, transcribe_fn: TranscribeFn | None = None) -> None:
        self._transcribe_fn = transcribe_fn

    def transcribe(self, audio_path: str) -> PerceptionOutput:
        if self._transcribe_fn is None:
            raise NotImplementedError(
                "SpeechAssessmentAdapter has no ASR backend configured; "
                "pass transcribe_fn=... or install a speech provider adapter."
            )
        path = Path(audio_path)
        if not path.is_file():
            raise FileNotFoundError(f"audio not found: {audio_path}")
        return self._transcribe_fn(str(path))

    def ocr(self, image_path: str) -> PerceptionOutput:
        raise NotImplementedError("SpeechAssessmentAdapter does not perform OCR")

    def extract(self, payload: bytes, *, source_type: SourceType) -> PerceptionOutput:
        if source_type != "speech":
            raise NotImplementedError(f"unsupported source_type={source_type}")
        if self._transcribe_fn is None:
            raise NotImplementedError("SpeechAssessmentAdapter has no ASR backend configured")
        # Treat payload as UTF-8 transcript fixture for offline tests / demos.
        text = payload.decode("utf-8")
        return PerceptionOutput(text=text, source_type="speech", confidence=0.8)
