"""Infer curriculum progress from grade, semester, and calendar week."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

# Prefer English structural key; accept legacy Chinese key if present.
_CHAPTERS_KEYS = ("chapters", "\u7ae0\u8282\u8fdb\u5ea6")  # chapters / 章节进度

_FALL = "\u4e0a\u5b66\u671f"  # 上学期
_SPRING = "\u4e0b\u5b66\u671f"  # 下学期
_BEIJING = "\u5317\u4eac"
_RENJIAO = "\u4eba\u6559\u7248"


def infer_semester(current_date: datetime) -> str:
    """Mar–Aug → 下学期; Sep–Feb → 上学期."""
    return _SPRING if 3 <= current_date.month <= 8 else _FALL


def _grade_key(grade: int) -> str:
    return f"{grade}\u5e74\u7ea7"  # N年级


def _default_mapping() -> dict[str, Any]:
    """Minimal embedded fallback (Beijing · Renjiao · grades 4–6)."""
    return {
        _BEIJING: {
            _RENJIAO: {
                _grade_key(4): {
                    _FALL: {
                        "chapters": [
                            {
                                "chapter": "mult_3digit",
                                "weeks": list(range(1, 21)),
                                "knowledge_ids": ["mult_3digit"],
                            }
                        ]
                    },
                    _SPRING: {
                        "chapters": [
                            {
                                "chapter": "rect_area",
                                "weeks": list(range(1, 21)),
                                "knowledge_ids": ["rect_area", "parallel_perp"],
                            }
                        ]
                    },
                },
                _grade_key(5): {
                    _FALL: {
                        "chapters": [
                            {
                                "chapter": "dec_mult",
                                "weeks": list(range(1, 21)),
                                "knowledge_ids": ["dec_mult", "simple_eq"],
                            }
                        ]
                    },
                    _SPRING: {
                        "chapters": [
                            {
                                "chapter": "frac_add_same",
                                "weeks": list(range(1, 7)),
                                "knowledge_ids": ["frac_add_same"],
                            },
                            {
                                "chapter": "frac_mult",
                                "weeks": list(range(7, 14)),
                                "knowledge_ids": ["frac_mult"],
                            },
                            {
                                "chapter": "simple_eq",
                                "weeks": list(range(14, 21)),
                                "knowledge_ids": ["simple_eq"],
                            },
                        ]
                    },
                },
                _grade_key(6): {
                    _FALL: {
                        "chapters": [
                            {
                                "chapter": "frac_div",
                                "weeks": list(range(1, 21)),
                                "knowledge_ids": ["frac_div", "ratio"],
                            }
                        ]
                    },
                    _SPRING: {
                        "chapters": [
                            {
                                "chapter": "percent",
                                "weeks": list(range(1, 21)),
                                "knowledge_ids": ["percent", "factors"],
                            }
                        ]
                    },
                },
            }
        }
    }


class ProgressMapper:
    """Map region/grade/semester/date to chapter and knowledge ids."""

    def __init__(self, data_path: str | Path | None = None) -> None:
        if data_path is None:
            root = Path(__file__).resolve().parents[2]
            data_path = root / "data" / "curriculum" / "progress_mapping.json"
        self.data_path = Path(data_path)
        self.mapping = self._load_mapping()

    def _load_mapping(self) -> dict[str, Any]:
        if self.data_path.exists():
            with self.data_path.open(encoding="utf-8") as handle:
                return json.load(handle)
        return _default_mapping()

    @staticmethod
    def _chapters(semester_data: dict[str, Any]) -> list[dict[str, Any]]:
        for key in _CHAPTERS_KEYS:
            chapters = semester_data.get(key)
            if isinstance(chapters, list):
                return chapters
        return []

    def infer_current_progress(
        self,
        region: str,
        grade: int,
        semester: str,
        current_date: datetime,
    ) -> tuple[str, list[str]]:
        """Return (chapter name, knowledge_ids) for the inferred week."""
        start_month = 3 if semester == _SPRING else 9
        year = current_date.year
        if semester == _FALL and current_date.month < 9:
            year -= 1
        start_date = datetime(year, start_month, 1)
        week_number = (current_date - start_date).days // 7 + 1

        semester_data = (
            self.mapping.get(region, {})
            .get(_RENJIAO, {})
            .get(_grade_key(grade), {})
            .get(semester, {})
        )
        chapters = self._chapters(semester_data)

        current_chapter: str | None = None
        current_knowledge_points: list[str] = []
        for chapter in chapters:
            if week_number in chapter.get("weeks", []):
                current_chapter = chapter["chapter"]
                current_knowledge_points = list(chapter.get("knowledge_ids", []))
                break

        if not current_chapter and chapters:
            current_chapter = chapters[0]["chapter"]
            current_knowledge_points = list(chapters[0].get("knowledge_ids", []))

        return current_chapter or "", current_knowledge_points
