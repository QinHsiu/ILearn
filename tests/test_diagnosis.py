from pathlib import Path

import pytest

from ilearn.core.diagnosis import Diagnoser
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    GradeResult,
    StudentProfile,
)
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

ROOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


@pytest.fixture
def diagnoser():
    return Diagnoser(PilotBeijingRenjiaoProvider(ROOT))


@pytest.fixture
def profile_beijing():
    return StudentProfile(region="北京", grade=5, age=11)


@pytest.fixture
def profile_shanghai():
    return StudentProfile(region="上海", grade=5, age=11)


def make_paper(*items: AssessmentItem) -> AssessmentPaper:
    return AssessmentPaper(
        items=list(items),
        grade=5,
        curriculum_label="北京·人教·小学数学",
    )


def make_grade(item_id: str, correct: bool, knowledge_ids: list[str], **tags) -> GradeResult:
    return GradeResult(
        item_id=item_id,
        final_correct=correct,
        knowledge_ids=knowledge_ids,
        error_tags=tags.get("error_tags", []),
    )


def test_top5_and_traceable(diagnoser, profile_beijing):
    paper = make_paper(
        AssessmentItem(
            id="i1",
            stem="q1",
            type="choice",
            difficulty="easy",
            knowledge_ids=["frac_add_same"],
            answer_key="A",
        ),
        AssessmentItem(
            id="i2",
            stem="q2",
            type="fill",
            difficulty="easy",
            knowledge_ids=["dec_mult"],
            answer_key="1",
        ),
        AssessmentItem(
            id="i3",
            stem="q3",
            type="fill",
            difficulty="medium",
            knowledge_ids=["simple_eq"],
            answer_key="2",
        ),
        AssessmentItem(
            id="i4",
            stem="q4",
            type="choice",
            difficulty="medium",
            knowledge_ids=["frac_mult"],
            answer_key="B",
        ),
        AssessmentItem(
            id="i5",
            stem="q5",
            type="fill",
            difficulty="hard",
            knowledge_ids=["frac_add_same"],
            answer_key="3",
        ),
        AssessmentItem(
            id="i6",
            stem="q6",
            type="choice",
            difficulty="easy",
            knowledge_ids=["dec_mult"],
            answer_key="C",
        ),
    )
    grades = [
        make_grade("i1", False, ["frac_add_same"], error_tags=["concept_gap"]),
        make_grade("i2", False, ["dec_mult"], error_tags=["calc_error"]),
        make_grade("i3", False, ["simple_eq"], error_tags=["method_wrong"]),
        make_grade("i4", True, ["frac_mult"]),
        make_grade("i5", False, ["frac_add_same"], error_tags=["concept_gap"]),
        make_grade("i6", True, ["dec_mult"]),
    ]
    d = diagnoser.diagnose(profile_beijing, paper, grades)
    assert len(d.interventions) <= 5
    assert d.curriculum_label.startswith("北京")
    assert d.knowledge_mastery
    for km in d.knowledge_mastery:
        assert km.item_ids
        assert 0.0 <= km.score_rate <= 1.0


def test_mastery_level_thresholds(diagnoser, profile_beijing):
    paper = make_paper(
        AssessmentItem(
            id="a",
            stem="a",
            type="choice",
            difficulty="easy",
            knowledge_ids=["frac_add_same"],
            answer_key="A",
        ),
        AssessmentItem(
            id="b",
            stem="b",
            type="choice",
            difficulty="easy",
            knowledge_ids=["frac_add_same"],
            answer_key="B",
        ),
        AssessmentItem(
            id="c",
            stem="c",
            type="choice",
            difficulty="easy",
            knowledge_ids=["dec_mult"],
            answer_key="C",
        ),
        AssessmentItem(
            id="d",
            stem="d",
            type="choice",
            difficulty="easy",
            knowledge_ids=["dec_mult"],
            answer_key="D",
        ),
    )
    grades = [
        make_grade("a", True, ["frac_add_same"]),
        make_grade("b", True, ["frac_add_same"]),
        make_grade("c", True, ["dec_mult"]),
        make_grade("d", False, ["dec_mult"], error_tags=["calc_error"]),
    ]
    d = diagnoser.diagnose(profile_beijing, paper, grades)
    by_id = {km.knowledge_id: km for km in d.knowledge_mastery}
    assert by_id["frac_add_same"].level == "mastered"
    assert by_id["frac_add_same"].score_rate >= 0.8
    assert by_id["dec_mult"].level == "unstable"
    assert 0.5 <= by_id["dec_mult"].score_rate < 0.8


def test_weak_mastery_level(diagnoser, profile_beijing):
    paper = make_paper(
        AssessmentItem(
            id="w1",
            stem="w",
            type="fill",
            difficulty="easy",
            knowledge_ids=["simple_eq"],
            answer_key="1",
        ),
        AssessmentItem(
            id="w2",
            stem="w2",
            type="fill",
            difficulty="easy",
            knowledge_ids=["simple_eq"],
            answer_key="2",
        ),
    )
    grades = [
        make_grade("w1", False, ["simple_eq"], error_tags=["concept_gap"]),
        make_grade("w2", False, ["simple_eq"], error_tags=["concept_gap"]),
    ]
    d = diagnoser.diagnose(profile_beijing, paper, grades)
    km = next(x for x in d.knowledge_mastery if x.knowledge_id == "simple_eq")
    assert km.level == "weak"
    assert km.score_rate < 0.5


def test_region_mismatch_disclaimer(diagnoser, profile_shanghai):
    paper = make_paper(
        AssessmentItem(
            id="x",
            stem="x",
            type="choice",
            difficulty="easy",
            knowledge_ids=["frac_add_same"],
            answer_key="A",
        ),
    )
    grades = [make_grade("x", True, ["frac_add_same"])]
    d = diagnoser.diagnose(profile_shanghai, paper, grades)
    assert d.region_mismatch_disclaimer
    assert "北京" in d.region_mismatch_disclaimer


def test_beijing_no_disclaimer(diagnoser, profile_beijing):
    paper = make_paper(
        AssessmentItem(
            id="x",
            stem="x",
            type="choice",
            difficulty="easy",
            knowledge_ids=["frac_add_same"],
            answer_key="A",
        ),
    )
    grades = [make_grade("x", True, ["frac_add_same"])]
    d = diagnoser.diagnose(profile_beijing, paper, grades)
    assert d.region_mismatch_disclaimer is None


def test_beijing_english_no_disclaimer(diagnoser):
    profile = StudentProfile(region="Beijing", grade=5, age=11)
    paper = make_paper(
        AssessmentItem(
            id="x",
            stem="x",
            type="choice",
            difficulty="easy",
            knowledge_ids=["frac_add_same"],
            answer_key="A",
        ),
    )
    grades = [make_grade("x", True, ["frac_add_same"])]
    d = diagnoser.diagnose(profile, paper, grades)
    assert d.region_mismatch_disclaimer is None


def test_ability_scores_in_range(diagnoser, profile_beijing):
    paper = make_paper(
        AssessmentItem(
            id="l1",
            stem="l",
            type="choice",
            difficulty="easy",
            knowledge_ids=["frac_add_same"],
            answer_key="A",
        ),
        AssessmentItem(
            id="m1",
            stem="m",
            type="fill",
            difficulty="easy",
            knowledge_ids=["dec_mult"],
            answer_key="1",
        ),
    )
    grades = [
        make_grade("l1", False, ["frac_add_same"], error_tags=["method_wrong"]),
        make_grade("m1", True, ["dec_mult"]),
    ]
    d = diagnoser.diagnose(profile_beijing, paper, grades)
    assert d.ability_scores
    for tag, score in d.ability_scores.items():
        assert 0.0 <= score <= 100.0
        assert tag in {"logic", "spatial", "mental_math"}


def test_ability_error_penalty_is_mean_per_item(diagnoser, profile_beijing):
    items = [
        AssessmentItem(
            id=f"i{index}",
            stem="fraction question",
            type="fill",
            difficulty="easy",
            knowledge_ids=["frac_add_same"],
            answer_key="1",
        )
        for index in range(20)
    ]
    grades = [
        make_grade(
            item.id,
            index < 10,
            ["frac_add_same"],
            error_tags=[] if index < 10 else ["calc_error"],
        )
        for index, item in enumerate(items)
    ]

    diagnosis = diagnoser.diagnose(profile_beijing, make_paper(*items), grades)

    assert diagnosis.ability_scores["logic"] == pytest.approx(47.5)


def test_interventions_sorted_weakest_first(diagnoser, profile_beijing):
    paper = make_paper(
        AssessmentItem(
            id="k1",
            stem="k1",
            type="choice",
            difficulty="easy",
            knowledge_ids=["frac_add_same"],
            answer_key="A",
        ),
        AssessmentItem(
            id="k2",
            stem="k2",
            type="choice",
            difficulty="easy",
            knowledge_ids=["dec_mult"],
            answer_key="B",
        ),
        AssessmentItem(
            id="k3",
            stem="k3",
            type="choice",
            difficulty="easy",
            knowledge_ids=["simple_eq"],
            answer_key="C",
        ),
    )
    grades = [
        make_grade("k1", False, ["frac_add_same"], error_tags=["concept_gap"]),
        make_grade("k2", True, ["dec_mult"]),
        make_grade("k3", False, ["simple_eq"], error_tags=["concept_gap"]),
    ]
    d = diagnoser.diagnose(profile_beijing, paper, grades)
    assert d.interventions
    rates = {
        km.knowledge_id: km.score_rate
        for km in d.knowledge_mastery
        if km.level != "mastered"
    }
    prev_rate = -1.0
    for iv in d.interventions:
        assert iv.priority >= 1
        rate = rates[iv.knowledge_id]
        assert rate >= prev_rate or prev_rate == -1.0
        prev_rate = rate
