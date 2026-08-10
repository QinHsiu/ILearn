from ilearn.agents.diagnosis import PortraitDimensionUpdater
from ilearn.core.schemas import GradeResult, LearnerPortrait, StudentProfile


def test_contextual_dimensions_set_from_profile():
    portrait = LearnerPortrait(student_key="bj_g5")
    profile = StudentProfile(region="北京", grade=5, age=11)
    grade = GradeResult(item_id="q1", final_correct=True, knowledge_ids=["frac_add_same"])
    updated = PortraitDimensionUpdater.apply(portrait, [grade], profile=profile)
    assert updated.dimensions.contextual.get("grade_band", 0.0) > 0.0
    assert updated.dimensions.contextual.get("region_weight", 0.0) > 0.0
