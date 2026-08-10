from ilearn.core.ocr import OcrExtractor
from ilearn.core.schemas import AssessmentItem


def _constructed_item() -> AssessmentItem:
    return AssessmentItem(
        id="c1",
        stem="计算 12+8",
        type="constructed",
        difficulty="easy",
        knowledge_ids=["g5_add"],
        answer_key="20",
        rubric_steps=["列式", "计算", "写答"],
    )


def test_ocr_extractor_offline_degrades():
    result = OcrExtractor(llm=None).extract(
        item=_constructed_item(),
        image_base64="aGVsbG8=",
        mime_type="image/png",
    )
    assert result.degraded is True
    assert len(result.steps) >= 1
    assert result.confidence == 0.0
