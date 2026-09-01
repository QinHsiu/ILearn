"""Build a fully pre-seeded C1 SessionState from a demo unit fixture."""

from __future__ import annotations

from uuid import uuid4

from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    BlueprintSlot,
    DiagnosisReport,
    GradeResult,
    Intervention,
    KnowledgeEvidence,
    KnowledgeMastery,
    LearningPlanReport,
    PaperBlueprint,
    PlanDay,
    SessionPhase,
    SessionState,
    StudentAnswer,
    StudentProfile,
)

_KPS = ("kp_5fbf83ae12", "kp_4433814116", "dec_mult")
_TYPES = ("choice", "fill", "constructed")
_KP_NAMES = {
    "kp_5fbf83ae12": "小数乘整数",
    "kp_4433814116": "小数乘小数",
    "dec_mult": "小数乘法",
}
_DIFFICULTIES = (
    *("easy",) * 10,
    *("medium",) * 8,
    *("hard",) * 2,
)
_STEMS = (
    "超市里苹果每千克 3.5 元，小明买 2 千克。用小数乘法计算应付多少元？",
    "文具店铅笔每支 0.8 元，买 0.5 打（6 支）。用小数乘法算一算要付多少元？",
    "操场一圈 0.4 千米，同学们跑了 3 圈。用小数乘法求一共跑了多少千米？",
    "牛奶每盒 2.5 元，妈妈买了 4 盒。请用小数乘法算出总价。",
    "蛋糕胚用了 0.6 千克面粉，每千克 12.5 元。小数乘法：面粉花了多少元？",
    "公交起步 1.5 元，小明坐了相当于 2 个起步价的路程。用小数乘法求车费。",
    "跳绳比赛每人跳 1.2 分钟，班级安排 5 人接力。用小数乘法求总时长。",
    "公园门票儿童半价 0.5 倍，原价 20 元。用小数乘法计算儿童票价。",
    "科技馆讲解耳机租金每小时 3.5 元，租用 1.5 小时。用小数乘法求租金。",
    "篮球每个 45 元，学校按 0.8 的折扣采购 1 个。用小数乘法求实付。",
    "一本故事书 18.6 元，书店满减后按 0.9 付款。用小数乘法求实付金额。",
    "菜场青菜每千克 2.4 元，买 0.75 千克。用小数乘法计算应付多少元？",
    "游泳馆门票 32 元，家庭套餐打 0.7 折。用小数乘法求套餐价。",
    "做柠檬水用了 0.25 千克柠檬，每千克 16 元。用小数乘法求成本。",
    "运动会跑道每圈 0.25 千米，小明跑了 8 圈。用小数乘法求总路程。",
    "超市大米 5.8 元/千克，买 3 千克。请用小数乘法计算总价。",
    "手工课彩纸每张 0.35 元，买 0.4 刀（10 张为一刀）。用小数乘法求费用。",
    "图书馆复印每页 0.15 元，印了 20 页。用小数乘法求复印费。",
    "水果店草莓 12.8 元/盒，会员打 0.85 折买 1 盒。用小数乘法求实付。",
    "小区物业费每平方米 1.25 元，小明家阳台 6.4 平方米。用小数乘法求费用。",
)
_ANSWER_KEYS = (
    "7",
    "2.4",
    "1.2",
    "10",
    "7.5",
    "3",
    "6",
    "10",
    "5.25",
    "36",
    "16.74",
    "1.8",
    "22.4",
    "4",
    "2",
    "17.4",
    "1.4",
    "3",
    "10.88",
    "8",
)
_CHOICES = (
    ["5", "7", "6.5", "8"],
    ["2.4", "4.8", "0.4", "3.2"],
    ["1.2", "0.7", "3.4", "1.5"],
    ["8", "10", "12", "6"],
    ["6", "7.5", "8", "5.5"],
    ["2", "3", "4.5", "1.5"],
    ["5.2", "6", "7.2", "4"],
    ["10", "15", "20", "5"],
    ["5.25", "4.5", "3.5", "6"],
    ["36", "45", "40", "32"],
    ["16.74", "18.6", "15", "20"],
    ["1.8", "2.4", "3.15", "1.2"],
    ["22.4", "32", "24", "16"],
    ["4", "4.25", "3.5", "5"],
    ["2", "2.5", "1.75", "3"],
    ["17.4", "15.8", "18", "14.4"],
    ["1.4", "3.5", "0.35", "2.8"],
    ["3", "2.5", "4", "1.5"],
    ["10.88", "12.8", "11.5", "9.6"],
    ["8", "7.65", "6.4", "9"],
)


def seed_demo_session(unit: dict, *, session_id: str | None = None) -> SessionState:
    """Build a closed-loop PLAN-phase session for a demo teaching unit."""
    sid = session_id or uuid4().hex
    profile = _profile(unit)
    items = _items()
    grades, answers, evidence = _grades_and_evidence(sid, items)
    diagnosis = _diagnosis(grades)
    plan = _plan()
    paper = AssessmentPaper(
        items=items,
        grade=5,
        curriculum_label="北京·人教·小学数学",
        blueprint=PaperBlueprint(
            grade=5,
            slots=[
                BlueprintSlot(
                    difficulty=item.difficulty,
                    item_type=item.type,
                    knowledge_id=item.knowledge_ids[0],
                )
                for item in items
            ],
        ),
    )
    overrides = unit.get("profile_overrides") or {}
    pre_score = 100.0 * sum(1 for g in grades if g.final_correct) / max(len(grades), 1)
    gain = float(unit.get("demo_mastery_gain", 18.0))
    post_score = max(0.0, min(100.0, pre_score + gain))
    return SessionState(
        session_id=sid,
        profile=profile,
        phase=SessionPhase.PLAN,
        paper=paper,
        answers=answers,
        grades=grades,
        diagnosis=diagnosis,
        plan=plan,
        evidence_log=evidence,
        metadata={
            "demo_unit": unit["id"],
            "demo_class_data": unit.get("demo_class_data") or {},
            "demo_mastery_gain": unit.get("demo_mastery_gain", 18.0),
            "post_assessment_score": post_score,
            "demo_weaknesses_resolved": unit.get("demo_weaknesses_resolved", 1),
            "initial_mastery": unit.get("initial_mastery") or {},
            "parent_view_count": 3,
            "teacher_notes_count": 2,
            "session_duration_seconds": 1680,
            "diagnosis_enrichment": {
                "parent_summary": (
                    "给家长的行动建议：小明在「小数乘整数」上比较稳，"
                    "但「小数乘小数」和运算律推广还薄弱。"
                    "建议每天花约 5 分钟完成 2 道生活情境乘法题，先让孩子口述小数位数再动笔。"
                ),
                "teacher_summary": (
                    "给教师的课堂建议：班级演示学情显示「小数乘小数」与"
                    "「整数乘法运算律推广到小数」是共性薄弱点。"
                    "可用购物找零、折扣变式做形成性抽查，并核对积的小数位数。"
                ),
                "diagnosis_confidence": {"score": 0.82, "label": "较高"},
                "weak_skills": ["kp_4433814116", "dec_mult"],
            },
            "estimated_duration": unit.get("estimated_duration"),
            "nickname": overrides.get("nickname") or profile.nickname,
            "student_summary": {
                "current_task": "巩固：小数乘小数",
                "completed_tasks": 2,
                "total_tasks": 5,
                "stars_earned": 5,
                "next_challenge": "挑战：运算律推广到小数",
                "narrative": "今天又进步啦，继续加油！",
            },
        },
    )


def _profile(unit: dict) -> StudentProfile:
    overrides = unit.get("profile_overrides") or {}
    return StudentProfile(
        region=unit.get("region") or "北京",
        grade=int(unit.get("grade") or 5),
        age=int(overrides.get("age") or 11),
        subject=overrides.get("subject") or "math",
        nickname=overrides.get("nickname") or "小明",
        gender=overrides.get("gender") or "male",
    )


def _items() -> list[AssessmentItem]:
    items: list[AssessmentItem] = []
    for index in range(20):
        item_type = _TYPES[index % 3]
        knowledge_id = _KPS[index % 3]
        answer_key = _ANSWER_KEYS[index]
        items.append(
            AssessmentItem(
                id=f"demo_m51_{index + 1:02d}",
                stem=_STEMS[index],
                type=item_type,
                difficulty=_DIFFICULTIES[index],
                knowledge_ids=[knowledge_id],
                answer_key=answer_key,
                choices=list(_CHOICES[index]) if item_type == "choice" else None,
                rubric_steps=_rubric(knowledge_id) if item_type == "constructed" else [],
                situation_tag="life",
            )
        )
    return items


def _rubric(knowledge_id: str) -> list[str]:
    return [
        f"列出与「{_KP_NAMES[knowledge_id]}」对应的乘法算式",
        "确定积的小数位数并完成计算",
        "结合生活情境写出带单位的答",
    ]


def _is_correct(index: int) -> bool:
    # 12 correct / 8 incorrect, errors biased to 小数乘小数 and dec_mult.
    remainder = index % 3
    if remainder == 0:
        return True
    if remainder == 1:
        return index in {1, 4, 7}
    return index in {2, 5}


def _grades_and_evidence(
    session_id: str, items: list[AssessmentItem]
) -> tuple[list[GradeResult], list[StudentAnswer], list[KnowledgeEvidence]]:
    grades: list[GradeResult] = []
    answers: list[StudentAnswer] = []
    evidence: list[KnowledgeEvidence] = []
    for index, item in enumerate(items):
        correct = _is_correct(index)
        knowledge_id = item.knowledge_ids[0]
        key = item.answer_key or ""
        given = key if correct else "0"
        answers.append(StudentAnswer(item_id=item.id, answer_text=given))
        grades.append(
            GradeResult(
                item_id=item.id,
                final_correct=correct,
                knowledge_ids=[knowledge_id],
                error_tags=[] if correct else ["calc_error"],
                grading_degraded=item.type == "constructed",
                lane="probe",
            )
        )
        evidence.append(
            KnowledgeEvidence(
                session_id=session_id,
                item_id=item.id,
                knowledge_id=knowledge_id,
                lane="probe",
                correct=correct,
                error_tag=None if correct else "calc_error",
                confidence=0.9,
            )
        )
    return grades, answers, evidence


def _diagnosis(grades: list[GradeResult]) -> DiagnosisReport:
    rows: list[KnowledgeMastery] = []
    interventions: list[Intervention] = []
    priority = 1
    for knowledge_id in _KPS:
        related = [g for g in grades if knowledge_id in g.knowledge_ids]
        correct = sum(1 for g in related if g.final_correct)
        score_rate = correct / max(len(related), 1)
        level = _mastery_level(score_rate)
        rows.append(
            KnowledgeMastery(
                knowledge_id=knowledge_id,
                knowledge_name=_KP_NAMES[knowledge_id],
                score_rate=round(score_rate, 2),
                error_tag_counts={"calc_error": len(related) - correct},
                level=level,
                item_ids=[g.item_id for g in related],
            )
        )
        if level == "weak":
            interventions.append(
                Intervention(
                    knowledge_id=knowledge_id,
                    title=f"突破{_KP_NAMES[knowledge_id]}",
                    why=f"本轮测评得分率约 {score_rate:.0%}，生活情境小数乘法易错。",
                    what_to_fix_first="先核对积的小数位数，再口算检验运算律是否用对。",
                    priority=priority,
                )
            )
            priority += 1
    return DiagnosisReport(
        knowledge_mastery=rows,
        interventions=interventions,
        ability_scores={"计算": 0.62, "理解": 0.7, "应用": 0.55},
        curriculum_label="北京·人教·小学数学",
        evidence_refs=[f"demo-ev-{i + 1}" for i in range(len(grades))],
    )


def _mastery_level(score_rate: float) -> str:
    if score_rate >= 0.8:
        return "mastered"
    if score_rate >= 0.5:
        return "unstable"
    return "weak"


def _plan() -> LearningPlanReport:
    markdown = (
        "# 小数乘法学习计划\n\n"
        "**适用年级：** 5年级  \n"
        "**课标：** 北京·人教·小学数学  \n"
        "**建议每日学习：** 25 分钟\n\n"
        "## 目标\n\n"
        "重点突破薄弱知识点「小数乘小数」和「整数乘法运算律推广到小数」，"
        "巩固已掌握的「小数乘整数」。\n\n"
        "## 每日安排\n\n"
        "### 第 1 天\n"
        "- 针对「小数乘小数」做错题回顾，核对积的小数位数\n"
        "- 完成 2 道超市购物变式题\n\n"
        "### 第 2 天\n"
        "- 用分配律把小数乘法拆成整数再合并\n"
        "- 完成 2 道运算律推广练习\n\n"
        "### 第 3 天\n"
        "- 综合生活情境练习并对照评分标准检查步骤\n"
    )
    return LearningPlanReport(
        goal="7 天内突破小数乘小数与运算律推广，稳住小数乘整数。",
        milestones=[
            "第1–2天：突破「小数乘小数」",
            "第3–5天：掌握运算律推广到小数",
            "第6–7天：综合生活情境练习",
        ],
        days=[
            PlanDay(
                day=1,
                focus_knowledge_ids=["kp_4433814116"],
                tasks=["回顾小数乘小数错题", "完成 2 道购物变式"],
                minutes=25,
            ),
            PlanDay(
                day=2,
                focus_knowledge_ids=["dec_mult"],
                tasks=["用分配律拆分小数乘法", "完成 2 道运算律推广题"],
                minutes=25,
            ),
            PlanDay(
                day=3,
                focus_knowledge_ids=["kp_4433814116", "dec_mult"],
                tasks=["综合生活情境练习", "对照评分标准检查步骤"],
                minutes=30,
            ),
        ],
        markdown=markdown,
        status="draft",
    )
