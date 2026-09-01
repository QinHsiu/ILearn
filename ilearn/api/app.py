"""FastAPI application factory for ILearn session endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from ilearn.core.audience_summary import build_parent_summary, build_teacher_summary
from ilearn.core.effectiveness import (
    compute_metrics,
    effectiveness_payload,
    render_effectiveness_markdown,
)
from ilearn.demo.units import load_demo_unit
from ilearn.core.export_markdown import (
    render_advice_report_markdown,
    render_assessment_review_markdown,
)
from ilearn.core.feature_flags import FeatureRegistry
from ilearn.core.orchestrator import Orchestrator
from ilearn.core.pdf_export import markdown_to_pdf
from ilearn.core.rate_limiter import RateLimiter, RateLimitMiddleware
from ilearn.core.settings import clear_settings_cache, get_settings
from ilearn.core.subject_adapter import normalize_region
from ilearn.core.user_errors import UserFriendlyError, map_exception_message
from ilearn.core.validators import validate_submit_answers
from ilearn.api.auth import create_auth_router
from ilearn.api.dashboard import create_dashboard_router
from ilearn.api.demo import create_demo_router
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


class HeartbeatResponse(BaseModel):
    ok: bool
    phase: str
    server_time: str


class ReportResponse(BaseModel):
    markdown: str
    session: SessionState


class TutorStartRequest(BaseModel):
    item_id: str


class TutorHintRequest(BaseModel):
    item_id: str
    user_message: str


class AdaptiveStartRequest(BaseModel):
    semester: str | None = None


class AdaptiveAnchorResult(BaseModel):
    item_id: str
    is_correct: bool
    knowledge_ids: list[str] = Field(default_factory=list)


class AdaptiveContinueRequest(BaseModel):
    anchor_results: list[AdaptiveAnchorResult]


class AdaptiveAssessmentResponse(BaseModel):
    is_anchor: bool
    paper: AssessmentPaper
    inferred_chapter: str | None = None
    inferred_kps: list[str] = Field(default_factory=list)
    anchor_kps: list[str] = Field(default_factory=list)
    target_kps: list[str] = Field(default_factory=list)
    semester: str | None = None
    diagnosis: dict | None = None
    requested: int = 0
    delivered: int = 0
    shortfall: int = 0
    layer2_used: bool = False
    layer2_source: str = "none"
    multimodal_count: int = 0
    curriculum_ref_summary: dict | None = None


def create_app(
    *,
    sessions_dir: Path | str | None = None,
    pilot_data_dir: Path | str | None = None,
    relationships_path: Path | str | None = None,
    llm: LLMClient | None = None,
    credentials: dict[str, dict[str, str]] | None = None,
) -> FastAPI:
    """Build a FastAPI app wired to the ILearn orchestrator."""
    load_dotenv()
    clear_settings_cache()
    settings = get_settings()
    auth_credentials = credentials or {
        "parent": {
            "username": settings.parent_username,
            "password": settings.parent_password,
            "user_id": settings.parent_user_id,
        },
        "teacher": {
            "username": settings.teacher_username,
            "password": settings.teacher_password,
            "user_id": settings.teacher_user_id,
        },
    }
    if llm is None:
        llm = LLMClient.from_env()
    if not llm.available():
        llm = None
    store = SessionStore(sessions_dir or settings.sessions_dir or _DEFAULT_SESSIONS_DIR)
    relationships = RelationshipStore(
        relationships_path or _PROJECT_ROOT / "data" / "relationships.json",
        store,
    )
    curriculum = PilotBeijingRenjiaoProvider(pilot_data_dir or _DEFAULT_PILOT_DATA)
    pilot_assets_root = Path(pilot_data_dir or _DEFAULT_PILOT_DATA) / "assets"
    orchestrator = Orchestrator(store=store, curriculum=curriculum, llm=llm)

    app = FastAPI(title="ILearn", version="0.1.0")
    app.include_router(create_auth_router(auth_credentials))
    app.include_router(create_dashboard_router(store, relationships))
    app.include_router(create_demo_router(store, relationships))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(_WEB_ORIGINS),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if settings.rate_limit_enabled:
        limiter = RateLimiter(
            max_requests=settings.rate_limit_max_requests,
            window_seconds=settings.rate_limit_window_seconds,
        )
        app.add_middleware(RateLimitMiddleware, limiter=limiter)

    @app.exception_handler(FileNotFoundError)
    async def handle_not_found(_request, exc: FileNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(UserFriendlyError)
    async def handle_user_friendly(_request, exc: UserFriendlyError) -> JSONResponse:
        return JSONResponse(status_code=400, content=exc.to_response())

    @app.exception_handler(ValueError)
    async def handle_bad_request(_request, exc: ValueError) -> JSONResponse:
        mapped = map_exception_message(str(exc))
        if mapped is not None:
            return JSONResponse(status_code=400, content=mapped.to_response())
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(CurriculumError)
    async def handle_curriculum_error(_request, exc: CurriculumError) -> JSONResponse:
        mapped = map_exception_message(str(exc))
        if mapped is not None:
            return JSONResponse(status_code=422, content=mapped.to_response())
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    spa_index = _FRONTEND_DIST / "index.html"
    spa_enabled = spa_index.is_file()

    @app.get("/", include_in_schema=False, response_model=None)
    def root() -> Response:
        if spa_enabled:
            return FileResponse(spa_index)
        return RedirectResponse(url="/docs")

    @app.get("/capabilities")
    def capabilities() -> dict:
        """Offline / hybrid / online feature tiers for UI transparency."""
        return FeatureRegistry.capabilities_payload(llm_available=llm is not None)

    @app.get("/pilot-assets/{asset_path:path}", include_in_schema=True)
    def pilot_assets(asset_path: str) -> FileResponse:
        """Serve committed pilot images from data/pilot/assets/."""
        normalized = asset_path.replace("\\", "/")
        parts = Path(normalized).parts
        if not normalized or any(part == ".." for part in parts):
            raise HTTPException(status_code=400, detail="invalid asset path")
        candidate = (pilot_assets_root / normalized).resolve()
        try:
            candidate.relative_to(pilot_assets_root.resolve())
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid asset path") from None
        if not candidate.is_file():
            raise HTTPException(status_code=404, detail="asset not found")
        return FileResponse(candidate)

    @app.post("/sessions", response_model=CreateSessionResponse)
    def create_session(profile: StudentProfile) -> CreateSessionResponse:
        canonical = normalize_region(profile.region)
        if canonical is None:
            raise UserFriendlyError(
                "E-004",
                technical_detail=f"RegionNotSupported: {profile.region}",
            )
        profile = profile.model_copy(update={"region": canonical})
        session_id = orchestrator.create_session(profile)
        return CreateSessionResponse(session_id=session_id)

    @app.get("/sessions", response_model=list[SessionSummary])
    def list_sessions(nickname: str | None = None) -> list[SessionSummary]:
        if not (nickname or "").strip():
            raise ValueError("nickname query parameter is required")
        return orchestrator.list_sessions(nickname)

    @app.get("/sessions/{session_id}", response_model=SessionState)
    def get_session(session_id: str) -> SessionState:
        return orchestrator.get_session(session_id)

    @app.post("/sessions/{session_id}/heartbeat", response_model=HeartbeatResponse)
    def heartbeat(session_id: str) -> HeartbeatResponse:
        return HeartbeatResponse.model_validate(orchestrator.heartbeat(session_id))

    @app.delete("/sessions/{session_id}", status_code=204)
    def delete_session(session_id: str) -> Response:
        orchestrator.delete_session(session_id)
        return Response(status_code=204)

    @app.post("/sessions/{session_id}/assessment", response_model=AssessmentPaper)
    def generate_assessment(session_id: str) -> AssessmentPaper:
        return orchestrator.generate_assessment(session_id)

    @app.post(
        "/sessions/{session_id}/assessment/adaptive/start",
        response_model=AdaptiveAssessmentResponse,
    )
    def adaptive_assessment_start(
        session_id: str, body: AdaptiveStartRequest | None = None
    ) -> AdaptiveAssessmentResponse:
        payload = orchestrator.start_adaptive_assessment(
            session_id, semester=(body.semester if body else None)
        )
        return AdaptiveAssessmentResponse(
            is_anchor=bool(payload.get("is_anchor")),
            paper=payload["paper"],
            inferred_chapter=payload.get("inferred_chapter"),
            inferred_kps=list(payload.get("inferred_kps") or []),
            anchor_kps=list(payload.get("anchor_kps") or []),
            semester=payload.get("semester"),
            requested=int(payload.get("requested") or 0),
            delivered=int(payload.get("delivered") or 0),
            shortfall=int(payload.get("shortfall") or 0),
            layer2_used=bool(payload.get("layer2_used")),
            layer2_source=str(payload.get("layer2_source") or "none"),
            multimodal_count=int(payload.get("multimodal_count") or 0),
            curriculum_ref_summary=payload.get("curriculum_ref_summary"),
        )

    @app.post(
        "/sessions/{session_id}/assessment/adaptive/continue",
        response_model=AdaptiveAssessmentResponse,
    )
    def adaptive_assessment_continue(
        session_id: str, body: AdaptiveContinueRequest
    ) -> AdaptiveAssessmentResponse:
        payload = orchestrator.continue_adaptive_assessment(
            session_id,
            [row.model_dump() for row in body.anchor_results],
        )
        return AdaptiveAssessmentResponse(
            is_anchor=bool(payload.get("is_anchor")),
            paper=payload["paper"],
            inferred_chapter=payload.get("inferred_chapter"),
            inferred_kps=list(payload.get("inferred_kps") or []),
            target_kps=list(payload.get("target_kps") or []),
            semester=payload.get("semester"),
            diagnosis=payload.get("diagnosis"),
            requested=int(payload.get("requested") or 0),
            delivered=int(payload.get("delivered") or 0),
            shortfall=int(payload.get("shortfall") or 0),
            layer2_used=bool(payload.get("layer2_used")),
            layer2_source=str(payload.get("layer2_source") or "none"),
            multimodal_count=int(payload.get("multimodal_count") or 0),
            curriculum_ref_summary=payload.get("curriculum_ref_summary"),
        )

    @app.post("/sessions/{session_id}/submit", response_model=SessionState)
    def submit(session_id: str, body: SubmitRequest) -> SessionState:
        answers = validate_submit_answers(body.answers)
        return orchestrator.submit(
            session_id, answers, item_meta=body.item_meta
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

    @app.get("/sessions/{session_id}/effectiveness")
    def get_effectiveness(session_id: str) -> dict:
        session = store.load(session_id)
        return effectiveness_payload(session)

    @app.get("/sessions/{session_id}/summary/teacher")
    def get_teacher_summary(session_id: str) -> dict:
        session = store.load(session_id)
        return build_teacher_summary(session).model_dump()

    @app.get("/sessions/{session_id}/summary/parent")
    def get_parent_summary(session_id: str) -> dict:
        session = store.load(session_id)
        return build_parent_summary(session).model_dump()

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

    @app.get("/sessions/{session_id}/export/effectiveness.pdf")
    def export_effectiveness_pdf(session_id: str) -> Response:
        session = store.load(session_id)
        metrics = compute_metrics(session)
        unit_id = session.metadata.get("demo_unit")
        unit_name = ""
        if unit_id:
            try:
                unit_name = str(load_demo_unit(str(unit_id)).get("name") or "")
            except FileNotFoundError:
                unit_name = str(unit_id)
        markdown = render_effectiveness_markdown(metrics, unit_name=unit_name)
        pdf = markdown_to_pdf(markdown)
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="ILearn-effectiveness.pdf"'
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
                "pilot-assets",
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
