"""Aggregate Markdown report rendering for ILearn sessions."""

from __future__ import annotations

from ilearn.core.schemas import SessionState

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
            lines.append("| 知识点 | 得分率 | 掌握等级 | 关联题目 |")
            lines.append("| --- | ---: | --- | --- |")
            for km in sorted(
                diagnosis.knowledge_mastery,
                key=lambda row: (row.score_rate, row.knowledge_id),
            ):
                item_refs = "、".join(km.item_ids)
                level = _LEVEL_LABELS.get(km.level, km.level)
                lines.append(
                    f"| {km.knowledge_id} | {km.score_rate:.0%} | {level} | {item_refs} |"
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
            for item in diagnosis.interventions:
                lines.append(
                    f"{item.priority}. **{item.title}**（{item.knowledge_id}）"
                )
                lines.append(f"   - 原因：{item.why}")
                lines.append(f"   - 优先修复：{item.what_to_fix_first}")
        else:
            lines.append("_当前无明显薄弱知识点，建议保持复习节奏。_")

    lines.extend(["", "## 学习计划", ""])

    if plan is None:
        lines.append("_暂无学习计划。_")
    else:
        lines.append(plan.markdown)

    if plan is not None and plan.disclaimer:
        lines.extend(["", "## 说明", "", plan.disclaimer])

    return "\n".join(lines).strip()
