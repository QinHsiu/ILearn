"""Minimal teacher tier suggestion for demo decision support."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TierSuggestion(BaseModel):
    basic: list[str] = Field(default_factory=list)
    advanced: list[str] = Field(default_factory=list)
    challenge: list[str] = Field(default_factory=list)
    next_step: str = ""


def classify_tiers(
    students: list[dict[str, Any]],
    *,
    weak_topic: str | None = None,
) -> TierSuggestion:
    """Partition by avg mastery: <0.4 basic, <0.7 advanced, else challenge."""
    basic: list[str] = []
    advanced: list[str] = []
    challenge: list[str] = []
    for row in students:
        name = str(row.get("name") or row.get("student_id") or "学生")
        avg = float(row.get("avg_mastery") or 0.0)
        if avg < 0.4:
            basic.append(name)
        elif avg < 0.7:
            advanced.append(name)
        else:
            challenge.append(name)

    topic = weak_topic or "本单元薄弱点"
    if basic:
        next_step = f"基础组（{len(basic)}人）先巩固「{topic}」概念，布置 5 分钟口述题"
    elif advanced:
        next_step = f"提高组（{len(advanced)}人）做变式练习，课上抽查错因"
    else:
        next_step = f"挑战组可拓展综合题；全班复盘「{topic}」共性误区"

    return TierSuggestion(
        basic=basic,
        advanced=advanced,
        challenge=challenge,
        next_step=next_step,
    )


def build_tier_assignment(
    tiers: TierSuggestion,
    *,
    topic: str,
) -> dict[str, dict[str, Any]]:
    """Produce three assignable practice drafts (P7 win-bar beyond copy)."""
    return {
        "basic": {
            "title": f"基础巩固 · {topic}",
            "students": list(tiers.basic),
            "item_count": 5,
            "difficulty": "easy",
            "focus": "概念口述 + 例题仿写",
        },
        "advanced": {
            "title": f"提高变式 · {topic}",
            "students": list(tiers.advanced),
            "item_count": 5,
            "difficulty": "medium",
            "focus": "错因变式",
        },
        "challenge": {
            "title": f"挑战综合 · {topic}",
            "students": list(tiers.challenge),
            "item_count": 4,
            "difficulty": "hard",
            "focus": "综合应用",
        },
    }


def materialize_tier_papers(
    tiers: TierSuggestion,
    *,
    topic: str,
    grade: int = 5,
    curriculum_label: str = "北京·人教",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build real AssessmentPaper payloads + assignment receipt (P7)."""
    from datetime import datetime, timezone

    from ilearn.core.schemas import AssessmentItem, AssessmentPaper, ItemSourceRef

    assignment = build_tier_assignment(tiers, topic=topic)
    papers: dict[str, Any] = {}
    receipt_papers: dict[str, Any] = {}
    for key, spec in assignment.items():
        n = int(spec["item_count"])
        difficulty = str(spec["difficulty"])
        items: list[AssessmentItem] = []
        for i in range(1, n + 1):
            items.append(
                AssessmentItem(
                    id=f"tier_{key}_{i}",
                    stem=f"【{topic}·{spec['title']}】练习题 {i}：请写出关键步骤（不要求终答）。",
                    type="constructed",
                    difficulty=difficulty,  # type: ignore[arg-type]
                    knowledge_ids=[f"kp_{topic}"],
                    answer_key=None,
                    rubric_steps=["审题", "选择方法", "分步计算", "检验"],
                    source_refs=[
                        ItemSourceRef(
                            source_label="tier-assignment",
                            textbook_chapter=topic,
                            curriculum_objective_ids=[f"obj_{topic}"],
                            example_id=f"tier_{key}_{i}",
                            confidence=0.75,
                        )
                    ],
                )
            )
        paper = AssessmentPaper(
            items=items,
            grade=grade,  # type: ignore[arg-type]
            curriculum_label=curriculum_label,
        )
        papers[key] = paper.model_dump(mode="json")
        receipt_papers[key] = {
            "title": spec["title"],
            "students": spec["students"],
            "item_count": len(items),
            "item_ids": [it.id for it in items],
            "difficulty": difficulty,
        }
    receipt = {
        "topic": topic,
        "assigned_at": datetime.now(timezone.utc).isoformat(),
        "status": "assigned",
        "papers": receipt_papers,
        "next_step": tiers.next_step,
    }
    return papers, receipt

