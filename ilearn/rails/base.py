"""TutorRail protocol — Hint Ladder and answer-leak checks as pluggable rails."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ilearn.agents.guard import GuardAgent, GuardVerdict
from ilearn.core.schemas import AssessmentItem, TutorPhase


@dataclass(frozen=True)
class RailVerdict:
    ok: bool
    reason: str = ""
    rewritten_message: str | None = None


@runtime_checkable
class TutorRail(Protocol):
    name: str

    def pre_model_check(
        self,
        *,
        phase: TutorPhase,
        item: AssessmentItem,
        student_message: str,
    ) -> RailVerdict: ...

    def post_model_check(
        self,
        *,
        phase: TutorPhase,
        item: AssessmentItem,
        model_message: str,
    ) -> RailVerdict: ...


class HintLadderRail:
    """Forbid giving the final answer while still on early hint phases."""

    name = "hint_ladder"

    _BLOCK_PHASES = frozenset({"locate_gap", "hint_1", "hint_2", "retry"})

    def pre_model_check(
        self,
        *,
        phase: TutorPhase,
        item: AssessmentItem,
        student_message: str,
    ) -> RailVerdict:
        return RailVerdict(ok=True)

    def post_model_check(
        self,
        *,
        phase: TutorPhase,
        item: AssessmentItem,
        model_message: str,
    ) -> RailVerdict:
        if phase not in self._BLOCK_PHASES:
            return RailVerdict(ok=True)
        key = (item.answer_key or "").strip()
        if key and key in (model_message or ""):
            return RailVerdict(ok=False, reason="hint_ladder_blocks_answer")
        return RailVerdict(ok=True)


class AnswerLeakRail:
    """Standalone leak detector extracted from GuardAgent for unit testing."""

    name = "answer_leak"

    def __init__(self, guard: GuardAgent | None = None) -> None:
        self._guard = guard or GuardAgent()

    def pre_model_check(
        self,
        *,
        phase: TutorPhase,
        item: AssessmentItem,
        student_message: str,
    ) -> RailVerdict:
        return RailVerdict(ok=True)

    def post_model_check(
        self,
        *,
        phase: TutorPhase,
        item: AssessmentItem,
        model_message: str,
    ) -> RailVerdict:
        verdict: GuardVerdict = self._guard.check(model_message, item.answer_key)
        if verdict.is_leak:
            return RailVerdict(ok=False, reason=verdict.reason or "answer_leak")
        return RailVerdict(ok=True)


def run_rails(
    rails: list[TutorRail],
    *,
    phase: TutorPhase,
    item: AssessmentItem,
    student_message: str = "",
    model_message: str = "",
    stage: str = "post",
) -> RailVerdict:
    for rail in rails:
        if stage == "pre":
            verdict = rail.pre_model_check(
                phase=phase, item=item, student_message=student_message
            )
        else:
            verdict = rail.post_model_check(
                phase=phase, item=item, model_message=model_message
            )
        if not verdict.ok:
            return verdict
    return RailVerdict(ok=True)
