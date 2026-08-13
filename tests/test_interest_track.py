import random
from pathlib import Path

from ilearn.core.assessment import AssessmentBuilder
from ilearn.core.diagnosis import PortraitUpdater
from ilearn.core.schemas import GradeResult, LearnerPortrait, StudentProfile
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider


ROOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_portrait_updates_situation_interest_from_answer_signals():
    portrait = LearnerPortrait(student_key="student")
    grades = [
        GradeResult(
            item_id="sports-item",
            final_correct=True,
            knowledge_ids=["rect_area"],
        ),
        GradeResult(
            item_id="sports-skipped",
            final_correct=False,
            knowledge_ids=["rect_area"],
        ),
    ]

    PortraitUpdater.update(
        portrait,
        grades,
        "session",
        PilotBeijingRenjiaoProvider(ROOT),
        item_meta={
            "sports-item": {"elapsed_ms": 5000},
            "sports-skipped": {"skipped": True, "elapsed_ms": 1000},
        },
        item_situations={"sports-item": "sports", "sports-skipped": "sports"},
    )

    assert portrait.situation_interest["sports"] < 0.5
    assert portrait.situation_interest["sports"] > 0.0


def test_builder_biases_toward_known_preferred_situation():
    provider = PilotBeijingRenjiaoProvider(ROOT)
    profile = StudentProfile(region="北京", grade=5, age=11)
    portrait = LearnerPortrait(
        student_key="student",
        situation_interest={"sports": 1.0},
    )

    paper = AssessmentBuilder(provider, rng=random.Random(3)).build(
        profile, portrait=portrait
    )

    assert any(item.situation_tag == "sports" for item in paper.items)
