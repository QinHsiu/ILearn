from pathlib import Path

from ilearn.agents.orchestrator import MultiAgentOrchestrator
from ilearn.agents.planning import PlanningAgent
from ilearn.agents.protocol import AgentContext, SessionPhase
from ilearn.core.schemas import (
    DiagnosisReport,
    Intervention,
    KnowledgeMastery,
    LearningPlanReport,
    PlanVersion,
    StudentProfile,
)
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.storage.sessions import SessionStore

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def _sample_diagnosis() -> DiagnosisReport:
    return DiagnosisReport(
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


def test_plan_version_defaults():
    plan = LearningPlanReport(goal="g", markdown="# plan")
    assert plan.version == 1
    assert plan.status == "draft"


def test_replan_supersedes_previous_plan(tmp_path):
    agent = PlanningAgent(PilotBeijingRenjiaoProvider(PILOT))
    profile = StudentProfile(region="北京", grade=5, age=11)
    diagnosis = _sample_diagnosis()
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.PLAN,
        profile=profile,
        diagnosis=diagnosis,
    )
    first = agent.run(ctx).payload["plan"]
    assert first.version == 1
    assert first.status == "draft"

    ctx2 = AgentContext(
        session_id="s1",
        phase=SessionPhase.PLAN,
        profile=profile,
        diagnosis=diagnosis,
        plan=first,
    )
    result = agent.run(ctx2)
    second = result.payload["plan"]
    history = result.payload["plan_history_append"]

    assert second.version == 2
    assert second.status == "draft"
    assert len(history) == 1
    assert history[0].status == "superseded"
    assert history[0].version == 1
    assert history[0].plan.status == "superseded"


def test_orchestrator_persists_plan_history_on_replan(tmp_path):
    orch = MultiAgentOrchestrator(
        store=SessionStore(tmp_path),
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        llm=None,
    )
    sid = orch.create_session(StudentProfile(region="北京", grade=5, age=11))
    paper = orch.generate_assessment(sid)
    answers = {item.id: (item.answer_key or "") for item in paper.items}
    orch.submit(sid, answers)
    orch.grade(sid)
    orch.diagnose(sid)
    orch.plan(sid)
    orch.plan(sid)

    session = orch._store.load(sid)
    assert session.plan is not None
    assert session.plan.version == 2
    assert len(session.plan_history) >= 1
    assert session.plan_history[0].status == "superseded"
    assert isinstance(session.plan_history[0], PlanVersion)
