"""Session phase transition guard and history."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ilearn.core.schemas import SessionPhase, SessionState
from ilearn.core.session_paper import has_assessment_paper
from ilearn.core.user_errors import UserFriendlyError

# Legal edges matching the sync orchestrator (not the idealized async sketch).
_TRANSITIONS: dict[SessionPhase, set[SessionPhase]] = {
    SessionPhase.ONBOARD: {
        SessionPhase.ASSESS,
        SessionPhase.PRACTICE,
        SessionPhase.DIAGNOSE,
        SessionPhase.PLAN,
    },
    SessionPhase.ASSESS: {SessionPhase.PRACTICE, SessionPhase.ASSESS},
    SessionPhase.PRACTICE: {
        SessionPhase.GRADE,
        SessionPhase.PRACTICE,
        SessionPhase.ASSESS,
        SessionPhase.DIAGNOSE,
        SessionPhase.PLAN,
    },
    SessionPhase.GRADE: {
        SessionPhase.DIAGNOSE,
        SessionPhase.GRADE,
        SessionPhase.PRACTICE,
    },
    SessionPhase.DIAGNOSE: {SessionPhase.PLAN, SessionPhase.DIAGNOSE},
    SessionPhase.PLAN: {
        SessionPhase.PLAN,
        SessionPhase.PRACTICE_LOOP,
        SessionPhase.PRACTICE,
    },
    SessionPhase.PRACTICE_LOOP: {
        SessionPhase.PRACTICE,
        SessionPhase.GRADE,
        SessionPhase.PRACTICE_LOOP,
        SessionPhase.PLAN,
    },
}


class PhaseGuard:
    """Validate phase moves and record phase_history on the session."""

    @classmethod
    def can_transition(cls, current: SessionPhase, target: SessionPhase) -> bool:
        if current == target:
            return True
        return target in _TRANSITIONS.get(current, set())

    @classmethod
    def assert_transition(
        cls, current: SessionPhase, target: SessionPhase
    ) -> None:
        if cls.can_transition(current, target):
            return
        raise UserFriendlyError(
            "E-010",
            technical_detail=f"illegal phase transition: {current.value} -> {target.value}",
            user_action=(
                f"当前阶段为「{current.value}」，无法进入「{target.value}」。"
                "请按测评 → 提交 → 批改 → 诊断 → 规划的顺序操作。"
            ),
        )

    @classmethod
    def assert_ready_for(cls, action: str, session: SessionState) -> None:
        """Data completeness checks before orchestrator actions."""
        if action in {"submit", "grade"}:
            if session.paper is None:
                raise UserFriendlyError(
                    "E-011",
                    technical_detail="missing assessment paper",
                    user_action="请先生成测评卷，再继续作答或辅导。",
                )
        if action == "tutor":
            if not has_assessment_paper(session):
                raise UserFriendlyError(
                    "E-011",
                    technical_detail="missing assessment paper",
                    user_action="请先生成测评卷，再继续作答或辅导。",
                )
        if action == "grade":
            if not session.answers and not session.image_answers:
                raise UserFriendlyError(
                    "E-012",
                    technical_detail="missing answers before grade",
                    user_action="请先提交答案，再进行批改。",
                )
        if action == "diagnose":
            if not session.grades:
                raise UserFriendlyError(
                    "E-002",
                    technical_detail="session must be graded before diagnosis",
                    user_action="诊断数据不足，请先完成批改（建议至少完成若干题目后再试）。",
                )
        if action in {"plan", "replan", "practice_loop"}:
            if session.diagnosis is None:
                raise UserFriendlyError(
                    "E-013",
                    technical_detail="session must be diagnosed before planning",
                    user_action="请先完成诊断，再生成或调整学习计划。",
                )

    @classmethod
    def transition(cls, session: SessionState, target: SessionPhase) -> SessionState:
        """Assert legality, append history, set phase."""
        current = session.phase
        cls.assert_transition(current, target)
        history = list(session.metadata.get("phase_history") or [])
        if not isinstance(history, list):
            history = []
        entry: dict[str, Any] = {
            "from": current.value,
            "to": target.value,
            "at": datetime.now(timezone.utc).isoformat(),
        }
        history.append(entry)
        # Keep history bounded
        session.metadata["phase_history"] = history[-50:]
        session.phase = target
        return session
