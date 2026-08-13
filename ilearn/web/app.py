"""Streamlit teaching interface for the ILearn MVP (DEPRECATED as primary UI).

Prefer the React + Vite app under ``frontend/`` (`npm run dev` on :5173).
This module is retained temporarily for comparison only.
"""

from __future__ import annotations

import base64
import html
import os
from pathlib import Path
from typing import Any

import httpx

DEFAULT_API_BASE = "http://127.0.0.1:8000"
STEP_NAMES = ("建档", "测评作答", "批改与学情", "学习计划")

_PHASE_LABELS = {
    "onboard": "建档",
    "assess": "组题",
    "practice": "练题",
    "grade": "批改",
    "diagnose": "诊断",
    "plan": "规划",
    "practice_loop": "巩固练习",
}

_LEVEL_LABELS = {
    "mastered": "已掌握",
    "unstable": "需巩固",
    "weak": "待提升",
}
_ERROR_LABELS = {
    "concept_gap": "概念缺口",
    "calc_error": "计算错误",
    "misread": "审题偏差",
    "method_wrong": "方法不当",
    "incomplete": "过程不完整",
}
_ABILITY_LABELS = {
    "logic": "逻辑推理",
    "spatial": "空间观念",
    "mental_math": "心算能力",
    "calculation": "运算能力",
    "application": "应用能力",
    "reasoning": "数学推理",
}


class ILearnAPI:
    """Small synchronous HTTP adapter for the Streamlit UI."""

    def __init__(
        self,
        base_url: str,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=httpx.Timeout(90.0, connect=5.0))

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = self.client.request(
                method, f"{self.base_url}{path}", **kwargs
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            try:
                detail = exc.response.json().get("detail")
            except (ValueError, AttributeError):
                detail = None
            raise RuntimeError(detail or f"服务返回错误（{exc.response.status_code}）") from exc
        except httpx.RequestError as exc:
            raise RuntimeError(
                f"无法连接 ILearn API：{self.base_url}。请确认 API 已启动。"
            ) from exc
        return response.json()

    def start_session(
        self,
        region: str,
        grade: int,
        age: int,
        *,
        nickname: str | None = None,
        gender: str = "unspecified",
    ) -> tuple[str, dict[str, Any]]:
        payload: dict[str, Any] = {
            "region": region,
            "grade": grade,
            "age": age,
            "gender": gender,
        }
        if nickname is not None:
            payload["nickname"] = nickname
        created = self._request(
            "POST",
            "/sessions",
            json=payload,
        )
        session_id = created["session_id"]
        paper = self._request("POST", f"/sessions/{session_id}/assessment")
        return session_id, paper

    def submit_and_run(
        self,
        session_id: str,
        answers: dict[str, str],
        *,
        images: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        self._request(
            "POST", f"/sessions/{session_id}/submit", json={"answers": answers}
        )
        if images:
            self._request(
                "POST",
                f"/sessions/{session_id}/submit-images",
                json={"images": images},
            )
        return self._request("POST", f"/sessions/{session_id}/run")

    def get_phase(self, session_id: str) -> dict[str, Any]:
        return self._request("GET", f"/sessions/{session_id}/phase")

    def submit_images(
        self, session_id: str, images: list[dict[str, str]]
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/sessions/{session_id}/submit-images",
            json={"images": images},
        )

    def get_report(self, session_id: str) -> dict[str, Any]:
        return self._request("GET", f"/sessions/{session_id}/report")


def phase_label(phase: str) -> str:
    """Return a learner-friendly label for an orchestrator phase."""
    return _PHASE_LABELS.get(phase, phase)


def image_payload(
    item_id: str,
    file_bytes: bytes,
    *,
    mime_type: str = "image/png",
) -> dict[str, str]:
    """Build an ImageAnswer payload for the submit-images API."""
    return {
        "item_id": item_id,
        "image_base64": base64.b64encode(file_bytes).decode("ascii"),
        "mime_type": mime_type,
    }


def mime_type_for_upload(filename: str) -> str | None:
    """Map an uploaded filename to a supported image MIME type."""
    suffix = Path(filename).suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(suffix)


def grade_summary(grades: list[dict[str, Any]]) -> dict[str, int]:
    """Return headline grading counts for display."""
    return {
        "correct": sum(bool(grade.get("final_correct")) for grade in grades),
        "total": len(grades),
        "degraded": sum(bool(grade.get("grading_degraded")) for grade in grades),
    }


def mastery_rows(mastery: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Translate diagnosis data into a compact Chinese mastery table."""
    rows = []
    for item in mastery:
        errors = item.get("error_tag_counts") or {}
        error_text = "—"
        if errors:
            error_text = "、".join(
                f"{_ERROR_LABELS.get(tag, tag)} × {count}"
                for tag, count in errors.items()
                if count
            ) or "—"
        rows.append(
            {
                "知识点": str(
                    item.get("knowledge_name") or item.get("knowledge_id", "—")
                ),
                "掌握率": f"{float(item.get('score_rate', 0)):.0%}",
                "水平": _LEVEL_LABELS.get(item.get("level"), str(item.get("level", "—"))),
                "主要错因": error_text,
            }
        )
    return rows


def ability_label(name: str) -> str:
    """Return a learner-friendly ability name."""
    return _ABILITY_LABELS.get(name, name.replace("_", " ").title())


def ability_progress(score: float) -> float:
    """Convert a 0–100 ability score to Streamlit's 0.0–1.0 scale."""
    return max(0.0, min(100.0, float(score))) / 100.0


def format_source_ref_display(ref: dict[str, Any]) -> list[str]:
    """Render source reference fields for Streamlit diagnosis expanders."""
    lines: list[str] = []
    if ref.get("example_id"):
        lines.append(f'例题 ID：{ref["example_id"]}')
    if ref.get("textbook_chapter"):
        lines.append(f'教材章节：{ref["textbook_chapter"]}')
    objective_ids = ref.get("curriculum_objective_ids") or []
    if objective_ids:
        lines.append(f'课标条目：{"、".join(str(value) for value in objective_ids)}')
    if ref.get("source_label"):
        lines.append(f'来源：{ref["source_label"]}')
    return lines


def wrong_item_source_entries(session: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect wrong items that have traceable source references."""
    grades = session.get("grades") or []
    paper = session.get("paper") or {}
    items_by_id = {item["id"]: item for item in paper.get("items") or []}
    entries: list[dict[str, Any]] = []
    for grade in grades:
        if grade.get("final_correct"):
            continue
        item = items_by_id.get(grade.get("item_id", ""))
        if item is None:
            continue
        source_refs = item.get("source_refs") or []
        source_lines = [
            line
            for ref in source_refs
            for line in format_source_ref_display(ref)
        ]
        if not source_lines:
            continue
        entries.append(
            {
                "item_id": item["id"],
                "stem": item.get("stem", ""),
                "source_lines": source_lines,
            }
        )
    return entries


def _load_css(grade: int = 5, gender: str = "unspecified") -> str:
    from ilearn.web.themes import load_theme_css, theme_key_for

    base = Path(__file__).with_name("styles.css").read_text(encoding="utf-8")
    theme = load_theme_css(theme_key_for(grade, gender))
    return f"{base}\n{theme}"


def _init_state(st: Any) -> None:
    defaults = {
        "wizard_step": 0,
        "session_id": None,
        "paper": None,
        "question_index": 0,
        "answers": {},
        "image_uploads": {},
        "session_report": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _render_header(st: Any) -> None:
    st.markdown(
        """
        <div class="brand-wrap">
          <div class="brand">ILearn</div>
          <div class="subtitle">K12 学情诊断与个性化学习规划</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_stepper(st: Any) -> None:
    current = st.session_state.wizard_step
    steps = []
    for index, name in enumerate(STEP_NAMES):
        state = "active" if index == current else "done" if index < current else ""
        steps.append(
            f'<div class="step {state}"><span>{index + 1}</span>{name}</div>'
        )
    st.markdown(
        f'<div class="stepper">{"".join(steps)}</div>', unsafe_allow_html=True
    )


def _show_error(st: Any, exc: Exception) -> None:
    st.error(str(exc))


def _render_profile(st: Any, api: ILearnAPI) -> None:
    st.markdown("## 先认识一下你")
    st.caption("完成基础建档后，我们将按当前试点课标生成一份 20 题测评。试点内容目前覆盖 4–6 年级数学。")
    with st.form("profile_form"):
        nickname = st.text_input("昵称", placeholder="例如：小明（可选）")
        region = st.text_input("所在地区", value="北京", placeholder="例如：北京")
        left, right = st.columns(2)
        with left:
            grade = st.selectbox(
                "年级",
                options=tuple(range(1, 13)),
                index=4,
                format_func=lambda x: f"{x} 年级",
            )
        with right:
            age = st.number_input("年龄", min_value=6, max_value=18, value=11)
        gender = st.selectbox(
            "性别",
            options=("unspecified", "male", "female"),
            format_func=lambda x: {"unspecified": "不愿透露", "male": "男", "female": "女"}[
                x
            ],
        )
        submitted = st.form_submit_button("开始测评", use_container_width=True)

    if submitted:
        if not region.strip():
            st.warning("请填写所在地区。")
            return
        nickname_value = nickname.strip() or None
        try:
            with st.spinner("正在准备适合你的测评题目…"):
                session_id, paper = api.start_session(
                    region.strip(),
                    int(grade),
                    int(age),
                    nickname=nickname_value,
                    gender=gender,
                )
        except RuntimeError as exc:
            _show_error(st, exc)
            return
        st.session_state.profile = {"grade": int(grade), "gender": gender}
        st.session_state.session_id = session_id
        st.session_state.paper = paper
        st.session_state.answers = {}
        st.session_state.image_uploads = {}
        st.session_state.question_index = 0
        st.session_state.wizard_step = 1
        st.rerun()


def _answer_widget(st: Any, item: dict[str, Any]) -> str:
    item_id = item["id"]
    current = st.session_state.answers.get(item_id, "")
    key = f"answer_{item_id}"
    if item.get("type") == "choice" and item.get("choices"):
        choices = [str(choice) for choice in item["choices"]]
        index = choices.index(current) if current in choices else None
        return st.radio(
            "请选择一个答案",
            choices,
            index=index,
            key=key,
            label_visibility="collapsed",
        ) or ""
    if item.get("type") == "constructed":
        answer = st.text_area(
            "请填写最终答案（可附主要步骤）",
            value=current,
            key=key,
            height=150,
            placeholder="请优先写最终答案；如有需要，可继续写计算过程…",
        )
        upload = st.file_uploader(
            "可选：上传手写作答照片",
            type=("png", "jpg", "jpeg", "webp"),
            key=f"image_{item_id}",
            help="支持 PNG / JPG / WebP，将随提交一并发送至批改服务。",
        )
        if upload is not None:
            mime_type = mime_type_for_upload(upload.name)
            if mime_type is None:
                st.warning("仅支持 PNG、JPG 或 WebP 格式的图片。")
            else:
                st.session_state.image_uploads[item_id] = {
                    "bytes": upload.getvalue(),
                    "mime_type": mime_type,
                }
        elif item_id in st.session_state.image_uploads:
            del st.session_state.image_uploads[item_id]
        return answer
    return st.text_input(
        "填写答案",
        value=current,
        key=key,
        placeholder="请输入你的答案",
        label_visibility="collapsed",
    )


def _save_answer(st: Any, item_id: str, answer: str) -> bool:
    normalized = str(answer).strip()
    if not normalized:
        st.warning("请先完成本题，再继续。")
        return False
    st.session_state.answers[item_id] = normalized
    return True


def _render_assessment(st: Any, api: ILearnAPI) -> None:
    items = (st.session_state.paper or {}).get("items", [])
    if not items:
        st.error("测评题目尚未生成，请返回建档页重试。")
        if st.button("返回建档"):
            st.session_state.wizard_step = 0
            st.rerun()
        return

    index = min(st.session_state.question_index, len(items) - 1)
    item = items[index]
    st.markdown(
        f'<div class="question-progress">第 {index + 1}/{len(items)} 题</div>',
        unsafe_allow_html=True,
    )
    st.progress((index + 1) / len(items))
    st.markdown(
        f'<div class="question-card"><div class="question-meta">'
        f'{html.escape(str(item.get("difficulty", ""))).upper()} · '
        f'{html.escape(str(item.get("type", "")))}</div>'
        f'<div class="stem">{html.escape(str(item.get("stem", "")))}</div></div>',
        unsafe_allow_html=True,
    )
    answer = _answer_widget(st, item)

    previous, spacer, next_col = st.columns([1, 2, 1.4])
    with previous:
        if index > 0 and st.button("← 上一题", use_container_width=True):
            if str(answer).strip():
                st.session_state.answers[item["id"]] = str(answer).strip()
            st.session_state.question_index -= 1
            st.rerun()
    with next_col:
        if index < len(items) - 1:
            if st.button("下一题 →", type="primary", use_container_width=True):
                if _save_answer(st, item["id"], answer):
                    st.session_state.question_index += 1
                    st.rerun()
        elif st.button("提交全部答案", type="primary", use_container_width=True):
            if not _save_answer(st, item["id"], answer):
                return
            missing = [
                question["id"]
                for question in items
                if not st.session_state.answers.get(question["id"], "").strip()
            ]
            if missing:
                st.warning(f"还有 {len(missing)} 题未完成，请返回检查。")
                return
            try:
                with st.spinner("正在批改并分析学情，请稍候…"):
                    image_payloads = [
                        image_payload(
                            item_id,
                            payload["bytes"],
                            mime_type=payload["mime_type"],
                        )
                        for item_id, payload in st.session_state.image_uploads.items()
                    ]
                    api.submit_and_run(
                        st.session_state.session_id,
                        st.session_state.answers,
                        images=image_payloads or None,
                    )
                    st.session_state.session_report = api.get_report(
                        st.session_state.session_id
                    )
            except RuntimeError as exc:
                _show_error(st, exc)
                return
            st.session_state.wizard_step = 2
            st.rerun()


def _render_diagnosis(st: Any) -> None:
    session = (st.session_state.session_report or {}).get("session") or {}
    grades = session.get("grades") or []
    diagnosis = session.get("diagnosis") or {}
    summary = grade_summary(grades)

    st.markdown("## 这次测评表现")
    first, second, third = st.columns(3)
    first.metric("答对题数", f'{summary["correct"]} / {summary["total"]}')
    rate = summary["correct"] / summary["total"] if summary["total"] else 0
    second.metric("正确率", f"{rate:.0%}")
    third.metric("重点巩固", f'{len(diagnosis.get("interventions") or [])} 项')
    if summary["degraded"]:
        st.caption(f'其中 {summary["degraded"]} 题采用基础规则批改。')

    st.markdown("### 知识掌握")
    rows = mastery_rows(diagnosis.get("knowledge_mastery") or [])
    if rows:
        st.dataframe(rows, hide_index=True, use_container_width=True)
    else:
        st.info("暂无知识点掌握数据。")

    st.markdown("### 能力表现")
    ability_scores = diagnosis.get("ability_scores") or {}
    for name, score in ability_scores.items():
        numeric = max(0.0, min(100.0, float(score)))
        st.markdown(f"**{ability_label(name)}**　{numeric:.0f}")
        st.progress(ability_progress(numeric))
    st.caption("能力分数由本次题目表现启发式估算，不属于心理测量结果。")

    interventions = diagnosis.get("interventions") or []
    if interventions:
        st.markdown("### 优先巩固建议")
        for item in interventions:
            with st.expander(
                f'{item.get("priority", "·")}. {item.get("title", item.get("knowledge_id", "知识点"))}'
            ):
                st.write(item.get("why", ""))
                st.markdown(f'**先从这里开始：** {item.get("what_to_fix_first", "")}')

    wrong_sources = wrong_item_source_entries(session)
    if wrong_sources:
        st.markdown("### 错题参考来源")
        for entry in wrong_sources:
            stem = str(entry.get("stem", "")).replace("\n", " ")
            if len(stem) > 60:
                stem = stem[:57] + "..."
            with st.expander(f'{entry["item_id"]} · {stem}'):
                for line in entry.get("source_lines") or []:
                    st.markdown(f"- {line}")

    disclaimer = diagnosis.get("region_mismatch_disclaimer")
    if disclaimer:
        st.warning(disclaimer)
    if st.button("查看学习计划 →", type="primary", use_container_width=True):
        st.session_state.wizard_step = 3
        st.rerun()


def _render_plan(st: Any) -> None:
    report = st.session_state.session_report or {}
    session = report.get("session") or {}
    plan = session.get("plan") or {}
    st.markdown("## 你的学习计划")
    st.markdown(
        f'<div class="goal-card"><span>学习目标</span>'
        f'<strong>{html.escape(str(plan.get("goal", "稳步巩固薄弱知识点")))}</strong></div>',
        unsafe_allow_html=True,
    )

    milestones = plan.get("milestones") or []
    if milestones:
        st.markdown("### 阶段里程碑")
        for milestone in milestones:
            st.markdown(f"- {milestone}")

    st.markdown("### 每日安排")
    for day in plan.get("days") or []:
        tasks = "".join(
            f"<li>{html.escape(str(task))}</li>" for task in day.get("tasks") or []
        )
        focus = " · ".join(str(value) for value in day.get("focus_knowledge_ids") or [])
        st.markdown(
            f'<div class="day-card"><div class="day-title">'
            f'<strong>第 {day.get("day", "·")} 天</strong>'
            f'<span>{day.get("minutes", "—")} 分钟</span></div>'
            f'<div class="day-focus">{html.escape(focus)}</div><ul>{tasks}</ul></div>',
            unsafe_allow_html=True,
        )

    with st.expander("查看完整 Markdown 报告"):
        st.markdown(report.get("markdown") or plan.get("markdown") or "暂无报告。")
    st.info(
        plan.get("disclaimer")
        or "本计划为智能助手建议，不能替代教师专业评价。"
    )
    if st.button("重新建档"):
        for key in (
            "session_id",
            "paper",
            "answers",
            "image_uploads",
            "session_report",
        ):
            st.session_state[key] = (
                {} if key in ("answers", "image_uploads") else None
            )
        st.session_state.question_index = 0
        st.session_state.wizard_step = 0
        st.rerun()


def _render_sidebar(st: Any, api: ILearnAPI) -> None:
    with st.sidebar:
        st.markdown("### 会话状态")
        session_id = st.session_state.session_id
        if not session_id:
            st.caption("完成建档后将显示当前阶段。")
            return
        st.caption(f"会话 {session_id[:8]}…")
        try:
            phase_info = api.get_phase(session_id)
        except RuntimeError as exc:
            st.warning(str(exc))
            return
        phase = phase_info.get("phase", "—")
        st.markdown(
            f'<span class="phase-badge">{html.escape(phase_label(str(phase)))}</span>',
            unsafe_allow_html=True,
        )
        loop_count = int(phase_info.get("loop_count") or 0)
        if loop_count:
            st.caption(f"巩固练习轮次：{loop_count}")


def main() -> None:
    """Run the Streamlit application."""
    import streamlit as st

    st.set_page_config(
        page_title="ILearn · K12 学情与学习规划",
        page_icon="📘",
        layout="centered",
        initial_sidebar_state="expanded",
    )
    _init_state(st)
    profile = st.session_state.get("profile") or {}
    st.markdown(
        f"<style>{_load_css(profile.get('grade', 5), profile.get('gender', 'unspecified'))}</style>",
        unsafe_allow_html=True,
    )
    api = ILearnAPI(os.getenv("ILEARN_API_BASE", DEFAULT_API_BASE))
    _render_sidebar(st, api)
    _render_header(st)
    _render_stepper(st)

    renderers = (
        lambda: _render_profile(st, api),
        lambda: _render_assessment(st, api),
        lambda: _render_diagnosis(st),
        lambda: _render_plan(st),
    )
    renderers[st.session_state.wizard_step]()
    st.markdown(
        '<div class="footer-note">循序学习 · 看见进步</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
