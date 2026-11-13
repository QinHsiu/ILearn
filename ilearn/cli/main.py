"""Typer CLI for ILearn run and eval commands."""

from __future__ import annotations

import json
import os
from pathlib import Path

import typer
from dotenv import load_dotenv

from ilearn.core.grading import StepGrader
from ilearn.core.orchestrator import Orchestrator
from ilearn.core.schemas import SessionPhase, StudentProfile
from ilearn.agents.eval_agent import EvalAgent
from ilearn.eval.runner import run_eval
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.providers.llm import LLMClient
from ilearn.storage.sessions import SessionStore

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SESSIONS_DIR = _PROJECT_ROOT / "data" / "sessions"
_DEFAULT_PILOT_DATA = _PROJECT_ROOT / "data" / "pilot"
_DEFAULT_FIXTURES = _PROJECT_ROOT / "data" / "eval" / "step_grading_fixtures.json"
_MISTAKE_LOCATION_FIXTURES = _PROJECT_ROOT / "data" / "eval" / "mistake_location_fixtures.json"
_MISTAKE_CORRECTION_FIXTURES = _PROJECT_ROOT / "data" / "eval" / "mistake_correction_fixtures.json"
_SCAFFOLDING_FIXTURES = _PROJECT_ROOT / "data" / "eval" / "scaffolding_fixtures.json"
_REPORT_EXCERPT_LINES = 12

app = typer.Typer(help="ILearn MVP CLI")
agents_app = typer.Typer(help="Multi-agent pipeline commands")
audit_app = typer.Typer(help="Audit / trace / resume commands")
app.add_typer(agents_app, name="agents")
app.add_typer(audit_app, name="audit")

# Bypass scheduler + read-only experience (must not call LLM)
from ilearn.cli.experience import app as experience_app  # noqa: E402
from ilearn.cli.scheduler import app as scheduler_app  # noqa: E402

app.add_typer(scheduler_app, name="scheduler")
app.add_typer(experience_app, name="experience")


_PHASE_LABELS = {
    SessionPhase.ONBOARD: "建档",
    SessionPhase.ASSESS: "组题",
    SessionPhase.PRACTICE: "练题",
    SessionPhase.GRADE: "批改",
    SessionPhase.DIAGNOSE: "诊断",
    SessionPhase.PLAN: "规划",
    SessionPhase.PRACTICE_LOOP: "巩固练习",
}


def _load_configured_llm() -> LLMClient | None:
    load_dotenv()
    configured_llm = LLMClient.from_env()
    return configured_llm if configured_llm.available() else None


def _resolve_sessions_dir() -> Path:
    configured = os.getenv("ILEARN_SESSIONS_DIR")
    return Path(configured) if configured else _DEFAULT_SESSIONS_DIR


def _build_orchestrator(
    sessions_dir: Path | None = None,
    *,
    offline: bool = False,
) -> Orchestrator:
    llm = None if offline else _load_configured_llm()
    store = SessionStore(sessions_dir or _resolve_sessions_dir())
    curriculum = PilotBeijingRenjiaoProvider(_DEFAULT_PILOT_DATA)
    return Orchestrator(store=store, curriculum=curriculum, llm=llm)


def _session_artifact_dir(session_id: str, sessions_dir: Path) -> Path:
    path = sessions_dir / session_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load_answers(path: Path) -> dict[str, str]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise typer.BadParameter("answers file must be a JSON object mapping item id to answer")
    return {str(key): str(value) for key, value in raw.items()}


@app.command()
def run(
    region: str = typer.Option(..., "--region", help="Learner region, e.g. 北京"),
    grade: int = typer.Option(..., "--grade", help="Grade level (4, 5, or 6)"),
    age: int = typer.Option(..., "--age", help="Learner age"),
    answers_file: Path | None = typer.Option(
        None,
        "--answers-file",
        help="JSON file mapping item ids to student answers",
    ),
    auto_answer: bool = typer.Option(
        False,
        "--auto-answer",
        help="Use answer keys for an offline end-to-end demo",
    ),
) -> None:
    """Run an assessment session end-to-end or emit a paper for manual answering."""
    sessions_dir = _DEFAULT_SESSIONS_DIR
    orchestrator = _build_orchestrator(sessions_dir)
    profile = StudentProfile(region=region, grade=grade, age=age)

    session_id = orchestrator.create_session(profile)
    paper = orchestrator.generate_assessment(session_id)
    artifact_dir = _session_artifact_dir(session_id, sessions_dir)

    paper_path = artifact_dir / "paper.json"
    paper_path.write_text(paper.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(f"Paper: {paper_path}")

    if answers_file is None and not auto_answer:
        return

    answers = (
        _load_answers(answers_file)
        if answers_file
        else {item.id: (item.answer_key or "") for item in paper.items}
    )
    orchestrator.submit(session_id, answers)
    orchestrator.run_after_submit(session_id)
    report_md = orchestrator.report(session_id)

    report_path = artifact_dir / "report.md"
    report_path.write_text(report_md, encoding="utf-8")
    typer.echo(f"Report: {report_path}")

    excerpt_lines = report_md.splitlines()[:_REPORT_EXCERPT_LINES]
    if excerpt_lines:
        typer.echo("")
        typer.echo("--- report excerpt ---")
        typer.echo("\n".join(excerpt_lines))


@app.command()
def eval(
    fixtures: Path = typer.Option(
        _DEFAULT_FIXTURES,
        "--fixtures",
        help="Path to step-grading fixtures JSON",
    ),
    use_llm: bool = typer.Option(
        False,
        "--use-llm",
        help="Use configured LLM for constructed-item grading (default: offline rules only)",
    ),
    agents: bool = typer.Option(
        False,
        "--agents",
        help="Grade via PracticeAgent and print agent trace",
    ),
    mathtutorbench: bool = typer.Option(
        False,
        "--mathtutorbench",
        help="Run mistake-location benchmark (MathTutorBench-style fixtures)",
    ),
    completeness: bool = typer.Option(
        False,
        "--completeness",
        "--tutor-gym",
        help="Run TutorGym-style step completeness benchmark",
    ),
    mistake_correction: bool = typer.Option(
        False,
        "--mistake-correction",
        help="Run mistake-correction benchmark (MathTutorBench-style fixtures)",
    ),
    scaffolding: bool = typer.Option(
        False,
        "--scaffolding",
        help="Run scaffolding hint-level benchmark (MathTutorBench-style fixtures)",
    ),
) -> None:
    """Evaluate step grading against fixture expectations."""
    llm = _load_configured_llm() if use_llm else None

    if completeness:
        eval_agent = EvalAgent(fixtures_dir=_DEFAULT_FIXTURES.parent, llm=llm)
        report = eval_agent.run_completeness()
        typer.echo(f"total: {report['total']}")
        typer.echo(f"completeness: {report['completeness']:.4f}")
        typer.echo(f"avg_step_score: {report.get('avg_step_score', 0.0):.4f}")
        return

    if mistake_correction:
        fixtures_path = _MISTAKE_CORRECTION_FIXTURES
        if not fixtures_path.is_file():
            typer.echo(f"Fixtures not found: {fixtures_path}", err=True)
            raise typer.Exit(code=1)
        eval_agent = EvalAgent(fixtures_dir=fixtures_path.parent, llm=llm)
        report = eval_agent.run_mistake_correction(fixtures_path=fixtures_path)
        typer.echo(f"total: {report['total']}")
        typer.echo(f"correction_acc: {report['correction_acc']:.4f}")
        return

    if scaffolding:
        fixtures_path = _SCAFFOLDING_FIXTURES
        if not fixtures_path.is_file():
            typer.echo(f"Fixtures not found: {fixtures_path}", err=True)
            raise typer.Exit(code=1)
        eval_agent = EvalAgent(fixtures_dir=fixtures_path.parent, llm=llm)
        report = eval_agent.run_scaffolding(fixtures_path=fixtures_path)
        typer.echo(f"total: {report['total']}")
        typer.echo(f"hint_level_match: {report['hint_level_match']:.4f}")
        return

    if mathtutorbench:
        fixtures_path = _MISTAKE_LOCATION_FIXTURES
        if not fixtures_path.is_file():
            typer.echo(f"Fixtures not found: {fixtures_path}", err=True)
            raise typer.Exit(code=1)
        eval_agent = EvalAgent(fixtures_dir=fixtures_path.parent, llm=llm)
        report = eval_agent.run_mistake_location(fixtures_path=fixtures_path)
        typer.echo(f"total: {report['total']}")
        typer.echo(f"step_f1: {report['step_f1']:.4f}")
        typer.echo(f"first_error_acc: {report['first_error_acc']:.4f}")
        return

    if not fixtures.is_file():
        typer.echo(f"Fixtures not found: {fixtures}", err=True)
        raise typer.Exit(code=1)

    llm = _load_configured_llm() if use_llm else None
    if agents:
        eval_agent = EvalAgent(fixtures_dir=fixtures.parent, llm=llm)
        report = eval_agent.run_step_grading(fixtures_path=fixtures)
        typer.echo(f"accuracy: {report['accuracy']:.4f}")
        typer.echo(f"step_f1: {report['step_f1']:.4f}")
        typer.echo(f"json_valid_rate: {report['json_valid_rate']:.4f}")
        typer.echo(f"total: {report['total']}")
        typer.echo(f"agents_invoked: {', '.join(report['agents_invoked'])}")
        return

    metrics = run_eval(fixtures, grader=StepGrader(llm))
    typer.echo(f"accuracy: {metrics.accuracy:.4f}")
    typer.echo(f"macro_f1: {metrics.macro_f1:.4f}")
    typer.echo(f"json_valid_rate: {metrics.json_valid_rate:.4f}")


@agents_app.command("run")
def agents_run(
    region: str = typer.Option(..., "--region", help="Learner region, e.g. 北京"),
    grade: int = typer.Option(..., "--grade", help="Grade level (4, 5, or 6)"),
    age: int = typer.Option(..., "--age", help="Learner age"),
    offline: bool = typer.Option(
        False,
        "--offline",
        help="Run without LLM (auto-answer demo using answer keys)",
    ),
) -> None:
    """Run the multi-agent pipeline and print session phase plus report path."""
    sessions_dir = _resolve_sessions_dir()
    orchestrator = _build_orchestrator(sessions_dir, offline=offline)
    profile = StudentProfile(region=region, grade=grade, age=age)

    session_id = orchestrator.create_session(profile)
    typer.echo(f"会话 ID: {session_id}")

    paper = orchestrator.generate_assessment(session_id)
    phase = orchestrator.current_phase(session_id)
    typer.echo(
        f"Phase: {phase.value} ({_PHASE_LABELS.get(phase, phase.value)}) · {len(paper.items)} 题"
    )

    answers = {item.id: (item.answer_key or "") for item in paper.items}
    orchestrator.submit(session_id, answers)
    session = orchestrator.run_after_submit(session_id)
    report_md = orchestrator.report(session_id)

    artifact_dir = _session_artifact_dir(session_id, sessions_dir)
    report_path = artifact_dir / "report.md"
    report_path.write_text(report_md, encoding="utf-8")

    final_phase = orchestrator.current_phase(session_id)
    typer.echo(
        f"Phase: {final_phase.value} ({_PHASE_LABELS.get(final_phase, final_phase.value)})"
    )
    if session.loop_count:
        typer.echo(f"Practice loops: {session.loop_count}")
    typer.echo(f"Report: {report_path}")


@app.command("trace")
def trace_session(
    session_id: str = typer.Argument(..., help="Session id to render as a span tree"),
) -> None:
    """Show OpenTelemetry-inspired span tree for one session's event_log."""
    import json

    from ilearn.orchestration.events import build_span_tree

    store = SessionStore(_resolve_sessions_dir())
    try:
        session = store.load(session_id)
    except FileNotFoundError:
        typer.echo(f"Session not found: {session_id}", err=True)
        raise typer.Exit(code=1)
    tree = build_span_tree(session.event_log or [])
    typer.echo(json.dumps(tree, ensure_ascii=False, indent=2))


@audit_app.command("replay")
def audit_replay(
    session_id: str = typer.Argument(..., help="Session id"),
) -> None:
    """Replay decision digests chronologically (read-only verification view)."""
    store = SessionStore(_resolve_sessions_dir())
    try:
        session = store.load(session_id)
    except FileNotFoundError:
        typer.echo(f"Session not found: {session_id}", err=True)
        raise typer.Exit(code=1)
    events = session.event_log or []
    if not events:
        typer.echo("No event_log entries (legacy session may only have decision_log).")
        for row in session.decision_log or []:
            phase = row.phase.value if hasattr(row.phase, "value") else str(row.phase)
            typer.echo(f"- {phase} · {row.agent} · ok={row.ok} · {row.reason}")
        return
    for event in events:
        if event.kind == "stage_span":
            continue
        stage = event.stage.value if hasattr(event.stage, "value") else str(event.stage)
        typer.echo(
            f"{event.ts.isoformat()} · {event.kind} · {stage} · {event.agent} · "
            f"in={event.input_digest[:12]} out={event.output_digest[:12]} · "
            f"hash={event.content_hash[:12]}"
        )


@audit_app.command("derailment")
def audit_derailment(
    persist: bool = typer.Option(
        True,
        "--persist/--no-persist",
        help="Write reports/derailment_latest.json under the sessions dir",
    ),
) -> None:
    """Aggregate UNEXPECTED_STATE events across sessions (derailment rate view)."""
    import json

    from ilearn.orchestration.unexpected import (
        derailment_report,
        persist_derailment_report,
    )

    sessions_dir = _resolve_sessions_dir()
    store = SessionStore(sessions_dir)
    report = derailment_report(store.list_all())
    typer.echo(json.dumps(report, ensure_ascii=False, indent=2))
    if persist:
        path = persist_derailment_report(sessions_dir / "reports", report)
        typer.echo(f"Persisted: {path}")


@app.command("resume")
def resume_cmd(
    session_id: str = typer.Argument(..., help="Session id paused on UNEXPECTED_STATE"),
    decision: str = typer.Option(
        "continue",
        "--decision",
        help="continue | replan | human_takeover",
    ),
    note: str = typer.Option("", "--note", help="Operator note"),
) -> None:
    """Inject a handling decision and append a resume event."""
    from ilearn.orchestration.unexpected import resume_session

    store = SessionStore(_resolve_sessions_dir())
    try:
        session = store.load(session_id)
    except FileNotFoundError:
        typer.echo(f"Session not found: {session_id}", err=True)
        raise typer.Exit(code=1)
    try:
        event = resume_session(session, decision=decision, note=note)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)
    store.save(session)
    typer.echo(f"Resumed with decision={decision} event_id={event.event_id}")


if __name__ == "__main__":
    app()
