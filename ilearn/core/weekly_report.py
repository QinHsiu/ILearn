"""W3: calendar-week parent report per nickname (Mon–Sun, Beijing time).

This week vs last week, evidence first: sessions, active days, evidence rows,
unassisted probe passes, hinted passes (shown, never counted as mastery), probe
gaps, mastery. Accuracy is included for reference only and labelled as such.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, Field

from ilearn.core.mastery_public import build_mastery_public_view
from ilearn.core.schemas import SessionState

BEIJING = timezone(timedelta(hours=8))

HONESTY_NOTE = (
    "提示后做对不计入掌握；正确率只作参考，证据条数、独立探针通过与探针缺口优先。"
)


class WeekBucket(BaseModel):
    label: str
    start: str
    end: str
    session_count: int = 0
    active_days: int = 0
    evidence_count: int = 0
    probe_correct_count: int = 0
    hinted_correct_count: int = 0
    probe_gap_count: int | None = None
    mastery_percent: int | None = None
    accuracy_percent: int | None = None
    focus: list[str] = Field(default_factory=list)
    session_ids: list[str] = Field(default_factory=list)


class WeeklyReport(BaseModel):
    nickname: str
    generated_at: str
    week_start: str
    week_end: str
    this_week: WeekBucket
    last_week: WeekBucket
    has_baseline: bool = False
    delta: dict[str, int | None] = Field(default_factory=dict)
    narrative: str = ""
    honesty_note: str = HONESTY_NOTE


def _stamp(session: SessionState) -> datetime | None:
    if session.paper is None or session.paper.created_at is None:
        return None
    ts = session.paper.created_at
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(BEIJING)


def _week_bounds(now: datetime) -> tuple[date, date]:
    local = now.astimezone(BEIJING)
    monday = local.date() - timedelta(days=local.weekday())
    return monday, monday + timedelta(days=6)


def _bucket(label: str, start: date, end: date, sessions: list[SessionState]) -> WeekBucket:
    rows = [(s, _stamp(s)) for s in sessions]
    inside = sorted(
        ((s, ts) for s, ts in rows if ts is not None and start <= ts.date() <= end),
        key=lambda pair: pair[1],
    )
    picked = [s for s, _ in inside]
    days = {ts.date() for _, ts in inside}

    evidence = 0
    probe_ok = 0
    hinted_ok = 0
    correct = 0
    graded = 0
    for s in picked:
        for ev in s.evidence_log or []:
            evidence += 1
            if ev.lane == "probe" and ev.correct:
                probe_ok += 1
            elif ev.correct and ev.hint_level != "none":
                hinted_ok += 1
        for g in s.grades or []:
            graded += 1
            if g.final_correct:
                correct += 1

    probe_gap: int | None = None
    mastery: int | None = None
    focus: list[str] = []
    if picked:
        latest = picked[-1]
        view = build_mastery_public_view(latest)
        probe_gap = view.probe_gap_count
        mastery = view.mastery_percent
        if latest.diagnosis is not None:
            for row in latest.diagnosis.knowledge_mastery or []:
                if row.level in {"weak", "unstable"}:
                    name = row.knowledge_name or row.knowledge_id
                    if name not in focus:
                        focus.append(name)
    accuracy = int(round(correct * 100 / graded)) if graded else None

    return WeekBucket(
        label=label,
        start=start.isoformat(),
        end=end.isoformat(),
        session_count=len(picked),
        active_days=len(days),
        evidence_count=evidence,
        probe_correct_count=probe_ok,
        hinted_correct_count=hinted_ok,
        probe_gap_count=probe_gap,
        mastery_percent=mastery,
        accuracy_percent=accuracy,
        focus=focus[:3],
        session_ids=[s.session_id for s in picked],
    )


def _diff(a: int | None, b: int | None) -> int | None:
    if a is None or b is None:
        return None
    return a - b


def _fmt(n: int | None, unit: str, *, invert_good: bool = False) -> str:
    if n is None:
        return "—"
    if n == 0:
        return f"持平"
    sign = "+" if n > 0 else ""
    good = (n < 0) if invert_good else (n > 0)
    return f"{sign}{n}{unit}（{'更好' if good else '需关注'}）"


def build_weekly_report(
    nickname: str,
    sessions: list[SessionState],
    *,
    now: datetime | None = None,
) -> WeeklyReport:
    current = now or datetime.now(timezone.utc)
    monday, sunday = _week_bounds(current)
    this_week = _bucket("本周", monday, sunday, sessions)
    last_week = _bucket("上周", monday - timedelta(days=7), sunday - timedelta(days=7), sessions)

    delta: dict[str, int | None] = {
        "session_count": this_week.session_count - last_week.session_count,
        "active_days": this_week.active_days - last_week.active_days,
        "evidence_count": this_week.evidence_count - last_week.evidence_count,
        "probe_correct_count": this_week.probe_correct_count - last_week.probe_correct_count,
        "probe_gap_count": _diff(this_week.probe_gap_count, last_week.probe_gap_count),
        "mastery_percent": _diff(this_week.mastery_percent, last_week.mastery_percent),
    }
    has_baseline = last_week.session_count > 0

    if this_week.session_count == 0 and not has_baseline:
        narrative = "本周与上周暂无学习记录；完成一次测评后，这里会按自然周汇总证据。"
    elif not has_baseline:
        narrative = (
            f"本周学习 {this_week.session_count} 次、活跃 {this_week.active_days} 天，"
            f"证据 {this_week.evidence_count} 条，独立探针通过 {this_week.probe_correct_count} 次。"
            "上周暂无记录，下周起可对比。"
        )
    else:
        parts = [
            f"学习次数{_fmt(delta['session_count'], '次')}",
            f"活跃天数{_fmt(delta['active_days'], '天')}",
            f"证据{_fmt(delta['evidence_count'], '条')}",
            f"独立探针通过{_fmt(delta['probe_correct_count'], '次')}",
        ]
        if delta["probe_gap_count"] is not None:
            parts.append(f"探针缺口{_fmt(delta['probe_gap_count'], '', invert_good=True)}")
        if delta["mastery_percent"] is not None:
            parts.append(f"掌握度{_fmt(delta['mastery_percent'], '%')}")
        narrative = "比上周：" + "；".join(parts) + "。"

    return WeeklyReport(
        nickname=(nickname or "").strip() or "学习者",
        generated_at=current.astimezone(BEIJING).isoformat(),
        week_start=monday.isoformat(),
        week_end=sunday.isoformat(),
        this_week=this_week,
        last_week=last_week,
        has_baseline=has_baseline,
        delta=delta,
        narrative=narrative,
    )


def weekly_report_as_dict(report: WeeklyReport) -> dict[str, Any]:
    return report.model_dump()
