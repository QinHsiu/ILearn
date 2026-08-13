from pathlib import Path

from ilearn.agents.planning import PlanningAgent, should_enter_practice_loop
from ilearn.agents.protocol import AgentContext, SessionPhase
from ilearn.core.schemas import (
    CurriculumCitation,
    DiagnosisReport,
    Intervention,
    KnowledgeMastery,
    StudentProfile,
)
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_should_loop_when_weak_knowledge_exists():
    diagnosis = DiagnosisReport(
        curriculum_label="北京·人教·小学数学",
        knowledge_mastery=[
            KnowledgeMastery(knowledge_id="k1", score_rate=0.2, level="weak"),
        ],
    )
    assert should_enter_practice_loop(diagnosis, loop_count=0) is True
    assert should_enter_practice_loop(diagnosis, loop_count=2) is False  # cap at 2 loops


def test_should_not_loop_when_no_weak_knowledge():
    diagnosis = DiagnosisReport(
        curriculum_label="北京·人教·小学数学",
        knowledge_mastery=[
            KnowledgeMastery(knowledge_id="k1", score_rate=1.0, level="mastered"),
        ],
    )
    assert should_enter_practice_loop(diagnosis, loop_count=0) is False


def test_planning_agent_includes_citations():
    agent = PlanningAgent(PilotBeijingRenjiaoProvider(PILOT))
    diagnosis = DiagnosisReport(
        curriculum_label="北京·人教·小学数学",
        knowledge_mastery=[
            KnowledgeMastery(knowledge_id="frac_add_same", score_rate=0.2, level="weak"),
        ],
        interventions=[
            Intervention(
                knowledge_id="frac_add_same",
                title="同分母分数加法",
                why="得分率偏低",
                what_to_fix_first="概念理解",
                priority=1,
            ),
        ],
    )
    citations = [
        CurriculumCitation(
            citation_id="bj-g5-frac-01",
            title="分数加减",
            excerpt="同分母分数加减法；异分母需通分。",
            source_label="北京·人教·小学数学",
        ),
    ]
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.PLAN,
        profile=StudentProfile(region="北京", grade=5, age=11),
        diagnosis=diagnosis,
        metadata={"citations": citations},
    )
    result = agent.run(ctx)
    plan = result.payload["plan"]
    assert "本计划为智能助手建议" in plan.disclaimer
    assert "课标依据" in plan.markdown
    assert "分数加减" in plan.markdown
    assert result.payload["should_loop"] is True
    assert result.phase == SessionPhase.PRACTICE_LOOP


def test_planning_agent_stays_on_plan_when_loop_cap_reached():
    agent = PlanningAgent(PilotBeijingRenjiaoProvider(PILOT))
    diagnosis = DiagnosisReport(
        curriculum_label="北京·人教·小学数学",
        knowledge_mastery=[
            KnowledgeMastery(knowledge_id="k1", score_rate=0.2, level="weak"),
        ],
    )
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.PLAN,
        profile=StudentProfile(region="北京", grade=5, age=11),
        diagnosis=diagnosis,
        loop_count=2,
    )
    result = agent.run(ctx)
    assert result.payload["should_loop"] is False
    assert result.phase == SessionPhase.PLAN


def test_planning_agent_allows_third_loop_for_learning_difficulty():
    agent = PlanningAgent(PilotBeijingRenjiaoProvider(PILOT))
    diagnosis = DiagnosisReport(
        curriculum_label="北京·人教·小学数学",
        knowledge_mastery=[
            KnowledgeMastery(knowledge_id="k1", score_rate=0.2, level="weak"),
        ],
    )
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.PLAN,
        profile=StudentProfile(
            region="北京", grade=5, age=11, learning_difficulty=True
        ),
        diagnosis=diagnosis,
        loop_count=3,
    )

    result = agent.run(ctx)

    assert result.payload["should_loop"] is True
    assert result.phase == SessionPhase.PRACTICE_LOOP
