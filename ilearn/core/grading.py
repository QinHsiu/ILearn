"""Hybrid rule/LLM step grader engine for ILearn.

Public grading entry point: ``ilearn.core.grader.ItemGrader`` (host-owned facade).
"""

from __future__ import annotations

import re
from typing import Any

from ilearn.core.schemas import (
    ERROR_TAGS,
    AssessmentItem,
    AssessmentPaper,
    ErrorTag,
    GradeResult,
    StepResult,
    StudentAnswer,
)
from ilearn.providers.llm import LLMClient, LLMError

_VALID_ERROR_TAGS = set(ERROR_TAGS)
_CHOICE_LETTERS = {"A", "B", "C", "D", "E"}
_FINAL_TOKEN = re.compile(
    r"-?\d+(?:\.\d+)?(?:[/:]-?\d+(?:\.\d+)?)?%?|[A-Za-z]+|[\u4e00-\u9fff]+"
)

_GRADE_SYSTEM_PROMPT = """You are a math tutor grader for elementary students (grades 4-6).
Respond with ONLY a JSON object (no markdown) matching this schema:
{
  "final_correct": boolean,
  "steps": [string],
  "step_results": [{"step_index": int, "step_text": string, "status": "correct"|"incorrect"|"partial", "comment": string}],
  "error_tags": [one or more of: concept_gap, calc_error, misread, method_wrong, incomplete],
  "knowledge_ids": [string],
  "hint_level_suggestion": "none"|"low"|"medium"|"high"
}
Use controlled error_tags only. Align step_results to rubric_steps when provided.
"""

def normalize_answer(text: str) -> str:
    """Normalize whitespace and case for text comparison."""
    return " ".join(text.strip().split()).casefold()


def answers_match(student: str, key: str) -> bool:
    """Compare student answer to key with whitespace/case normalization and numeric tolerance."""
    s_norm = normalize_answer(student)
    k_norm = normalize_answer(key)
    if s_norm == k_norm:
        return True
    try:
        s_val = float(s_norm.replace(",", ""))
        k_val = float(k_norm.replace(",", ""))
        if abs(s_val - k_val) < 1e-9:
            return True
        return abs(s_val - k_val) / max(abs(k_val), 1e-9) < 1e-6
    except ValueError:
        return False


def _offline_constructed_answer_matches(answer: str, key: str) -> bool:
    if answers_match(answer, key):
        return True
    tokens = _FINAL_TOKEN.findall(answer)
    return bool(tokens) and answers_match(tokens[-1], key)


def _heuristic_error_tags(item: AssessmentItem, answer: str, correct: bool) -> list[ErrorTag]:
    if correct:
        return []
    if item.type == "choice":
        if answer.strip().upper() in _CHOICE_LETTERS:
            return ["misread"]
        return ["concept_gap"]
    if item.type == "fill":
        try:
            float(normalize_answer(answer).replace(",", ""))
            return ["calc_error"]
        except ValueError:
            return ["concept_gap"]
    return ["incomplete"]


def _build_step_results(
    item: AssessmentItem, final_correct: bool, answer: str
) -> list[StepResult]:
    if item.rubric_steps:
        status: str = "correct" if final_correct else "incorrect"
        return [
            StepResult(
                step_index=i,
                step_text=step,
                status=status,
                comment="",
            )
            for i, step in enumerate(item.rubric_steps)
        ]
    return [
        StepResult(
            step_index=0,
            step_text=answer.strip() or "(no answer)",
            status="correct" if final_correct else "incorrect",
            comment="",
        )
    ]


def _filter_error_tags(raw: Any) -> list[ErrorTag]:
    if not isinstance(raw, list):
        return []
    return [tag for tag in raw if isinstance(tag, str) and tag in _VALID_ERROR_TAGS]


def _parse_llm_grade(item: AssessmentItem, data: dict[str, Any]) -> GradeResult:
    step_results: list[StepResult] = []
    for entry in data.get("step_results") or []:
        if not isinstance(entry, dict):
            continue
        status = entry.get("status", "incorrect")
        if status not in ("correct", "incorrect", "partial"):
            status = "incorrect"
        step_results.append(
            StepResult(
                step_index=int(entry.get("step_index", 0)),
                step_text=str(entry.get("step_text", "")),
                status=status,
                comment=str(entry.get("comment", "")),
            )
        )

    steps_raw = data.get("steps") or []
    steps = [str(step) for step in steps_raw] if isinstance(steps_raw, list) else []

    hint = data.get("hint_level_suggestion", "none")
    if hint not in ("none", "low", "medium", "high"):
        hint = "none"

    knowledge_ids = data.get("knowledge_ids") or item.knowledge_ids
    if not isinstance(knowledge_ids, list):
        knowledge_ids = list(item.knowledge_ids)

    return GradeResult(
        item_id=item.id,
        final_correct=bool(data.get("final_correct", False)),
        steps=steps,
        step_results=step_results,
        error_tags=_filter_error_tags(data.get("error_tags")),
        knowledge_ids=[str(kid) for kid in knowledge_ids],
        hint_level_suggestion=hint,
        grading_degraded=False,
    )


def _build_user_prompt(
    item: AssessmentItem, answer: str, *, rule_correct: bool | None = None
) -> str:
    parts = [
        f"Item ID: {item.id}",
        f"Type: {item.type}",
        f"Stem: {item.stem}",
        f"Student answer: {answer}",
    ]
    if item.answer_key is not None:
        parts.append(f"Answer key: {item.answer_key}")
    if item.choices:
        parts.append(f"Choices: {item.choices}")
    if item.rubric_steps:
        parts.append(f"Rubric steps: {item.rubric_steps}")
    if item.knowledge_ids:
        parts.append(f"Knowledge IDs: {item.knowledge_ids}")
    if rule_correct is not None:
        parts.append(
            f"Rule check (objective): {'correct' if rule_correct else 'incorrect'}"
        )
    return "\n".join(parts)


class VisionGrader:
    """Thin wrapper: OCR extraction followed by text step grading."""

    def __init__(self, llm: LLMClient | None) -> None:
        from ilearn.core.ocr import OcrExtractor

        self._ocr = OcrExtractor(llm)
        self._grader = StepGrader(llm)

    def grade_image(
        self,
        item: AssessmentItem,
        image_base64: str,
        mime_type: str,
    ) -> GradeResult:
        ocr_result = self._ocr.extract(item, image_base64, mime_type)
        answer_text = "\n".join(ocr_result.steps) if ocr_result.steps else ""
        result = self._grader.grade_item(item, answer_text)
        result.item_id = item.id
        if ocr_result.degraded or ocr_result.confidence < 0.5:
            result.grading_degraded = True
        # Do not clear grading_degraded based on OCR success alone: text grading
        # (e.g. offline fallback or LLM failure) can degrade independently of OCR.
        return result


class StepGrader:
    """Grade assessment items with deterministic rules and optional LLM enrichment."""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm

    def _llm_available(self) -> bool:
        return self._llm is not None and self._llm.available()

    def _grade_with_llm(
        self,
        item: AssessmentItem,
        answer: str,
        *,
        rule_correct: bool | None = None,
        force_incorrect: bool = False,
    ) -> GradeResult | None:
        if not self._llm_available():
            return None
        try:
            prompt = _build_user_prompt(item, answer, rule_correct=rule_correct)
            data = self._llm.chat_json(_GRADE_SYSTEM_PROMPT, prompt)
            result = _parse_llm_grade(item, data)
            result.item_id = item.id
            if force_incorrect:
                result.final_correct = False
            if not result.error_tags and result.final_correct is False:
                result.error_tags = _heuristic_error_tags(item, answer, False)
            return result
        except LLMError:
            return None

    def _degraded_result(
        self, item: AssessmentItem, answer: str, *, final_correct: bool
    ) -> GradeResult:
        return GradeResult(
            item_id=item.id,
            final_correct=final_correct,
            steps=[answer.strip()] if answer.strip() else [],
            step_results=[
                StepResult(
                    step_index=0,
                    step_text=answer.strip() or "(no answer)",
                    status="correct" if final_correct else "incorrect",
                    comment="",
                )
            ],
            error_tags=_heuristic_error_tags(item, answer, final_correct)
            if not final_correct
            else [],
            knowledge_ids=list(item.knowledge_ids),
            grading_degraded=True,
        )

    def grade_item(self, item: AssessmentItem, answer: str) -> GradeResult:
        if item.type in ("choice", "fill") and item.answer_key is not None:
            correct = answers_match(answer, item.answer_key)
            if correct:
                return GradeResult(
                    item_id=item.id,
                    final_correct=True,
                    steps=[answer.strip()],
                    step_results=_build_step_results(item, True, answer),
                    error_tags=[],
                    knowledge_ids=list(item.knowledge_ids),
                    grading_degraded=False,
                )

            llm_result = self._grade_with_llm(
                item, answer, rule_correct=False, force_incorrect=True
            )
            if llm_result is not None:
                return llm_result

            return GradeResult(
                item_id=item.id,
                final_correct=False,
                steps=[answer.strip()],
                step_results=_build_step_results(item, False, answer),
                error_tags=_heuristic_error_tags(item, answer, False),
                knowledge_ids=list(item.knowledge_ids),
                grading_degraded=False,
            )

        llm_result = self._grade_with_llm(item, answer)
        if llm_result is not None:
            return llm_result

        fallback_correct = (
            _offline_constructed_answer_matches(answer, item.answer_key)
            if item.answer_key is not None
            else False
        )
        return self._degraded_result(item, answer, final_correct=fallback_correct)

    def grade_paper(
        self, paper: AssessmentPaper, answers: list[StudentAnswer]
    ) -> list[GradeResult]:
        answer_map = {entry.item_id: entry.answer_text for entry in answers}
        return [
            self.grade_item(item, answer_map.get(item.id, ""))
            for item in paper.items
        ]
