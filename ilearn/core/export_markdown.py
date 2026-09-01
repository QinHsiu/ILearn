"""Markdown renderers for PDF export (assessment review + full report)."""

from __future__ import annotations

from ilearn.core.export_data import (
    ExportReportData,
    build_assessment_export_data,
)
from ilearn.core.report import render_full_report
from ilearn.core.schemas import SessionState


def render_assessment_review_markdown(session: SessionState) -> str:
    """做题复盘 markdown shaped like doc/deepseek_edition/report.txt sections."""
    data = build_assessment_export_data(session)
    return _render_assessment_markdown(data)


def render_advice_report_markdown(session: SessionState) -> str:
    """Personalized advice PDF source — existing full learning report."""
    return render_full_report(session)


def _render_assessment_markdown(data: ExportReportData) -> str:
    lines: list[str] = [
        "# ILearn 做题复盘",
        "",
        "## 个性化学习报告",
        "",
        f"- **姓名：** {data.student_name}",
        f"- **年级：** {data.grade} 年级",
        f"- **地区：** {data.region}",
        f"- **测评日期：** {data.assessment_date}",
        "",
        "## 摘要",
        "",
        f"- **正确率：** {data.summary.accuracy * 100:.1f}%",
        f"- **掌握技能：** {len(data.summary.mastered_skills)} 个",
        f"- **待加强：** {len(data.summary.weak_skills)} 个",
    ]
    hinted = [h for h in data.hint_details if h.hint_interactions]
    lines.append(f"- **需要提示的题目：** {len(hinted)} 题")
    lines.extend(["", "## 题目作答记录", ""])
    lines.append("| 题号 | 对错 | 用时 | 苏格拉底 | 辅导后 |")
    lines.append("| --- | --- | ---: | --- | --- |")

    hints_by_qid = {h.question_id: h for h in data.hint_details}
    for answer in data.answers:
        mark = "正确" if answer.is_correct else "错误"
        if answer.time_spent_seconds > 0:
            total = int(round(answer.time_spent_seconds))
            time_label = f"{total // 60}:{total % 60:02d}"
        else:
            time_label = "—"
        if answer.hint_count > 0:
            hint_label = f"{answer.hint_count} 次"
        elif answer.hint_opened:
            hint_label = "已打开"
        else:
            hint_label = "未使用"
        if answer.hint_count > 0 or answer.hint_opened:
            after_label = (
                "做对"
                if answer.solved_after_hint
                else ("仍错" if answer.solved_after_hint is False else "—")
            )
        else:
            after_label = "—"
        lines.append(
            f"| 第 {answer.index} 题 | {mark} | {time_label} | {hint_label} | {after_label} |"
        )

    lines.append("")
    for answer in data.answers:
        mark = "正确" if answer.is_correct else "错误"
        lines.append(f"### 第 {answer.index} 题 · {mark}")
        lines.append("")
        lines.append(answer.stem)
        lines.append("")
        lines.append(f"- **你的答案：** {answer.student_answer or '（未作答）'}")
        # Product choice: always show key for reviewability; emphasize when wrong.
        key_label = "正确答案" if not answer.is_correct else "标准答案"
        lines.append(f"- **{key_label}：** {answer.correct_answer or '（无）'}")
        if answer.time_spent_seconds > 0:
            total = int(round(answer.time_spent_seconds))
            lines.append(f"- **单题用时：** {total // 60} 分 {total % 60} 秒")
        if answer.has_image:
            lines.append("- 已上传手写图片")
        detail = hints_by_qid.get(answer.question_id)
        if detail and detail.hint_interactions:
            n = len(detail.hint_interactions)
            lines.append(f"- **苏格拉底交互：** {n} 次")
            if answer.solved_after_hint is True:
                lines.append("- **辅导后结果：** 做对")
            elif answer.solved_after_hint is False:
                lines.append("- **辅导后结果：** 仍错")
            for hint in detail.hint_interactions:
                user = (hint.user_input or "").strip() or "（空）"
                ai = (hint.ai_hint or "").strip() or "（空）"
                lines.append(f"  - 第{hint.turn}次：用户「{user}」→ AI「{ai}」")
        elif answer.hint_opened:
            lines.append("- **苏格拉底交互：** 已打开但未产生提示记录")
        lines.append("")

    if hinted:
        lines.extend(["## 苏格拉底交互汇总", ""])
        total = sum(len(h.hint_interactions) for h in hinted)
        solved = sum(1 for h in hinted if h.final_correct)
        lines.append(f"- **总计提示次数：** {total} 次")
        lines.append(f"- **有提示的题目：** {len(hinted)} 题")
        lines.append(f"- **提示后做对：** {solved} 题")
        lines.append("")
        for hq in hinted:
            result = "正确" if hq.final_correct else "错误"
            lines.append(
                f"- 第 {hq.index} 题：{len(hq.hint_interactions)} 次提示 · 最终{result}"
            )
        lines.append("")

    return "\n".join(lines).strip()
