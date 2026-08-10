"""MathTutorBench-style offline eval tasks (mistake location, step metrics)."""

from __future__ import annotations

import json
import re
from fractions import Fraction
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ilearn.core.grading import StepGrader, answers_match, normalize_answer
from ilearn.core.schemas import AssessmentItem
from ilearn.providers.llm import LLMClient

__all__ = [
    "MistakeCorrectionFixture",
    "MistakeLocationFixture",
    "ScaffoldingFixture",
    "run_mistake_correction_benchmark",
    "run_mistake_location_benchmark",
    "run_scaffolding_benchmark",
]

_FRACTION = re.compile(r"(-?\d+)\s*/\s*(-?\d+)")
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


class MistakeLocationFixture(BaseModel):
    id: str
    stem: str
    answer_key: str
    rubric_steps: list[str] = Field(default_factory=list)
    student_steps: list[str] = Field(default_factory=list)
    gold_first_error_step: int | None = None


class MistakeCorrectionFixture(BaseModel):
    id: str
    stem: str
    wrong_answer: str
    gold_correction: str
    rubric_steps: list[str] = Field(default_factory=list)


class ScaffoldingFixture(BaseModel):
    id: str
    stem: str
    error_tag: str
    gold_hint_level: str


_DEFAULT_HINT: dict[str, str] = {
    "concept_gap": "medium",
    "calc_error": "low",
    "misread": "low",
    "method_wrong": "high",
    "incomplete": "medium",
}


def load_mistake_location_fixtures(path: Path) -> list[MistakeLocationFixture]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("fixtures file must contain a JSON array")
    return [MistakeLocationFixture.model_validate(entry) for entry in raw]


def load_mistake_correction_fixtures(path: Path) -> list[MistakeCorrectionFixture]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("fixtures file must contain a JSON array")
    return [MistakeCorrectionFixture.model_validate(entry) for entry in raw]


def load_scaffolding_fixtures(path: Path) -> list[ScaffoldingFixture]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("fixtures file must contain a JSON array")
    return [ScaffoldingFixture.model_validate(entry) for entry in raw]


def propose_correction(wrong: str, answer_key: str) -> str:
    return answer_key if not answers_match(wrong, answer_key) else wrong


def score_mistake_correction(fixture: MistakeCorrectionFixture) -> bool:
    return answers_match(
        propose_correction(fixture.wrong_answer, fixture.gold_correction),
        fixture.gold_correction,
    )


def suggest_hint_level(error_tag: str) -> str:
    return _DEFAULT_HINT.get(error_tag, "medium")


def score_scaffolding(fixture: ScaffoldingFixture) -> bool:
    return suggest_hint_level(fixture.error_tag) == fixture.gold_hint_level


def _parse_numeric(text: str) -> float | None:
    text = text.strip()
    frac = _FRACTION.search(text)
    if frac:
        try:
            return float(Fraction(int(frac.group(1)), int(frac.group(2))))
        except ZeroDivisionError:
            return None
    nums = _FRACTION.sub("", text)
    matches = _NUMBER.findall(nums)
    if not matches:
        return None
    try:
        return float(matches[-1].replace(",", ""))
    except ValueError:
        return None


def _step_correct(
    rubric_label: str,
    student_text: str,
    *,
    answer_key: str,
    step_index: int,
) -> bool:
    text = student_text.strip()
    if not text:
        return False
    label = rubric_label.strip()
    if label == "列式":
        return bool(re.search(r"[\d+\-×÷*/=]", text)) or bool(_NUMBER.search(text))
    if label in {"计算", "写答"}:
        student_val = _parse_numeric(text)
        key_val = _parse_numeric(answer_key)
        if student_val is not None and key_val is not None:
            return abs(student_val - key_val) < 1e-6
        return answers_match(text, answer_key)
    if step_index >= 2:
        student_val = _parse_numeric(text)
        key_val = _parse_numeric(answer_key)
        if student_val is not None and key_val is not None:
            return abs(student_val - key_val) < 1e-6
    return bool(text)


def detect_first_error_step(
    fixture: MistakeLocationFixture,
    *,
    grader: StepGrader | None = None,
) -> int | None:
    """Return 1-based index of first incorrect rubric step, or None if all correct."""
    if grader is not None and grader._llm_available():
        item = AssessmentItem(
            id=fixture.id,
            stem=fixture.stem,
            type="constructed",
            difficulty="easy",
            knowledge_ids=["eval"],
            answer_key=fixture.answer_key,
            rubric_steps=fixture.rubric_steps,
        )
        answer_text = "\n".join(fixture.student_steps)
        result = grader.grade_item(item, answer_text)
        for step in result.step_results:
            if step.status != "correct":
                return step.step_index + 1
        return None if result.final_correct else 1

    for index, rubric_label in enumerate(fixture.rubric_steps):
        student_text = (
            fixture.student_steps[index]
            if index < len(fixture.student_steps)
            else ""
        )
        if not _step_correct(
            rubric_label,
            student_text,
            answer_key=fixture.answer_key,
            step_index=index,
        ):
            return index + 1
    return None


def _step_labels(fixture: MistakeLocationFixture) -> list[bool]:
    """Per-step correctness flags aligned to rubric_steps."""
    return [
        _step_correct(
            label,
            fixture.student_steps[i] if i < len(fixture.student_steps) else "",
            answer_key=fixture.answer_key,
            step_index=i,
        )
        for i, label in enumerate(fixture.rubric_steps)
    ]


def _step_f1(expected: list[bool], predicted: list[bool]) -> float:
    if not expected:
        return 0.0
    tp = sum(e and p for e, p in zip(expected, predicted, strict=True))
    fp = sum(not e and p for e, p in zip(expected, predicted, strict=True))
    fn = sum(e and not p for e, p in zip(expected, predicted, strict=True))
    if tp == 0:
        return 0.0 if (fp or fn) else 1.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def run_mistake_location_benchmark(
    fixtures_path: Path,
    *,
    llm: LLMClient | None = None,
) -> dict[str, Any]:
    """Run mistake-location fixtures and return aggregate metrics."""
    fixtures = load_mistake_location_fixtures(fixtures_path)
    if not fixtures:
        return {"total": 0, "step_f1": 0.0, "first_error_acc": 0.0}

    grader = StepGrader(llm)
    first_error_hits = 0
    first_error_total = 0
    step_f1_scores: list[float] = []

    for fixture in fixtures:
        predicted = detect_first_error_step(fixture, grader=grader)
        expected = fixture.gold_first_error_step
        if expected is not None:
            first_error_total += 1
            if predicted == expected:
                first_error_hits += 1
        elif predicted is None:
            first_error_hits += 1
            first_error_total += 1

        expected_flags = _step_labels(fixture)
        predicted_flags = [
            _step_correct(
                label,
                fixture.student_steps[i] if i < len(fixture.student_steps) else "",
                answer_key=fixture.answer_key,
                step_index=i,
            )
            for i, label in enumerate(fixture.rubric_steps)
        ]
        step_f1_scores.append(_step_f1(expected_flags, predicted_flags))

    return {
        "total": len(fixtures),
        "step_f1": sum(step_f1_scores) / len(step_f1_scores),
        "first_error_acc": first_error_hits / first_error_total if first_error_total else 0.0,
    }


def run_mistake_correction_benchmark(
    fixtures_path: Path,
    *,
    llm: LLMClient | None = None,
) -> dict[str, Any]:
    """Run mistake-correction fixtures and return aggregate metrics."""
    del llm  # offline-only for Phase 1
    fixtures = load_mistake_correction_fixtures(fixtures_path)
    if not fixtures:
        return {"total": 0, "correction_acc": 0.0}
    hits = sum(score_mistake_correction(fixture) for fixture in fixtures)
    return {
        "total": len(fixtures),
        "correction_acc": hits / len(fixtures),
    }


def run_scaffolding_benchmark(
    fixtures_path: Path,
    *,
    llm: LLMClient | None = None,
) -> dict[str, Any]:
    """Run scaffolding hint-level fixtures and return aggregate metrics."""
    del llm  # offline-only for Phase 1
    fixtures = load_scaffolding_fixtures(fixtures_path)
    if not fixtures:
        return {"total": 0, "hint_level_match": 0.0}
    hits = sum(score_scaffolding(fixture) for fixture in fixtures)
    return {
        "total": len(fixtures),
        "hint_level_match": hits / len(fixtures),
    }
