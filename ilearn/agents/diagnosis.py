"""Diagnosis agent — learning-situation report and portrait updates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ilearn.agents.protocol import AgentContext, AgentResult, SessionPhase
from ilearn.core.cognitive_profile import (
    CognitiveDimension,
    CognitiveSkillGraph,
    SkillNode,
)
from ilearn.core.diagnosis import Diagnoser, PortraitDimensionUpdater, PortraitUpdater
from ilearn.core.knowledge_graph import KnowledgeGraph
from ilearn.core.schemas import DiagnosisReport, LearnerPortrait, StudentProfile
from ilearn.providers.curriculum import CurriculumProvider

__all__ = ["DiagnosisAgent", "PortraitDimensionUpdater", "PortraitUpdater"]

_DIMENSION_ADVICE: dict[CognitiveDimension, str] = {
    CognitiveDimension.REMEMBER: "建议先巩固基本概念与定义的记忆，配合闪卡或口头复述。",
    CognitiveDimension.UNDERSTAND: "建议用自己的话解释概念，并对照图形/例题核对理解。",
    CognitiveDimension.APPLY: "建议多做变式练习，把步骤迁移到新情境。",
    CognitiveDimension.ANALYZE: "建议拆解题干条件与关系，画出结构图再求解。",
    CognitiveDimension.EVALUATE: "建议对比多种解法并判断合理性，养成验算习惯。",
    CognitiveDimension.CREATE: "建议尝试编题或一题多解，主动建构新表示。",
}


def _student_key(profile: StudentProfile) -> str:
    region = profile.region.strip().casefold().replace(" ", "_")
    return f"{region}_g{profile.grade}"


def _event_get(event: Any, key: str, default: Any = None) -> Any:
    if isinstance(event, dict):
        return event.get(key, default)
    return getattr(event, key, default)


def _event_is_correct(event: Any) -> bool | None:
    if _event_get(event, "is_correct") is not None:
        return bool(_event_get(event, "is_correct"))
    if _event_get(event, "correct") is not None:
        return bool(_event_get(event, "correct"))
    return None


class DiagnosisAgent:
    name = "diagnosis"

    def __init__(
        self,
        curriculum: CurriculumProvider,
        *,
        knowledge_graph: KnowledgeGraph | None = None,
        cognitive_graph: CognitiveSkillGraph | None = None,
    ) -> None:
        self._curriculum = curriculum
        self._diagnoser = Diagnoser(curriculum)
        self._knowledge_graph = knowledge_graph or KnowledgeGraph()
        if cognitive_graph is not None:
            self._cognitive_graph: CognitiveSkillGraph | None = cognitive_graph
        else:
            default_path = (
                Path(__file__).resolve().parents[2] / "data" / "cognitive_skills.json"
            )
            self._cognitive_graph = (
                CognitiveSkillGraph(default_path) if default_path.exists() else None
            )

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
        enrichment = self.enrich_with_prerequisites(
            diagnosis, evidence, grades=ctx.grades
        )
        data_status, data_message = self._classify_evidence_volume(evidence, ctx.grades)
        enrichment["data_status"] = data_status
        enrichment["message"] = data_message
        from ilearn.core.audience_summary import generate_audience_summary

        enrichment["parent_summary"] = generate_audience_summary(
            diagnosis, enrichment, audience="parent"
        )
        enrichment["teacher_summary"] = generate_audience_summary(
            diagnosis, enrichment, audience="teacher"
        )
        flags = list(diagnosis.flags)
        if enrichment.get("prerequisite_gaps") and "prerequisite_gaps" not in flags:
            flags.append("prerequisite_gaps")
        if enrichment.get("cognitive_findings") and "cognitive_gap" not in flags:
            flags.append("cognitive_gap")
        if data_status in {"insufficient_data", "limited_data"} and data_status not in flags:
            flags.append(data_status)
        if flags != diagnosis.flags:
            diagnosis = diagnosis.model_copy(update={"flags": flags})
        return AgentResult(
            phase=SessionPhase.PLAN,
            payload={
                "diagnosis": diagnosis,
                "portrait": portrait,
                "diagnosis_enrichment": enrichment,
            },
        )

    @staticmethod
    def _classify_evidence_volume(
        evidence: list[Any], grades: list[Any]
    ) -> tuple[str, str]:
        count = len(evidence) if evidence else len(grades)
        if count <= 0:
            return (
                "insufficient_data",
                "暂无作答数据，请完成至少一道题目后再进行诊断。",
            )
        if count < 3:
            return (
                "limited_data",
                "作答数据较少，诊断置信度较低，建议完成更多题目。",
            )
        return ("ok", "")

    def enrich_with_prerequisites(
        self,
        diagnosis: DiagnosisReport,
        evidence_log: list[Any],
        *,
        grades: list[Any] | None = None,
    ) -> dict[str, Any]:
        """Attach prerequisite gaps and learning advice without changing report schema."""
        from ilearn.core.audience_summary import aggregate_error_attribution

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
        cognitive_findings: list[dict[str, Any]] = []
        if self._cognitive_graph is not None:
            for event in evidence_log:
                if _event_is_correct(event) is not False:
                    continue
                skill_id = _event_get(event, "skill_id")
                finding = self.diagnose_with_cognitive_profile(
                    evidence_log, skill_id=skill_id, knowledge_id=_event_get(event, "knowledge_id")
                )
                if finding.get("gap_skill"):
                    cognitive_findings.append(finding)
        error_attribution = aggregate_error_attribution(grades)
        from ilearn.core.diagnosis_explainer import DiagnosisExplainer

        attribution_explanations = DiagnosisExplainer.build_explanations(
            weak_skills=weak_skills,
            error_attribution=error_attribution,
            cognitive_findings=cognitive_findings,
        )
        unknown_skills = self._collect_unknown_skills(evidence_log)
        return {
            "weak_skills": weak_skills,
            "prerequisite_gaps": gaps,
            "learning_advice": advice,
            "cognitive_findings": cognitive_findings,
            "error_attribution": error_attribution,
            "attribution_explanations": attribution_explanations,
            "unknown_skills": unknown_skills,
        }

    def diagnose_with_cognitive_profile(
        self,
        evidence_log: list[Any],
        *,
        skill_id: str | None = None,
        knowledge_id: str | None = None,
    ) -> dict[str, Any]:
        """Root-cause diagnosis against the cognitive skill graph."""
        empty = {
            "root_cause": "",
            "gap_skill": "",
            "recommendation": "",
            "dimension": None,
        }
        if self._cognitive_graph is None:
            return empty
        node = self._resolve_skill_node(skill_id=skill_id, knowledge_id=knowledge_id)
        if node is None:
            return empty

        for prereq in node.prerequisites:
            if not self._is_cognitive_skill_mastered(prereq, evidence_log):
                prereq_node = self._cognitive_graph.get(prereq)
                name = prereq_node.name if prereq_node else prereq
                return {
                    "root_cause": "前置技能缺失",
                    "gap_skill": prereq,
                    "recommendation": f"请先复习{name}",
                    "dimension": prereq_node.dimension.value if prereq_node else None,
                }

        return {
            "root_cause": f"{node.dimension.value}层次不足",
            "gap_skill": node.skill_id,
            "recommendation": self._get_dimension_advice(node.dimension),
            "dimension": node.dimension.value,
        }

    def _resolve_skill_node(
        self,
        *,
        skill_id: str | None,
        knowledge_id: str | None,
    ) -> SkillNode | None:
        assert self._cognitive_graph is not None
        if skill_id:
            node = self._cognitive_graph.get(skill_id)
            if node is not None:
                return node
        if knowledge_id:
            matches = self._cognitive_graph.by_legacy_knowledge_id(knowledge_id)
            if matches:
                return matches[0]
            matches = self._cognitive_graph.by_knowledge_point(knowledge_id)
            if matches:
                return matches[0]
        return None

    def _is_cognitive_skill_mastered(
        self, skill_id: str, evidence: list[Any]
    ) -> bool:
        relevant = [
            e
            for e in evidence
            if _event_get(e, "skill_id") == skill_id
            or skill_id
            in list(_event_get(e, "knowledge_ids", []) or [])
            or _event_get(e, "knowledge_id") == skill_id
        ]
        if not relevant:
            return False
        correct = 0
        for event in relevant:
            flag = _event_is_correct(event)
            if flag is None:
                return False
            correct += 1 if flag else 0
        return (correct / len(relevant)) >= 0.7

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
            or (isinstance(e, dict) and e.get("knowledge_id") == skill)
            or (
                isinstance(e, dict)
                and skill in list(e.get("knowledge_ids") or [])
            )
        ]
        if not relevant:
            return False
        correct = 0
        for event in relevant:
            flag = _event_is_correct(event)
            if flag is None:
                return False
            correct += 1 if flag else 0
        return (correct / len(relevant)) >= 0.7

    @staticmethod
    def _get_dimension_advice(dimension: CognitiveDimension) -> str:
        return _DIMENSION_ADVICE.get(dimension, "建议针对性复习该技能点。")

    def _collect_unknown_skills(self, evidence_log: list[Any]) -> list[str]:
        """skill_ids present in evidence but missing from the cognitive graph."""
        if self._cognitive_graph is None:
            return []
        unknown: list[str] = []
        for event in evidence_log:
            skill_id = _event_get(event, "skill_id")
            if not skill_id:
                continue
            sid = str(skill_id)
            if self._cognitive_graph.get(sid) is None:
                unknown.append(sid)
        return list(dict.fromkeys(unknown))

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
