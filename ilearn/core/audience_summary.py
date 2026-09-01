"""Audience-friendly summaries for parents and teachers."""

from __future__ import annotations

import math
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel

from ilearn.core.effectiveness import compute_metrics
from ilearn.core.schemas import DiagnosisReport, SessionState

Audience = Literal["parent", "teacher"]

_ERROR_LABELS: dict[str, str] = {
    "concept_gap": "概念理解不清",
    "calc_error": "计算过程易错",
    "misread": "审题不够仔细",
    "method_wrong": "解题方法选择不当",
    "incomplete": "解题步骤不完整",
}


def generate_audience_summary(
    diagnosis: DiagnosisReport | None,
    enrichment: dict[str, Any] | None = None,
    *,
    audience: Audience = "parent",
) -> str:
    """Turn diagnosis/enrichment into actionable Chinese advice."""
    enrichment = enrichment or {}
    weak = list(enrichment.get("weak_skills") or [])
    if diagnosis is not None and not weak:
        weak = [
            row.knowledge_id
            for row in diagnosis.knowledge_mastery
            if row.level == "weak"
        ]
    attribution = enrichment.get("error_attribution") or {}
    top_errors = list(attribution.get("top_tags") or [])

    if not weak and not top_errors:
        if audience == "teacher":
            return "本轮测评未发现明显薄弱点，可安排拓展题或提高题巩固学习动机。"
        return "孩子目前掌握得不错，可以适当挑战更高难度的内容。"

    lines: list[str] = []
    if audience == "parent":
        lines.append("给家长的行动建议：")
        for skill in weak[:3]:
            lines.append(f"• 在「{skill}」上，建议每天花约5分钟完成2道专项练习。")
        if top_errors:
            labels = "、".join(_ERROR_LABELS.get(t, t) for t in top_errors[:3])
            lines.append(f"• 近期主要失分倾向：{labels}。练习时请先让孩子口述思路再动笔。")
        gaps = list(enrichment.get("prerequisite_gaps") or [])
        if gaps:
            lines.append(
                "• 建议先复习前置内容：" + "、".join(gaps[:3]) + "，再继续当前单元。"
            )
    else:
        lines.append("给教师的课堂建议：")
        for skill in weak[:5]:
            lines.append(f"• 关注「{skill}」：可用变式题做形成性抽查。")
        if top_errors:
            labels = "、".join(_ERROR_LABELS.get(t, t) for t in top_errors[:3])
            lines.append(f"• 班级/个例错误类型集中在：{labels}，可设计对应纠错微课。")
        if enrichment.get("learning_advice"):
            lines.append(f"• 系统建议：{enrichment['learning_advice']}")
    return "\n".join(lines)


def aggregate_error_attribution(grades: list[Any] | None) -> dict[str, Any]:
    """Aggregate existing GradeResult.error_tags into enrichment-friendly stats."""
    counts: dict[str, int] = {}
    if not grades:
        return {"counts": {}, "top_tags": [], "wrong_count": 0}
    wrong = 0
    for grade in grades:
        if getattr(grade, "final_correct", True):
            continue
        wrong += 1
        tags = list(getattr(grade, "error_tags", None) or [])
        if not tags:
            counts["unknown"] = counts.get("unknown", 0) + 1
            continue
        for tag in tags:
            key = str(tag)
            counts[key] = counts.get(key, 0) + 1
    top = sorted(counts.keys(), key=lambda k: (-counts[k], k))
    return {"counts": counts, "top_tags": top[:5], "wrong_count": wrong}


class WeaknessStat(BaseModel):
    skill: str
    affected_students: int


class InterventionStudent(BaseModel):
    name: str
    weakness: str
    session_id: str


class TeacherSummary(BaseModel):
    class_name: str
    student_count: int
    avg_mastery: float
    top_weaknesses: list[WeaknessStat]
    need_intervention_students: list[InterventionStudent]
    auto_graded_rate: float
    estimated_time_saved_minutes: float
    narrative: str


class ParentSummary(BaseModel):
    child_name: str
    current_mastery: float  # 0..1
    mastery_change: float  # fraction, e.g. 0.18
    weak_skills: list[str]
    learning_phase: str
    daily_practice_tips: list[str]
    next_milestone: str
    narrative: str


def build_teacher_summary(session: SessionState) -> TeacherSummary:
    demo = bool(session.metadata.get("demo_unit"))
    class_data = session.metadata.get("demo_class_data") or {}
    if not isinstance(class_data, dict):
        class_data = {}
    enrichment = _enrichment(session)
    metrics = compute_metrics(session)

    class_name = "demo_class_5a" if demo else "当前班级"
    student_count = int(class_data.get("class_size") or 1)
    if class_data:
        avg_mastery = float(class_data.get("avg_mastery") or 0.0)
    else:
        rows = (
            list(session.diagnosis.knowledge_mastery) if session.diagnosis is not None else []
        )
        avg_mastery = (
            sum(row.score_rate for row in rows) / len(rows) if rows else 0.0
        )

    common = list(class_data.get("common_weaknesses") or [])
    if common:
        affected = max(1, math.ceil(student_count * 0.3))
        top_weaknesses = [
            WeaknessStat(skill=str(skill), affected_students=affected) for skill in common
        ]
    else:
        weak_rows = [
            row
            for row in (
                session.diagnosis.knowledge_mastery if session.diagnosis is not None else []
            )
            if row.level == "weak"
        ][:3]
        top_weaknesses = [
            WeaknessStat(
                skill=row.knowledge_name or row.knowledge_id,
                affected_students=1,
            )
            for row in weak_rows
        ]

    skills = [row.skill for row in top_weaknesses]
    first_skill = skills[0] if skills else ""
    child_name = session.profile.nickname or "学生"
    need_intervention_students = [
        InterventionStudent(
            name=child_name,
            weakness=first_skill,
            session_id=session.session_id,
        )
    ]
    if demo:
        peer_skills = [
            skills[1] if len(skills) > 1 else first_skill,
            skills[2] if len(skills) > 2 else first_skill,
        ]
        for name, skill in zip(("小红", "小刚"), peer_skills, strict=True):
            if not skill:
                skill = first_skill
            need_intervention_students.append(
                InterventionStudent(
                    name=name,
                    weakness=skill,
                    session_id=session.session_id,
                )
            )

    auto_graded_rate = metrics.auto_graded_count / max(metrics.total_questions, 1)
    estimated_time_saved_minutes = (
        metrics.traditional_grading_time_minutes - metrics.estimated_grading_time_minutes
    )
    teacher_text = enrichment.get("teacher_summary")
    if isinstance(teacher_text, str) and teacher_text.strip():
        narrative = teacher_text
    else:
        narrative = generate_audience_summary(
            session.diagnosis, enrichment, audience="teacher"
        )

    return TeacherSummary(
        class_name=class_name,
        student_count=student_count,
        avg_mastery=avg_mastery,
        top_weaknesses=top_weaknesses,
        need_intervention_students=need_intervention_students,
        auto_graded_rate=auto_graded_rate,
        estimated_time_saved_minutes=estimated_time_saved_minutes,
        narrative=narrative,
    )


def build_parent_summary(session: SessionState) -> ParentSummary:
    enrichment = _enrichment(session)
    metrics = compute_metrics(session)
    child_name = session.profile.nickname or "孩子"
    post = metrics.post_assessment_score
    pre = metrics.pre_assessment_score
    current = post if post is not None else pre
    current_mastery = current / 100.0
    mastery_change = metrics.mastery_gain / 100.0

    weak_skills = [str(s) for s in (enrichment.get("weak_skills") or [])]
    if not weak_skills and session.diagnosis is not None:
        weak_skills = [
            row.knowledge_id
            for row in session.diagnosis.knowledge_mastery
            if row.level == "weak"
        ]
    weak_skills = weak_skills[:5]

    phase = session.phase
    learning_phase = phase.value if isinstance(phase, Enum) else str(phase)

    parent_text = enrichment.get("parent_summary")
    if not isinstance(parent_text, str) or not parent_text.strip():
        parent_text = generate_audience_summary(
            session.diagnosis, enrichment, audience="parent"
        )
    daily_practice_tips = _split_tips(parent_text)
    if not daily_practice_tips:
        daily_practice_tips = _split_tips(
            generate_audience_summary(session.diagnosis, enrichment, audience="parent")
        )

    plan = session.plan
    next_milestone = (
        plan.goal
        if plan is not None and getattr(plan, "goal", None)
        else "完成本单元薄弱点巩固"
    )
    narrative = parent_text if parent_text else generate_audience_summary(
        session.diagnosis, enrichment, audience="parent"
    )

    return ParentSummary(
        child_name=child_name,
        current_mastery=current_mastery,
        mastery_change=mastery_change,
        weak_skills=weak_skills,
        learning_phase=learning_phase,
        daily_practice_tips=daily_practice_tips,
        next_milestone=next_milestone,
        narrative=narrative,
    )


def _enrichment(session: SessionState) -> dict[str, Any]:
    raw = session.metadata.get("diagnosis_enrichment") or {}
    return raw if isinstance(raw, dict) else {}


def _split_tips(text: str) -> list[str]:
    parts: list[str] = []
    for chunk in text.replace("•", "\n").split("\n"):
        item = chunk.strip()
        if item:
            parts.append(item)
    return parts
