from __future__ import annotations

from abc import ABC, abstractmethod

from ilearn.providers.curriculum import CurriculumProvider, PILOT_GRADES

_REGION_ALIASES = {
    "北京": "北京",
    "beijing": "北京",
    "上海": "上海",
    "shanghai": "上海",
}


def normalize_region(region: str) -> str | None:
    key = (region or "").strip().casefold()
    raw = (region or "").strip()
    if raw in _REGION_ALIASES:
        return _REGION_ALIASES[raw]
    if key in _REGION_ALIASES:
        return _REGION_ALIASES[key]
    return None


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

    @abstractmethod
    def get_supported_regions(self) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def get_curriculum(self, grade: int, region: str) -> dict[str, object]:
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

    def get_supported_regions(self) -> list[str]:
        return ["北京", "上海"]

    def get_curriculum(self, grade: int, region: str) -> dict[str, object]:
        canonical = normalize_region(region)
        if canonical is None:
            return {
                "status": "unsupported",
                "message": "当前仅支持北京或上海地区课标，请切换地区后重试。",
            }
        if grade not in PILOT_GRADES:
            return {
                "status": "unsupported",
                "message": f"试点内容目前覆盖 4–6 年级数学，暂不支持 {grade} 年级",
            }
        return {
            "status": "ok",
            "label": self._curriculum.label,
            "grade": grade,
            "region": canonical,
        }


def get_adapter(subject: str, curriculum: CurriculumProvider) -> SubjectAdapter:
    key = (subject or "").strip().casefold()
    if key == "math":
        return MathSubjectAdapter(curriculum)
    raise ValueError(f"unsupported subject: {subject}")
