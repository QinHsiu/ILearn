"""Natural-language explanations for diagnosis attributions."""

from __future__ import annotations

from typing import Any

from ilearn.core.knowledge_labels import resolve_knowledge_label

_ERROR_LABELS: dict[str, str] = {
    "concept_gap": "概念理解偏差",
    "calc_error": "计算过程失误",
    "misread": "审题理解偏差",
    "method_wrong": "方法选择不当",
    "incomplete": "步骤不完整",
    "unknown": "未标注错误类型",
}


class DiagnosisExplainer:
    """Build human-readable explanation chains from enrichment + grades."""

    @staticmethod
    def explain_attribution(
        skill_id: str,
        error_type: str,
        *,
        wrong_count: int = 1,
        concept_detail: str | None = None,
        mastery_names: dict[str, str] | None = None,
    ) -> str:
        skill = resolve_knowledge_label(skill_id, mastery_names=mastery_names)
        label = _ERROR_LABELS.get(error_type, error_type)
        detail = concept_detail or "相关定义或关键步骤尚未稳定掌握"
        if error_type in {"concept_gap", "conceptual"}:
            return (
                f"在「{skill}」上判为「{label}」：相关错题约 {wrong_count} 次，"
                f"错误模式一致指向同一概念理解问题——{detail}。"
            )
        if error_type in {"calc_error", "procedural"}:
            return (
                f"在「{skill}」上判为「{label}」：错题约 {wrong_count} 次，"
                f"更像计算/步骤执行偏差。建议逐步验算后再核对结论。"
            )
        if error_type in {"misread", "comprehension"}:
            return (
                f"在「{skill}」上判为「{label}」：错题约 {wrong_count} 次，"
                f"作答方向与题意可能不一致。建议先圈出已知与所求再动笔。"
            )
        return (
            f"在「{skill}」上出现「{label}」相关错误（约 {wrong_count} 次）。"
            f"建议结合错题回顾关键步骤。"
        )

    @classmethod
    def build_explanations(
        cls,
        *,
        weak_skills: list[str],
        error_attribution: dict[str, Any] | None,
        cognitive_findings: list[dict[str, Any]] | None = None,
        mastery_names: dict[str, str] | None = None,
    ) -> list[str]:
        attribution = error_attribution or {}
        counts = dict(attribution.get("counts") or {})
        top_tags = list(attribution.get("top_tags") or [])
        explanations: list[str] = []
        seen_findings: set[str] = set()
        for finding in cognitive_findings or []:
            raw_skill = str(
                finding.get("gap_skill_label")
                or finding.get("gap_skill")
                or finding.get("skill_id")
                or ""
            )
            if not raw_skill:
                continue
            root = str(finding.get("root_cause") or "")
            finding_key = f"{raw_skill}|{root}"
            if finding_key in seen_findings:
                continue
            seen_findings.add(finding_key)
            skill = resolve_knowledge_label(raw_skill, mastery_names=mastery_names)
            rec = str(finding.get("recommendation") or "")
            explanations.append(
                f"技能「{skill}」：{root}。{rec}".strip()
            )
        skill = (
            resolve_knowledge_label(weak_skills[0], mastery_names=mastery_names)
            if weak_skills
            else "相关知识点"
        )
        for tag in top_tags[:3]:
            explanations.append(
                cls.explain_attribution(
                    skill,
                    str(tag),
                    wrong_count=int(counts.get(tag, 1)),
                    mastery_names=mastery_names,
                )
            )
        return cls._dedupe_preserve_order(explanations)

    @staticmethod
    def _dedupe_preserve_order(items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            out.append(item)
        return out
