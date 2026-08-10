"""Multi-subject layered quota templates for assessment blueprints."""

from __future__ import annotations

import json
from pathlib import Path

from ilearn.core.schemas import BlueprintSlot, Difficulty, ItemType, PaperBlueprint, StudentProfile

from ilearn.providers.curriculum import require_pilot_grade

# Joint (difficulty, type) blueprint: 10 easy / 8 medium / 2 hard and 8 choice / 8 fill / 4 constructed.
MIX_BLUEPRINT: list[tuple[Difficulty, ItemType]] = [
    ("easy", "choice"),
    ("easy", "fill"),
    ("easy", "choice"),
    ("easy", "fill"),
    ("easy", "constructed"),
    ("easy", "choice"),
    ("easy", "fill"),
    ("easy", "choice"),
    ("easy", "fill"),
    ("easy", "constructed"),
    ("medium", "choice"),
    ("medium", "fill"),
    ("medium", "choice"),
    ("medium", "fill"),
    ("medium", "constructed"),
    ("medium", "choice"),
    ("medium", "fill"),
    ("medium", "constructed"),
    ("hard", "choice"),
    ("hard", "fill"),
]

_LAYER_TO_DIFFICULTY: dict[str, Difficulty] = {
    "basic": "easy",
    "raising": "medium",
    "extension": "hard",
}


def load_quota(subject: str, pilot_dir: Path | str) -> dict:
    if subject == "math":
        return {
            "subject": "math",
            "slots": list(MIX_BLUEPRINT),
        }
    path = Path(pilot_dir) / "subjects" / f"{subject}_quota.json"
    if not path.is_file():
        raise ValueError(f"unknown subject quota template: {subject}")
    return json.loads(path.read_text(encoding="utf-8"))


def _slots_from_quota(quota: dict) -> list[tuple[Difficulty, ItemType]]:
    if "slots" in quota:
        return list(quota["slots"])
    difficulties: list[Difficulty] = []
    for layer, count in quota["layers"].items():
        difficulty = _LAYER_TO_DIFFICULTY.get(layer)
        if difficulty is None:
            raise ValueError(f"unknown layer label: {layer}")
        difficulties.extend([difficulty] * count)
    item_types: list[ItemType] = []
    for item_type, count in quota["types"].items():
        item_types.extend([item_type] * count)
    if len(difficulties) != len(item_types):
        raise ValueError("layer and type counts must both sum to paper size")
    return list(zip(difficulties, item_types, strict=True))


def build_blueprint_for_subject(
    profile: StudentProfile,
    pilot_dir: Path | str,
    weak_ids: list[str] | None = None,
) -> PaperBlueprint:
    quota = load_quota(profile.subject, pilot_dir)
    weak_queue = list(weak_ids) if weak_ids else []
    slots: list[BlueprintSlot] = []
    for difficulty, item_type in _slots_from_quota(quota):
        kid = weak_queue.pop(0) if weak_queue else None
        slots.append(
            BlueprintSlot(
                difficulty=difficulty,
                item_type=item_type,
                knowledge_id=kid,
            )
        )
    return PaperBlueprint(grade=require_pilot_grade(profile.grade), slots=slots)  # type: ignore[arg-type]
