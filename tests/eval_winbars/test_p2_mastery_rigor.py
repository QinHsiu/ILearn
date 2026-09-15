"""P2 mastery rigor public view win-bar tests."""

from ilearn.core.mastery import apply_evidence_to_mastery
from ilearn.core.mastery_public import build_mastery_public_view
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    DiagnosisReport,
    HintInteraction,
    KnowledgeEvidence,
    KnowledgeMastery,
    LearnerPortrait,
    MasteryRecord,
    SessionState,
    StudentProfile,
)


def _session() -> SessionState:
    profile = StudentProfile(region="北京", grade=5, age=11, nickname="小明")
    paper = AssessmentPaper(
        items=[
            AssessmentItem(
                id="q1",
                stem="1+1",
                type="fill",
                difficulty="easy",
                knowledge_ids=["kp1"],
            )
        ],
        grade=5,
        curriculum_label="北京·人教",
    )
    diagnosis = DiagnosisReport(
        knowledge_mastery=[
            KnowledgeMastery(
                knowledge_id="kp1",
                knowledge_name="加法",
                score_rate=0.4,
                level="weak",
            ),
            KnowledgeMastery(
                knowledge_id="kp2",
                knowledge_name="小数",
                score_rate=0.55,
                level="unstable",
            ),
        ],
        curriculum_label="北京·人教",
    )
    return SessionState(
        session_id="s1",
        profile=profile,
        paper=paper,
        diagnosis=diagnosis,
        evidence_log=[
            KnowledgeEvidence(
                evidence_id="e1",
                session_id="s1",
                item_id="q1",
                knowledge_id="kp1",
                correct=False,
                lane="practice",
            ),
            KnowledgeEvidence(
                evidence_id="e2",
                session_id="s1",
                item_id="q1",
                knowledge_id="kp1",
                correct=True,
                lane="practice",
            ),
        ],
        hint_interactions={
            "q1": [
                HintInteraction(
                    item_id="q1",
                    turn=1,
                    user_input="不会",
                    ai_hint="想想进位",
                    solved_after_hint=True,
                )
            ]
        },
        metadata={
            "pre_assessment_score": 50,
            "post_assessment_score": 62,
        },
    )


def test_p2_mastery_view_exposes_four_tuple():
    view = build_mastery_public_view(_session())
    assert view.evidence_count == 2
    assert view.probe_gap_count == 2
    assert view.discounted_hint_correct == 1
    assert view.mastery_percent is not None


def test_p2_hint_correct_does_not_raise_probe():
    portrait = LearnerPortrait(
        student_key="s1",
        mastery_records={"kp1": MasteryRecord(probe_mastery=0.4, practice_score=0.4)},
    )
    before = portrait.mastery_records["kp1"].probe_mastery
    apply_evidence_to_mastery(
        portrait,
        [
            KnowledgeEvidence(
                evidence_id="e_hint",
                session_id="s1",
                item_id="q1",
                knowledge_id="kp1",
                correct=True,
                lane="probe",
                hint_level="low",
            )
        ],
    )
    after = portrait.mastery_records["kp1"].probe_mastery
    assert after <= before + 1e-9
