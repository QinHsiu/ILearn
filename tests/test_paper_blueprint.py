import random
from pathlib import Path

import pytest

from ilearn.core.assessment import (
    AssessmentBuildError,
    AssessmentBuilder,
    build_blueprint,
    fill_blueprint,
    validate_paper,
)
from ilearn.core.schemas import StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_blueprint_has_20_slots_with_correct_quotas():
    bp = build_blueprint(StudentProfile(region="北京", grade=5, age=11))
    assert len(bp.slots) == 20
    assert sum(1 for slot in bp.slots if slot.difficulty == "easy") == 10
    assert sum(1 for slot in bp.slots if slot.difficulty == "medium") == 8
    assert sum(1 for slot in bp.slots if slot.difficulty == "hard") == 2
    assert sum(1 for slot in bp.slots if slot.item_type == "choice") == 8
    assert sum(1 for slot in bp.slots if slot.item_type == "fill") == 8
    assert sum(1 for slot in bp.slots if slot.item_type == "constructed") == 4


def test_blueprint_assigns_weak_knowledge_ids():
    bp = build_blueprint(
        StudentProfile(region="北京", grade=5, age=11),
        weak_ids=["frac_add_same", "dec_mult"],
    )
    assigned = [slot.knowledge_id for slot in bp.slots if slot.knowledge_id]
    assert "frac_add_same" in assigned
    assert "dec_mult" in assigned


def test_fill_blueprint_produces_valid_paper():
    profile = StudentProfile(region="北京", grade=5, age=11)
    curriculum = PilotBeijingRenjiaoProvider(PILOT)
    blueprint = build_blueprint(profile)
    paper = fill_blueprint(
        profile,
        blueprint,
        curriculum,
        rng=random.Random(42),
    )
    validate_paper(paper)
    assert paper.blueprint is blueprint
    assert paper.paper_version == "1.0.0"
    assert len(paper.items) == 20


def test_validate_paper_rejects_wrong_size():
    profile = StudentProfile(region="北京", grade=5, age=11)
    curriculum = PilotBeijingRenjiaoProvider(PILOT)
    paper = AssessmentBuilder(curriculum, rng=random.Random(1)).build_followup(
        profile, ["frac_add_same"], size=3
    )
    with pytest.raises(AssessmentBuildError, match="20 items"):
        validate_paper(paper)


def test_two_phase_matches_direct_build_quotas():
    profile = StudentProfile(region="北京", grade=5, age=11)
    curriculum = PilotBeijingRenjiaoProvider(PILOT)
    rng = random.Random(99)
    direct = AssessmentBuilder(curriculum, rng=rng).build(profile)
    blueprint = build_blueprint(profile)
    paper = fill_blueprint(profile, blueprint, curriculum, rng=random.Random(99))
    assert len(direct.items) == len(paper.items) == 20
    for attr in ("easy", "medium", "hard"):
        assert sum(1 for i in paper.items if i.difficulty == attr) == sum(
            1 for i in direct.items if i.difficulty == attr
        )
