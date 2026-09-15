"""P12 error notebook: wrong items with steps/citation, never answer_key."""

from __future__ import annotations

from typing import Any

from ilearn.core.schemas import SessionState


def build_error_notebook(session: SessionState) -> list[dict[str, Any]]:
    paper = session.paper
    if paper is None:
        return []
    by_id = {item.id: item for item in paper.items}
    rows: list[dict[str, Any]] = []
    for grade in session.grades or []:
        if grade.final_correct:
            continue
        item = by_id.get(grade.item_id)
        if item is None:
            continue
        citation_label = None
        for ref in item.source_refs or []:
            citation_label = ref.source_label or ref.example_id or ref.textbook_chapter
            if citation_label:
                break
        rows.append(
            {
                "item_id": item.id,
                "stem": item.stem,
                "rubric_steps": list(item.rubric_steps or []),
                "knowledge_ids": list(item.knowledge_ids or []),
                "citation_label": citation_label,
                "answer_key": None,
                "student_answer": next(
                    (
                        a.answer_text
                        for a in (session.answers or [])
                        if a.item_id == item.id
                    ),
                    None,
                ),
            }
        )
    return rows


MASK_NOTE = "终答已遮罩：错题本只保留题干、步骤、来源与你的作答，重练时也不给最终答案。"


def error_notebook_block(session: SessionState) -> dict[str, Any]:
    """W4: error-notebook home payload — count, knowledge focus, mask note, repractice flag."""
    rows = build_error_notebook(session)
    focus: list[str] = []
    for row in rows:
        for kid in row.get("knowledge_ids") or []:
            if kid not in focus:
                focus.append(kid)
    return {
        "session_id": session.session_id,
        "count": len(rows),
        "knowledge_focus": focus[:5],
        "mask_note": MASK_NOTE,
        "repractice_ready": bool(rows),
        "items": rows,
    }
