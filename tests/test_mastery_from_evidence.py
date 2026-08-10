from ilearn.core.mastery import apply_evidence_to_mastery, mastery_stars
from ilearn.core.schemas import KnowledgeEvidence, LearnerPortrait


def test_probe_correct_raises_probe_mastery_not_practice():
    portrait = LearnerPortrait(student_key="bj_g5")
    events = [
        KnowledgeEvidence(
            session_id="s1",
            item_id="q1",
            knowledge_id="frac_add_same",
            lane="probe",
            correct=True,
            confidence=1.0,
        )
    ]
    updated = apply_evidence_to_mastery(portrait, events)
    rec = updated.mastery_records["frac_add_same"]
    assert rec.probe_mastery > 0.0
    assert rec.practice_score == 0.0
    assert rec.evidence_count == 1
    assert mastery_stars(rec.probe_mastery) >= 1


def test_practice_correct_raises_practice_not_probe():
    portrait = LearnerPortrait(student_key="bj_g5")
    events = [
        KnowledgeEvidence(
            session_id="s1",
            item_id="q1",
            knowledge_id="frac_add_same",
            lane="practice",
            correct=True,
            confidence=1.0,
        )
    ]
    updated = apply_evidence_to_mastery(portrait, events)
    rec = updated.mastery_records["frac_add_same"]
    assert rec.practice_score > 0.0
    assert rec.probe_mastery == 0.0


def test_mastery_confidence_scales_with_evidence_count():
    from ilearn.core.mastery import mastery_confidence

    portrait = LearnerPortrait(student_key="bj_g5")
    events = [
        KnowledgeEvidence(
            session_id="s1",
            item_id=f"q{i}",
            knowledge_id="frac_add_same",
            lane="probe",
            correct=True,
            confidence=1.0,
        )
        for i in range(3)
    ]
    apply_evidence_to_mastery(portrait, events)
    assert mastery_confidence(3) == 0.5
    assert mastery_confidence(8) == 1.0
