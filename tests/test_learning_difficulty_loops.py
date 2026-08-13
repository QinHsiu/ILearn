from ilearn.agents.planning import max_practice_loops, should_enter_practice_loop
from ilearn.core.schemas import (
    DiagnosisReport,
    KnowledgeMastery,
    StudentProfile,
)


def test_learning_difficulty_allows_four_practice_loops():
    profile = StudentProfile(region="北京", grade=5, age=11, learning_difficulty=True)
    assert max_practice_loops(profile) == 4


def test_standard_profile_allows_two_practice_loops():
    profile = StudentProfile(region="北京", grade=5, age=11)
    assert max_practice_loops(profile) == 2


def test_practice_loop_uses_profile_specific_cap():
    diagnosis = DiagnosisReport(
        curriculum_label="pilot",
        knowledge_mastery=[
            KnowledgeMastery(
                knowledge_id="k",
                score_rate=0.0,
                level="weak",
                item_ids=["i"],
            )
        ],
    )
    difficult = StudentProfile(
        region="北京", grade=5, age=11, learning_difficulty=True
    )
    standard = StudentProfile(region="北京", grade=5, age=11)

    assert should_enter_practice_loop(diagnosis, 3, profile=difficult)
    assert not should_enter_practice_loop(diagnosis, 2, profile=standard)
