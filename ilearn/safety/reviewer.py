"""Independent SafetyReviewAgent — rule-based, no LLM, no LearnerState writes."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Literal, Protocol

from pydantic import BaseModel, Field, model_validator


class ReviewRequest(BaseModel):
    request_id: str
    learner_id: str
    originating_agent: str
    content: str
    content_hash: str = ""
    context: dict = Field(default_factory=dict)


class ReviewDecision(BaseModel):
    decision: Literal["allow", "block", "escalate"]
    reason: str = ""
    rule_ids: list[str] = Field(default_factory=list)
    request_id: str
    reviewed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reviewer_version: str = "safety-reviewer/v1"
    decision_hash: str = ""

    def compute_hash(self) -> str:
        return hashlib.sha256(
            self.model_dump_json(exclude={"decision_hash"}).encode("utf-8")
        ).hexdigest()

    @model_validator(mode="after")
    def _seal(self) -> ReviewDecision:
        if not self.decision_hash:
            self.decision_hash = self.compute_hash()
        return self


class SafetyRule(Protocol):
    rule_id: str

    def check(self, req: ReviewRequest) -> tuple[bool, str]: ...


class AnswerLeakRule:
    rule_id = "answer_leak"

    def __init__(self, target_answers: dict[str, str]) -> None:
        self._answers = dict(target_answers)

    def check(self, req: ReviewRequest) -> tuple[bool, str]:
        skill = str(req.context.get("target_skill") or "")
        answer = self._answers.get(skill, "")
        if answer and answer in req.content:
            return False, f"content contains target answer for {skill}"
        return True, ""


class PhaseHintRule:
    """禁止在 practice 阶段返回 level>=3 的提示（防止泄题）。"""

    rule_id = "phase_hint"

    def check(self, req: ReviewRequest) -> tuple[bool, str]:
        if (
            req.context.get("phase") == "practice"
            and int(req.context.get("hint_level") or 0) >= 3
        ):
            return False, "hint level >= 3 not allowed in practice phase"
        return True, ""


class SafetyReviewAgent:
    """最小权限：只读 ReviewRequest，输出 ReviewDecision。"""

    def __init__(self, rules: list[SafetyRule], event_log) -> None:
        self._rules = list(rules)
        self._log = event_log

    def review(self, req: ReviewRequest) -> ReviewDecision:
        if not req.content_hash and req.content:
            req = req.model_copy(
                update={
                    "content_hash": hashlib.sha256(
                        req.content.encode("utf-8")
                    ).hexdigest()
                }
            )
        failures: list[tuple[str, str]] = []
        for rule in self._rules:
            ok, reason = rule.check(req)
            if not ok:
                failures.append((rule.rule_id, reason))
        decision = ReviewDecision(
            decision="block" if failures else "allow",
            reason="; ".join(f"{rid}: {r}" for rid, r in failures) if failures else "",
            rule_ids=[rid for rid, _ in failures],
            request_id=req.request_id,
            reviewed_at=datetime.now(timezone.utc),
        )
        self._log.append(
            "safety.reviewed",
            decision.model_dump(mode="json"),
            req.learner_id,
        )
        return decision
