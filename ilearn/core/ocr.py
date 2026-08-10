"""Vision OCR extraction — image to structured steps only (OPT-011)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ilearn.core.schemas import AssessmentItem
from ilearn.providers.llm import LLMClient, LLMError

_OCR_SYSTEM_PROMPT = """Extract handwritten math steps from the image.
Respond with ONLY a JSON object (no markdown) matching this schema:
{
  "pages": [{"page_index": int, "text": string}],
  "steps": [string],
  "confidence": float
}
List each distinct solution step in order. confidence is 0.0-1.0 for extraction quality.
"""


class OcrPage(BaseModel):
    page_index: int = Field(ge=0, default=0)
    text: str = ""


class OcrResult(BaseModel):
    pages: list[OcrPage] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    degraded: bool = False


class OcrExtractor:
    """Extract structured math steps from handwritten images via vision LLM."""

    def __init__(self, llm: LLMClient | None) -> None:
        self._llm = llm

    @staticmethod
    def _degraded_result(_item: AssessmentItem) -> OcrResult:
        return OcrResult(
            pages=[],
            steps=["（离线模式：无法识别手写图片）"],
            confidence=0.0,
            degraded=True,
        )

    @staticmethod
    def _build_user_prompt(item: AssessmentItem) -> str:
        parts = [
            f"Item ID: {item.id}",
            f"Stem: {item.stem}",
        ]
        if item.rubric_steps:
            parts.append(f"Expected rubric steps: {item.rubric_steps}")
        return "\n".join(parts)

    @staticmethod
    def _parse_ocr_data(data: dict[str, Any]) -> OcrResult:
        pages: list[OcrPage] = []
        for entry in data.get("pages") or []:
            if isinstance(entry, dict):
                pages.append(
                    OcrPage(
                        page_index=int(entry.get("page_index", 0)),
                        text=str(entry.get("text", "")),
                    )
                )
        steps_raw = data.get("steps") or []
        steps = [str(step) for step in steps_raw] if isinstance(steps_raw, list) else []
        confidence = float(data.get("confidence", 1.0))
        confidence = max(0.0, min(1.0, confidence))
        return OcrResult(pages=pages, steps=steps, confidence=confidence, degraded=False)

    def extract(
        self,
        item: AssessmentItem,
        image_base64: str,
        mime_type: str,
    ) -> OcrResult:
        if self._llm is None or not self._llm.vision_available():
            return self._degraded_result(item)

        try:
            data = self._llm.grade_image_json(
                _OCR_SYSTEM_PROMPT,
                image_base64,
                mime_type,
                self._build_user_prompt(item),
            )
            return self._parse_ocr_data(data)
        except LLMError:
            return self._degraded_result(item)
