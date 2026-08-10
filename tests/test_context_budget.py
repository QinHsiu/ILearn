from ilearn.agents.protocol import AgentContext
from ilearn.core.context_budget import trim_context
from ilearn.core.schemas import (
    GradeResult,
    KnowledgeEvidence,
    SessionPhase,
    StudentAnswer,
    StudentProfile,
)


def _evidence(index: int) -> KnowledgeEvidence:
    return KnowledgeEvidence(
        evidence_id=f"ev-{index}",
        session_id="s1",
        item_id=f"q-{index}",
        knowledge_id="frac_add_same",
        lane="practice",
        correct=True,
    )


def test_trim_keeps_recent_evidence_and_profile():
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.DIAGNOSE,
        profile=StudentProfile(region="北京", grade=5, age=11),
        evidence_log=[_evidence(index) for index in range(80)],
    )

    out = trim_context(ctx, max_evidence=40)

    assert len(out.evidence_log) == 40
    assert out.profile.grade == ctx.profile.grade
    assert out.evidence_log[0].evidence_id == "ev-40"
    assert out.evidence_log[-1].evidence_id == ctx.evidence_log[-1].evidence_id
    assert len(ctx.evidence_log) == 80


def test_trim_forced_by_char_budget_drops_oldest_lists_and_adds_summary():
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.DIAGNOSE,
        profile=StudentProfile(region="北京", grade=5, age=11),
        answers=[
            StudentAnswer(item_id=f"q-{index}", answer_text="answer")
            for index in range(2)
        ],
        grades=[
            GradeResult(item_id=f"q-{index}", final_correct=True)
            for index in range(2)
        ],
        evidence_log=[_evidence(index) for index in range(2)],
        metadata={"source": "test"},
    )

    out = trim_context(ctx, max_chars=1)

    assert out.answers == []
    assert out.grades == []
    assert out.metadata["source"] == "test"
    assert "evidence=" in out.metadata["context_summary"]
    assert "grades=2" in out.metadata["context_summary"]
    assert ctx.metadata == {"source": "test"}


def test_trim_char_budget_is_based_on_profile_and_evidence():
    grades = [
        GradeResult(item_id=f"q-{index}", final_correct=index >= 3)
        for index in range(20)
    ]
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.DIAGNOSE,
        profile=StudentProfile(region="北京", grade=5, age=11),
        grades=grades,
        evidence_log=[_evidence(0)],
    )

    out = trim_context(ctx, max_chars=1000)

    assert out.grades == grades
