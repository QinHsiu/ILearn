"""Learning-situation diagnosis from graded assessment results."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path

from ilearn.core.schemas import (
    AssessmentPaper,
    DiagnosisReport,
    GradeResult,
    Intervention,
    KnowledgeMastery,
    LearnerPortrait,
    MasteryLevel,
    StudentProfile,
    WeaknessEntry,
)
from ilearn.providers.curriculum import CurriculumProvider, PilotBeijingRenjiaoProvider

_ERROR_FIX_HINTS: dict[str, str] = {
    "concept_gap": "概念理解",
    "calc_error": "计算准确性",
    "misread": "审题与读题",
    "method_wrong": "解题方法",
    "incomplete": "步骤完整性",
}

_ERROR_TAG_LABELS: dict[str, str] = {
    "concept_gap": "概念缺口",
    "calc_error": "计算错误",
    "misread": "审题失误",
    "method_wrong": "方法不当",
    "incomplete": "步骤不完整",
}


def _default_pilot_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "pilot"


def _is_beijing_region(region: str) -> bool:
    normalized = region.strip().casefold()
    return normalized in ("北京", "beijing")


def _mastery_level(score_rate: float) -> MasteryLevel:
    if score_rate >= 0.8:
        return "mastered"
    if score_rate >= 0.5:
        return "unstable"
    return "weak"


def _dominant_error_tag(counts: dict[str, int]) -> str | None:
    if not counts:
        return None
    return max(counts.items(), key=lambda pair: pair[1])[0]


def _error_penalty(error_tags: list[str]) -> float:
    return min(30.0, len(error_tags) * 5.0)


class Diagnoser:
    """Aggregate knowledge mastery, abilities, and Top-5 interventions."""

    def __init__(self, curriculum: CurriculumProvider | None = None) -> None:
        self._curriculum = curriculum or PilotBeijingRenjiaoProvider(_default_pilot_dir())

    def diagnose(
        self,
        profile: StudentProfile,
        paper: AssessmentPaper,
        grades: list[GradeResult],
    ) -> DiagnosisReport:
        grade_by_id = {grade.item_id: grade for grade in grades}
        knowledge_by_id = {
            node.id: node for node in self._curriculum.list_knowledge(profile.grade)
        }

        item_records: dict[str, list[tuple[str, GradeResult]]] = defaultdict(list)
        for item in paper.items:
            grade = grade_by_id.get(item.id)
            if grade is None:
                continue
            for knowledge_id in item.knowledge_ids:
                item_records[knowledge_id].append((item.id, grade))

        knowledge_mastery: list[KnowledgeMastery] = []
        for knowledge_id, records in sorted(item_records.items()):
            item_ids = [item_id for item_id, _ in records]
            grade_rows = [grade for _, grade in records]
            correct = sum(1 for grade in grade_rows if grade.final_correct)
            score_rate = correct / len(grade_rows)
            error_tag_counts: dict[str, int] = defaultdict(int)
            for grade in grade_rows:
                for tag in grade.error_tags:
                    error_tag_counts[tag] += 1
            knowledge_mastery.append(
                KnowledgeMastery(
                    knowledge_id=knowledge_id,
                    knowledge_name=(
                        knowledge_by_id[knowledge_id].name
                        if knowledge_id in knowledge_by_id
                        else knowledge_id
                    ),
                    score_rate=score_rate,
                    error_tag_counts=dict(error_tag_counts),
                    level=_mastery_level(score_rate),
                    item_ids=item_ids,
                )
            )

        interventions = self._build_interventions(knowledge_mastery, knowledge_by_id)
        ability_scores = self._compute_ability_scores(
            paper, grade_by_id, knowledge_by_id
        )

        region_mismatch: str | None = None
        if not _is_beijing_region(profile.region):
            region_mismatch = (
                f"当前测评使用的是{paper.curriculum_label}试点课标，"
                f"与您填写的地区（{profile.region}）可能不完全匹配，结果仅供参考。"
            )

        return DiagnosisReport(
            knowledge_mastery=knowledge_mastery,
            interventions=interventions,
            ability_scores=ability_scores,
            curriculum_label=paper.curriculum_label,
            region_mismatch_disclaimer=region_mismatch,
        )

    def _build_interventions(
        self,
        knowledge_mastery: list[KnowledgeMastery],
        knowledge_by_id: dict[str, object],
    ) -> list[Intervention]:
        candidates = sorted(
            (km for km in knowledge_mastery if km.level != "mastered"),
            key=lambda km: (km.score_rate, km.knowledge_id),
        )[:5]

        interventions: list[Intervention] = []
        for priority, km in enumerate(candidates, start=1):
            node = knowledge_by_id.get(km.knowledge_id)
            title = node.name if node is not None else km.knowledge_id
            dominant = _dominant_error_tag(km.error_tag_counts)
            fix_first = (
                _ERROR_FIX_HINTS.get(dominant, "基础巩固")
                if dominant
                else "基础巩固"
            )
            if dominant and dominant in _ERROR_TAG_LABELS:
                why = (
                    f"得分率 {km.score_rate:.0%}，主要问题："
                    f"{_ERROR_TAG_LABELS[dominant]}"
                )
            else:
                why = f"得分率 {km.score_rate:.0%}，需要加强练习"
            interventions.append(
                Intervention(
                    knowledge_id=km.knowledge_id,
                    title=title,
                    why=why,
                    what_to_fix_first=fix_first,
                    priority=priority,
                )
            )
        return interventions

    def _compute_ability_scores(
        self,
        paper: AssessmentPaper,
        grade_by_id: dict[str, GradeResult],
        knowledge_by_id: dict[str, object],
    ) -> dict[str, float]:
        tag_grades: dict[str, list[GradeResult]] = defaultdict(list)
        for item in paper.items:
            grade = grade_by_id.get(item.id)
            if grade is None:
                continue
            tags: set[str] = set()
            for knowledge_id in item.knowledge_ids:
                node = knowledge_by_id.get(knowledge_id)
                if node is not None:
                    tags.update(node.ability_tags)
            for tag in tags:
                tag_grades[tag].append(grade)

        ability_scores: dict[str, float] = {}
        for tag, grades in sorted(tag_grades.items()):
            correct_rate = sum(1 for grade in grades if grade.final_correct) / len(
                grades
            )
            penalty = sum(
                _error_penalty(list(grade.error_tags)) for grade in grades
            ) / len(grades)
            ability_scores[tag] = round(
                max(0.0, min(100.0, correct_rate * 100.0 - penalty)), 1
            )
        return ability_scores


def _knowledge_name(
    curriculum: CurriculumProvider,
    knowledge_id: str,
    grade: int | None = None,
) -> str:
    grades = [grade] if grade is not None else (4, 5, 6)
    for lookup_grade in grades:
        for node in curriculum.list_knowledge(lookup_grade):
            if node.id == knowledge_id:
                return node.name
    return knowledge_id


class PortraitUpdater:
    """Append weakness entries and decay knowledge state from incorrect grades."""

    @staticmethod
    def update(
        portrait: LearnerPortrait,
        grades: list[GradeResult],
        session_id: str,
        curriculum: CurriculumProvider,
        grade: int | None = None,
    ) -> LearnerPortrait:
        for grade_row in grades:
            if grade_row.final_correct:
                continue
            for kid in grade_row.knowledge_ids:
                portrait.weakness_log.append(
                    WeaknessEntry(
                        knowledge_id=kid,
                        topic=_knowledge_name(curriculum, kid, grade),
                        logic_gap=(
                            grade_row.error_tags[0]
                            if grade_row.error_tags
                            else "unknown"
                        ),
                        session_id=session_id,
                    )
                )
                portrait.knowledge_state[kid] = min(
                    portrait.knowledge_state.get(kid, 1.0), 0.4
                )
        portrait.updated_at = datetime.utcnow()
        return portrait
