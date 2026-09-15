"""P8 concept micro-lesson resource slots (script + storyboard + poster + video slot)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from ilearn.core.intervention_library import INTERVENTION_MAP, lookup_intervention

MediaStatus = Literal["video", "poster", "storyboard", "slot"]


class ConceptLesson(BaseModel):
    knowledge_id: str
    title: str
    duration_sec: int = 60
    script_steps: list[str] = Field(default_factory=list)
    asset_url: str | None = None
    storyboard_url: str | None = None
    poster_url: str | None = None
    video_slot_url: str | None = None
    media_status: MediaStatus = "slot"
    source: str = "intervention_library"
    no_final_answer: bool = True


_SCRIPTS: dict[str, list[str]] = {
    "frac_add_same": [
        "同分母：份一样大，只比取了几份",
        "分母照抄，分子相加减",
        "用一句话复述：为什么分母不变？",
    ],
    "frac_mult": [
        "分数乘法表示「求一个数的几分之几」",
        "能约分先约分，再乘分子分母",
        "口述：这一步约掉了什么？",
    ],
    "frac_div": [
        "除以一个数 = 乘它的倒数",
        "先写出倒数，再按乘法做",
        "检查：倒数乘原数是否为 1",
    ],
    "mult_3digit": [
        "竖式：分步乘，按数位对齐",
        "先用个位乘，再用十位乘（记得错一位）",
        "相加前口头核对每一行",
    ],
    "rect_area": [
        "面积 = 长 × 宽（单位先统一）",
        "标出长和宽，再乘",
        "用平方单位说出结果含义",
    ],
}

_CONCEPT_DIR = Path(__file__).resolve().parents[2] / "data" / "pilot" / "assets" / "concept"


def _asset_exists(name: str) -> bool:
    return (_CONCEPT_DIR / name).is_file()


def _resolve_media(kid: str) -> tuple[str | None, str | None, str | None, MediaStatus]:
    """Prefer real video, then poster SVG, then storyboard md; else reserved slot."""
    video_name = f"{kid}.mp4"
    poster_name = f"{kid}.svg"
    board_name = f"{kid}.md"
    video_url = f"/pilot-assets/concept/{video_name}"
    poster_url = f"/pilot-assets/concept/{poster_name}" if _asset_exists(poster_name) else None
    storyboard = f"/pilot-assets/concept/{board_name}" if _asset_exists(board_name) else None
    if _asset_exists(video_name):
        return storyboard, poster_url, video_url, "video"
    if poster_url:
        return storyboard, poster_url, video_url, "poster"
    if storyboard:
        return storyboard, None, video_url, "storyboard"
    return None, None, video_url, "slot"


def get_concept_lesson(knowledge_id: str | None) -> ConceptLesson | None:
    if not knowledge_id:
        return None
    kid = str(knowledge_id)
    hit = lookup_intervention(kid) or INTERVENTION_MAP.get(kid)
    title = (hit or {}).get("micro_lesson") or f"概念卡 · {kid}"
    steps = list(_SCRIPTS.get(kid) or [])
    if not steps and hit:
        steps = [
            str(hit.get("micro_lesson") or title),
            str(hit.get("hint") or "用自己的话复述关键一步"),
            "对照题目条件，口述下一步（不要看终答）",
        ]
    if not steps:
        return None
    storyboard, poster_url, video_slot, status = _resolve_media(kid)
    primary = poster_url or storyboard or video_slot
    return ConceptLesson(
        knowledge_id=kid,
        title=title,
        duration_sec=60,
        script_steps=steps[:4],
        asset_url=primary,
        storyboard_url=storyboard,
        poster_url=poster_url,
        video_slot_url=video_slot,
        media_status=status,
        source="intervention_library",
        no_final_answer=True,
    )


def concept_lesson_for_item(item: Any) -> ConceptLesson | None:
    kids = list(getattr(item, "knowledge_ids", None) or [])
    for kid in kids:
        lesson = get_concept_lesson(str(kid))
        if lesson:
            return lesson
    if kids:
        kid = str(kids[0])
        storyboard, poster_url, video_slot, status = _resolve_media(kid)
        return ConceptLesson(
            knowledge_id=kid,
            title=f"概念卡 · {kid}",
            duration_sec=60,
            script_steps=[
                "用自己的话复述本题相关概念",
                "对照 rubric 步骤口述思路",
                "请教家长/老师检查卡点（不要要终答）",
            ],
            asset_url=poster_url or storyboard or video_slot,
            storyboard_url=storyboard,
            poster_url=poster_url,
            video_slot_url=video_slot,
            media_status=status,
            source="generic_slot",
            no_final_answer=True,
        )
    return None
