from pathlib import Path

from ilearn.agents.diagnosis import DiagnosisAgent, PortraitUpdater
from ilearn.agents.protocol import AgentContext, SessionPhase
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    GradeResult,
    LearnerPortrait,
    StudentProfile,
)
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_portrait_updater_appends_weakness():
    portrait = LearnerPortrait(student_key="bj_g5")
    grade = GradeResult(
        item_id="q1",
        final_correct=False,
        error_tags=["concept_gap"],
        knowledge_ids=["frac_add_same"],
    )
    updated = PortraitUpdater.update(
        portrait,
        [grade],
        session_id="s1",
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        grade=5,
    )
    assert len(updated.weakness_log) == 1
    assert updated.weakness_log[0].knowledge_id == "frac_add_same"
    assert updated.weakness_log[0].topic == "同分母分数加法"
    assert updated.weakness_log[0].logic_gap == "concept_gap"
    assert updated.knowledge_state["frac_add_same"] == 0.4


def test_portrait_updater_skips_correct_grades():
    portrait = LearnerPortrait(student_key="bj_g5")
    grade = GradeResult(
        item_id="q1",
        final_correct=True,
        knowledge_ids=["frac_add_same"],
    )
    updated = PortraitUpdater.update(
        portrait,
        [grade],
        session_id="s1",
        curriculum=PilotBeijingRenjiaoProvider(PILOT),
        grade=5,
    )
    assert updated.weakness_log == []
    assert updated.knowledge_state == {}


def test_diagnosis_agent_returns_top_interventions():
    agent = DiagnosisAgent(PilotBeijingRenjiaoProvider(PILOT))
    paper = AssessmentPaper(
        items=[
            AssessmentItem(
                id="i1",
                stem="q1",
                type="choice",
                difficulty="easy",
                knowledge_ids=["frac_add_same"],
                answer_key="A",
            ),
            AssessmentItem(
                id="i2",
                stem="q2",
                type="fill",
                difficulty="easy",
                knowledge_ids=["dec_mult"],
                answer_key="1",
            ),
        ],
        grade=5,
        curriculum_label="北京·人教·小学数学",
    )
    grades = [
        GradeResult(
            item_id="i1",
            final_correct=False,
            error_tags=["concept_gap"],
            knowledge_ids=["frac_add_same"],
        ),
        GradeResult(
            item_id="i2",
            final_correct=True,
            knowledge_ids=["dec_mult"],
        ),
    ]
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.DIAGNOSE,
        profile=StudentProfile(region="北京", grade=5, age=11),
        paper=paper,
        grades=grades,
    )
    result = agent.run(ctx)
    assert result.phase == SessionPhase.PLAN
    diagnosis = result.payload["diagnosis"]
    portrait = result.payload["portrait"]
    assert len(diagnosis.interventions) <= 5
    assert diagnosis.interventions
    assert portrait.weakness_log[0].knowledge_id == "frac_add_same"
    assert portrait.student_key == "北京_g5"
