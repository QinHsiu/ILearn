"""CLI: proactive scheduler scan / replay / consume (bypass — no session FSM, no LLM)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import typer

from ilearn.core.projection import load_latest_state, load_state_at
from ilearn.scheduler.dispatcher import Scheduler
from ilearn.scheduler.event_log import SchedulerEventLog
from ilearn.scheduler.feedback import apply_consumption
from ilearn.scheduler.matcher import ConsumptionMatcher
from ilearn.scheduler.replay import replay_receipt, verify_receipt
from ilearn.storage.learner_state_store import LearnerStateStore

app = typer.Typer(help="主动调度器（旁路，不进入会话状态机）")

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_LEARNERS = _PROJECT_ROOT / "data" / "learners"
_DEFAULT_SCHED_LOG = _PROJECT_ROOT / "data" / "scheduler_events"


def _learners_root() -> Path:
    import os

    configured = os.getenv("ILEARN_LEARNERS_DIR")
    return Path(configured) if configured else _DEFAULT_LEARNERS


def _event_log() -> SchedulerEventLog:
    import os

    configured = os.getenv("ILEARN_SCHEDULER_LOG_DIR")
    root = Path(configured) if configured else _DEFAULT_SCHED_LOG
    return SchedulerEventLog(root)


def _load_pending_receipts(learner_id: str):
    return _event_log().list_pending_receipts(learner_id)


def _persist_state(state, *, reason: str) -> None:
    """Persist projected state via a sealed engagement/review event trail marker.

    Consumption feedback already applied in-memory; write state.json cache directly
    and append a synthetic state note via engagement.updated so the version is durable.
    """
    from ilearn.core.state_event import StateEvent

    store = LearnerStateStore(_learners_root())
    # Append a marker event then overwrite is wrong — instead append review/engagement
    # events that reconstruct the same fields when possible. For durable snapshot we
    # write the folded state after appending a hash-chained engagement marker.
    current = store.load(state.learner_id)
    store.append(
        state.learner_id,
        StateEvent(
            learner_id=state.learner_id,
            event_type="engagement.updated",
            payload={
                "last_consumption_reason": reason,
                **{
                    k: v
                    for k, v in state.engagement_signals.items()
                    if k in ("dismissed_triggers", "orphaned_skills", "migration_contract_id")
                },
            },
            prev_state_hash=current.state_hash,
        ),
    )
    # Re-apply review_schedule / review_meta via review.scheduled events
    current = store.load(state.learner_id)
    for skill_id, due_at in state.review_schedule.items():
        meta = dict(state.review_meta.get(skill_id) or {})
        current = store.append(
            state.learner_id,
            StateEvent(
                learner_id=state.learner_id,
                event_type="review.scheduled",
                payload={
                    "skill_id": skill_id,
                    "due_at": due_at.isoformat() if hasattr(due_at, "isoformat") else str(due_at),
                    "interval_days": meta.get("interval_days", 1.0),
                    "ease_factor": meta.get("ease_factor", 2.5),
                    "review_count": meta.get("review_count", 0),
                    "last_quality": meta.get("last_quality"),
                },
                prev_state_hash=current.state_hash,
            ),
        )


def _load_receipt(receipt_id: str, learner_id: str | None = None):
    log = _event_log()
    if learner_id:
        return log.load_receipt(learner_id, receipt_id)
    for path in sorted(log.root.glob("*/scheduler_events.jsonl")):
        lid = path.parent.name
        try:
            return log.load_receipt(lid, receipt_id)
        except KeyError:
            continue
    raise KeyError(f"receipt not found: {receipt_id}")


@app.command("scan")
def scan(
    learner_id: str = typer.Argument(..., help="Learner id"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Compute receipts without writing"),
) -> None:
    """扫描到期项并产出调度回执。"""
    state = load_latest_state(learner_id, learners_root=_learners_root())
    if dry_run:
        receipts = Scheduler(event_log=None).scan(state)
        typer.echo(f"dry-run: would emit {len(receipts)} receipts")
        for r in receipts:
            typer.echo(f"  [{r.trigger}] {r.reason}")
        return

    receipts = Scheduler(event_log=_event_log()).scan(state)
    if not receipts:
        typer.echo("no dispatches")
        return
    for r in receipts:
        typer.echo(f"[{r.trigger}] {r.reason}  hash={r.receipt_hash[:12]}")


@app.command("replay")
def replay(
    receipt_id: str = typer.Argument(..., help="Receipt id (rcpt-...)"),
    learner_id: str | None = typer.Option(None, "--learner-id", help="Learner id (optional)"),
) -> None:
    """重放单条调度回执，验证其决策仍成立。"""
    try:
        receipt = _load_receipt(receipt_id, learner_id)
    except KeyError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    try:
        state = load_state_at(
            receipt.learner_id,
            receipt.state_version,
            learners_root=_learners_root(),
        )
        ok = verify_receipt(receipt) and replay_receipt(receipt, state)
    except (ValueError, LookupError) as exc:
        typer.echo(f"FAIL: {exc}", err=True)
        raise typer.Exit(1) from exc

    typer.echo("PASS" if ok else "FAIL")
    raise typer.Exit(0 if ok else 1)


@app.command("consume")
def consume(
    learner_id: str = typer.Argument(..., help="Learner id"),
    event_json: str = typer.Argument(..., help="JSON learner.* event"),
) -> None:
    """将一条 learner.* 事件与待消费回执匹配，写入消费事件并反馈状态。"""
    event = json.loads(event_json)
    if "occurred_at" in event and isinstance(event["occurred_at"], str):
        pass  # matcher accepts ISO strings
    pending = _load_pending_receipts(learner_id)
    cons = ConsumptionMatcher(pending).match(event)
    if not cons:
        typer.echo("no matching pending receipt")
        raise typer.Exit(0)
    _event_log().append(
        "scheduler.consumed",
        cons.model_dump(mode="json"),
        learner_id,
    )
    state = load_latest_state(learner_id, learners_root=_learners_root())
    new_state = apply_consumption(
        state,
        cons,
        receipt_state_version=cons.receipt_state_version,
    )
    _persist_state(new_state, reason=f"consumption:{cons.consumption_id}")
    typer.echo(
        f"consumed {cons.receipt_id} → {cons.outcome} quality={cons.quality}"
    )


@app.command("expire")
def expire(
    learner_id: str = typer.Argument(..., help="Learner id"),
) -> None:
    """将超过窗口的未消费回执标记为 expired（可观测，非静默丢弃）。"""
    now = datetime.now(timezone.utc)
    pending = _load_pending_receipts(learner_id)
    matcher = ConsumptionMatcher(pending)
    expired = matcher.expire_overdue(now=now)
    if not expired:
        typer.echo("no overdue receipts")
        return
    state = load_latest_state(learner_id, learners_root=_learners_root())
    for cons in expired:
        _event_log().append(
            "scheduler.consumed",
            cons.model_dump(mode="json"),
            learner_id,
        )
        state = apply_consumption(state, cons)
    _persist_state(state, reason=f"expire_batch:{len(expired)}")
    typer.echo(f"expired {len(expired)} receipts")
