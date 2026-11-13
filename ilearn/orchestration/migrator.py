"""Pure-function LearnerState migration across lifecycle templates."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from ilearn.core.datetime_utils import utc_now
from ilearn.core.learner_state import LearnerState, MasteryEstimate
from ilearn.orchestration.derivation import derive_mastery
from ilearn.orchestration.migration import MigrationReceipt, StateMigrationContract


class StateMigrator:
    def migrate(
        self,
        state: LearnerState,
        contract: StateMigrationContract,
        now: datetime | None = None,
    ) -> tuple[LearnerState, MigrationReceipt]:
        now = now or utc_now()
        mapping = {m.source_skill: m for m in contract.skill_mappings}
        target = state.model_copy(deep=True)
        target.version = state.version + 1
        target.mastery = {}
        target.review_schedule = {}
        target.review_meta = {}
        orphaned: list[str] = []
        mapped: dict[str, str] = {}
        derivation_traces: list[dict] = []

        # Layer 1: explicit isomorphic mappings
        for source_skill, estimate in state.mastery.items():
            m = mapping.get(source_skill)
            if m is None:
                continue
            mapped[source_skill] = m.target_skill
            adjusted = round(estimate.mastery * m.confidence, 4)
            prev = target.mastery.get(m.target_skill)
            if prev is None or adjusted > prev.mastery:
                target.mastery[m.target_skill] = MasteryEstimate(
                    skill_id=m.target_skill,
                    mastery=adjusted,
                    evidence_count=estimate.evidence_count,
                    last_updated=estimate.last_updated,
                )

        # Layer 2: derivations (override same target — fuller evidence trail)
        for spec in contract.derivations:
            value, trace = derive_mastery(state, spec, now)
            evidence = sum(
                s.evidence_count
                for s in state.mastery.values()
                if s.skill_id in spec.source_skills
            )
            target.mastery[spec.target_skill] = MasteryEstimate(
                skill_id=spec.target_skill,
                mastery=value,
                evidence_count=evidence,
                last_updated=now,
            )
            derivation_traces.append(trace)
            for s in spec.source_skills:
                if s in state.mastery:
                    mapped[s] = spec.target_skill

        # Orphaned: not mapped and not consumed by derivation
        consumed = set(mapped.keys()) | {
            s for spec in contract.derivations for s in spec.source_skills
        }
        for source_skill in state.mastery:
            if source_skill in consumed:
                continue
            if contract.default_target_skill is not None:
                target_skill = contract.default_target_skill
                mapped[source_skill] = target_skill
                estimate = state.mastery[source_skill]
                prev = target.mastery.get(target_skill)
                if prev is None or estimate.mastery > prev.mastery:
                    target.mastery[target_skill] = MasteryEstimate(
                        skill_id=target_skill,
                        mastery=estimate.mastery,
                        evidence_count=estimate.evidence_count,
                        last_updated=estimate.last_updated,
                    )
            else:
                orphaned.append(source_skill)

        # Review schedule via mapping / derivation
        for source_skill, due_at in state.review_schedule.items():
            m = mapping.get(source_skill)
            if m:
                target.review_schedule[m.target_skill] = due_at
                if source_skill in state.review_meta:
                    target.review_meta[m.target_skill] = dict(
                        state.review_meta[source_skill]
                    )
                continue
            for spec in contract.derivations:
                if source_skill in spec.source_skills:
                    target.review_schedule[spec.target_skill] = due_at
                    if source_skill in state.review_meta:
                        target.review_meta[spec.target_skill] = dict(
                            state.review_meta[source_skill]
                        )
                    break
            else:
                if contract.default_target_skill and source_skill in mapped:
                    ts = mapped[source_skill]
                    target.review_schedule[ts] = due_at

        prefix_map = contract.prefix_map()
        target.misconceptions = []
        for misc in state.misconceptions:
            new_code = misc.code
            for prefix, replacement in prefix_map.items():
                if misc.code.startswith(prefix):
                    new_code = replacement + misc.code[len(prefix) :]
                    break
            target.misconceptions.append(misc.model_copy(update={"code": new_code}))

        target.engagement_signals = dict(state.engagement_signals)
        target.engagement_signals["orphaned_skills"] = orphaned
        target.engagement_signals["migration_contract_id"] = contract.contract_id
        target.state_hash = target.compute_hash()

        receipt = MigrationReceipt(
            receipt_id=f"mig-{uuid4().hex[:12]}",
            learner_id=state.learner_id,
            contract_id=contract.contract_id,
            contract_hash=contract.contract_hash(),
            source_version=state.version,
            target_version=target.version,
            source_state_hash=state.state_hash,
            target_state_hash=target.state_hash,
            mapped_skills=mapped,
            orphaned_skills=orphaned,
            migrated_at=now,
            derivation_traces=derivation_traces,
        ).seal()
        return target, receipt
