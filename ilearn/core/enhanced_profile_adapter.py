"""Adapt legacy SessionState fields ↔ StudentFiveDimProfile."""

from __future__ import annotations

from ilearn.core.datetime_utils import utc_now
from ilearn.core.models.enhanced_profile import (
    ContextualDimension,
    StudentFiveDimProfile,
)
from ilearn.core.schemas import SessionState


class ProfileAdapter:
    """Bootstrap and project between legacy session data and five-dim profile."""

    @staticmethod
    def from_session(session: SessionState) -> StudentFiveDimProfile:
        profile = StudentFiveDimProfile(student_id=session.session_id)
        sp = session.profile
        profile.contextual = ContextualDimension(
            grade=str(sp.grade),
            subject=str(sp.subject),
            region=sp.region or "",
        )

        mastery: dict[str, float] = {}
        if session.diagnosis and session.diagnosis.knowledge_mastery:
            for row in session.diagnosis.knowledge_mastery:
                mastery[row.knowledge_id] = float(row.score_rate)
        elif session.portrait and session.portrait.knowledge_state:
            mastery = {
                str(k): float(v) for k, v in session.portrait.knowledge_state.items()
            }

        if mastery:
            profile.cognitive.knowledge_mastery = mastery
            weak = [kid for kid, score in mastery.items() if score < 0.6]
            strong = [kid for kid, score in mastery.items() if score >= 0.8]
            profile.cognitive.weak_concepts = weak
            profile.cognitive.strong_concepts = strong

        profile.last_updated = utc_now()
        return profile

    @staticmethod
    def cognitive_mastery_map(profile: StudentFiveDimProfile) -> dict[str, float]:
        """Optional projection for enhanced consumers — does not mutate legacy."""
        return dict(profile.cognitive.knowledge_mastery)
