"""Assemble report.txt-shaped export structures from SessionState."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ilearn.core.datetime_utils import utc_now
from ilearn.core.knowledge_labels import mastery_name_map, resolve_knowledge_label
from ilearn.core.schemas import SessionState


@dataclass
class AnswerRecord:
    question_id: str
    index: int
    stem: str
    type: str
    correct_answer: str
    student_answer: str
    is_correct: bool
    has_image: bool = False
    time_spent_seconds: float = 0.0
    hint_count: int = 0
    hint_opened: bool = False
    solved_after_hint: bool | None = None


@dataclass
class HintRecord:
    turn: int
    user_input: str
    ai_hint: str
    has_image: bool = False
    solved_after_hint: bool | None = None


@dataclass
class QuestionHintDetail:
    question_id: str
    index: int
    hint_interactions: list[HintRecord] = field(default_factory=list)
    final_correct: bool = False


@dataclass
class DiagnosticSummary:
    accuracy: float
    mastered_skills: list[str] = field(default_factory=list)
    weak_skills: list[str] = field(default_factory=list)


@dataclass
class ExportReportData:
    """Mirrors doc/deepseek_edition/report.txt ReportData (live field names)."""

    student_name: str
    grade: int
    region: str
    assessment_date: str
    answers: list[AnswerRecord] = field(default_factory=list)
    hint_details: list[QuestionHintDetail] = field(default_factory=list)
    summary: DiagnosticSummary = field(default_factory=lambda: DiagnosticSummary(accuracy=0.0))


def build_assessment_export_data(session: SessionState) -> ExportReportData:
    """Build draft-shaped export data; raises ValueError if paper/grades missing."""
    if session.paper is None or not session.grades:
        raise ValueError("尚无测评与批改结果，无法导出做题复盘")

    answers_by_id = {a.item_id: a for a in session.answers}
    grades_by_id = {g.item_id: g for g in session.grades}
    image_ids = {img.item_id for img in session.image_answers}
    item_meta_raw = session.metadata.get("item_meta") if isinstance(session.metadata, dict) else {}
    item_meta = item_meta_raw if isinstance(item_meta_raw, dict) else {}
    hints_by_qid = session.hint_interactions or {}

    answer_records: list[AnswerRecord] = []
    for idx, item in enumerate(session.paper.items, start=1):
        grade = grades_by_id.get(item.id)
        if grade is None:
            continue
        student = answers_by_id.get(item.id)
        meta = item_meta.get(item.id) if isinstance(item_meta.get(item.id), dict) else {}
        elapsed_ms = float(meta.get("elapsed_ms") or 0)
        hints = list(hints_by_qid.get(item.id) or [])
        solved_after = None
        for hint in hints:
            if hint.solved_after_hint is True:
                solved_after = True
                break
        if hints and solved_after is None:
            solved_after = bool(grade.final_correct)
        answer_records.append(
            AnswerRecord(
                question_id=item.id,
                index=idx,
                stem=item.stem,
                type=item.type,
                correct_answer=item.answer_key or "",
                student_answer=(student.answer_text if student else "") or "",
                is_correct=bool(grade.final_correct),
                has_image=item.id in image_ids,
                time_spent_seconds=round(elapsed_ms / 1000.0, 1),
                hint_count=len(hints),
                hint_opened=bool(meta.get("hint_used")) or bool(hints),
                solved_after_hint=solved_after,
            )
        )

    if not answer_records:
        raise ValueError("尚无测评与批改结果，无法导出做题复盘")

    correct_n = sum(1 for a in answer_records if a.is_correct)
    accuracy = correct_n / len(answer_records)

    mastered: list[str] = []
    weak: list[str] = []
    if session.diagnosis is not None:
        names = mastery_name_map(session.diagnosis)
        for km in session.diagnosis.knowledge_mastery:
            label = resolve_knowledge_label(km.knowledge_id, mastery_names=names)
            if km.level == "mastered":
                mastered.append(label)
            elif km.level == "weak":
                weak.append(label)

    hint_details: list[QuestionHintDetail] = []
    index_by_id = {a.question_id: a.index for a in answer_records}
    correct_by_id = {a.question_id: a.is_correct for a in answer_records}
    for qid, interactions in (session.hint_interactions or {}).items():
        if qid not in index_by_id:
            continue
        hint_details.append(
            QuestionHintDetail(
                question_id=qid,
                index=index_by_id[qid],
                hint_interactions=[
                    HintRecord(
                        turn=h.turn,
                        user_input=h.user_input,
                        ai_hint=h.ai_hint,
                        has_image=h.has_image,
                        solved_after_hint=h.solved_after_hint,
                    )
                    for h in interactions
                ],
                final_correct=correct_by_id.get(qid, False),
            )
        )

    date_str = utc_now().strftime("%Y-%m-%d")
    # Prefer any timestamp on first hint if present (sessions lack created_at).
    for detail in hint_details:
        for h in session.hint_interactions.get(detail.question_id, []):
            if isinstance(h.timestamp, datetime):
                date_str = h.timestamp.strftime("%Y-%m-%d")
                break

    return ExportReportData(
        student_name=(session.profile.nickname or "").strip() or "未命名",
        grade=int(session.profile.grade),
        region=session.profile.region,
        assessment_date=date_str,
        answers=answer_records,
        hint_details=hint_details,
        summary=DiagnosticSummary(
            accuracy=accuracy,
            mastered_skills=mastered,
            weak_skills=weak,
        ),
    )
