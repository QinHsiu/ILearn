"""CLI: cross-template LearnerState migration (no LLM)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import typer

from ilearn.core.learner_state import LearnerState
from ilearn.core.projection import load_latest_state
from ilearn.core.state_event import StateEvent
from ilearn.orchestration.migration import MigrationReceipt, StateMigrationContract
from ilearn.orchestration.migration_replay import replay_migration
from ilearn.orchestration.migrator import StateMigrator
from ilearn.scheduler.event_log import SchedulerEventLog
from ilearn.storage.learner_state_store import LearnerStateStore

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_LEARNERS = _PROJECT_ROOT / "data" / "learners"
_DEFAULT_SCHED_LOG = _PROJECT_ROOT / "data" / "scheduler_events"

# Optional sub-app (also registered as top-level commands on main)
app = typer.Typer(help="跨模板 LearnerState 迁移")


def _learners_root() -> Path:
    import os

    configured = os.getenv("ILEARN_LEARNERS_DIR")
    return Path(configured) if configured else _DEFAULT_LEARNERS


def _event_log() -> SchedulerEventLog:
    import os

    configured = os.getenv("ILEARN_SCHEDULER_LOG_DIR")
    root = Path(configured) if configured else _DEFAULT_SCHED_LOG
    return SchedulerEventLog(root)


def _persist_migrated(target: LearnerState, receipt: MigrationReceipt) -> None:
    store = LearnerStateStore(_learners_root())
    current = store.load(target.learner_id)
    current = store.append(
        target.learner_id,
        StateEvent(
            learner_id=target.learner_id,
            event_type="engagement.updated",
            payload={
                "orphaned_skills": receipt.orphaned_skills,
                "migration_contract_id": receipt.contract_id,
                "migration_receipt_id": receipt.receipt_id,
            },
            prev_state_hash=current.state_hash,
        ),
    )
    for skill_id, est in target.mastery.items():
        current = store.append(
            target.learner_id,
            StateEvent(
                learner_id=target.learner_id,
                event_type="mastery.update",
                payload={
                    "skill_id": skill_id,
                    "mastery": est.mastery,
                    "delta_evidence": 0,
                    "timestamp": est.last_updated.isoformat(),
                },
                prev_state_hash=current.state_hash,
            ),
        )
    for skill_id, due_at in target.review_schedule.items():
        meta = dict(target.review_meta.get(skill_id) or {})
        current = store.append(
            target.learner_id,
            StateEvent(
                learner_id=target.learner_id,
                event_type="review.scheduled",
                payload={
                    "skill_id": skill_id,
                    "due_at": due_at.isoformat(),
                    **{k: v for k, v in meta.items() if k != "due_at"},
                },
                prev_state_hash=current.state_hash,
            ),
        )


def migrate_cmd(
    learner_id: str = typer.Argument(..., help="Learner id"),
    contract_path: Path = typer.Argument(..., help="Path to StateMigrationContract JSON"),
) -> None:
    """执行跨模板状态迁移，写入迁移事件与回执。"""
    contract = StateMigrationContract.model_validate_json(
        contract_path.read_text(encoding="utf-8")
    )
    state = load_latest_state(learner_id, learners_root=_learners_root())
    now = datetime.now(timezone.utc)
    target, receipt = StateMigrator().migrate(state, contract, now)
    _event_log().append(
        "learner.state_migrated",
        {
            "receipt": receipt.model_dump(mode="json"),
            "contract": contract.model_dump(mode="json"),
        },
        learner_id,
    )
    _persist_migrated(target, receipt)
    typer.echo(
        f"migrated v{receipt.source_version}→v{receipt.target_version} "
        f"mapped={len(receipt.mapped_skills)} orphaned={len(receipt.orphaned_skills)}"
    )


def verify_migration_cmd(
    receipt_path: Path = typer.Argument(..., help="MigrationReceipt JSON"),
    state_path: Path = typer.Argument(..., help="Source LearnerState JSON"),
    contract_path: Path = typer.Argument(..., help="StateMigrationContract JSON"),
) -> None:
    """独立验证迁移回执可重放。"""
    receipt = MigrationReceipt.model_validate_json(
        receipt_path.read_text(encoding="utf-8")
    )
    state = LearnerState.model_validate_json(state_path.read_text(encoding="utf-8"))
    contract = StateMigrationContract.model_validate_json(
        contract_path.read_text(encoding="utf-8")
    )
    try:
        ok = replay_migration(state, receipt, contract)
    except ValueError as exc:
        typer.echo(f"FAIL: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo("PASS" if ok else "FAIL")
    raise typer.Exit(0 if ok else 1)


app.command("run")(migrate_cmd)
app.command("verify")(verify_migration_cmd)


def register(parent: typer.Typer) -> None:
    """Register top-level `ilearn migrate` and `ilearn verify-migration`."""
    parent.command("migrate")(migrate_cmd)
    parent.command("verify-migration")(verify_migration_cmd)
