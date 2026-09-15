"""TutorAgent uses free LLM hints and falls back to the rule engine."""

from unittest.mock import MagicMock

from ilearn.agents.tutor import TutorAgent
from ilearn.core.schemas import AssessmentItem
from ilearn.providers.llm import LLMError

_ITEM = AssessmentItem(
    id="t1",
    stem="1/2 + 1/3 = ?",
    type="fill",
    difficulty="easy",
    knowledge_ids=["fraction_add"],
    answer_key="5/6",
    rubric_steps=["通分", "相加", "化简"],
)


def test_tutor_uses_llm_hint_when_available():
    llm = MagicMock()
    llm.available.return_value = True
    llm.chat_text.return_value = "通分时，分母应该变成几？"
    turn = TutorAgent(llm=llm).step("locate_gap", "我直接把分子分母加了", _ITEM, "calc_error")
    assert turn.phase == "hint_1"
    assert "通分时，分母应该变成几" in turn.message
    llm.chat_text.assert_called_once()
    user_prompt = llm.chat_text.call_args.kwargs.get("user") or llm.chat_text.call_args[0][1]
    assert "5/6" not in user_prompt


def test_tutor_falls_back_when_llm_fails():
    llm = MagicMock()
    llm.available.return_value = True
    llm.chat_text.side_effect = LLMError("rate limited")
    turn = TutorAgent(llm=llm).step("locate_gap", "不会", _ITEM, "calc_error")
    assert turn.phase == "hint_1"
    assert "从这个方向入手" in turn.message


def test_tutor_redacts_answer_if_llm_leaks():
    llm = MagicMock()
    llm.available.return_value = True
    llm.chat_text.return_value = "正确答案是 5/6，你再算一遍。"
    turn = TutorAgent(llm=llm).step("hint_1", "还是不会", _ITEM)
    assert "5/6" not in turn.message


def test_tutor_without_llm_keeps_rule_engine():
    turn = TutorAgent(llm=None).step("locate_gap", "第二步", _ITEM, "calc_error")
    assert turn.phase == "hint_1"
    assert "从这个方向入手" in turn.message
