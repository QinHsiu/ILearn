from pathlib import Path
from random import Random

from ilearn.agents.practice import PracticeAgent
from ilearn.agents.protocol import AgentContext, SessionPhase
from ilearn.core.assessment import build_blueprint, fill_blueprint
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    ImageAnswer,
    StudentProfile,
)
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider

PILOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


def test_image_grade_receipt_records_ocr_confidence():
    item = AssessmentItem(
        id="c1",
        stem="计算 12+8",
        type="constructed",
        difficulty="easy",
        knowledge_ids=["g5_add"],
        answer_key="20",
        rubric_steps=["列式", "计算", "写答"],
    )
    paper = AssessmentPaper(
        items=[item], grade=5, curriculum_label="北京·人教·小学数学"
    )
    result = PracticeAgent(llm=None).run(
        AgentContext(
            session_id="s1",
            phase=SessionPhase.GRADE,
            profile=StudentProfile(region="北京", grade=5, age=11),
            paper=paper,
            image_answers=[
                ImageAnswer(
                    item_id="c1", image_base64="aGVsbG8=", mime_type="image/png"
                )
            ],
        )
    )
    grade = result.payload["grades"][0]
    assert grade.receipt is not None
    assert grade.receipt.ocr_confidence is not None
    assert grade.receipt.ocr_degraded is True


def test_fill_blueprint_respects_seed():
    profile = StudentProfile(region="北京", grade=5, age=11)
    curriculum = PilotBeijingRenjiaoProvider(PILOT)
    bp = build_blueprint(profile)
    p1 = fill_blueprint(profile, bp, curriculum, rng=Random(42))
    p2 = fill_blueprint(profile, bp, curriculum, rng=Random(42))
    assert [i.id for i in p1.items] == [i.id for i in p2.items]
