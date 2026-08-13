"""Learning-situation diagnosis from graded assessment results."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path

from ilearn.core.datetime_utils import utc_now

from ilearn.core.review import ReviewState, sm2_update
from ilearn.core.mastery import apply_evidence_to_mastery
from ilearn.core.schemas import (
    AssessmentPaper,
    DiagnosisReport,
    GradeResult,
    HintLevel,
    Intervention,
    KnowledgeEvidence,
    KnowledgeMastery,
    LearnerPortrait,
    MasteryLevel,
    MasteryRecord,
    StudentProfile,
    WeaknessEntry,
    WeaknessEvent,
)
from ilearn.core.evidence import claim_refs
from ilearn.eval.gap import gap_flag
from ilearn.providers.curriculum import CurriculumProvider, PilotBeijingRenjiaoProvider

_ERROR_FIX_HINTS: dict[str, str] = {
    "concept_gap": "概念理解",
    "calc_error": "计算准确性",
    "misread": "审题与读题",
    "method_wrong": "解题方法",
    "incomplete": "步骤完整性",
}

_ERROR_TAG_LABELS: dict[str, str] = {
    "concept_gap": "概念缺口",
    "calc_error": "计算错误",
    "misread": "审题失误",
    "method_wrong": "方法不当",
    "incomplete": "步骤不完整",
}


def _default_pilot_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "pilot"


def _is_beijing_region(region: str) -> bool:
    normalized = region.strip().casefold()
    return normalized in ("北京", "beijing")


def _mastery_level(score_rate: float) -> MasteryLevel:
    if score_rate >= 0.8:
        return "mastered"
    if score_rate >= 0.5:
        return "unstable"
    return "weak"


def _ema_update(current: float, observed: float, *, alpha: float = 0.3) -> float:
    return max(0.0, min(1.0, current * (1.0 - alpha) + observed * alpha))


def _get_mastery_record(portrait: LearnerPortrait, knowledge_id: str) -> MasteryRecord:
    if knowledge_id not in portrait.mastery_records:
        legacy = portrait.knowledge_state.get(knowledge_id)
        portrait.mastery_records[knowledge_id] = MasteryRecord(
            practice_score=legacy if legacy is not None else 0.0,
        )
    return portrait.mastery_records[knowledge_id]


def _dominant_error_tag(counts: dict[str, int]) -> str | None:
    if not counts:
        return None
    return max(counts.items(), key=lambda pair: pair[1])[0]


def _error_penalty(error_tags: list[str]) -> float:
    return min(30.0, len(error_tags) * 5.0)


def _sm2_quality(grade_row: GradeResult) -> int:
    """Map a graded item's correctness to an SM-2 quality score (0-5)."""
    if grade_row.final_correct:
        return 4
    statuses = {step.status for step in grade_row.step_results}
    if "partial" in statuses or ("correct" in statuses and "incorrect" in statuses):
        return 2
    return 1


def _incorrect_evidence_count(
    evidence: list[KnowledgeEvidence] | None,
    knowledge_id: str,
) -> int:
    if not evidence:
        return 0
    return sum(
        1
        for ev in evidence
        if ev.knowledge_id == knowledge_id and not ev.correct
    )


def is_leech(
    portrait: LearnerPortrait,
    knowledge_id: str,
    *,
    threshold: int = 3,
    evidence: list[KnowledgeEvidence] | None = None,
) -> bool:
    """True when incorrect evidence for a knowledge node reaches the leech threshold."""
    if evidence is not None:
        return _incorrect_evidence_count(evidence, knowledge_id) >= threshold
    rec = portrait.mastery_records.get(knowledge_id)
    if rec is None:
        return False
    return rec.probe_mastery < 0.3 and rec.evidence_count >= threshold


class Diagnoser:
    """Aggregate knowledge mastery, abilities, and Top-5 interventions."""

    def __init__(self, curriculum: CurriculumProvider | None = None) -> None:
        self._curriculum = curriculum or PilotBeijingRenjiaoProvider(_default_pilot_dir())

    def diagnose(
        self,
        profile: StudentProfile,
        paper: AssessmentPaper,
        grades: list[GradeResult],
        *,
        portrait: LearnerPortrait | None = None,
        evidence: list[KnowledgeEvidence] | None = None,
    ) -> DiagnosisReport:
        grade_by_id = {grade.item_id: grade for grade in grades}
        knowledge_by_id = {
            node.id: node for node in self._curriculum.list_knowledge(profile.grade)
        }

        item_records: dict[str, list[tuple[str, GradeResult]]] = defaultdict(list)
        for item in paper.items:
            grade = grade_by_id.get(item.id)
            if grade is None:
                continue
            for knowledge_id in item.knowledge_ids:
                item_records[knowledge_id].append((item.id, grade))

        knowledge_mastery: list[KnowledgeMastery] = []
        for knowledge_id, records in sorted(item_records.items()):
            item_ids = [item_id for item_id, _ in records]
            grade_rows = [grade for _, grade in records]
            correct = sum(1 for grade in grade_rows if grade.final_correct)
            score_rate = correct / len(grade_rows)
            error_tag_counts: dict[str, int] = defaultdict(int)
            for grade in grade_rows:
                for tag in grade.error_tags:
                    error_tag_counts[tag] += 1
            knowledge_mastery.append(
                KnowledgeMastery(
                    knowledge_id=knowledge_id,
                    knowledge_name=(
                        knowledge_by_id[knowledge_id].name
                        if knowledge_id in knowledge_by_id
                        else knowledge_id
                    ),
                    score_rate=score_rate,
                    error_tag_counts=dict(error_tag_counts),
                    level=_mastery_level(score_rate),
                    item_ids=item_ids,
                )
            )

        interventions = self._build_interventions(
            knowledge_mastery,
            knowledge_by_id,
            paper=paper,
            portrait=portrait or LearnerPortrait(student_key=""),
            evidence=evidence,
        )
        ability_scores = self._compute_ability_scores(
            paper, grade_by_id, knowledge_by_id
        )
        evidence_refs = claim_refs(
            [ev.evidence_id for ev in evidence] if evidence else []
        )
        effective_portrait = portrait or LearnerPortrait(student_key="")
        flags = gap_flag(effective_portrait)

        region_mismatch: str | None = None
        if not _is_beijing_region(profile.region):
            region_mismatch = (
                f"当前测评使用的是{paper.curriculum_label}试点课标，"
                f"与您填写的地区（{profile.region}）可能不完全匹配，结果仅供参考。"
            )

        return DiagnosisReport(
            knowledge_mastery=knowledge_mastery,
            interventions=interventions,
            ability_scores=ability_scores,
            curriculum_label=paper.curriculum_label,
            region_mismatch_disclaimer=region_mismatch,
            evidence_refs=evidence_refs,
            flags=flags,
        )

    def _build_interventions(
        self,
        knowledge_mastery: list[KnowledgeMastery],
        knowledge_by_id: dict[str, object],
        *,
        paper: AssessmentPaper,
        portrait: LearnerPortrait,
        evidence: list[KnowledgeEvidence] | None = None,
    ) -> list[Intervention]:
        candidates = sorted(
            (km for km in knowledge_mastery if km.level != "mastered"),
            key=lambda km: (
                not is_leech(portrait, km.knowledge_id, evidence=evidence),
                km.score_rate,
                km.knowledge_id,
            ),
        )[:5]

        interventions: list[Intervention] = []
        for priority, km in enumerate(candidates, start=1):
            node = knowledge_by_id.get(km.knowledge_id)
            title = node.name if node is not None else km.knowledge_id
            dominant = _dominant_error_tag(km.error_tag_counts)
            fix_first = (
                _ERROR_FIX_HINTS.get(dominant, "基础巩固")
                if dominant
                else "基础巩固"
            )
            leech = is_leech(portrait, km.knowledge_id, evidence=evidence)
            if dominant and dominant in _ERROR_TAG_LABELS:
                why = (
                    f"得分率 {km.score_rate:.0%}，主要问题："
                    f"{_ERROR_TAG_LABELS[dominant]}"
                )
            else:
                why = f"得分率 {km.score_rate:.0%}，需要加强练习"
            if leech:
                why = f"{why}；连续多次未掌握（需重点突破）"
            kid_evidence_ids = claim_refs(
                [
                    ev.evidence_id
                    for ev in (evidence or [])
                    if ev.knowledge_id == km.knowledge_id
                ]
            )
            curriculum_objective_ids: list[str] = []
            for item in paper.items:
                if km.knowledge_id not in item.knowledge_ids:
                    continue
                for obj_id in item.curriculum_objective_ids:
                    if obj_id and obj_id not in curriculum_objective_ids:
                        curriculum_objective_ids.append(obj_id)
            interventions.append(
                Intervention(
                    knowledge_id=km.knowledge_id,
                    title=title,
                    why=why,
                    what_to_fix_first=fix_first,
                    priority=priority,
                    leech=leech,
                    evidence_ids=kid_evidence_ids,
                    curriculum_objective_ids=curriculum_objective_ids[:2],
                )
            )
        return interventions

    def _compute_ability_scores(
        self,
        paper: AssessmentPaper,
        grade_by_id: dict[str, GradeResult],
        knowledge_by_id: dict[str, object],
    ) -> dict[str, float]:
        tag_grades: dict[str, list[GradeResult]] = defaultdict(list)
        for item in paper.items:
            grade = grade_by_id.get(item.id)
            if grade is None:
                continue
            tags: set[str] = set()
            for knowledge_id in item.knowledge_ids:
                node = knowledge_by_id.get(knowledge_id)
                if node is not None:
                    tags.update(node.ability_tags)
            for tag in tags:
                tag_grades[tag].append(grade)

        ability_scores: dict[str, float] = {}
        for tag, grades in sorted(tag_grades.items()):
            correct_rate = sum(1 for grade in grades if grade.final_correct) / len(
                grades
            )
            penalty = sum(
                _error_penalty(list(grade.error_tags)) for grade in grades
            ) / len(grades)
            ability_scores[tag] = round(
                max(0.0, min(100.0, correct_rate * 100.0 - penalty)), 1
            )
        return ability_scores


def _knowledge_name(
    curriculum: CurriculumProvider,
    knowledge_id: str,
    grade: int | None = None,
) -> str:
    grades = [grade] if grade is not None else (4, 5, 6)
    for lookup_grade in grades:
        for node in curriculum.list_knowledge(lookup_grade):
            if node.id == knowledge_id:
                return node.name
    return knowledge_id


def _upsert_weakness_event(portrait: LearnerPortrait, event: WeaknessEvent) -> None:
    for idx, existing in enumerate(portrait.weakness_events):
        if (
            existing.session_id == event.session_id
            and existing.knowledge_id == event.knowledge_id
        ):
            portrait.weakness_events[idx] = WeaknessEvent(
                knowledge_id=event.knowledge_id,
                session_id=event.session_id,
                step_index=(
                    event.step_index
                    if event.step_index is not None
                    else existing.step_index
                ),
                error_tag=event.error_tag if event.error_tag is not None else existing.error_tag,
                confidence=max(existing.confidence, event.confidence),
                evidence_id=(
                    event.evidence_id
                    if event.confidence >= existing.confidence
                    else existing.evidence_id
                ),
                created_at=existing.created_at,
            )
            return
    portrait.weakness_events.append(event)


class PortraitUpdater:
    """Append weakness entries and decay knowledge state from incorrect grades."""

    @staticmethod
    def update(
        portrait: LearnerPortrait,
        grades: list[GradeResult],
        session_id: str,
        curriculum: CurriculumProvider,
        grade: int | None = None,
        evidence: list[KnowledgeEvidence] | None = None,
        item_meta: dict[str, dict[str, object]] | None = None,
        item_situations: dict[str, str] | None = None,
    ) -> LearnerPortrait:
        now = utc_now()
        if evidence:
            apply_evidence_to_mastery(portrait, evidence)
            for ev in evidence:
                if ev.correct:
                    continue
                _upsert_weakness_event(
                    portrait,
                    WeaknessEvent(
                        knowledge_id=ev.knowledge_id,
                        step_index=ev.step_index,
                        error_tag=ev.error_tag,
                        confidence=ev.confidence,
                        evidence_id=ev.evidence_id,
                        session_id=session_id,
                        created_at=ev.created_at,
                    ),
                )

        for grade_row in grades:
            if not evidence:
                observed = 1.0 if grade_row.final_correct else 0.0
                quality = _sm2_quality(grade_row)
                for kid in grade_row.knowledge_ids:
                    record = _get_mastery_record(portrait, kid)
                    record.evidence_count += 1
                    if grade_row.lane == "probe":
                        record.probe_mastery = _ema_update(record.probe_mastery, observed)
                        record.last_probe_at = now
                    else:
                        record.practice_score = _ema_update(record.practice_score, observed)

                    review_state = portrait.review_states.get(kid, ReviewState())
                    portrait.review_states[kid] = sm2_update(review_state, quality)
            else:
                quality = _sm2_quality(grade_row)
                for kid in grade_row.knowledge_ids:
                    review_state = portrait.review_states.get(kid, ReviewState())
                    portrait.review_states[kid] = sm2_update(review_state, quality)

            if grade_row.final_correct:
                continue
            for kid in grade_row.knowledge_ids:
                portrait.weakness_log.append(
                    WeaknessEntry(
                        knowledge_id=kid,
                        topic=_knowledge_name(curriculum, kid, grade),
                        logic_gap=(
                            grade_row.error_tags[0]
                            if grade_row.error_tags
                            else "unknown"
                        ),
                        session_id=session_id,
                    )
                )
                _upsert_weakness_event(
                    portrait,
                    WeaknessEvent(
                        knowledge_id=kid,
                        error_tag=(
                            grade_row.error_tags[0]
                            if grade_row.error_tags
                            else None
                        ),
                        session_id=session_id,
                    ),
                )
                if not evidence:
                    portrait.knowledge_state[kid] = min(
                        portrait.knowledge_state.get(kid, 1.0), 0.4
                    )
        PortraitUpdater._update_situation_interest(
            portrait, grades, item_meta or {}, item_situations or {}
        )
        portrait.updated_at = now
        return portrait

    @staticmethod
    def _update_situation_interest(
        portrait: LearnerPortrait,
        grades: list[GradeResult],
        item_meta: dict[str, dict[str, object]],
        item_situations: dict[str, str],
    ) -> None:
        """Track a bounded preference signal from correctness and item behavior."""
        by_tag: dict[str, list[float]] = defaultdict(list)
        for grade_row in grades:
            meta = item_meta.get(grade_row.item_id, {})
            tag = item_situations.get(grade_row.item_id) or meta.get("situation_tag")
            if not tag:
                continue
            signal = 0.1 if grade_row.final_correct else -0.1
            if meta.get("skipped"):
                signal -= 0.2
            elapsed_ms = meta.get("elapsed_ms")
            if isinstance(elapsed_ms, (int, float)):
                if elapsed_ms < 1500:
                    signal -= 0.05
                elif elapsed_ms > 30000:
                    signal += 0.05
            by_tag[tag].append(signal)
        for tag, signals in by_tag.items():
            current = portrait.situation_interest.get(tag, 0.5)
            portrait.situation_interest[tag] = _clamp_score(
                current + sum(signals) / len(signals)
            )


_HINT_BEHAVIORAL_DELTA: dict[HintLevel, float] = {
    "none": 0.0,
    "low": 0.08,
    "medium": 0.15,
    "high": 0.25,
}


def _clamp_score(value: float) -> float:
    return max(0.0, min(1.0, value))


class PortraitDimensionUpdater:
    """Heuristic five-dimension portrait updates from graded attempts (no LLM)."""

    @staticmethod
    def apply(
        portrait: LearnerPortrait,
        grades: list[GradeResult],
        profile: StudentProfile | None = None,
    ) -> LearnerPortrait:
        if profile is not None:
            portrait.dimensions.contextual["grade_band"] = profile.grade / 10.0
            portrait.dimensions.contextual["region_weight"] = (
                1.0 if _is_beijing_region(profile.region) else 0.5
            )

        consecutive_wrong = 0
        for grade_row in grades:
            hint_delta = _HINT_BEHAVIORAL_DELTA.get(grade_row.hint_level_suggestion, 0.0)
            if hint_delta > 0.0:
                current = portrait.dimensions.behavioral.get("hint_dependency", 0.0)
                portrait.dimensions.behavioral["hint_dependency"] = _clamp_score(
                    current + hint_delta
                )

            if grade_row.final_correct:
                consecutive_wrong = 0
                portrait.dimensions.cognitive["knowledge_application"] = _clamp_score(
                    portrait.dimensions.cognitive.get("knowledge_application", 0.5)
                    + 0.05
                )
            else:
                consecutive_wrong += 1
                portrait.dimensions.cognitive["knowledge_application"] = _clamp_score(
                    portrait.dimensions.cognitive.get("knowledge_application", 0.5)
                    - 0.05
                )
                if consecutive_wrong >= 2:
                    current = portrait.dimensions.emotional.get("frustration", 0.0)
                    portrait.dimensions.emotional["frustration"] = _clamp_score(
                        current + 0.1 * consecutive_wrong
                    )

            if grade_row.lane == "probe" and not grade_row.final_correct:
                portrait.dimensions.metacognitive["probe_self_check"] = _clamp_score(
                    portrait.dimensions.metacognitive.get("probe_self_check", 0.0) + 0.2
                )

            for kid in grade_row.knowledge_ids:
                record = portrait.mastery_records.get(kid)
                if record is None:
                    continue
                gap = record.practice_score - record.probe_mastery
                if gap > 0.2:
                    portrait.dimensions.metacognitive["practice_probe_gap"] = _clamp_score(
                        gap
                    )

        return portrait

    @staticmethod
    def apply_from_evidence(
        portrait: LearnerPortrait,
        events: list[KnowledgeEvidence],
    ) -> LearnerPortrait:
        if not events:
            return portrait

        hint_delta_by_level: dict[HintLevel, float] = {
            "none": 0.0,
            "low": 0.08,
            "medium": 0.15,
            "high": 0.25,
        }
        by_knowledge: dict[str, list[KnowledgeEvidence]] = defaultdict(list)
        for ev in events:
            by_knowledge[ev.knowledge_id].append(ev)
            hint_delta = hint_delta_by_level.get(ev.hint_level, 0.0)
            if hint_delta > 0.0:
                current = portrait.dimensions.behavioral.get("hint_dependency", 0.0)
                portrait.dimensions.behavioral["hint_dependency"] = _clamp_score(
                    current + hint_delta
                )
            if ev.lane == "probe" and not ev.correct:
                portrait.dimensions.metacognitive["probe_self_check"] = _clamp_score(
                    portrait.dimensions.metacognitive.get("probe_self_check", 0.0) + 0.2
                )
            if ev.correct:
                portrait.dimensions.cognitive["knowledge_application"] = _clamp_score(
                    portrait.dimensions.cognitive.get("knowledge_application", 0.5)
                    + 0.05
                )
            else:
                portrait.dimensions.cognitive["knowledge_application"] = _clamp_score(
                    portrait.dimensions.cognitive.get("knowledge_application", 0.5)
                    - 0.05
                )

        for kid, kid_events in by_knowledge.items():
            practice_events = [e for e in kid_events if e.lane == "practice"]
            probe_events = [e for e in kid_events if e.lane == "probe"]
            if practice_events and probe_events:
                practice_rate = sum(1 for e in practice_events if e.correct) / len(
                    practice_events
                )
                probe_rate = sum(1 for e in probe_events if e.correct) / len(
                    probe_events
                )
                gap = practice_rate - probe_rate
                if gap > 0.2:
                    portrait.dimensions.metacognitive["practice_probe_gap"] = _clamp_score(
                        gap
                    )
            record = portrait.mastery_records.get(kid)
            if record is not None:
                gap = record.practice_score - record.probe_mastery
                if gap > 0.2:
                    portrait.dimensions.metacognitive["practice_probe_gap"] = _clamp_score(
                        gap
                    )

        return portrait
