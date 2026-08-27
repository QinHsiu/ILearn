"""Curriculum binding validation and runtime gates for multimodal items."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ilearn.core.knowledge_graph import KnowledgeGraph
from ilearn.core.progress_mapper import ProgressMapper
from ilearn.core.schemas import StudentProfile

REPO_ROOT = Path(__file__).resolve().parents[2]
_BEIJING = "北京"
_RENJIAO = "人教版"


def _grade_key(grade: int) -> str:
    return f"{grade}年级"


class CurriculumGate:
    """Validate curriculum_ref on items and filter banks by profile and progress."""

    def __init__(
        self,
        overrides_path: str | Path | None = None,
        syllabus_path: str | Path | None = None,
        graph: KnowledgeGraph | None = None,
        progress_mapper: ProgressMapper | None = None,
    ) -> None:
        if overrides_path is None:
            overrides_path = REPO_ROOT / "data" / "curriculum" / "chapter_overrides.json"
        if syllabus_path is None:
            syllabus_path = REPO_ROOT / "data" / "pilot" / "syllabus.json"
        self.overrides_path = Path(overrides_path)
        self.syllabus_path = Path(syllabus_path)
        self.overrides = self._load_overrides()
        self.syllabus = self._load_syllabus()
        self.objective_ids = {entry["citation_id"] for entry in self.syllabus}
        self.graph = graph or KnowledgeGraph()
        self.progress_mapper = progress_mapper or ProgressMapper()

    def _load_overrides(self) -> dict[str, Any]:
        with self.overrides_path.open(encoding="utf-8") as handle:
            return json.load(handle)

    def _load_syllabus(self) -> list[dict[str, Any]]:
        with self.syllabus_path.open(encoding="utf-8") as handle:
            return json.load(handle)

    def _find_chapter_block(
        self,
        region: str,
        edition: str,
        grade: int,
        semester: str,
        chapter: str,
    ) -> dict[str, Any] | None:
        chapters = (
            self.overrides.get(region, {})
            .get(edition, {})
            .get(_grade_key(grade), {})
            .get(semester, {})
            .get("chapters", [])
        )
        for block in chapters:
            if block.get("chapter") == chapter:
                return block
        return None

    def validate_item(self, item: dict) -> list[str]:
        """Return validation errors; empty list means the item is valid."""
        errors: list[str] = []
        curriculum_ref = item.get("curriculum_ref")
        if not curriculum_ref:
            errors.append("missing curriculum_ref")
            return errors

        region = curriculum_ref.get("region", "")
        edition = curriculum_ref.get("edition", "")
        grade = curriculum_ref.get("grade")
        semester = curriculum_ref.get("semester", "")
        chapter = curriculum_ref.get("chapter", "")
        weeks = curriculum_ref.get("weeks", [])
        objective_ids = curriculum_ref.get("objective_ids", [])
        item_knowledge_ids = item.get("knowledge_ids", [])

        if grade is None:
            errors.append("missing grade in curriculum_ref")
            return errors

        chapter_block = self._find_chapter_block(region, edition, grade, semester, chapter)
        if chapter_block is None:
            errors.append(f"chapter not found: {chapter}")
            return errors

        chapter_kps = set(chapter_block.get("knowledge_ids", []))
        if not set(item_knowledge_ids) & chapter_kps:
            errors.append("knowledge_ids do not intersect chapter knowledge_ids")

        chapter_weeks = set(chapter_block.get("weeks", []))
        if not set(weeks).issubset(chapter_weeks):
            errors.append("item weeks not subset of chapter weeks")

        if not objective_ids:
            errors.append("missing objective_ids")
        else:
            for oid in objective_ids:
                if oid not in self.objective_ids:
                    errors.append(f"objective_id not in syllabus: {oid}")

        return errors

    def _infer_current_kps(
        self,
        profile: StudentProfile,
        semester: str,
        now: datetime,
        current_kps: list[str] | None,
    ) -> list[str]:
        if current_kps is not None:
            return list(current_kps)
        _, inferred = self.progress_mapper.infer_current_progress(
            profile.region, profile.grade, semester, now
        )
        return list(inferred)

    def _passes_profile_gates(
        self,
        item: dict,
        profile: StudentProfile,
        semester: str,
        current_kps: list[str],
        knowledge_ids: list[str] | None,
    ) -> bool:
        curriculum_ref = item["curriculum_ref"]

        if profile.region != curriculum_ref["region"]:
            return False
        if curriculum_ref.get("edition") != _RENJIAO:
            return False
        if profile.grade != curriculum_ref["grade"]:
            return False
        if curriculum_ref["semester"] != semester:
            return False

        item_kps = set(item.get("knowledge_ids", []))
        progress_kps = set(knowledge_ids) if knowledge_ids else set(current_kps)
        if not item_kps & progress_kps:
            return False

        allowed_kps = set(current_kps)
        if knowledge_ids:
            allowed_kps |= set(knowledge_ids)

        for kp in item_kps:
            for prereq in self.graph.get_prerequisites(kp):
                if prereq not in allowed_kps:
                    return False

        return True

    def eligible_for_profile(
        self,
        item: dict,
        profile: StudentProfile,
        *,
        semester: str,
        now: datetime,
        current_kps: list[str] | None = None,
    ) -> bool:
        """Version, grade, semester, progress, and prerequisite gate."""
        if self.validate_item(item):
            return False

        inferred = self._infer_current_kps(profile, semester, now, current_kps)
        return self._passes_profile_gates(item, profile, semester, inferred, None)

    def filter_bank(
        self,
        bank: list[dict],
        profile: StudentProfile,
        *,
        semester: str,
        now: datetime,
        knowledge_ids: list[str] | None = None,
    ) -> list[dict]:
        """Return bank items safe to show for the profile now."""
        current_kps = self._infer_current_kps(profile, semester, now, None)
        eligible: list[dict] = []
        for item in bank:
            if self.validate_item(item):
                continue
            if self._passes_profile_gates(
                item, profile, semester, current_kps, knowledge_ids
            ):
                eligible.append(item)
        return eligible
