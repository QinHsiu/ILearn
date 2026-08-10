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
from ilearn.eval.runner import run_eval
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.providers.llm import LLMClient
from ilearn.storage.sessions import SessionStore

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SESSIONS_DIR = _PROJECT_ROOT / "data" / "sessions"
_DEFAULT_PILOT_DATA = _PROJECT_ROOT / "data" / "pilot"
_DEFAULT_FIXTURES = _PROJECT_ROOT / "data" / "eval" / "step_grading_fixtures.json"
_REPORT_EXCERPT_LINES = 12

app = typer.Typer(help="ILearn MVP CLI")
agents_app = typer.Typer(help="Multi-agent pipeline commands")
app.add_typer(agents_app, name="agents")

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
) -> None:
    """Evaluate step grading against fixture expectations."""
    if not fixtures.is_file():
        typer.echo(f"Fixtures not found: {fixtures}", err=True)
        raise typer.Exit(code=1)

    llm = _load_configured_llm() if use_llm else None
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


if __name__ == "__main__":
    app()
