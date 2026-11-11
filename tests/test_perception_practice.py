"""PracticeAgent can grade PerceptionOutput list without changing state machine."""

from ilearn.agents.practice import PracticeAgent
from ilearn.core.schemas import AssessmentItem, AssessmentPaper
from ilearn.perception.adapter import PerceptionOutput


def test_grade_perception_outputs_text_source():
    agent = PracticeAgent(llm=None)
    item = AssessmentItem(
        id="p1",
        stem="1+1=?",
        type="fill",
        difficulty="easy",
        knowledge_ids=["dec_mult"],
        answer_key="2",
    )
    paper = AssessmentPaper(curriculum_label="test", grade=5, items=[item])
    outputs = [
        PerceptionOutput(text="2", source_type="text", confidence=0.99, raw_ref="stdin")
    ]
    grades = agent.grade_perception_outputs(paper, outputs)
    assert len(grades) == 1
    assert grades[0].final_correct is True
    assert grades[0].receipt is not None
    assert grades[0].receipt.ocr_confidence == 0.99
