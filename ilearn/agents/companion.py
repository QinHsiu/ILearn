"""CompanionAgent — Ask / Answer entry; Evaluate as a tool; Plan/Predict stubs.

Multimodal: text or PerceptionInput (speech/image → text). Every reply includes
a TTS-ready ``speech`` envelope.
"""

from __future__ import annotations

import re
from typing import Any

from ilearn.core.schemas import (
    CompanionAction,
    CompanionIntent,
    CompanionMode,
    CompanionModality,
    CompanionPerceptionIn,
    CompanionReply,
    CompanionSpeechOut,
    LifeStage,
    SessionState,
    StudentProfile,
)
from ilearn.orchestration.events import append_orchestration_event
from ilearn.providers.curriculum import CurriculumProvider
from ilearn.rails.base import AnswerLeakRail, HintLadderRail, run_rails

_EVAL_PAT = re.compile(r"(测评|测验|考试|出卷|做套题|测一下|诊断卷)")
_PLAN_PAT = re.compile(r"(规划|计划|安排|日程|本周|下周学什么)")
_PRED_PAT = re.compile(r"(预测|会不会|能不能学会|风险|估计)")
_ANSWER_PAT = re.compile(r"(什么是|怎么|如何|讲解|讲一下|解释|为什么|帮我理解)")
_ASK_SHORT = re.compile(r"^(我想学|怎么办|不会|教我|帮帮我)[\s\W]*$", re.I)


def infer_life_stage(profile: StudentProfile) -> LifeStage:
    if profile.life_stage:
        return profile.life_stage
    grade = int(profile.grade)
    if grade <= 6:
        return "primary"
    if grade <= 9:
        return "junior_high"
    if grade <= 12:
        return "senior_high"
    return "undergrad"


def _speech_envelope(text: str, *, locale: str = "zh-CN") -> CompanionSpeechOut:
    return CompanionSpeechOut(ssml_or_text=text, locale=locale, speakable=bool(text.strip()))


class CompanionAgent:
    name = "companion"

    def __init__(self, curriculum: CurriculumProvider, llm: Any | None = None) -> None:
        self._curriculum = curriculum
        self._llm = llm
        pilot_dir = getattr(curriculum, "_data_dir", None)
        self._retriever = None
        if pilot_dir is not None:
            from ilearn.providers.curriculum_rag import CurriculumRagRetriever

            self._retriever = CurriculumRagRetriever(pilot_dir)

    def route_intent(self, message: str) -> CompanionIntent:
        text = (message or "").strip()
        if _EVAL_PAT.search(text):
            return "evaluate"
        if _PLAN_PAT.search(text):
            return "plan"
        if _PRED_PAT.search(text):
            return "predict"
        if _ASK_SHORT.match(text) or len(text) <= 4:
            return "ask"
        if _ANSWER_PAT.search(text) or "？" in text or "?" in text:
            return "answer"
        if len(text) < 12:
            return "ask"
        return "answer"

    def chat(
        self,
        session: SessionState,
        message: str | None = None,
        *,
        perception: CompanionPerceptionIn | None = None,
        mode: CompanionMode = "exam_tutor",
    ) -> CompanionReply:
        modality, text = self._resolve_input(message, perception)
        if not text.strip():
            reply_text = "我在听。你可以用文字或语音告诉我：想学什么、卡在哪？"
            return self._finalize(
                session,
                intent="ask",
                reply_text=reply_text,
                modality=modality,
                mode=mode,
                citations=[],
                actions=[],
                user_text=text,
            )

        intent = self.route_intent(text)
        life_stage = infer_life_stage(session.profile)

        if intent == "evaluate":
            reply_text = (
                "好的，我可以启动测评工具来摸清你的掌握情况。"
                "确认后将进入现有评估流水线（组卷→作答→批改→诊断）。"
            )
            actions = [CompanionAction(type="start_assessment", payload={})]
            return self._finalize(
                session,
                intent=intent,
                reply_text=reply_text,
                modality=modality,
                mode=mode,
                citations=[],
                actions=actions,
                life_stage=life_stage,
                user_text=text,
            )

        if intent == "plan":
            reply_text = "规划（日程/路径编排）能力将在下一期开放；当前可先答疑或启动测评收集证据。"
            return self._finalize(
                session,
                intent=intent,
                reply_text=reply_text,
                modality=modality,
                mode=mode,
                citations=[],
                actions=[],
                life_stage=life_stage,
                user_text=text,
            )

        if intent == "predict":
            reply_text = "预测（掌握风险/复习预警）能力将在下一期开放；当前可先测评或提问。"
            return self._finalize(
                session,
                intent=intent,
                reply_text=reply_text,
                modality=modality,
                mode=mode,
                citations=[],
                actions=[],
                life_stage=life_stage,
                user_text=text,
            )

        if intent == "ask":
            reply_text = self._ask_reply(text, life_stage)
            return self._finalize(
                session,
                intent=intent,
                reply_text=reply_text,
                modality=modality,
                mode=mode,
                citations=[],
                actions=[],
                life_stage=life_stage,
                user_text=text,
            )

        # answer
        if mode == "exam_tutor" and re.search(
            r"(直接告诉我|正确答案是多少|给我答案|不要提示只要答案)", text
        ):
            reply_text = (
                "考试辅导模式下我不会直接给最终答案。"
                "我们一步步想：已知条件是什么？想用哪一步运算？"
            )
            citations = []
            intent = "ask"
        else:
            reply_text, citations = self._answer_reply(
                session, text, life_stage, mode=mode
            )
            intent = "answer"
        return self._finalize(
            session,
            intent=intent,
            reply_text=reply_text,
            modality=modality,
            mode=mode,
            citations=citations,
            actions=[
                CompanionAction(
                    type="suggest_evaluate",
                    payload={"prompt": "如果想确认掌握程度，可以启动一次测评。"},
                )
            ]
            if intent == "answer"
            else [],
            life_stage=life_stage,
            user_text=text,
        )

    @staticmethod
    def _resolve_input(
        message: str | None,
        perception: CompanionPerceptionIn | None,
    ) -> tuple[CompanionModality, str]:
        if perception is not None:
            text = (perception.text or message or "").strip()
            return perception.source_type, text
        return "text", (message or "").strip()

    def _ask_reply(self, text: str, life_stage: LifeStage) -> str:
        stage_hint = {
            "primary": "小学",
            "junior_high": "初中",
            "senior_high": "高中",
            "undergrad": "大学",
            "graduate": "研究生",
        }.get(life_stage, "当前学段")
        return (
            f"我先确认一下（{stage_hint}）：你更想解决哪一块？"
            "① 某个具体知识点讲解 ② 一道不会的题 ③ 先做一套小测评摸底。"
            f"你刚才说「{text[:40]}」，可以再具体一点吗？"
        )

    def _answer_reply(
        self,
        session: SessionState,
        text: str,
        life_stage: LifeStage,
        *,
        mode: CompanionMode,
    ) -> tuple[str, list]:
        citations = []
        if self._retriever is not None:
            try:
                citations = self._retriever.retrieve(session.profile, text, top_k=3)
            except Exception:
                citations = []
        if not citations:
            body = (
                "未命中可引用的课标/例题片段。"
                "你可以换个说法，或启动测评让我用题目定位缺口。"
            )
            if life_stage not in {"primary", "junior_high"}:
                body = (
                    f"当前学段（{life_stage}）内容包尚未就绪。" + body
                )
        else:
            bits = []
            for c in citations[:2]:
                bits.append(f"「{c.title}」：{c.excerpt[:120]}")
            body = "根据课标检索，我这样理解：\n" + "\n".join(bits)
            body += "\n\n要不要我再出几道相关练习，或直接启动测评？"

        if mode == "exam_tutor":
            body = self._apply_exam_rails(body)
        return body, list(citations)

    def _apply_exam_rails(self, message: str) -> str:
        from ilearn.core.schemas import AssessmentItem

        item = AssessmentItem(
            id="companion",
            stem="companion",
            type="fill",
            difficulty="easy",
            knowledge_ids=[],
            answer_key="",
        )
        verdict = run_rails(
            [HintLadderRail(), AnswerLeakRail()],
            phase="hint_1",
            item=item,
            model_message=message,
            stage="post",
        )
        if not verdict.ok:
            return "先别急着看答案。说出你卡在哪一步，我用提问带你走。"
        return message

    def _finalize(
        self,
        session: SessionState,
        *,
        intent: CompanionIntent,
        reply_text: str,
        modality: CompanionModality,
        mode: CompanionMode,
        citations: list,
        actions: list[CompanionAction],
        life_stage: LifeStage | None = None,
        user_text: str = "",
    ) -> CompanionReply:
        speech = _speech_envelope(reply_text)
        reply = CompanionReply(
            intent=intent,
            reply=reply_text,
            speech=speech,
            citations=citations,
            actions=actions,
            input_modality=modality,
            mode=mode,
            life_stage=life_stage or infer_life_stage(session.profile),
        )
        append_orchestration_event(
            session,
            agent=self.name,
            stage=session.phase,
            reason=f"companion:{intent}",
            input_payload={"modality": modality, "mode": mode, "user_text": user_text},
            output_payload={
                "intent": intent,
                "reply": reply_text,
                "actions": [a.type for a in actions],
            },
            kind=f"companion_{intent}",
            metadata={
                "input_modality": modality,
                "user_text": user_text,
                "reply": reply_text,
                "intent": intent,
            },
        )
        return reply
