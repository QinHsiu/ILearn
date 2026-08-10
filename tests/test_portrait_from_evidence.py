from ilearn.core.diagnosis import PortraitDimensionUpdater
from ilearn.core.schemas import KnowledgeEvidence, LearnerPortrait, MasteryRecord


def test_high_hint_evidence_raises_behavioral_from_evidence_log():
    portrait = LearnerPortrait(student_key="x")
    events = [
        KnowledgeEvidence(
            session_id="s",
            item_id="q1",
            knowledge_id="k",
            lane="practice",
            correct=True,
            hint_level="high",
        )
        for _ in range(3)
    ]
    updated = PortraitDimensionUpdater.apply_from_evidence(portrait, events)
    assert updated.dimensions.behavioral.get("hint_dependency", 0) > 0.2


def test_probe_failures_raise_metacognitive_from_evidence():
    portrait = LearnerPortrait(student_key="x")
    events = [
        KnowledgeEvidence(
            session_id="s",
            item_id="q1",
            knowledge_id="k",
            lane="probe",
            correct=False,
        ),
        KnowledgeEvidence(
            session_id="s",
            item_id="q2",
            knowledge_id="k",
            lane="probe",
            correct=False,
        ),
    ]
    updated = PortraitDimensionUpdater.apply_from_evidence(portrait, events)
    assert updated.dimensions.metacognitive.get("probe_self_check", 0) > 0.0


def test_practice_probe_gap_from_evidence_rates():
    portrait = LearnerPortrait(student_key="x")
    events = [
        KnowledgeEvidence(
            session_id="s",
            item_id="q1",
            knowledge_id="k",
            lane="practice",
            correct=True,
        ),
        KnowledgeEvidence(
            session_id="s",
            item_id="q2",
            knowledge_id="k",
            lane="practice",
            correct=True,
        ),
        KnowledgeEvidence(
            session_id="s",
            item_id="q3",
            knowledge_id="k",
            lane="probe",
            correct=False,
        ),
        KnowledgeEvidence(
            session_id="s",
            item_id="q4",
            knowledge_id="k",
            lane="probe",
            correct=False,
        ),
    ]
    updated = PortraitDimensionUpdater.apply_from_evidence(portrait, events)
    assert updated.dimensions.metacognitive.get("practice_probe_gap", 0) >= 0.2
    portrait.mastery_records["k"] = MasteryRecord(
        practice_score=1.0,
        probe_mastery=0.0,
    )
    updated2 = PortraitDimensionUpdater.apply_from_evidence(portrait, events)
    assert updated2.dimensions.metacognitive.get("practice_probe_gap", 0) >= 0.2
