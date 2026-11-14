"""P8: SafetyReviewAgent."""

from ilearn.safety.reviewer import AnswerLeakRule, ReviewRequest, SafetyReviewAgent


class FakeEventLog:
    def __init__(self) -> None:
        self.rows: list[tuple] = []

    def append(self, event_type: str, payload: dict, learner_id: str) -> str:
        self.rows.append((event_type, payload, learner_id))
        return f"e{len(self.rows)}"


def test_blocks_answer_leak():
    log = FakeEventLog()
    agent = SafetyReviewAgent([AnswerLeakRule({"frac.add": "1/2"})], log)
    req = ReviewRequest(
        request_id="r1",
        learner_id="L1",
        originating_agent="tutor",
        content="答案是 1/2",
        content_hash="",
        context={"target_skill": "frac.add"},
    )
    decision = agent.review(req)
    assert decision.decision == "block"
    assert "answer_leak" in decision.rule_ids
    assert decision.decision_hash == decision.compute_hash()
    assert log.rows and log.rows[0][0] == "safety.reviewed"


def test_allows_clean_content():
    agent = SafetyReviewAgent(
        [AnswerLeakRule({"frac.add": "1/2"})], FakeEventLog()
    )
    req = ReviewRequest(
        request_id="r1",
        learner_id="L1",
        originating_agent="tutor",
        content="先想一下分母应该怎么处理",
        content_hash="",
        context={"target_skill": "frac.add"},
    )
    assert agent.review(req).decision == "allow"
