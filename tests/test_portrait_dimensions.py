from ilearn.agents.diagnosis import PortraitDimensionUpdater
from ilearn.core.schemas import GradeResult, LearnerPortrait, MasteryRecord


def test_high_hint_increases_behavioral_score():
    portrait = LearnerPortrait(student_key="bj_g5")
    grade = GradeResult(
        item_id="q1",
        final_correct=False,
        hint_level_suggestion="high",
        knowledge_ids=["frac_add_same"],
    )
    updated = PortraitDimensionUpdater.apply(portrait, [grade])
    assert updated.dimensions.behavioral.get("hint_dependency", 0.0) > 0.0


def test_consecutive_wrong_increases_emotional_frustration():
    portrait = LearnerPortrait(student_key="bj_g5")
    grades = [
        GradeResult(item_id="q1", final_correct=False, knowledge_ids=["frac_add_same"]),
        GradeResult(item_id="q2", final_correct=False, knowledge_ids=["dec_mult"]),
    ]
    updated = PortraitDimensionUpdater.apply(portrait, grades)
    assert updated.dimensions.emotional.get("frustration", 0.0) > 0.0


def test_probe_gap_sets_metacognitive_flag():
    portrait = LearnerPortrait(student_key="bj_g5")
    portrait.mastery_records["frac_add_same"] = MasteryRecord(
        practice_score=0.8,
        probe_mastery=0.4,
    )
    grade = GradeResult(
        item_id="q1",
        final_correct=True,
        knowledge_ids=["frac_add_same"],
        lane="practice",
    )
    updated = PortraitDimensionUpdater.apply(portrait, [grade])
    assert updated.dimensions.metacognitive.get("practice_probe_gap", 0.0) >= 0.2


def test_portrait_dimensions_default_empty():
    portrait = LearnerPortrait(student_key="bj_g5")
    assert portrait.dimensions.cognitive == {}
    assert portrait.dimensions.behavioral == {}
