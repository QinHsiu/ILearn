"""Deterministic teaching-effectiveness metrics from a SessionState."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from ilearn.core.schemas import AssessmentItem, GradeResult, SessionState


class TeachingEffectivenessMetrics(BaseModel):
    """Computed teaching-effectiveness KPIs (not persisted as a table)."""

    pre_assessment_score: float
    post_assessment_score: float | None = None
    mastery_gain: float
    weakness_resolved_count: int
    weakness_remaining_count: int
    total_questions: int
    auto_graded_count: int
    manual_review_count: int
    estimated_grading_time_minutes: float
    traditional_grading_time_minutes: float
    time_saved_percent: float
    session_duration_seconds: int
    hint_used_count: int
    avg_response_time_seconds: float
    completion_rate: float
    diagnosis_confidence: float
    evidence_count: int
    parent_view_count: int
    teacher_notes_count: int


def compute_metrics(session: SessionState) -> TeachingEffectivenessMetrics:
    """Derive effectiveness metrics with the locked edition-0901 formulas."""
    grades = list(session.grades or [])
    items_by_id = _items_by_id(session)
    n = len(session.paper.items) if session.paper is not None else len(grades)

    correct = sum(1 for grade in grades if grade.final_correct)
    pre_score = 100.0 * correct / max(len(grades), 1)
    post_score = _optional_float(session.metadata.get("post_assessment_score"))

    if post_score is not None:
        mastery_gain = post_score - pre_score
    else:
        mastery_gain = float(session.metadata.get("demo_mastery_gain") or 0)

    weak_remaining = 0
    if session.diagnosis is not None:
        weak_remaining = sum(
            1 for row in session.diagnosis.knowledge_mastery if row.level == "weak"
        )
    weak_resolved = int(session.metadata.get("demo_weaknesses_resolved") or 0)

    manual = sum(1 for grade in grades if _is_manual(grade, items_by_id))
    auto = len(grades) - manual
    traditional = n * 2.0
    ilearn = manual * 1.0 + 0.5
    if n == 0:
        time_saved = 0.0
        ilearn = 0.0
        traditional = 0.0
    else:
        time_saved = (traditional - ilearn) / traditional * 100.0

    paper_n = len(session.paper.items) if session.paper is not None else 0
    completion = 100.0 * len(session.answers) / max(paper_n, 1)

    return TeachingEffectivenessMetrics(
        pre_assessment_score=pre_score,
        post_assessment_score=post_score,
        mastery_gain=mastery_gain,
        weakness_resolved_count=weak_resolved,
        weakness_remaining_count=weak_remaining,
        total_questions=n,
        auto_graded_count=auto,
        manual_review_count=manual,
        estimated_grading_time_minutes=ilearn,
        traditional_grading_time_minutes=traditional,
        time_saved_percent=time_saved,
        session_duration_seconds=int(session.metadata.get("session_duration_seconds") or 0),
        hint_used_count=sum(len(rows) for rows in session.hint_interactions.values()),
        avg_response_time_seconds=float(
            session.metadata.get("avg_response_time_seconds") or 0
        ),
        completion_rate=completion,
        diagnosis_confidence=_diagnosis_confidence(session),
        evidence_count=len(session.evidence_log),
        parent_view_count=int(session.metadata.get("parent_view_count") or 0),
        teacher_notes_count=int(session.metadata.get("teacher_notes_count") or 0),
    )


def render_effectiveness_markdown(
    metrics: TeachingEffectivenessMetrics, *, unit_name: str = ""
) -> str:
    """Markdown source for the teaching-effectiveness PDF."""
    lines: list[str] = ["# ILearn 教学效果验证报告", ""]
    if unit_name:
        lines.extend(["## 教学单元", "", f"- **单元：** {unit_name}", ""])
    post = (
        metrics.post_assessment_score
        if metrics.post_assessment_score is not None
        else "—"
    )
    lines.extend(
        [
            "## 学习成效",
            "",
            f"- **前测得分：** {metrics.pre_assessment_score}",
            f"- **后测得分：** {post}",
            f"- **掌握度提升：** {metrics.mastery_gain}",
            f"- **已解决薄弱点：** {metrics.weakness_resolved_count}",
            f"- **仍存薄弱点：** {metrics.weakness_remaining_count}",
            "",
            "## 教师工作量",
            "",
            f"- **题目总数：** {metrics.total_questions}",
            f"- **自动批改：** {metrics.auto_graded_count}",
            f"- **人工复核：** {metrics.manual_review_count}",
            f"- **ILearn 批改时间（分钟）：** {metrics.estimated_grading_time_minutes}",
            f"- **传统批改时间（分钟）：** {metrics.traditional_grading_time_minutes}",
            f"- **批改时间节省：** {metrics.time_saved_percent}%",
            "",
            "## 参与度",
            "",
            f"- **完成率：** {metrics.completion_rate}",
            f"- **会话时长（秒）：** {metrics.session_duration_seconds}",
            f"- **提示次数：** {metrics.hint_used_count}",
            f"- **平均作答时间（秒）：** {metrics.avg_response_time_seconds}",
            "",
            "## 诊断与家校",
            "",
            f"- **诊断置信度：** {metrics.diagnosis_confidence}",
            f"- **证据条数：** {metrics.evidence_count}",
            f"- **家长查看次数：** {metrics.parent_view_count}",
            f"- **教师备注次数：** {metrics.teacher_notes_count}",
            "",
        ]
    )
    return "\n".join(lines).strip()


def effectiveness_payload(session: SessionState) -> dict[str, Any]:
    """JSON body for GET /sessions/{id}/effectiveness."""
    metrics = compute_metrics(session)
    return {
        "metrics": metrics.model_dump(),
        "comparison": {
            "traditional_vs_ilearn": {
                "grading_time": {
                    "traditional": f"{metrics.traditional_grading_time_minutes}分钟",
                    "ilearn": f"{metrics.estimated_grading_time_minutes}分钟",
                },
                "personalized": {
                    "traditional": "统一作业",
                    "ilearn": "自适应个性化",
                },
                "feedback_delay": {
                    "traditional": "1-2天",
                    "ilearn": "即时",
                },
            }
        },
    }


def _items_by_id(session: SessionState) -> dict[str, AssessmentItem]:
    if session.paper is None:
        return {}
    return {item.id: item for item in session.paper.items}


def _is_manual(
    grade: GradeResult, items_by_id: dict[str, AssessmentItem]
) -> bool:
    item = items_by_id.get(grade.item_id)
    constructed = item is not None and item.type == "constructed"
    return bool(grade.grading_degraded or constructed)


def _diagnosis_confidence(session: SessionState) -> float:
    enrichment = session.metadata.get("diagnosis_enrichment")
    if not isinstance(enrichment, dict):
        return 0.75
    raw = enrichment.get("diagnosis_confidence")
    if isinstance(raw, dict):
        score = raw.get("score")
        if score is None:
            return 0.75
        return float(score)
    if raw is None:
        return 0.75
    return float(raw)


def _optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
