"""Tests for ProgressMapper cold-start progress inference."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ilearn.core.progress_mapper import ProgressMapper, infer_semester

BEIJING = "\u5317\u4eac"
FALL = "\u4e0a\u5b66\u671f"
SPRING = "\u4e0b\u5b66\u671f"
RENJIAO = "\u4eba\u6559\u7248"


def test_infer_semester_spring_and_fall():
    assert infer_semester(datetime(2026, 3, 15)) == SPRING
    assert infer_semester(datetime(2026, 8, 31)) == SPRING
    assert infer_semester(datetime(2026, 9, 1)) == FALL
    assert infer_semester(datetime(2026, 2, 1)) == FALL


def test_infer_current_progress_hits_week(tmp_path: Path):
    mapping = {
        BEIJING: {
            RENJIAO: {
                "5\u5e74\u7ea7": {
                    SPRING: {
                        "chapters": [
                            {
                                "chapter": "frac_add_same",
                                "weeks": [1, 2, 3],
                                "knowledge_ids": ["frac_add_same"],
                            },
                            {
                                "chapter": "frac_mult",
                                "weeks": [4, 5, 6],
                                "knowledge_ids": ["frac_mult"],
                            },
                        ]
                    }
                }
            }
        }
    }
    path = tmp_path / "progress_mapping.json"
    path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
    mapper = ProgressMapper(str(path))
    chapter, kps = mapper.infer_current_progress(
        BEIJING, 5, SPRING, datetime(2026, 3, 25)
    )
    assert chapter == "frac_mult"
    assert kps == ["frac_mult"]


def test_infer_current_progress_falls_back_to_first_chapter(tmp_path: Path):
    mapping = {
        BEIJING: {
            RENJIAO: {
                "4\u5e74\u7ea7": {
                    FALL: {
                        "chapters": [
                            {
                                "chapter": "mult_3digit",
                                "weeks": [1, 2],
                                "knowledge_ids": ["mult_3digit"],
                            }
                        ]
                    }
                }
            }
        }
    }
    path = tmp_path / "progress_mapping.json"
    path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
    mapper = ProgressMapper(str(path))
    chapter, kps = mapper.infer_current_progress(
        BEIJING, 4, FALL, datetime(2026, 12, 1)
    )
    assert chapter == "mult_3digit"
    assert kps == ["mult_3digit"]


def test_missing_file_uses_embedded_fallback(tmp_path: Path):
    mapper = ProgressMapper(str(tmp_path / "missing.json"))
    chapter, kps = mapper.infer_current_progress(
        BEIJING, 5, SPRING, datetime(2026, 4, 1)
    )
    assert isinstance(chapter, str) and chapter
    assert isinstance(kps, list) and kps
    assert all(isinstance(x, str) for x in kps)


def test_repo_progress_mapping_loads():
    mapper = ProgressMapper()
    chapter, kps = mapper.infer_current_progress(
        BEIJING, 5, SPRING, datetime(2026, 4, 1)
    )
    assert chapter
    assert kps
