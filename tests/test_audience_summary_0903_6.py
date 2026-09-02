"""Edition 0903_6: parent summaries must hide internal skill ids."""

from __future__ import annotations

from ilearn.core.audience_summary import (
    build_parent_summary,
    translate_to_parent_language,
)
from ilearn.core.schemas import (
    DiagnosisReport,
    KnowledgeMastery,
    SessionState,
    StudentProfile,
)


def test_parent_summary_resolves_kp_ids_from_enrichment():
    session = SessionState(
        session_id="s-kp",
        profile=StudentProfile(region="北京", grade=5, age=11, nickname="小明"),
        diagnosis=DiagnosisReport(
            curriculum_label="pilot",
            knowledge_mastery=[
                KnowledgeMastery(
                    knowledge_id="kp_4433814116",
                    knowledge_name="小数乘小数",
                    score_rate=0.3,
                    level="weak",
                ),
                KnowledgeMastery(
                    knowledge_id="dec_mult",
                    knowledge_name="小数乘法",
                    score_rate=0.4,
                    level="weak",
                ),
            ],
        ),
        metadata={
            "diagnosis_enrichment": {
                "weak_skills": ["kp_4433814116", "dec_mult"],
            }
        },
    )
    summary = build_parent_summary(session)
    assert all("kp_" not in skill for skill in summary.weak_skills)
    assert all("_" not in skill for skill in summary.weak_skills)
    assert "小数乘小数" in summary.weak_skills
    assert "小数乘法" in summary.weak_skills
    assert all("kp_" not in tip for tip in summary.daily_practice_tips)


def test_parent_summary_friendly_fallback_for_unknown_ids():
    session = SessionState(
        session_id="s-unknown",
        profile=StudentProfile(region="北京", grade=5, age=11),
        diagnosis=DiagnosisReport(
            curriculum_label="pilot",
            knowledge_mastery=[],
        ),
        metadata={
            "diagnosis_enrichment": {
                "weak_skills": ["unknown_slug_xyz"],
            }
        },
    )
    summary = build_parent_summary(session)
    assert summary.weak_skills == ["一个需要加强的学习内容"]


def test_translate_to_parent_language_maps_ability_term():
    assert "本领" in translate_to_parent_language("提升核心能力")
