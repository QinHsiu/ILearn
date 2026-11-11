"""Constructed items use open-ended layered grading receipts."""

from ilearn.core.grader import ItemGrader
from ilearn.core.schemas import AssessmentItem


def test_constructed_item_gets_open_ended_receipt_offline():
    grader = ItemGrader(llm=None)
    item = AssessmentItem(
        id="c1",
        stem="用自己的话说明小数乘法的意义",
        type="constructed",
        difficulty="medium",
        knowledge_ids=["dec_mult"],
        answer_key="表示几个相同加数相加",
        rubric_steps=["说明含义", "举一例", "检验"],
    )
    result = grader.grade_item(item, "就是把相同的小数加几次")
    assert result.receipt is not None
    assert result.receipt.receipt_kind == "open_ended"
    assert result.receipt.rubric_version
    assert result.receipt.judge_trace_snapshot
    assert result.receipt.content_hash


def test_choice_item_stays_objective_receipt():
    grader = ItemGrader(llm=None)
    item = AssessmentItem(
        id="c2",
        stem="1+1=?",
        type="choice",
        difficulty="easy",
        knowledge_ids=["dec_mult"],
        answer_key="2",
        choices=["2", "3"],
    )
    result = grader.grade_item(item, "2")
    assert result.receipt is not None
    assert result.receipt.receipt_kind == "objective"
