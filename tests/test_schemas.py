from ilearn.core.schemas import StudentProfile, AssessmentPaper, ERROR_TAGS


def test_profile_grade_must_be_4_to_6():
    StudentProfile(region="北京", grade=5, age=11)
    try:
        StudentProfile(region="北京", grade=3, age=9)
        assert False, "expected validation error"
    except Exception:
        pass


def test_error_tags_controlled_vocab():
    assert "calc_error" in ERROR_TAGS
    assert len(ERROR_TAGS) == 5
