"""Generate example_bank entries from pilot templates for under-filled knowledge_ids."""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

from ilearn.data.importers.tal_scq5k import stem_hash_prefix
from ilearn.providers.curriculum import (
    eval_answer_expr,
    fill_template_slots,
    render_template_text,
)

DEFAULT_LABEL = "北京·人教·小学数学"
_GRADE_CHAPTER = {4: "四年级上册", 5: "五年级上册", 6: "六年级上册"}
_MAX_ATTEMPTS = 60


def supplement_legacy_from_templates(
    bank: dict[str, list[dict]],
    templates_path: Path,
    legacy_knowledge: list[dict],
    *,
    min_per_kp: int = 8,
) -> dict[str, list[dict]]:
    """Fill legacy pilot knowledge_ids up to ``min_per_kp`` using templates.json."""
    if not templates_path.is_file():
        return bank

    templates = json.loads(templates_path.read_text(encoding="utf-8"))
    by_kp: dict[str, list[dict]] = defaultdict(list)
    for template in templates:
        for kp_id in template.get("knowledge_ids", []):
            by_kp[kp_id].append(template)

    names = {entry["id"]: entry["name"] for entry in legacy_knowledge}
    grades = {entry["id"]: entry.get("grade", 5) for entry in legacy_knowledge}
    legacy_ids = [entry["id"] for entry in legacy_knowledge]

    result = {kp_id: list(examples) for kp_id, examples in bank.items()}
    seen: dict[str, set[str]] = {
        kp_id: {stem_hash_prefix(str(ex.get("stem", ""))) for ex in examples}
        for kp_id, examples in result.items()
    }

    for kp_id in legacy_ids:
        current = result.setdefault(kp_id, [])
        if len(current) >= min_per_kp:
            continue

        kp_templates = by_kp.get(kp_id, [])
        if not kp_templates:
            continue

        rng = random.Random(hash(kp_id) & 0xFFFFFFFF)
        attempts = 0
        template_index = 0
        while len(current) < min_per_kp and attempts < _MAX_ATTEMPTS:
            template = kp_templates[template_index % len(kp_templates)]
            template_index += 1
            attempts += 1
            try:
                values = fill_template_slots(template, rng)
                answer_expr = template.get("answer_expr") or ""
                if not answer_expr:
                    continue
                answer = eval_answer_expr(answer_expr, values)
                stem = render_template_text(
                    template["stem_template"], values, answer=answer
                )
            except (ValueError, KeyError, TypeError):
                continue

            stem_key = stem_hash_prefix(stem)
            kp_seen = seen.setdefault(kp_id, set())
            if stem_key in kp_seen:
                continue
            kp_seen.add(stem_key)

            grade = grades.get(kp_id, 5)
            chapter_prefix = _GRADE_CHAPTER.get(grade, "")
            name = names.get(kp_id, kp_id)
            current.append(
                {
                    "id": f"ex-tpl-{template['id']}-{len(current) + 1:02d}",
                    "stem": stem,
                    "chapter": f"{chapter_prefix} {name}".strip(),
                    "label": DEFAULT_LABEL,
                    "answer": str(answer),
                    "difficulty": template.get("difficulty", "medium"),
                    "source": "template",
                }
            )

        result[kp_id] = current

    return result
