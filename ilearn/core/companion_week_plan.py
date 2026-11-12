"""Companion Plan — offline executable week schedule (Phase-1)."""

from __future__ import annotations

from typing import Any

from ilearn.core.schemas import SessionState

_DAYS = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")

_STAGE_FOCUS: dict[str, list[str]] = {
    "primary": ["口算巩固", "概念微课", "错题重练", "亲子口述"],
    "junior_high": ["有理数/方程练习", "错题归因", "例题精读", "周末小测"],
    "senior_high": ["函数与导数专项", "错题本复盘", "限时套题", "易错点清单"],
    "undergrad": ["课程周任务拆解", "习题集精做", "概念卡片", "答疑整理"],
    "graduate": ["文献精读块", "方法笔记", "实验/推导检查点", "组会材料"],
    "early_childhood": ["游戏化数感", "短时专注", "亲子共读", "休息日"],
    "career": ["技能微课", "项目练习", "复盘", "休息"],
    "midlife": ["目标回顾", "微练习", "复盘", "休息"],
    "elder": ["兴趣微课", "轻松练习", "复盘", "休息"],
}


def _weak_labels(session: SessionState) -> list[str]:
    if session.diagnosis is None:
        return []
    labels: list[str] = []
    for row in session.diagnosis.knowledge_mastery:
        if row.level in {"weak", "unstable"}:
            labels.append(row.knowledge_name or row.knowledge_id)
    return labels[:6]


def build_week_plan(session: SessionState) -> dict[str, Any]:
    # Local import avoids circular dependency with CompanionAgent.
    from ilearn.agents.companion import infer_life_stage

    stage = infer_life_stage(session.profile)
    focus = list(_STAGE_FOCUS.get(stage, _STAGE_FOCUS["primary"]))
    weaks = _weak_labels(session)
    if weaks:
        # Prefer weak skills early in the week.
        focus = (weaks + focus)[:4]

    if session.plan is not None and (session.plan.markdown or "").strip():
        source = "session_plan"
        note = "已结合会话中的学习计划摘要。"
    elif weaks:
        source = "diagnosis"
        note = "根据诊断薄弱点生成。"
    else:
        source = "stage_default"
        note = "尚无测评证据，使用学段默认周计划；建议先测评再精修。"

    days: list[dict[str, Any]] = []
    for i, day in enumerate(_DAYS):
        task = focus[i % len(focus)]
        minutes = 25 if i < 5 else 40
        days.append(
            {
                "day": day,
                "task": task,
                "minutes": minutes,
                "slot": "放学后" if i < 5 else "上午",
            }
        )

    return {
        "life_stage": stage,
        "source": source,
        "note": note,
        "weak_focus": weaks,
        "days": days,
        "total_minutes": sum(d["minutes"] for d in days),
    }


def format_week_plan_reply(plan: dict[str, Any]) -> str:
    lines = [
        f"这是本周可执行安排（{plan.get('life_stage')} · {plan.get('note')}）：",
    ]
    for d in plan.get("days") or []:
        lines.append(
            f"- {d['day']}{d.get('slot', '')}：{d['task']}（约 {d['minutes']} 分钟）"
        )
    lines.append(f"合计约 {plan.get('total_minutes', 0)} 分钟。需要调整强度或先测评定位缺口，直接告诉我。")
    return "\n".join(lines)
