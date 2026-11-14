"""CLI: lifelong trajectory audit / replay."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import typer

from ilearn.audit.replay import replay_trajectory
from ilearn.audit.trajectory import build_trajectory
from ilearn.scheduler.event_log import SchedulerEventLog

app = typer.Typer(help="终身学习轨迹审计")

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _event_log() -> SchedulerEventLog:
    import os

    root = Path(os.getenv("ILEARN_SCHEDULER_LOG_DIR") or _PROJECT_ROOT / "data" / "scheduler_events")
    return SchedulerEventLog(root)


@app.command("show")
def show(
    learner_id: str = typer.Argument(...),
    days: int = typer.Option(365, "--days"),
    verify: bool = typer.Option(False, "--verify"),
) -> None:
    now = datetime.now(timezone.utc)
    events = _event_log().read_learner(learner_id, days=days)
    traj = build_trajectory(
        events, learner_id, window=(now - timedelta(days=days), now)
    )
    for n in traj.nodes:
        typer.echo(f"{n.occurred_at.isoformat()}  {n.event_type:28s}  {n.summary}")
    typer.echo(f"\ncontiguous={traj.is_contiguous}  nodes={len(traj.nodes)}")
    if verify:
        ok = replay_trajectory(traj)
        typer.echo("replay=PASS" if ok else "replay=FAIL")
        raise typer.Exit(0 if ok else 1)
