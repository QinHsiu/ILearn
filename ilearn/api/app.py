"""FastAPI application factory for ILearn session endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from pydantic import BaseModel

from ilearn.core.orchestrator import Orchestrator
from ilearn.core.schemas import (
    AssessmentPaper,
    DiagnosisReport,
    GradeResult,
    ImageAnswer,
    LearningPlanReport,
    SessionState,
    StudentProfile,
)
from ilearn.providers.curriculum import PilotBeijingRenjiaoProvider
from ilearn.providers.llm import LLMClient
from ilearn.storage.sessions import SessionStore

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SESSIONS_DIR = _PROJECT_ROOT / "data" / "sessions"
_DEFAULT_PILOT_DATA = _PROJECT_ROOT / "data" / "pilot"
_STREAMLIT_ORIGINS = (
    "http://localhost:8501",
    "http://127.0.0.1:8501",
)


class CreateSessionResponse(BaseModel):
    session_id: str


class SubmitRequest(BaseModel):
    answers: dict[str, str]


class ImageSubmitRequest(BaseModel):
    images: list[ImageAnswer]


class PhaseResponse(BaseModel):
    phase: str
    loop_count: int


class ReportResponse(BaseModel):
    markdown: str
    session: SessionState


def create_app(
    *,
    sessions_dir: Path | str | None = None,
    pilot_data_dir: Path | str | None = None,
    llm: LLMClient | None = None,
) -> FastAPI:
    """Build a FastAPI app wired to the ILearn orchestrator."""
    load_dotenv()
    if llm is None:
        llm = LLMClient.from_env()
    if not llm.available():
        llm = None
    store = SessionStore(sessions_dir or _DEFAULT_SESSIONS_DIR)
    curriculum = PilotBeijingRenjiaoProvider(pilot_data_dir or _DEFAULT_PILOT_DATA)
    orchestrator = Orchestrator(store=store, curriculum=curriculum, llm=llm)

    app = FastAPI(title="ILearn", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(_STREAMLIT_ORIGINS),
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

    @app.post("/sessions", response_model=CreateSessionResponse)
    def create_session(profile: StudentProfile) -> CreateSessionResponse:
        session_id = orchestrator.create_session(profile)
        return CreateSessionResponse(session_id=session_id)

    @app.post("/sessions/{session_id}/assessment", response_model=AssessmentPaper)
    def generate_assessment(session_id: str) -> AssessmentPaper:
        return orchestrator.generate_assessment(session_id)

    @app.post("/sessions/{session_id}/submit", response_model=SessionState)
    def submit(session_id: str, body: SubmitRequest) -> SessionState:
        return orchestrator.submit(session_id, body.answers)

    @app.post("/sessions/{session_id}/grade", response_model=list[GradeResult])
    def grade(session_id: str) -> list[GradeResult]:
        return orchestrator.grade(session_id)

    @app.post("/sessions/{session_id}/diagnose", response_model=DiagnosisReport)
    def diagnose(session_id: str) -> DiagnosisReport:
        return orchestrator.diagnose(session_id)

    @app.post("/sessions/{session_id}/plan", response_model=LearningPlanReport)
    def plan(session_id: str) -> LearningPlanReport:
        return orchestrator.plan(session_id)

    @app.get("/sessions/{session_id}/report", response_model=ReportResponse)
    def report(session_id: str) -> ReportResponse:
        session = store.load(session_id)
        markdown = orchestrator.report(session_id)
        return ReportResponse(markdown=markdown, session=session)

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

    return app


app = create_app()
