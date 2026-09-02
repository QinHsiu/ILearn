"""Audience-friendly summaries for parents and teachers."""

from __future__ import annotations

import logging
import math
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel

logger = logging.getLogger(__name__)

from ilearn.core.effectiveness import compute_metrics
from ilearn.core.knowledge_labels import (
    looks_like_internal_id,
    mastery_name_map,
    resolve_knowledge_label,
    resolve_knowledge_labels,
)
from ilearn.core.schemas import DiagnosisReport, SessionState

Audience = Literal["parent", "teacher"]

_ERROR_LABELS: dict[str, str] = {
    "concept_gap": "概念理解不清",
    "calc_error": "计算过程易错",
    "misread": "审题不够仔细",
    "method_wrong": "解题方法选择不当",
    "incomplete": "解题步骤不完整",
}

_PARENT_TERM_TRANSLATIONS: dict[str, str] = {
    "知识点": "学习内容",
    "掌握度": "理解程度",
    "认知": "思考",
    "元认知": "学习方法",
    "课标": "教学大纲",
    "诊断": "学情分析",
    "薄弱点": "需要加强的地方",
    "巩固": "复习",
    "测评": "小测验",
    "证据": "学习记录",
    "技能": "能力",
    "能力": "本领",
    "思维": "动脑筋",
    "逻辑": "条理",
    "推理": "推理能力",
    "运算": "计算",
    "空间": "空间感",
}

_PHASE_PARENT_LABELS: dict[str, str] = {
    "onboard": "建档准备",
    "assess": "测评进行中",
    "practice": "巩固练习",
    "grade": "批改与学情",
    "diagnose": "学情分析",
    "plan": "学习计划阶段",
    "practice_loop": "巩固轮次",
    "idle": "待开始",
}

_PARENT_MILESTONE_BY_MASTERY: tuple[tuple[float, str], ...] = (
    (0.5, "掌握核心概念"),
    (0.75, "攻克薄弱环节"),
    (1.01, "挑战综合应用题"),
)

_UNRESOLVED_SKILL_LABEL = "一个需要加强的知识点"


def _sanitize_parent_skill_labels(labels: list[str]) -> list[str]:
    """Ensure parent-facing lists never leak internal ids or slug tokens."""
    cleaned: list[str] = []
    for label in labels:
        text = (label or "").strip()
        if not text or looks_like_internal_id(text) or "kp_" in text:
            cleaned.append(_UNRESOLVED_SKILL_LABEL)
        else:
            cleaned.append(text)
    return list(dict.fromkeys(cleaned))


def _resolve_session_skill_names(
    session: SessionState,
    raw_ids: list[str],
) -> list[str]:
    names = mastery_name_map(session.diagnosis)
    resolved = resolve_knowledge_labels(
        [str(item) for item in raw_ids],
        mastery_names=names,
    )
    return _sanitize_parent_skill_labels(resolved)


def _parent_next_milestone(current_mastery: float, plan_goal: str | None) -> str:
    if plan_goal and plan_goal.strip():
        return plan_goal.strip()
    for threshold, label in _PARENT_MILESTONE_BY_MASTERY:
        if current_mastery < threshold:
            return label
    return _PARENT_MILESTONE_BY_MASTERY[-1][1]


def _generate_parent_tips(
    session: SessionState,
    resolved_skills: list[str],
    enrichment: dict[str, Any],
) -> list[str]:
    if not resolved_skills:
        return ["孩子表现不错！可以挑战一些更有趣的拓展题。"]
    tips = [
        f"针对「{name}」，可以每天花5分钟做1-2道相关练习。"
        for name in resolved_skills[:3]
    ]
    attribution = enrichment.get("error_attribution") or {}
    top_errors = list(attribution.get("top_tags") or [])[:2]
    if top_errors:
        labels = "、".join(_ERROR_LABELS.get(str(tag), str(tag)) for tag in top_errors)
        tips.append(f"近期主要失分倾向：{labels}。练习时请先让孩子口述思路再动笔。")
    gaps = _resolve_session_skill_names(
        session,
        [str(item) for item in (enrichment.get("prerequisite_gaps") or [])],
    )
    if gaps:
        tips.append("建议先复习前置内容：" + "、".join(gaps[:3]) + "，再继续当前单元。")
    return tips


def _display_skill_name(session: SessionState, raw: str) -> str:
    """Resolve a single skill/knowledge token for any audience-facing surface."""
    if not raw:
        return _UNRESOLVED_SKILL_LABEL
    return _resolve_session_skill_names(session, [str(raw)])[0]


def default_parent_summary() -> ParentSummary:
    return ParentSummary(
        child_name="孩子",
        current_mastery=0.5,
        mastery_change=0.0,
        weak_skills=["暂未检测到薄弱点"],
        learning_phase="建档准备",
        daily_practice_tips=["请先完成一次测评，系统将为您生成个性化建议。"],
        next_milestone="完成首次测评",
        narrative="请先完成测评，我们将为您生成专属学情摘要。",
    )


def default_teacher_summary() -> TeacherSummary:
    return TeacherSummary(
        class_name="当前班级",
        student_count=0,
        avg_mastery=0.0,
        top_weaknesses=[],
        need_intervention_students=[],
        auto_graded_rate=0.0,
        estimated_time_saved_minutes=0.0,
        narrative="暂无班级学情数据，请先绑定学生会话。",
    )


def default_student_summary() -> StudentSummary:
    return StudentSummary(
        current_task="完成首次测评",
        completed_tasks=0,
        total_tasks=1,
        stars_earned=0,
        next_challenge="开始你的学习之旅",
        narrative="完成测评后，这里会显示你的学习进度。",
    )


def build_parent_summary_safe(session: SessionState | None) -> ParentSummary:
    if session is None:
        return default_parent_summary()
    try:
        return build_parent_summary(session)
    except Exception:
        logger.exception("build_parent_summary failed")
        return default_parent_summary()


def build_teacher_summary_safe(session: SessionState | None) -> TeacherSummary:
    if session is None:
        return default_teacher_summary()
    try:
        return build_teacher_summary(session)
    except Exception:
        logger.exception("build_teacher_summary failed")
        return default_teacher_summary()


def build_student_summary_safe(session: SessionState | None) -> StudentSummary:
    if session is None:
        return default_student_summary()
    try:
        return build_student_summary(session)
    except Exception:
        logger.exception("build_student_summary failed")
        return default_student_summary()


def translate_to_parent_language(text: str) -> str:
    """Map ed-tech terms to parent-friendly everyday Chinese."""
    if not text:
        return text
    result = text
    for tech, friendly in _PARENT_TERM_TRANSLATIONS.items():
        result = result.replace(tech, friendly)
    return result


def translate_list_to_parent_language(items: list[str]) -> list[str]:
    return [translate_to_parent_language(item) for item in items]


def generate_audience_summary(
    diagnosis: DiagnosisReport | None,
    enrichment: dict[str, Any] | None = None,
    *,
    audience: Audience = "parent",
) -> str:
    """Turn diagnosis/enrichment into actionable Chinese advice."""
    enrichment = enrichment or {}
    names = mastery_name_map(diagnosis)
    weak = _sanitize_parent_skill_labels(
        resolve_knowledge_labels(
            list(enrichment.get("weak_skills") or []),
            mastery_names=names,
        )
    )
    if diagnosis is not None and not weak:
        weak = _sanitize_parent_skill_labels(
            resolve_knowledge_labels(
                [
                    row.knowledge_id
                    for row in diagnosis.knowledge_mastery
                    if row.level == "weak"
                ],
                mastery_names=names,
            )
        )
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
        gaps = _sanitize_parent_skill_labels(
            resolve_knowledge_labels(
                list(enrichment.get("prerequisite_gaps") or []),
                mastery_names=names,
            )
        )
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


class StudentSummary(BaseModel):
    current_task: str
    completed_tasks: int
    total_tasks: int
    stars_earned: int
    next_challenge: str
    narrative: str


def build_student_summary(session: SessionState) -> StudentSummary:
    plan = session.plan
    paper = session.paper

    if plan is not None and plan.days:
        total_tasks = max(len(plan.days), 1)
    else:
        total_tasks = max(len(paper.items) if paper else 0, 1)

    completed_tasks = min(len(session.answers), total_tasks)

    current_task = "完成今日练习"
    if plan is not None:
        if plan.goal:
            current_task = plan.goal
        elif plan.days:
            for task in plan.days[0].tasks:
                if task:
                    current_task = task
                    break

    weaknesses_resolved = int(session.metadata.get("demo_weaknesses_resolved") or 0)
    paper_bonus = 1 if paper and len(session.answers) >= len(paper.items) else 0
    stars_earned = weaknesses_resolved * 2 + paper_bonus

    next_challenge = "挑战下一关练习"
    if session.diagnosis is not None:
        names = mastery_name_map(session.diagnosis)
        for row in session.diagnosis.knowledge_mastery:
            if row.level == "weak":
                next_challenge = resolve_knowledge_label(
                    row.knowledge_id,
                    mastery_names=names,
                )
                break

    narrative = f"已完成 {completed_tasks}/{total_tasks} 个任务，继续加油！"

    merged: dict[str, Any] = {
        "current_task": current_task,
        "completed_tasks": completed_tasks,
        "total_tasks": total_tasks,
        "stars_earned": stars_earned,
        "next_challenge": next_challenge,
        "narrative": narrative,
    }
    overlay = session.metadata.get("student_summary")
    if isinstance(overlay, dict):
        for key in StudentSummary.model_fields:
            if key in overlay and overlay[key] is not None:
                merged[key] = overlay[key]

    return StudentSummary(**merged)


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
            WeaknessStat(
                skill=_display_skill_name(session, str(skill)),
                affected_students=affected,
            )
            for skill in common
        ]
    else:
        names = mastery_name_map(session.diagnosis)
        weak_rows = [
            row
            for row in (
                session.diagnosis.knowledge_mastery if session.diagnosis is not None else []
            )
            if row.level == "weak"
        ][:3]
        top_weaknesses = [
            WeaknessStat(
                skill=_display_skill_name(session, row.knowledge_id),
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
            weakness=_display_skill_name(session, first_skill) if first_skill else "待确认",
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
                    weakness=_display_skill_name(session, skill) if skill else "待确认",
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

    raw_weak = [str(s) for s in (enrichment.get("weak_skills") or [])]
    if not raw_weak and session.diagnosis is not None:
        raw_weak = [
            row.knowledge_id
            for row in session.diagnosis.knowledge_mastery
            if row.level == "weak"
        ]
    weak_skills = _resolve_session_skill_names(session, raw_weak)[:5]

    phase = session.phase
    phase_key = phase.value if isinstance(phase, Enum) else str(phase)
    learning_phase = _PHASE_PARENT_LABELS.get(phase_key, phase_key)

    parent_text = enrichment.get("parent_summary")
    if isinstance(parent_text, str) and parent_text.strip():
        parent_text = translate_to_parent_language(parent_text.strip())
        daily_practice_tips = translate_list_to_parent_language(_split_tips(parent_text))
    else:
        resolved_for_tips = weak_skills[:3]
        daily_practice_tips = translate_list_to_parent_language(
            _generate_parent_tips(session, resolved_for_tips, enrichment)
        )
        parent_text = "\n".join(
            ["给家长的行动建议：", *[f"• {tip}" for tip in daily_practice_tips]]
        )

    if not daily_practice_tips:
        daily_practice_tips = translate_list_to_parent_language(
            _generate_parent_tips(session, weak_skills[:3], enrichment)
        )

    plan = session.plan
    next_milestone = translate_to_parent_language(
        _parent_next_milestone(
            current_mastery,
            plan.goal if plan is not None and getattr(plan, "goal", None) else None,
        )
    )
    weak_skills = translate_list_to_parent_language(weak_skills)
    narrative = parent_text

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
