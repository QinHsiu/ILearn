"""W3: calendar-week (Mon–Sun, Beijing) parent report — this week vs last week, not just accuracy."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from ilearn.api.app import create_app
from ilearn.core.schemas import (
    AssessmentItem,
    AssessmentPaper,
    DiagnosisReport,
    GradeResult,
    KnowledgeEvidence,
    KnowledgeMastery,
    SessionState,
    StudentProfile,
)
from ilearn.core.weekly_report import build_weekly_report
from ilearn.storage.sessions import SessionStore

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "data" / "pilot"
BJ = timezone(timedelta(hours=8))
# Wednesday 2026-09-16 12:00 Beijing → this week = 09-14 (Mon) .. 09-20 (Sun)
NOW = datetime(2026, 9, 16, 12, 0, tzinfo=BJ)


def _sess(
    sid: str,
    created: datetime,
    *,
    weak: str = "小数乘法",
    probe_correct: int = 0,
    practice_correct: int = 0,
    graded: tuple[int, int] | None = None,
) -> SessionState:
    paper = AssessmentPaper(
        items=[
            AssessmentItem(id="q1", stem="x", type="fill", difficulty="easy", knowledge_ids=["kp"])
        ],
        grade=5,
        curriculum_label="北京·人教",
        created_at=created.astimezone(timezone.utc),
    )
    evidence = [
        KnowledgeEvidence(session_id=sid, item_id="q1", knowledge_id="kp", lane="probe", correct=True)
        for _ in range(probe_correct)
    ] + [
        KnowledgeEvidence(
            session_id=sid, item_id="q1", knowledge_id="kp", lane="practice", correct=True, hint_level="low"
        )
        for _ in range(practice_correct)
    ]
    grades: list[GradeResult] = []
    if graded:
        correct, total = graded
        grades = [GradeResult(item_id=f"g{i}", final_correct=i < correct) for i in range(total)]
    return SessionState(
        session_id=sid,
        profile=StudentProfile(region="北京", grade=5, age=11, nickname="小明"),
        paper=paper,
        grades=grades,
        evidence_log=evidence,
        diagnosis=DiagnosisReport(
            knowledge_mastery=[
                KnowledgeMastery(knowledge_id="kp", knowledge_name=weak, score_rate=0.3, level="weak")
            ],
            curriculum_label="北京·人教",
        ),
    )


def test_weekly_report_buckets_by_calendar_week_and_reports_delta():
    sessions = [
        # this week: Mon 09-14 and Tue 09-15 (two active days)
        _sess("tw1", datetime(2026, 9, 14, 19, 0, tzinfo=BJ), probe_correct=2, graded=(2, 3)),
        _sess("tw2", datetime(2026, 9, 15, 20, 0, tzinfo=BJ), probe_correct=1, practice_correct=1, graded=(3, 3)),
        # last week: Thu 09-10 only
        _sess("lw1", datetime(2026, 9, 10, 19, 0, tzinfo=BJ), probe_correct=1, graded=(1, 3), weak="小数意义"),
        # two weeks ago: must be ignored by both buckets
        _sess("old", datetime(2026, 9, 1, 19, 0, tzinfo=BJ), probe_correct=5),
    ]
    report = build_weekly_report("小明", sessions, now=NOW)

    assert report.week_start == "2026-09-14"
    assert report.week_end == "2026-09-20"
    this_week, last_week = report.this_week, report.last_week
    assert this_week.label == "本周"
    assert this_week.session_count == 2
    assert this_week.active_days == 2
    assert this_week.evidence_count == 4  # 2 + (1 probe + 1 practice)
    assert this_week.probe_correct_count == 3
    assert this_week.hinted_correct_count == 1  # hinted practice correct — shown, never counted as mastery
    assert this_week.accuracy_percent == 83  # (2+3)/6 — reference only
    assert this_week.focus == ["小数乘法"]

    assert last_week.label == "上周"
    assert last_week.start == "2026-09-07"
    assert last_week.session_count == 1
    assert last_week.active_days == 1
    assert last_week.evidence_count == 1
    assert last_week.focus == ["小数意义"]

    assert report.delta["session_count"] == 1
    assert report.delta["active_days"] == 1
    assert report.delta["evidence_count"] == 3
    assert report.delta["probe_correct_count"] == 2
    assert "比上周" in report.narrative
    assert "证据" in report.narrative
    assert "不计入掌握" in report.honesty_note
    assert "正确率" in report.honesty_note


def test_weekly_report_without_last_week_is_honest():
    sessions = [_sess("tw1", datetime(2026, 9, 15, 20, 0, tzinfo=BJ), probe_correct=1)]
    report = build_weekly_report("小明", sessions, now=NOW)
    assert report.last_week.session_count == 0
    assert report.has_baseline is False
    assert "上周" in report.narrative and "暂无" in report.narrative


def test_weekly_report_api(tmp_path: Path):
    store = SessionStore(tmp_path)
    store.save(_sess("tw1", datetime.now(BJ), probe_correct=1))
    client = TestClient(
        create_app(
            sessions_dir=tmp_path,
            pilot_data_dir=PILOT,
            relationships_path=tmp_path / "relationships.json",
            llm=None,
        )
    )
    r = client.get("/learners/小明/weekly-report")
    assert r.status_code == 200
    body = r.json()
    assert body["nickname"] == "小明"
    assert body["this_week"]["session_count"] == 1
    assert body["this_week"]["evidence_count"] == 1
    assert set(body["delta"]) >= {"session_count", "active_days", "evidence_count", "probe_correct_count"}
    assert "不计入掌握" in body["honesty_note"]
