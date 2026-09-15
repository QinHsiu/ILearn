"""Markdown builders for P5/P6/P12 PDF exports (no final answers)."""

from __future__ import annotations

from typing import Any

from ilearn.core.error_notebook import build_error_notebook
from ilearn.core.parent_action_summary import ParentActionSummary, build_parent_action_summary
from ilearn.core.schemas import SessionState
from ilearn.core.tier_suggest import classify_tiers, materialize_tier_papers


def grading_receipts_markdown(session: SessionState) -> str:
    lines = [
        f"# 批改收据 · {session.session_id}",
        "",
        "每题可复核来源；不含最终标准答案。",
        "",
    ]
    for grade in session.grades or []:
        lines.append(f"## 题目 `{grade.item_id}`")
        lines.append(f"- 正误：{'正确' if grade.final_correct else '需巩固'}")
        lines.append(f"- 通道：{grade.lane}")
        lines.append(f"- 降级批改：{'是' if grade.grading_degraded else '否'}")
        if grade.receipt:
            r = grade.receipt
            lines.append(f"- 批改版本：{r.grader_version}")
            lines.append(f"- 模型：{r.model_id or '规则/本地'}")
            if r.paper_created_at:
                lines.append(f"- 试卷时间：{r.paper_created_at.isoformat()}")
        lines.append("")
    if len(lines) <= 4:
        lines.append("_暂无批改记录_")
    return "\n".join(lines)


def parent_action_card_markdown(
    session: SessionState,
    *,
    summary: ParentActionSummary | None = None,
) -> str:
    if summary is None:
        weak: list[str] = []
        if session.diagnosis:
            for km in session.diagnosis.knowledge_mastery or []:
                if km.level in {"weak", "unstable"}:
                    weak.append(km.knowledge_name or km.knowledge_id)
        summary = build_parent_action_summary(
            child_name=session.profile.nickname or "孩子",
            current_mastery=0.5,
            mastery_change=0.0,
            weak_skills=weak[:3],
        )
    lines = [
        f"# 亲子一分钟题卡 · {session.profile.nickname or '孩子'}",
        "",
        summary.headline,
        "",
        "## 值得表扬",
        *[f"- {w}" for w in summary.wins],
        "",
        "## 本周盯梢",
        *[f"- {f}" for f in summary.focus],
        "",
        "## 今晚可做",
        *[f"- {a}" for a in summary.actions],
        "",
        "> 不直接报终答；陪孩子口述步骤即可。",
    ]
    return "\n".join(lines)


def error_notebook_markdown(session: SessionState) -> str:
    rows = build_error_notebook(session)
    lines = [
        f"# 错题本 · {session.session_id}",
        "",
        "终答已隐藏；请按步骤重练。",
        "",
    ]
    for i, row in enumerate(rows, 1):
        lines.append(f"## 错题 {i}")
        lines.append(row.get("stem") or "")
        if row.get("citation_label"):
            lines.append(f"- 出处：{row['citation_label']}")
        steps = row.get("rubric_steps") or []
        if steps:
            lines.append("- 步骤：")
            for s in steps:
                lines.append(f"  1. {s}")
        lines.append("")
    if not rows:
        lines.append("_本场暂无错题_")
    return "\n".join(lines)


def build_repractice_paper(session: SessionState) -> dict[str, Any]:
    """P12: materialize a short re-practice paper from wrong items (no answer_key)."""
    from ilearn.core.schemas import AssessmentItem, AssessmentPaper, ItemSourceRef

    notebook = build_error_notebook(session)
    items: list[AssessmentItem] = []
    for i, row in enumerate(notebook[:6], 1):
        items.append(
            AssessmentItem(
                id=f"retry_{row['item_id']}_{i}",
                stem=f"【重练】{row.get('stem') or row['item_id']}",
                type="constructed",
                difficulty="medium",
                knowledge_ids=list(row.get("knowledge_ids") or ["kp_retry"]),
                answer_key=None,
                rubric_steps=list(row.get("rubric_steps") or ["审题", "分步", "检验"]),
                source_refs=[
                    ItemSourceRef(
                        source_label=row.get("citation_label") or "error-notebook",
                        example_id=row["item_id"],
                        curriculum_objective_ids=["retry_from_error"],
                        confidence=0.6,
                    )
                ],
            )
        )
    paper = AssessmentPaper(
        items=items or [
            AssessmentItem(
                id="retry_empty",
                stem="本场暂无错题，可选择拓展挑战题。",
                type="constructed",
                difficulty="easy",
                knowledge_ids=["kp_ok"],
                answer_key=None,
            )
        ],
        grade=session.profile.grade,
        curriculum_label=session.paper.curriculum_label if session.paper else "北京·人教",
    )
    return paper.model_dump(mode="json")


def assign_tiers_for_session(
    session: SessionState,
    *,
    topic: str | None = None,
    students: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """P7: materialize papers + receipt into session metadata-friendly payload."""
    weak_topic = topic
    if not weak_topic and session.diagnosis:
        for km in session.diagnosis.knowledge_mastery or []:
            if km.level in {"weak", "unstable"}:
                weak_topic = km.knowledge_name or km.knowledge_id
                break
    weak_topic = weak_topic or "本单元薄弱点"
    rows = students or [
        {
            "name": session.profile.nickname or "学生",
            "avg_mastery": 0.45,
        }
    ]
    tiers = classify_tiers(rows, weak_topic=weak_topic)
    papers, receipt = materialize_tier_papers(
        tiers, topic=weak_topic, grade=int(session.profile.grade)
    )
    return {"papers": papers, "receipt": receipt, "tiers": tiers.model_dump()}
