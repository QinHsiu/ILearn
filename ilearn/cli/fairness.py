"""CLI: fairness audit (read-only, no LLM)."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from ilearn.core.projection import load_all_states
from ilearn.fairness.calculator import FairnessConfig, compute_fairness
from ilearn.scheduler.event_log import SchedulerEventLog

app = typer.Typer(help="公平性审计")

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _event_log() -> SchedulerEventLog:
    import os

    root = Path(os.getenv("ILEARN_SCHEDULER_LOG_DIR") or _PROJECT_ROOT / "data" / "scheduler_events")
    return SchedulerEventLog(root)


def _learners_root() -> Path:
    import os

    return Path(os.getenv("ILEARN_LEARNERS_DIR") or _PROJECT_ROOT / "data" / "learners")


def _load_learner_attributes() -> dict[str, dict]:
    path = _learners_root() / "attributes.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    # Derive grade from engagement_signals / empty attrs
    attrs: dict[str, dict] = {}
    for lid, state in load_all_states(learners_root=_learners_root()).items():
        grade = (state.engagement_signals or {}).get("grade")
        region = (state.engagement_signals or {}).get("region")
        row = {}
        if grade is not None:
            row["grade"] = str(grade)
        if region is not None:
            row["region"] = str(region)
        if row:
            attrs[lid] = row
    return attrs


@app.command("audit")
def audit(
    attribute: str = typer.Option("grade", "--attribute"),
    window_days: int = typer.Option(90, "--window-days"),
    mastery_gap: float = typer.Option(0.10, "--mastery-gap"),
    expired_gap: float = typer.Option(0.15, "--expired-gap"),
) -> None:
    events = _event_log().read_recent(days=window_days)
    learners = load_all_states(learners_root=_learners_root())
    attrs = _load_learner_attributes()
    report = compute_fairness(
        events,
        learners,
        attrs,
        attribute_name=attribute,
        cfg=FairnessConfig(
            mastery_gap_threshold=mastery_gap,
            expired_rate_gap_threshold=expired_gap,
        ),
    )
    for c in report.comparisons:
        marker = "!" if c.flagged else " "
        typer.echo(
            f"{marker} {c.metric:24s} {c.group_a} vs {c.group_b}: "
            f"gap={c.gap:+.3f} (n={c.n_a}/{c.n_b})"
        )
    typer.echo(f"\nflagged: {report.flagged_count}/{len(report.comparisons)}")
