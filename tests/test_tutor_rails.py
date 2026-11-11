"""Pluggable TutorRail checks."""

from ilearn.core.schemas import AssessmentItem
from ilearn.rails.base import AnswerLeakRail, HintLadderRail, run_rails


def _item() -> AssessmentItem:
    return AssessmentItem(
        id="r1",
        stem="1+1=?",
        type="fill",
        difficulty="easy",
        knowledge_ids=["k1"],
        answer_key="2",
    )


def test_hint_ladder_blocks_early_answer():
    rail = HintLadderRail()
    bad = rail.post_model_check(phase="hint_1", item=_item(), model_message="答案是 2")
    assert bad.ok is False
    ok = rail.post_model_check(phase="done", item=_item(), model_message="答案是 2")
    assert ok.ok is True


def test_answer_leak_rail_detects_direct_answer():
    rail = AnswerLeakRail()
    verdict = run_rails(
        [rail],
        phase="hint_1",
        item=_item(),
        model_message="正确答案是 2",
        stage="post",
    )
    assert verdict.ok is False
