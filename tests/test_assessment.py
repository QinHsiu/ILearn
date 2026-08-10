import random
from pathlib import Path

import pytest

from ilearn.core.assessment import AssessmentBuildError, AssessmentBuilder
from ilearn.core.schemas import KnowledgeNode, StudentProfile
from ilearn.providers.curriculum import CurriculumProvider, PilotBeijingRenjiaoProvider

ROOT = Path(__file__).resolve().parents[1] / "data" / "pilot"


@pytest.fixture
def builder():
    return AssessmentBuilder(PilotBeijingRenjiaoProvider(ROOT), rng=random.Random(42))


def test_build_20_mix_exact(builder):
    paper = builder.build(StudentProfile(region="北京", grade=5, age=11), n=20)
    assert len(paper.items) == 20
    assert sum(1 for i in paper.items if i.difficulty == "easy") == 10
    assert sum(1 for i in paper.items if i.difficulty == "medium") == 8
    assert sum(1 for i in paper.items if i.difficulty == "hard") == 2
    assert sum(1 for i in paper.items if i.type == "choice") == 8
    assert sum(1 for i in paper.items if i.type == "fill") == 8
    assert sum(1 for i in paper.items if i.type == "constructed") == 4


def test_build_sets_paper_metadata(builder):
    paper = builder.build(StudentProfile(region="北京", grade=5, age=11))
    assert paper.grade == 5
    assert paper.curriculum_label == "北京·人教·小学数学"
    assert paper.created_at is not None


def test_build_all_grades(builder):
    for grade in (4, 5, 6):
        paper = builder.build(StudentProfile(region="北京", grade=grade, age=10), n=20)
        assert len(paper.items) == 20
        assert paper.grade == grade


def test_instantiated_items_have_stems_and_keys(builder):
    paper = builder.build(StudentProfile(region="北京", grade=5, age=11), n=20)
    for item in paper.items:
        assert item.stem.strip()
        assert item.knowledge_ids
        if item.type == "choice":
            assert item.choices
            assert len(item.choices) >= 2
            assert item.answer_key in item.choices
        if item.type in ("choice", "fill"):
            assert item.answer_key is not None


def test_no_duplicate_template_ids_in_paper(builder):
    paper = builder.build(StudentProfile(region="北京", grade=5, age=11), n=20)
    template_ids = [item.id.rsplit("__", 1)[0] for item in paper.items]
    assert len(template_ids) == len(set(template_ids))


def test_fail_closed_when_provider_cannot_fill_blueprint():
    class EmptyProvider(CurriculumProvider):
        @property
        def label(self) -> str:
            return "empty"

        def list_knowledge(self, grade: int) -> list[KnowledgeNode]:
            return []

        def list_templates(self, grade, difficulty=None, item_type=None):
            return []

    builder = AssessmentBuilder(EmptyProvider())
    with pytest.raises(AssessmentBuildError):
        builder.build(StudentProfile(region="北京", grade=5, age=11), n=20)


def test_rejects_non_default_paper_size(builder):
    with pytest.raises(AssessmentBuildError):
        builder.build(StudentProfile(region="北京", grade=5, age=11), n=10)
