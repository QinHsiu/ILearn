"""Independent verify / replay of cross-template migration receipts."""

from __future__ import annotations

from ilearn.core.learner_state import LearnerState
from ilearn.orchestration.migration import MigrationReceipt, StateMigrationContract
from ilearn.orchestration.migrator import StateMigrator


def replay_migration(
    source_state: LearnerState,
    receipt: MigrationReceipt,
    contract: StateMigrationContract,
) -> bool:
    """在源状态上重放迁移，验证目标状态哈希与派生轨迹一致。"""
    if source_state.state_hash != receipt.source_state_hash:
        raise ValueError("source state tampered")
    if contract.contract_hash() != receipt.contract_hash:
        raise ValueError("contract changed since migration")
    target, replayed = StateMigrator().migrate(
        source_state, contract, receipt.migrated_at
    )
    if target.state_hash != receipt.target_state_hash:
        return False
    if len(replayed.derivation_traces) != len(receipt.derivation_traces):
        return False
    for a, b in zip(replayed.derivation_traces, receipt.derivation_traces):
        if a.get("rule") != b.get("rule") or a.get("shrink_factor") != b.get(
            "shrink_factor"
        ):
            return False
    return True
