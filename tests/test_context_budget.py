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


def _measured_size(ctx: AgentContext) -> int:
    return (
        len(repr(ctx.profile))
        + sum(len(event.model_dump_json()) for event in ctx.evidence_log)
        + sum(
            len(
                grade.model_dump_json(
                    include={
                        "item_id",
                        "final_correct",
                        "error_tags",
                        "knowledge_ids",
                    }
                )
            )
            for grade in ctx.grades
        )
        + sum(
            len(answer.model_dump_json(include={"item_id", "answer_text"}))
            for answer in ctx.answers
        )
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
            StudentAnswer(item_id=f"q-{index}", answer_text="x" * 300)
            for index in range(4)
        ],
        grades=[
            GradeResult(item_id=f"q-{index}", final_correct=True)
            for index in range(4)
        ],
        evidence_log=[_evidence(index) for index in range(2)],
        metadata={"source": "test"},
    )

    out = trim_context(ctx, max_chars=1000)

    assert _measured_size(out) <= 1000
    assert len(out.answers) < len(ctx.answers)
    if out.answers:
        assert out.answers[-1] == ctx.answers[-1]
    assert out.grades == ctx.grades
    assert out.metadata["source"] == "test"
    assert "evidence=" in out.metadata["context_summary"]
    assert "answers=4" in out.metadata["context_summary"]
    assert ctx.metadata == {"source": "test"}


def test_trim_reduces_oldest_evidence_when_lists_cannot_meet_budget():
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.DIAGNOSE,
        profile=StudentProfile(region="北京", grade=5, age=11),
        evidence_log=[_evidence(index) for index in range(10)],
    )

    out = trim_context(ctx, max_chars=400)

    assert _measured_size(out) <= 400
    assert len(out.evidence_log) < len(ctx.evidence_log)
    assert out.evidence_log[-1] == ctx.evidence_log[-1]
    assert "context_summary" in out.metadata


def test_trim_drops_raw_answers_before_derived_grades():
    grades = [GradeResult(item_id="q-0", final_correct=False)]
    ctx = AgentContext(
        session_id="s1",
        phase=SessionPhase.DIAGNOSE,
        profile=StudentProfile(region="北京", grade=5, age=11),
        answers=[
            StudentAnswer(item_id=f"q-{index}", answer_text="x" * 300)
            for index in range(4)
        ],
        grades=grades,
        evidence_log=[_evidence(0)],
    )

    out = trim_context(ctx, max_chars=1000)

    assert out.grades == grades
    assert len(out.answers) < len(ctx.answers)
