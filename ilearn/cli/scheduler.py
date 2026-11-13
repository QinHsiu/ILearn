"""CLI: proactive scheduler scan / replay (bypass — no session FSM, no LLM)."""

from __future__ import annotations

from pathlib import Path

import typer

from ilearn.core.projection import load_latest_state, load_state_at
from ilearn.scheduler.dispatcher import Scheduler
from ilearn.scheduler.event_log import SchedulerEventLog
from ilearn.scheduler.replay import replay_receipt, verify_receipt

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


def _load_receipt(receipt_id: str, learner_id: str | None = None):
    log = _event_log()
    if learner_id:
        return log.load_receipt(learner_id, receipt_id)
    # Scan all learner dirs under the log root
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
