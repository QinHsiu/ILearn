"""Tests for cognitive skill graph validation and seed coverage."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from ilearn.core.cognitive_profile import CognitiveSkillGraph, validate_cognitive_skills

FIXTURE = Path(__file__).parent / "fixtures" / "cognitive_skills_tiny.json"
ROOT = Path(__file__).resolve().parents[1]


def test_validate_accepts_tiny_fixture():
    errs = validate_cognitive_skills(FIXTURE)
    assert errs == []


def test_validate_rejects_bad_prereq():
    bad = {
        "skills": [
            {
                "skill_id": "a",
                "name": "x",
                "knowledge_point": "u",
                "dimension": "remember",
                "prerequisites": ["missing"],
                "grade": 4,
            }
        ]
    }
    path = Path(tempfile.mkdtemp()) / "bad.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    errs = validate_cognitive_skills(path)
    assert any("missing" in e for e in errs)


def test_seed_coverage():
    g = CognitiveSkillGraph(ROOT / "data" / "cognitive_skills.json")
    units: dict[str, list] = {}
    for skill in g.all_skills():
        units.setdefault(skill.knowledge_point, []).append(skill)
    assert len(units) >= 3
    for name, skills in units.items():
        assert len(skills) >= 10, name
