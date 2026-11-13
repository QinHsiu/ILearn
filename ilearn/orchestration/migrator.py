"""Pure-function LearnerState migration across lifecycle templates."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from ilearn.core.datetime_utils import utc_now
from ilearn.core.learner_state import LearnerState, MasteryEstimate
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
        # Derive target — never mutate source
        target = state.model_copy(deep=True)
        target.version = state.version + 1
        target.mastery = {}
        target.review_schedule = {}
        target.review_meta = {}
        orphaned: list[str] = []
        mapped: dict[str, str] = {}

        for source_skill, estimate in state.mastery.items():
            m = mapping.get(source_skill)
            if m is None and contract.default_target_skill is None:
                orphaned.append(source_skill)
                continue
            target_skill = m.target_skill if m else str(contract.default_target_skill)
            mapped[source_skill] = target_skill
            adjusted = round(estimate.mastery * (m.confidence if m else 1.0), 4)
            prev = target.mastery.get(target_skill)
            if prev is None or adjusted > prev.mastery:
                target.mastery[target_skill] = MasteryEstimate(
                    skill_id=target_skill,
                    mastery=adjusted,
                    evidence_count=estimate.evidence_count,
                    last_updated=estimate.last_updated,
                )

        for source_skill, due_at in state.review_schedule.items():
            m = mapping.get(source_skill)
            if m is None and contract.default_target_skill is None:
                continue
            target_skill = m.target_skill if m else str(contract.default_target_skill)
            target.review_schedule[target_skill] = due_at
            if source_skill in state.review_meta:
                target.review_meta[target_skill] = dict(state.review_meta[source_skill])

        # Misconceptions: prefix remap; unmapped codes kept
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
        ).seal()
        return target, receipt
