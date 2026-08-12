from ilearn.core.schemas import StudentProfile


def test_profile_defaults_gender_unspecified():
    p = StudentProfile(region="beijing", grade=5, age=11)
    assert p.nickname is None
    assert p.gender == "unspecified"


def test_profile_accepts_nickname_gender():
    p = StudentProfile(region="beijing", grade=5, age=11, nickname="小明", gender="male")
    assert p.nickname == "小明"
    assert p.gender == "male"
