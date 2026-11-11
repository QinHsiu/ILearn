"""Perception adapters (ASR / OCR) — separate from teaching execution."""

from ilearn.perception.adapter import PerceptionAdapter, PerceptionOutput, TextPerceptionAdapter
from ilearn.perception.speech import SpeechAssessmentAdapter

__all__ = [
    "PerceptionAdapter",
    "PerceptionOutput",
    "SpeechAssessmentAdapter",
    "TextPerceptionAdapter",
]
