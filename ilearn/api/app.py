"""FastAPI application factory for ILearn session endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from ilearn.core.export_markdown import (
    render_advice_report_markdown,
    render_assessment_review_markdown,
)
from ilearn.core.orchestrator import Orchestrator
from ilearn.core.pdf_export import markdown_to_pdf
from ilearn.api.dashboard import create_dashboard_router
from ilearn.core.schemas import (
    AssessmentPaper,
    DiagnosisReport,
    GradeResult,
    ImageAnswer,
    LearningPlanReport,
    SessionState,
    SessionSummary,
    StudentProfile,
    TutorTurn,
)
from ilearn.providers.curriculum import CurriculumError, PilotBeijingRenjiaoProvider
from ilearn.providers.llm import LLMClient
from ilearn.storage.sessions import SessionStore
from ilearn.storage.relationships import RelationshipStore

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SESSIONS_DIR = _PROJECT_ROOT / "data" / "sessions"
_DEFAULT_PILOT_DATA = _PROJECT_ROOT / "data" / "pilot"
_WEB_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8501",  # legacy Streamlit (deprecated)
    "http://127.0.0.1:8501",
)
_FRONTEND_DIST = _PROJECT_ROOT / "frontend" / "dist"


class CreateSessionResponse(BaseModel):
    session_id: str


class SubmitRequest(BaseModel):
    answers: dict[str, str]
    item_meta: dict[str, dict] = Field(default_factory=dict)


class ImageSubmitRequest(BaseModel):
    images: list[ImageAnswer]


class PhaseResponse(BaseModel):
    phase: str
    loop_count: int


class ReportResponse(BaseModel):
    markdown: str
    session: SessionState


class TutorStartRequest(BaseModel):
    item_id: str


class TutorHintRequest(BaseModel):
    item_id: str
    user_message: str


def create_app(
    *,
    sessions_dir: Path | str | None = None,
    pilot_data_dir: Path | str | None = None,
    relationships_path: Path | str | None = None,
    llm: LLMClient | None = None,
) -> FastAPI:
    """Build a FastAPI app wired to the ILearn orchestrator."""
    load_dotenv()
    if llm is None:
        llm = LLMClient.from_env()
    if not llm.available():
        llm = None
    store = SessionStore(sessions_dir or _DEFAULT_SESSIONS_DIR)
    relationships = RelationshipStore(
        relationships_path or _PROJECT_ROOT / "data" / "relationships.json",
        store,
    )
    curriculum = PilotBeijingRenjiaoProvider(pilot_data_dir or _DEFAULT_PILOT_DATA)
    orchestrator = Orchestrator(store=store, curriculum=curriculum, llm=llm)

    app = FastAPI(title="ILearn", version="0.1.0")
    app.include_router(create_dashboard_router(store, relationships))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(_WEB_ORIGINS),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(FileNotFoundError)
    async def handle_not_found(_request, exc: FileNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ValueError)
    async def handle_bad_request(_request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(CurriculumError)
    async def handle_curriculum_error(_request, exc: CurriculumError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    spa_index = _FRONTEND_DIST / "index.html"
    spa_enabled = spa_index.is_file()

    @app.get("/", include_in_schema=False, response_model=None)
    def root() -> Response:
        if spa_enabled:
            return FileResponse(spa_index)
        return RedirectResponse(url="/docs")

    @app.post("/sessions", response_model=CreateSessionResponse)
    def create_session(profile: StudentProfile) -> CreateSessionResponse:
        session_id = orchestrator.create_session(profile)
        return CreateSessionResponse(session_id=session_id)

    @app.get("/sessions", response_model=list[SessionSummary])
    def list_sessions(nickname: str | None = None) -> list[SessionSummary]:
        if not (nickname or "").strip():
            raise ValueError("nickname query parameter is required")
        return orchestrator.list_sessions(nickname)

    @app.delete("/sessions/{session_id}", status_code=204)
    def delete_session(session_id: str) -> Response:
        orchestrator.delete_session(session_id)
        return Response(status_code=204)

    @app.post("/sessions/{session_id}/assessment", response_model=AssessmentPaper)
    def generate_assessment(session_id: str) -> AssessmentPaper:
        return orchestrator.generate_assessment(session_id)

    @app.post("/sessions/{session_id}/submit", response_model=SessionState)
    def submit(session_id: str, body: SubmitRequest) -> SessionState:
        return orchestrator.submit(
            session_id, body.answers, item_meta=body.item_meta
        )

    @app.post("/sessions/{session_id}/grade", response_model=list[GradeResult])
    def grade(session_id: str) -> list[GradeResult]:
        return orchestrator.grade(session_id)

    @app.post("/sessions/{session_id}/diagnose", response_model=DiagnosisReport)
    def diagnose(session_id: str) -> DiagnosisReport:
        return orchestrator.diagnose(session_id)

    @app.post("/sessions/{session_id}/plan", response_model=LearningPlanReport)
    def plan(session_id: str) -> LearningPlanReport:
        return orchestrator.plan(session_id)

    @app.post("/sessions/{session_id}/tutor", response_model=TutorTurn)
    def tutor_start(session_id: str, body: TutorStartRequest) -> TutorTurn:
        return orchestrator.tutor_start(session_id, body.item_id)

    @app.post("/sessions/{session_id}/tutor/hint", response_model=TutorTurn)
    def tutor_hint(session_id: str, body: TutorHintRequest) -> TutorTurn:
        return orchestrator.tutor_hint(
            session_id, body.item_id, body.user_message
        )

    @app.post("/sessions/{session_id}/replan", response_model=LearningPlanReport)
    def replan(session_id: str) -> LearningPlanReport:
        return orchestrator.request_replan(session_id)

    @app.get("/sessions/{session_id}/report", response_model=ReportResponse)
    def report(session_id: str) -> ReportResponse:
        session = store.load(session_id)
        markdown = orchestrator.report(session_id)
        return ReportResponse(markdown=markdown, session=session)

    @app.get("/sessions/{session_id}/export/assessment.pdf")
    def export_assessment_pdf(session_id: str) -> Response:
        session = store.load(session_id)
        try:
            markdown = render_assessment_review_markdown(session)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        pdf = markdown_to_pdf(markdown)
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="ILearn-assessment.pdf"'
            },
        )

    @app.get("/sessions/{session_id}/export/report.pdf")
    def export_report_pdf(session_id: str) -> Response:
        session = store.load(session_id)
        markdown = render_advice_report_markdown(session)
        pdf = markdown_to_pdf(markdown)
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="ILearn-report.pdf"'
            },
        )

    @app.post("/sessions/{session_id}/run", response_model=SessionState)
    def run(session_id: str) -> SessionState:
        return orchestrator.run_after_submit(session_id)

    @app.get("/sessions/{session_id}/phase", response_model=PhaseResponse)
    def get_phase(session_id: str) -> PhaseResponse:
        session = store.load(session_id)
        return PhaseResponse(phase=session.phase.value, loop_count=session.loop_count)

    @app.post("/sessions/{session_id}/submit-images", response_model=SessionState)
    def submit_images(session_id: str, body: ImageSubmitRequest) -> SessionState:
        session = store.load(session_id)
        session.image_answers = body.images
        return store.save(session)

    @app.post("/sessions/{session_id}/followup", response_model=AssessmentPaper)
    def followup(session_id: str) -> AssessmentPaper:
        return orchestrator.start_practice_loop(session_id)

    if spa_enabled:
        assets_dir = _FRONTEND_DIST / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{spa_path:path}", include_in_schema=False, response_model=None)
        def spa_fallback(spa_path: str) -> Response:
            # Keep API / OpenAPI surfaces authoritative; only fall back for UI routes.
            blocked = (
                "sessions",
                "docs",
                "redoc",
                "openapi.json",
                "assets",
            )
            first = spa_path.split("/", 1)[0]
            if first in blocked or spa_path.startswith("api"):
                raise HTTPException(status_code=404, detail="Not Found")
            candidate = _FRONTEND_DIST / spa_path
            if candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(spa_index)

    return app


app = create_app()
