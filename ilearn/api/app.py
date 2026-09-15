"""FastAPI application factory for ILearn session endpoints."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from ilearn.core.companion_continuity import build_learner_continuity
from ilearn.core.error_notebook import build_error_notebook
from ilearn.core.audience_summary import (
    build_parent_summary_safe,
    build_student_summary_safe,
    build_teacher_summary_safe,
)
from ilearn.core.effectiveness import (
    compute_metrics,
    effectiveness_payload,
    render_effectiveness_markdown,
)
from ilearn.core.enhanced_api import (
    attach_enhanced_fields,
    enhanced_api_active,
    render_enhanced_report_markdown,
)
from ilearn.demo.units import load_demo_unit
from ilearn.core.export_markdown import (
    render_advice_report_markdown,
    render_assessment_review_markdown,
)
from ilearn.core.feature_flags import FeatureRegistry
from ilearn.core.orchestrator import Orchestrator
from ilearn.core.pdf_export import (
    PdfExportError,
    get_pdf_backend_info,
    markdown_to_pdf,
    markdown_to_pdf_report,
    resolve_pdf_backend,
)
from ilearn.core.rate_limiter import RateLimiter, RateLimitMiddleware
from ilearn.core.settings import clear_settings_cache, get_settings
from ilearn.core.subject_adapter import normalize_region
from ilearn.core.user_errors import UserFriendlyError, map_exception_message
from ilearn.core.validators import validate_submit_answers
from ilearn.api.auth import create_auth_router
from ilearn.api.dashboard import create_dashboard_router
from ilearn.api.demo import create_demo_router
from ilearn.api.waitlist import create_waitlist_router
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
logger = logging.getLogger(__name__)


class CreateSessionResponse(BaseModel):
    session_id: str


class SubmitRequest(BaseModel):
    answers: dict[str, str]
    item_meta: dict[str, dict] = Field(default_factory=dict)
    timer_events: list[dict] | None = None


class TimerTelemetryRequest(BaseModel):
    timer_events: list[dict] | None = None
    item_meta_patch: dict[str, dict] | None = None


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
    relationships.reconcile()
    curriculum = PilotBeijingRenjiaoProvider(pilot_data_dir or _DEFAULT_PILOT_DATA)
    pilot_assets_root = Path(pilot_data_dir or _DEFAULT_PILOT_DATA) / "assets"
    orchestrator = Orchestrator(store=store, curriculum=curriculum, llm=llm)

    def _schedule_profile_background(
        background_tasks: BackgroundTasks,
        session_id: str,
        *,
        attach_recommendations: bool = False,
    ) -> None:
        from ilearn.core.enhanced_flags import is_enhanced_enabled
        from ilearn.services.profile_update_service import update_profile_background

        if not is_enhanced_enabled("ENABLE_ENHANCED_BACKGROUND"):
            return
        background_tasks.add_task(
            update_profile_background,
            store,
            session_id,
            llm,
            attach_recommendations=attach_recommendations,
        )

    app = FastAPI(title="ILearn", version="0.1.0")
    app.include_router(create_auth_router(auth_credentials))
    app.include_router(create_dashboard_router(store, relationships))
    app.include_router(create_demo_router(store, relationships))
    waitlist_path = _PROJECT_ROOT / "data" / "waitlist.jsonl"
    app.include_router(create_waitlist_router(path=waitlist_path))

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "ilearn"}
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
        detail = str(exc)
        if detail.startswith("session not found"):
            detail = "学习会话不存在或已过期，请从历史记录重新进入或新建会话"
        return JSONResponse(status_code=404, content={"detail": detail})

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
        from ilearn.core.quality_gates_public import quality_gates_payload

        payload = FeatureRegistry.capabilities_payload(llm_available=llm is not None)
        payload["quality_gates"] = quality_gates_payload()["summary"]
        payload["quality_gates_url"] = "/quality-gates"
        return payload

    @app.get("/quality-gates")
    def quality_gates() -> dict:
        from ilearn.core.quality_gates_public import quality_gates_payload

        return quality_gates_payload()

    @app.get("/sessions/{session_id}/mastery-public")
    def get_mastery_public(session_id: str) -> dict:
        from ilearn.core.mastery_public import build_mastery_public_view

        session = store.load(session_id)
        view = build_mastery_public_view(session)
        return {"session_id": session_id, **view.model_dump()}

    @app.get("/system/pdf-backend")
    def pdf_backend_status() -> dict:
        """Active PDF renderer and whether WeasyPrint fallback is in use."""
        return get_pdf_backend_info()

    def _pdf_response(pdf: bytes, filename: str) -> Response:
        backend = resolve_pdf_backend()
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-PDF-Backend": backend,
            },
        )

    def _load_session_optional(session_id: str) -> SessionState | None:
        try:
            return store.load(session_id)
        except FileNotFoundError:
            logger.warning("session not found for summary: %s", session_id)
            return None

    def _render_pdf_bytes(render: Callable[[], bytes]) -> bytes:
        try:
            return render()
        except PdfExportError as exc:
            logger.error("PDF export unavailable: %s", exc.message)
            raise HTTPException(
                status_code=503,
                detail={"code": exc.code, "message": exc.message},
            ) from exc
        except ImportError as exc:
            logger.warning("PDF dependency missing: %s", exc)
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "PDF_UNAVAILABLE",
                    "message": "PDF 渲染引擎未就绪，请检查系统依赖或稍后重试。",
                },
            ) from exc
        except Exception as exc:
            logger.exception("PDF generation failed")
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "PDF_GENERATION_FAILED",
                    "message": f"报告生成失败，请重试。错误参考: {exc}",
                },
            ) from exc

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

    @app.post("/sessions/{session_id}/timer-telemetry", status_code=204)
    def timer_telemetry(session_id: str, body: TimerTelemetryRequest) -> Response:
        orchestrator.append_timer_telemetry(
            session_id,
            timer_events=body.timer_events,
            item_meta_patch=body.item_meta_patch,
        )
        return Response(status_code=204)

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
            session_id,
            answers,
            item_meta=body.item_meta,
            timer_events=body.timer_events,
        )

    @app.post("/sessions/{session_id}/grade", response_model=list[GradeResult])
    def grade(session_id: str) -> list[GradeResult]:
        return orchestrator.grade(session_id)

    @app.post("/sessions/{session_id}/diagnose", response_model=DiagnosisReport)
    def diagnose(
        session_id: str, background_tasks: BackgroundTasks
    ) -> DiagnosisReport:
        report = orchestrator.diagnose(session_id)
        _schedule_profile_background(background_tasks, session_id)
        return report

    @app.post("/sessions/{session_id}/plan", response_model=LearningPlanReport)
    def plan(session_id: str, background_tasks: BackgroundTasks) -> LearningPlanReport:
        report = orchestrator.plan(session_id)
        _schedule_profile_background(
            background_tasks, session_id, attach_recommendations=True
        )
        return report

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

    @app.get("/sessions/{session_id}/replan/explain")
    def replan_explain(session_id: str) -> dict:
        session = store.load(session_id)
        explain = (session.metadata or {}).get("replan_explain")
        if not explain:
            from ilearn.core.replan_explain import build_replan_explanation

            built = build_replan_explanation(
                portrait=session.portrait,
                diagnosis=session.diagnosis,
                previous_plan=None,
                new_plan=session.plan,
            )
            return {"session_id": session_id, "explain": built.model_dump()}
        return {"session_id": session_id, "explain": explain}

    @app.get("/sessions/{session_id}/items/{item_id}/concept-lesson")
    def get_concept_lesson(session_id: str, item_id: str) -> dict:
        from ilearn.core.concept_lesson import concept_lesson_for_item

        session = store.load(session_id)
        paper = session.paper
        if paper is None:
            raise HTTPException(status_code=404, detail="paper not found")
        item = next((i for i in paper.items if i.id == item_id), None)
        if item is None:
            raise HTTPException(status_code=404, detail="item not found")
        lesson = concept_lesson_for_item(item)
        if lesson is None:
            raise HTTPException(status_code=404, detail="concept lesson not found")
        return {"session_id": session_id, "item_id": item_id, "lesson": lesson.model_dump()}

    @app.get("/sessions/{session_id}/report", response_model=ReportResponse)
    def report(session_id: str) -> ReportResponse:
        session = store.load(session_id)
        markdown = orchestrator.report(session_id)
        return ReportResponse(markdown=markdown, session=session)

    @app.get("/sessions/{session_id}/effectiveness")
    def get_effectiveness(session_id: str) -> dict:
        session = store.load(session_id)
        return effectiveness_payload(session)

    @app.get("/learners/{nickname}/continuity")
    def get_learner_continuity(nickname: str) -> dict:
        sessions = store.list_by_nickname(nickname)
        return build_learner_continuity(nickname, sessions).model_dump()

    @app.get("/sessions/{session_id}/grading-receipts")
    def get_grading_receipts(session_id: str) -> dict:
        session = store.load(session_id)
        rows = []
        for grade in session.grades or []:
            receipt = grade.receipt.model_dump(mode="json") if grade.receipt else None
            rows.append(
                {
                    "item_id": grade.item_id,
                    "final_correct": grade.final_correct,
                    "grading_degraded": grade.grading_degraded,
                    "lane": grade.lane,
                    "receipt": receipt,
                }
            )
        return {"session_id": session_id, "receipts": rows}

    @app.get("/sessions/{session_id}/error-notebook")
    def get_error_notebook(session_id: str) -> dict:
        session = store.load(session_id)
        return {
            "session_id": session_id,
            "items": build_error_notebook(session),
        }

    @app.get("/sessions/{session_id}/decision-log/summary")
    def get_decision_log_summary(session_id: str) -> dict:
        session = store.load(session_id)
        phases: list[str] = []
        agents: list[str] = []
        for row in session.decision_log or []:
            agent = getattr(row, "agent", None) or getattr(row, "agent_name", None)
            phase = getattr(row, "phase", None)
            if hasattr(phase, "value"):
                phase = phase.value
            if phase and str(phase) not in phases:
                phases.append(str(phase))
            if agent and str(agent) not in agents:
                agents.append(str(agent))
        history = session.metadata.get("phase_history") if isinstance(session.metadata, dict) else None
        if isinstance(history, list):
            for p in history:
                if str(p) not in phases:
                    phases.append(str(p))
        if not phases:
            phases = [session.phase.value if hasattr(session.phase, "value") else str(session.phase)]
        return {
            "session_id": session_id,
            "phases": phases,
            "agents": agents,
            "decision_count": len(session.decision_log or []),
        }

    @app.get("/sessions/{session_id}/summary/teacher")
    def get_teacher_summary(session_id: str, enhanced: bool = False) -> dict:
        session = _load_session_optional(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="session not found")
        payload = build_teacher_summary_safe(session).model_dump()
        if enhanced_api_active(enhanced):
            return attach_enhanced_fields(payload, session)
        return payload

    @app.get("/sessions/{session_id}/summary/parent")
    def get_parent_summary(session_id: str, enhanced: bool = False) -> dict:
        session = _load_session_optional(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="session not found")
        payload = build_parent_summary_safe(session).model_dump()
        if enhanced_api_active(enhanced):
            return attach_enhanced_fields(payload, session)
        return payload

    @app.get("/sessions/{session_id}/summary/student")
    def get_student_summary(session_id: str, enhanced: bool = False) -> dict:
        session = _load_session_optional(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="session not found")
        payload = build_student_summary_safe(session).model_dump()
        if enhanced_api_active(enhanced):
            return attach_enhanced_fields(payload, session)
        return payload

    @app.get("/sessions/{session_id}/enhanced/report.pdf")
    def export_enhanced_report_pdf(session_id: str) -> Response:
        from ilearn.core.enhanced_flags import is_enhanced_enabled

        if not is_enhanced_enabled("ENABLE_ENHANCED_API"):
            raise HTTPException(
                status_code=404,
                detail="enhanced report disabled",
            )
        session = store.load(session_id)
        markdown = render_enhanced_report_markdown(session)
        pdf = _render_pdf_bytes(lambda: markdown_to_pdf_report(markdown))
        return _pdf_response(pdf, "ILearn-enhanced-report.pdf")

    @app.get("/sessions/{session_id}/export/assessment.pdf")
    def export_assessment_pdf(session_id: str) -> Response:
        session = store.load(session_id)
        try:
            markdown = render_assessment_review_markdown(session)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        pdf = _render_pdf_bytes(lambda: markdown_to_pdf(markdown))
        return _pdf_response(pdf, "ILearn-assessment.pdf")

    @app.get("/sessions/{session_id}/export/report.pdf")
    def export_report_pdf(session_id: str) -> Response:
        session = store.load(session_id)
        markdown = render_advice_report_markdown(session)
        pdf = _render_pdf_bytes(lambda: markdown_to_pdf_report(markdown))
        return _pdf_response(pdf, "ILearn-report.pdf")

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

        def _render() -> bytes:
            return markdown_to_pdf(markdown)

        pdf = _render_pdf_bytes(_render)
        return _pdf_response(pdf, "ILearn-effectiveness.pdf")

    @app.get("/sessions/{session_id}/export/grading-receipts.pdf")
    def export_grading_receipts_pdf(session_id: str) -> Response:
        from ilearn.core.winbar_exports import grading_receipts_markdown

        session = store.load(session_id)
        markdown = grading_receipts_markdown(session)
        pdf = _render_pdf_bytes(lambda: markdown_to_pdf(markdown))
        return _pdf_response(pdf, "ILearn-grading-receipts.pdf")

    @app.get("/sessions/{session_id}/export/parent-card.pdf")
    def export_parent_card_pdf(session_id: str) -> Response:
        from ilearn.core.audience_summary import build_parent_summary_safe
        from ilearn.core.parent_action_summary import ParentActionSummary
        from ilearn.core.winbar_exports import parent_action_card_markdown

        session = store.load(session_id)
        parent = build_parent_summary_safe(session)
        action = None
        if parent.action_summary:
            action = ParentActionSummary.model_validate(parent.action_summary)
        markdown = parent_action_card_markdown(session, summary=action)
        pdf = _render_pdf_bytes(lambda: markdown_to_pdf(markdown))
        return _pdf_response(pdf, "ILearn-parent-card.pdf")

    @app.get("/sessions/{session_id}/export/error-notebook.pdf")
    def export_error_notebook_pdf(session_id: str) -> Response:
        from ilearn.core.winbar_exports import error_notebook_markdown

        session = store.load(session_id)
        markdown = error_notebook_markdown(session)
        pdf = _render_pdf_bytes(lambda: markdown_to_pdf(markdown))
        return _pdf_response(pdf, "ILearn-error-notebook.pdf")

    @app.post("/sessions/{session_id}/tiers/assign")
    def assign_tier_papers(session_id: str, body: dict | None = None) -> dict:
        from ilearn.core.class_receipts import apply_tier_assign_and_save

        session = store.load(session_id)
        payload = body or {}
        topic = payload.get("topic") if isinstance(payload, dict) else None
        students = payload.get("students") if isinstance(payload, dict) else None
        return apply_tier_assign_and_save(
            store,
            session,
            topic=topic if isinstance(topic, str) else None,
            students=students if isinstance(students, list) else None,
        )

    @app.get("/sessions/{session_id}/tiers/receipt")
    def get_tier_receipt(session_id: str) -> dict:
        session = store.load(session_id)
        receipt = (session.metadata or {}).get("tier_assignment_receipt")
        if not receipt:
            raise HTTPException(status_code=404, detail="tier assignment not found")
        return {"session_id": session_id, "receipt": receipt}

    @app.get("/sessions/{session_id}/tiers/timeline")
    def get_tier_timeline(session_id: str) -> dict:
        session = store.load(session_id)
        timeline = (session.metadata or {}).get("tier_assignment_timeline") or []
        return {
            "session_id": session_id,
            "timeline": timeline,
            "count": len(timeline),
        }

    @app.post("/sessions/{session_id}/error-notebook/repractice")
    def build_error_repractice(session_id: str) -> dict:
        from ilearn.core.winbar_exports import build_repractice_paper

        session = store.load(session_id)
        paper = build_repractice_paper(session)
        meta = dict(session.metadata or {})
        meta["repractice_paper"] = paper
        session.metadata = meta
        store.save(session)
        return {"session_id": session_id, "paper": paper, "item_count": len(paper.get("items") or [])}

    @app.post("/sessions/{session_id}/repractice/activate")
    def activate_repractice(session_id: str) -> SessionState:
        """Swap session paper to repractice set and reset answers/grades for a new attempt."""
        from ilearn.core.schemas import AssessmentPaper

        session = store.load(session_id)
        raw = (session.metadata or {}).get("repractice_paper")
        if not raw:
            from ilearn.core.winbar_exports import build_repractice_paper

            raw = build_repractice_paper(session)
            meta = dict(session.metadata or {})
            meta["repractice_paper"] = raw
            session.metadata = meta
        paper = AssessmentPaper.model_validate(raw)
        session.paper = paper
        session.answers = []
        session.image_answers = []
        session.grades = []
        session.diagnosis = None
        session.plan = None
        from ilearn.core.schemas import SessionPhase

        session.phase = SessionPhase.PRACTICE
        store.save(session)
        return session

    @app.get("/sessions/{session_id}/invite")
    def get_session_invite(session_id: str) -> dict:
        from ilearn.core.invite import ensure_session_invite

        session = store.load(session_id)
        code = ensure_session_invite(session, store)
        return {
            "session_id": session_id,
            "invite_code": code,
            "hint": "把绑定码发给家长/老师，无需粘贴完整会话 ID",
        }

    @app.post("/sessions/{session_id}/unlock-requests")
    def create_unlock_request(session_id: str, body: dict | None = None) -> dict:
        session = store.load(session_id)
        payload = body or {}
        item_id = str(payload.get("item_id") or "").strip()
        if not item_id:
            raise HTTPException(status_code=400, detail="item_id required")
        meta = dict(session.metadata or {})
        rows = list(meta.get("unlock_requests") or [])
        from datetime import datetime, timezone

        row = {
            "item_id": item_id,
            "status": "pending",
            "requested_at": datetime.now(timezone.utc).isoformat(),
        }
        rows = [r for r in rows if r.get("item_id") != item_id] + [row]
        meta["unlock_requests"] = rows[-50:]
        session.metadata = meta
        store.save(session)
        return {"session_id": session_id, "request": row}

    @app.get("/sessions/{session_id}/unlock-requests")
    def list_unlock_requests(session_id: str) -> dict:
        session = store.load(session_id)
        rows = (session.metadata or {}).get("unlock_requests") or []
        return {"session_id": session_id, "requests": rows}

    @app.post("/sessions/{session_id}/unlock-requests/{item_id}/approve")
    def approve_unlock_request(session_id: str, item_id: str) -> dict:
        session = store.load(session_id)
        meta = dict(session.metadata or {})
        rows = list(meta.get("unlock_requests") or [])
        found = False
        for row in rows:
            if row.get("item_id") == item_id:
                row["status"] = "approved"
                found = True
        if not found:
            rows.append({"item_id": item_id, "status": "approved"})
        meta["unlock_requests"] = rows
        session.metadata = meta
        store.save(session)
        answer_key = None
        if session.paper:
            for item in session.paper.items:
                if item.id == item_id:
                    answer_key = item.answer_key
                    break
        return {
            "session_id": session_id,
            "item_id": item_id,
            "status": "approved",
            "answer_key": answer_key,
        }

    @app.post("/sessions/{session_id}/run", response_model=SessionState)
    def run(session_id: str, background_tasks: BackgroundTasks) -> SessionState:
        state = orchestrator.run_after_submit(session_id)
        _schedule_profile_background(
            background_tasks, session_id, attach_recommendations=True
        )
        return state

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
                "waitlist",
                "healthz",
                "demo",
                "auth",
                "dashboard",
                "learners",
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
