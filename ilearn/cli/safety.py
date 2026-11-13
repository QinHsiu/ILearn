"""CLI: safety review stats (read-only over event log)."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from ilearn.scheduler.event_log import SchedulerEventLog

app = typer.Typer(help="独立安全审查")

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _event_log() -> SchedulerEventLog:
    import os

    root = Path(os.getenv("ILEARN_SCHEDULER_LOG_DIR") or _PROJECT_ROOT / "data" / "scheduler_events")
    return SchedulerEventLog(root)


@app.command("stats")
def stats(last: int = typer.Option(7, "--last", help="Lookback days")) -> None:
    rows = _event_log().list_by_type("safety.reviewed", days=last)
    allow = sum(1 for r in rows if (r.get("payload") or {}).get("decision") == "allow")
    block = sum(1 for r in rows if (r.get("payload") or {}).get("decision") == "block")
    typer.echo(
        json.dumps(
            {"total": len(rows), "allow": allow, "block": block, "days": last},
            indent=2,
        )
    )
