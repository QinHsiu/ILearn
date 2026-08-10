from datetime import datetime, timezone

from ilearn.core.grader import GRADER_VERSION, ItemGrader
from ilearn.core.schemas import AssessmentItem, GradingReceipt


def test_grade_result_includes_receipt():
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
    paper_created_at = datetime(2026, 8, 10, tzinfo=timezone.utc)
    result = grader.grade_item(item, "2", paper_created_at=paper_created_at)
    assert result.receipt is not None
    assert result.receipt.grader_version == GRADER_VERSION
    assert result.receipt.paper_created_at == paper_created_at
    assert result.receipt.model_id is None


class _FakeLLM:
    """Minimal stand-in exposing the real LLMClient's `.model` attribute name."""

    def __init__(self, model: str) -> None:
        self.model = model

    def available(self) -> bool:
        return False


def test_grade_result_receipt_captures_model_id_from_llm_model_attr():
    grader = ItemGrader(llm=_FakeLLM("gpt-test"))
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
    assert result.receipt is not None
    assert result.receipt.model_id == "gpt-test"
