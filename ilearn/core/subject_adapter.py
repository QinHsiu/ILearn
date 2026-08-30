from __future__ import annotations

from abc import ABC, abstractmethod

from ilearn.providers.curriculum import CurriculumProvider, PILOT_GRADES


class SubjectAdapter(ABC):
    @abstractmethod
    def get_grade_range(self) -> tuple[int, int]:
        raise NotImplementedError

    @abstractmethod
    def supports(self, grade: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def curriculum(self) -> CurriculumProvider:
        raise NotImplementedError


class MathSubjectAdapter(SubjectAdapter):
    def __init__(self, curriculum: CurriculumProvider) -> None:
        self._curriculum = curriculum

    def get_grade_range(self) -> tuple[int, int]:
        return (4, 6)

    def supports(self, grade: int) -> bool:
        return grade in PILOT_GRADES

    def curriculum(self) -> CurriculumProvider:
        return self._curriculum


def get_adapter(subject: str, curriculum: CurriculumProvider) -> SubjectAdapter:
    key = (subject or "").strip().casefold()
    if key == "math":
        return MathSubjectAdapter(curriculum)
    raise ValueError(f"unsupported subject: {subject}")
