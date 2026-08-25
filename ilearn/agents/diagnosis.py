"""Diagnosis agent — learning-situation report and portrait updates."""

from __future__ import annotations

from typing import Any

from ilearn.agents.protocol import AgentContext, AgentResult, SessionPhase
from ilearn.core.diagnosis import Diagnoser, PortraitDimensionUpdater, PortraitUpdater
from ilearn.core.knowledge_graph import KnowledgeGraph
from ilearn.core.schemas import DiagnosisReport, LearnerPortrait, StudentProfile
from ilearn.providers.curriculum import CurriculumProvider

__all__ = ["DiagnosisAgent", "PortraitDimensionUpdater", "PortraitUpdater"]


def _student_key(profile: StudentProfile) -> str:
    region = profile.region.strip().casefold().replace(" ", "_")
    return f"{region}_g{profile.grade}"


class DiagnosisAgent:
    name = "diagnosis"

    def __init__(
        self,
        curriculum: CurriculumProvider,
        *,
        knowledge_graph: KnowledgeGraph | None = None,
    ) -> None:
        self._curriculum = curriculum
        self._diagnoser = Diagnoser(curriculum)
        self._knowledge_graph = knowledge_graph or KnowledgeGraph()

    def run(self, ctx: AgentContext) -> AgentResult:
        if ctx.paper is None:
            raise ValueError("DiagnosisAgent requires paper in context")
        evidence = list(ctx.evidence_log)
        portrait = ctx.portrait or LearnerPortrait(student_key=_student_key(ctx.profile))
        item_situations = {
            item.id: item.situation_tag
            for item in ctx.paper.items
            if item.situation_tag is not None
        }
        portrait = PortraitUpdater.update(
            portrait,
            ctx.grades,
            ctx.session_id,
            self._curriculum,
            grade=ctx.profile.grade,
            evidence=evidence or None,
            item_meta=ctx.metadata.get("item_meta") or {},
            item_situations=item_situations,
        )
        diagnosis = self._diagnoser.diagnose(
            ctx.profile,
            ctx.paper,
            ctx.grades,
            portrait=portrait,
            evidence=evidence or None,
        )
        if evidence:
            portrait = PortraitDimensionUpdater.apply_from_evidence(portrait, evidence)
        else:
            portrait = PortraitDimensionUpdater.apply(
                portrait, ctx.grades, profile=ctx.profile
            )
        enrichment = self.enrich_with_prerequisites(diagnosis, evidence)
        if enrichment.get("prerequisite_gaps"):
            flags = list(diagnosis.flags)
            if "prerequisite_gaps" not in flags:
                flags.append("prerequisite_gaps")
            diagnosis = diagnosis.model_copy(update={"flags": flags})
        return AgentResult(
            phase=SessionPhase.PLAN,
            payload={
                "diagnosis": diagnosis,
                "portrait": portrait,
                "diagnosis_enrichment": enrichment,
            },
        )

    def enrich_with_prerequisites(
        self,
        diagnosis: DiagnosisReport,
        evidence_log: list[Any],
    ) -> dict[str, Any]:
        """Attach prerequisite gaps and learning advice without changing report schema."""
        weak_skills = [
            row.knowledge_id
            for row in diagnosis.knowledge_mastery
            if row.level == "weak"
        ]
        prerequisite_gaps: list[str] = []
        for skill in weak_skills:
            for prereq in self._knowledge_graph.get_prerequisites(skill):
                if not self._is_skill_mastered(prereq, evidence_log, diagnosis):
                    prerequisite_gaps.append(prereq)
        gaps = list(dict.fromkeys(prerequisite_gaps))
        advice = self._generate_learning_advice(weak_skills, gaps)
        return {
            "weak_skills": weak_skills,
            "prerequisite_gaps": gaps,
            "learning_advice": advice,
        }

    def _is_skill_mastered(
        self,
        skill: str,
        evidence: list[Any],
        diagnosis: DiagnosisReport,
    ) -> bool:
        for row in diagnosis.knowledge_mastery:
            if row.knowledge_id == skill:
                return row.level == "mastered" or row.score_rate >= 0.7
        relevant = [
            e
            for e in evidence
            if getattr(e, "knowledge_id", None) == skill
            or skill in list(getattr(e, "knowledge_ids", []) or [])
        ]
        if not relevant:
            return False
        correct = 0
        for event in relevant:
            if getattr(event, "is_correct", None) is not None:
                correct += 1 if event.is_correct else 0
            elif getattr(event, "correct", None) is not None:
                correct += 1 if event.correct else 0
            else:
                return False
        return (correct / len(relevant)) >= 0.7

    @staticmethod
    def _generate_learning_advice(weak_skills: list[str], gaps: list[str]) -> str:
        advice: list[str] = []
        if gaps:
            advice.append(
                "\u5efa\u8bae\u5148\u5de9\u56fa\u524d\u7f6e\u77e5\u8bc6\u70b9\uff1a"
                + ", ".join(gaps)
            )
        if weak_skills:
            advice.append(
                "\u8584\u5f31\u70b9\u4e3a\uff1a"
                + ", ".join(weak_skills)
                + "\uff0c\u5efa\u8bae\u91c7\u7528\u8d39\u66fc\u5b66\u4e60\u6cd5\uff0c"
                "\u5c1d\u8bd5\u8bb2\u7ed9\u4ed6\u4eba\u542c\u3002"
            )
        return "\n".join(advice)
