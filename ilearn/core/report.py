"""Aggregate Markdown report rendering for ILearn sessions."""

from __future__ import annotations

from ilearn.core.schemas import ItemSourceRef, SessionState
from ilearn.core.audience_summary import (
    generate_audience_summary,
    translate_to_parent_language,
    _ERROR_LABELS,
)
from ilearn.core.knowledge_labels import mastery_name_map, resolve_knowledge_label, resolve_knowledge_labels

_ABILITY_LABELS: dict[str, str] = {
    "logic": "逻辑推理",
    "spatial": "空间想象",
    "mental_math": "数感与运算",
}

_LEVEL_LABELS: dict[str, str] = {
    "mastered": "已掌握",
    "unstable": "不稳定",
    "weak": "薄弱",
}


def format_source_ref_lines(ref: ItemSourceRef) -> list[str]:
    """Render one source reference as Markdown bullet lines."""
    lines: list[str] = []
    if ref.example_id:
        lines.append(f"- **例题 ID：** {ref.example_id}")
    if ref.example_stem:
        lines.append(f"- **例题原文：** {ref.example_stem}")
    if ref.example_answer:
        lines.append(f"- **例题答案：** {ref.example_answer}")
    if ref.example_difficulty:
        lines.append(f"- **例题难度：** {ref.example_difficulty}")
    if ref.textbook_chapter:
        lines.append(f"- **教材章节：** {ref.textbook_chapter}")
    if ref.curriculum_objective_ids:
        ids = "、".join(ref.curriculum_objective_ids)
        lines.append(f"- **课标条目：** {ids}")
    if ref.source_label:
        lines.append(f"- **来源：** {ref.source_label}")
    return lines


def render_full_report(session: SessionState) -> str:
    """Render a Chinese Markdown report with diagnosis and plan sections."""
    profile = session.profile
    diagnosis = session.diagnosis
    plan = session.plan

    lines = [
        "# ILearn 学习报告",
        "",
        "## 基本信息",
        "",
        f"- **地区：** {profile.region}",
        f"- **年级：** {profile.grade} 年级",
        f"- **年龄：** {profile.age} 岁",
    ]

    if session.paper is not None:
        lines.append(f"- **测评题量：** {len(session.paper.items)} 题")
        lines.append(f"- **课标：** {session.paper.curriculum_label}")

    if diagnosis is not None and diagnosis.region_mismatch_disclaimer:
        lines.extend(["", f"> {diagnosis.region_mismatch_disclaimer}"])

    lines.extend(["", "## 学情诊断", ""])

    if diagnosis is None:
        lines.append("_暂无诊断数据。_")
    else:
        lines.extend(["### 知识掌握", ""])
        if diagnosis.knowledge_mastery:
            names = mastery_name_map(diagnosis)
            lines.append("| 知识点 | 得分率 | 掌握等级 | 关联题目 |")
            lines.append("| --- | ---: | --- | --- |")
            for km in sorted(
                diagnosis.knowledge_mastery,
                key=lambda row: (row.score_rate, row.knowledge_id),
            ):
                item_refs = "、".join(km.item_ids)
                level = _LEVEL_LABELS.get(km.level, km.level)
                label = resolve_knowledge_label(km.knowledge_id, mastery_names=names)
                lines.append(
                    f"| {label} | {km.score_rate:.0%} | {level} | {item_refs} |"
                )
        else:
            lines.append("_暂无知识点数据。_")

        lines.extend(["", "### 能力估算（启发式，非心理测量）", ""])
        if diagnosis.ability_scores:
            for tag, score in sorted(diagnosis.ability_scores.items()):
                label = _ABILITY_LABELS.get(tag, tag)
                lines.append(f"- **{label}：** {score:.0f} 分")
        else:
            lines.append("_暂无能力估算数据。_")

        lines.extend(["", "### 优先干预（Top-5）", ""])
        if diagnosis.interventions:
            names = mastery_name_map(diagnosis)
            for item in diagnosis.interventions:
                kid_label = resolve_knowledge_label(item.knowledge_id, mastery_names=names)
                lines.append(
                    f"{item.priority}. **{item.title}**（{kid_label}）"
                )
                lines.append(f"   - 原因：{item.why}")
                lines.append(f"   - 优先修复：{item.what_to_fix_first}")
        else:
            lines.append("_当前无明显薄弱知识点，建议保持复习节奏。_")

        enrichment = {}
        if isinstance(session.metadata, dict):
            enrichment = session.metadata.get("diagnosis_enrichment") or {}
        parent_summary = enrichment.get("parent_summary") or generate_audience_summary(
            diagnosis, enrichment, audience="parent"
        )
        parent_summary = translate_to_parent_language(str(parent_summary))
        teacher_summary = enrichment.get("teacher_summary") or generate_audience_summary(
            diagnosis, enrichment, audience="teacher"
        )
        lines.extend(["", "### 家长可读摘要", "", parent_summary])
        lines.extend(["", "### 教师可读摘要", "", teacher_summary])
        attribution = enrichment.get("error_attribution") or {}
        if attribution.get("top_tags"):
            lines.extend(["", "### 错误类型归因", ""])
            counts = attribution.get("counts") or {}
            for tag in attribution["top_tags"]:
                label = _ERROR_LABELS.get(str(tag), str(tag))
                lines.append(f"- **{label}：** {counts.get(tag, 0)} 次")
        explanations = enrichment.get("attribution_explanations") or []
        if explanations:
            lines.extend(["", "### 诊断解释", ""])
            for text in explanations:
                lines.append(f"- {text}")
        unknown = enrichment.get("unknown_skills") or []
        if unknown:
            names = mastery_name_map(diagnosis)
            unknown_labels = resolve_knowledge_labels(
                [str(s) for s in unknown],
                mastery_names=names,
            )
            lines.extend(["", "### 待确认技能", ""])
            lines.append("、".join(unknown_labels))
        conf = enrichment.get("diagnosis_confidence") or {}
        if conf.get("score") is not None:
            lines.extend(
                [
                    "",
                    "### 诊断置信度",
                    "",
                    f"- **分数：** {conf.get('score')}（{conf.get('label') or ''}）",
                    f"- **说明：** {conf.get('reason') or ''}",
                ]
            )
        hint_eff = enrichment.get("hint_effectiveness") or {}
        if hint_eff.get("hint_turns_scored"):
            rate = hint_eff.get("solved_after_hint_rate")
            rate_txt = f"{rate:.0%}" if isinstance(rate, float) else "—"
            lines.extend(
                [
                    "",
                    "### 提示效果",
                    "",
                    f"- 已评分提示轮次：{hint_eff.get('hint_turns_scored')}",
                    f"- 提示后做对比例：{rate_txt}",
                ]
            )

    if session.paper is not None and session.grades:
        wrong_grades = [grade for grade in session.grades if not grade.final_correct]
        if wrong_grades:
            items_by_id = {item.id: item for item in session.paper.items}
            lines.extend(["", "### 错题参考来源", ""])
            for grade in wrong_grades:
                item = items_by_id.get(grade.item_id)
                if item is None:
                    continue
                stem_preview = item.stem.replace("\n", " ")
                if len(stem_preview) > 80:
                    stem_preview = stem_preview[:77] + "..."
                lines.append(f"**{item.id}** — {stem_preview}")
                if item.source_refs:
                    for ref in item.source_refs:
                        lines.extend(format_source_ref_lines(ref))
                else:
                    lines.append("- _暂无参考来源数据。_")
                lines.append("")

    lines.extend(["", "## 学习计划", ""])

    if plan is None:
        lines.append("_暂无学习计划。_")
    else:
        lines.append(plan.markdown)

    if plan is not None and plan.disclaimer:
        lines.extend(["", "## 说明", "", plan.disclaimer])

    return "\n".join(lines).strip()
