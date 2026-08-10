from ilearn.core.grader import GRADER_VERSION, ItemGrader
from ilearn.core.schemas import AssessmentItem


def test_item_grader_offline_choice():
    grader = ItemGrader(llm=None)
    item = AssessmentItem(
        id="c1",
        stem="1+1=?",
        type="choice",
        difficulty="easy",
        knowledge_ids=["dec_mult"],
        answer_key="2",
        choices=["2", "3", "4", "5"],
    )
    result = grader.grade_item(item, "2")
    assert result.final_correct is True
    assert GRADER_VERSION
